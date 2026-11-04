# ruff: noqa: F401, F811  (pytest 픽스처를 test_matches_api에서 가져와 쓴다)
"""팀 분배·경기 진행 API. 실제 MariaDB로 검증하고 항상 롤백한다."""

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.venue import Venue, VenueSport
from tests.test_matches_api import api, login, make_match, session, venue_id


async def fill(
    api: AsyncClient, host: dict[str, str], mid: int, users: list[dict[str, str]], **body: object
) -> None:
    """users 전원이 신청하고 주최자가 모두 수락한다."""
    for u, extra in zip(users, [body] * len(users), strict=True):
        assert (
            await api.post(f"/api/v1/matches/{mid}/apply", json=extra or None, headers=u)
        ).status_code == 201
    for p in (await api.get(f"/api/v1/matches/{mid}/participations", headers=host)).json():
        if p["status"] == "applied":
            res = await api.post(
                f"/api/v1/matches/{mid}/participations/{p['id']}/accept", headers=host
            )
            assert res.status_code == 200, res.text


async def doubles_full(
    api: AsyncClient, venue_id: int
) -> tuple[dict[str, str], list[dict[str, str]], int]:
    host = await login(api, 1)
    users = [await login(api, n) for n in (2, 3, 4)]
    mid = await make_match(api, host, venue_id, team_size=2)  # 정원 4 = 주최자 + 3
    await fill(api, host, mid, users)
    return host, users, mid


async def test_balance_and_view(api: AsyncClient, venue_id: int) -> None:
    host, users, mid = await doubles_full(api, venue_id)
    res = await api.post(f"/api/v1/matches/{mid}/teams/balance", headers=host)
    assert res.status_code == 200, res.text
    body = res.json()
    assert sorted(len(t["members"]) for t in body["teams"]) == [2, 2]
    assert 1 <= body["closeness"] <= 5 and body["is_manual"] is False
    assert all(1 <= m["tier"] <= 5 for t in body["teams"] for m in t["members"])
    assert "rating" not in res.text
    seen = await api.get(f"/api/v1/matches/{mid}/teams", headers=users[0])
    assert seen.status_code == 200 and seen.json() == body


async def test_balance_rules(api: AsyncClient, venue_id: int) -> None:
    host, users, mid = await doubles_full(api, venue_id)
    outsider = await login(api, 9)
    assert (
        await api.post(f"/api/v1/matches/{mid}/teams/balance", headers=users[0])
    ).status_code == 403
    assert (
        await api.get(f"/api/v1/matches/{mid}/teams", headers=host)
    ).status_code == 404  # 아직 안 나눔
    assert (await api.get(f"/api/v1/matches/{mid}/teams", headers=outsider)).status_code == 403
    open_match = await make_match(api, host, venue_id, team_size=2)
    res = await api.post(f"/api/v1/matches/{open_match}/teams/balance", headers=host)
    assert res.status_code == 409 and res.json()["detail"]["code"] == "MATCH_NOT_READY"


async def test_manual_adjustment(api: AsyncClient, venue_id: int) -> None:
    host, users, mid = await doubles_full(api, venue_id)
    parts = (await api.get(f"/api/v1/matches/{mid}/participations", headers=host)).json()
    assert len(parts) == 4
    me = (await api.get("/api/v1/auth/me", headers=host)).json()["id"]
    others = [(await api.get("/api/v1/auth/me", headers=u)).json()["id"] for u in users]
    team = lambda uid, n: {"user_id": uid, "team_no": n}  # noqa: E731
    ok = await api.put(
        f"/api/v1/matches/{mid}/teams",
        json={
            "assignments": [team(me, 1), team(others[0], 1), team(others[1], 2), team(others[2], 2)]
        },
        headers=host,
    )
    assert ok.status_code == 200 and ok.json()["is_manual"] is True
    cases = [
        [team(me, 1), team(others[0], 1), team(others[1], 2)],  # 한 명 빠짐
        [team(me, 1), team(me, 2), team(others[0], 2), team(others[1], 2)],  # 중복
        [team(me, 1), team(others[0], 3), team(others[1], 2), team(others[2], 2)],  # 없는 팀
        [team(me, 1), team(others[0], 1), team(others[1], 1), team(others[2], 1)],  # 빈 팀
        [team(me, 1), team(others[0], 1), team(others[1], 2), team(99999, 2)],  # 참가자 아님
    ]
    for assignments in cases:
        res = await api.put(
            f"/api/v1/matches/{mid}/teams", json={"assignments": assignments}, headers=host
        )
        assert res.status_code == 422, assignments
    denied = await api.put(
        f"/api/v1/matches/{mid}/teams",
        json={
            "assignments": [team(me, 1), team(others[0], 1), team(others[1], 2), team(others[2], 2)]
        },
        headers=users[0],
    )
    assert denied.status_code == 403


async def test_start_and_complete_flow(api: AsyncClient, venue_id: int) -> None:
    host, users, mid = await doubles_full(api, venue_id)
    base = f"/api/v1/matches/{mid}"
    assert (await api.post(f"{base}/start", headers=host)).status_code == 409  # 확정 전
    assert (await api.post(f"{base}/confirm", headers=host)).json() == {"status": "confirmed"}
    assert (await api.post(f"{base}/start", headers=users[0])).status_code == 403
    assert (await api.post(f"{base}/start", headers=host)).json() == {"status": "playing"}
    assert (
        await api.post(f"{base}/cancel", headers=host)
    ).status_code == 409  # 진행 중엔 취소 불가
    assert (await api.post(f"{base}/complete", headers=host)).json() == {"status": "completed"}


async def _futsal_venue(session: AsyncSession) -> int:
    v = Venue(name="풋살장", address="가상 주소", point=(127.0, 37.5))
    session.add(v)
    await session.flush()
    session.add(VenueSport(venue_id=v.id, sport="football"))
    await session.flush()
    return v.id


async def test_futsal_needs_one_goalkeeper_per_team(
    api: AsyncClient, session: AsyncSession
) -> None:
    vid = await _futsal_venue(session)
    host = await login(api, 1)
    mid = await make_match(api, host, vid, sport="football", team_size=5, position="GK")
    users = [await login(api, n) for n in range(2, 11)]
    await fill(api, host, mid, users[:1], position="GK")
    await fill(api, host, mid, users[1:], position="FIELD")
    res = await api.post(f"/api/v1/matches/{mid}/teams/balance", headers=host)
    assert res.status_code == 200, res.text
    gks = [sum(1 for m in t["members"] if m["position"] == "GK") for t in res.json()["teams"]]
    assert gks == [1, 1]


async def test_futsal_without_enough_goalkeepers_is_rejected(
    api: AsyncClient, session: AsyncSession
) -> None:
    vid = await _futsal_venue(session)
    host = await login(api, 1)
    mid = await make_match(
        api, host, vid, sport="football", team_size=5, position="GK"
    )  # GK는 주최자뿐
    users = [await login(api, n) for n in range(2, 11)]
    await fill(api, host, mid, users, position="FIELD")
    res = await api.post(f"/api/v1/matches/{mid}/teams/balance", headers=host)
    assert res.status_code == 409 and res.json()["detail"]["code"] == "TEAM_CONSTRAINT"


async def test_unknown_position_is_rejected(api: AsyncClient, venue_id: int) -> None:
    host, other = await login(api, 1), await login(api, 2)
    bad = await api.post(
        "/api/v1/matches",
        json={
            "sport": "badminton",
            "venue_id": venue_id,
            "title": "x",
            "starts_at": "2099-01-01T10:00:00+00:00",
            "duration_min": 60,
            "team_size": 1,
            "position": "GK",
        },
        headers=host,
    )
    assert bad.status_code == 422
    mid = await make_match(api, host, venue_id)
    res = await api.post(f"/api/v1/matches/{mid}/apply", json={"position": "GK"}, headers=other)
    assert res.status_code == 422 and res.json()["detail"]["code"] == "UNKNOWN_POSITION"
