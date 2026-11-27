# ruff: noqa: F401, F811  (pytest 픽스처를 test_matches_api에서 가져와 쓴다)
"""매칭 알림(수락·확정), 매치에서 주최자 차단, 관리자 구장 등록."""

from httpx import AsyncClient
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import Role
from app.models.user import User
from tests.test_matches_api import api, login, make_match, session, venue_id

ME = "/api/v1/me/notifications"


async def notes(api: AsyncClient, headers: dict[str, str]) -> list[tuple[str, int, bool]]:
    data = (await api.get(ME, headers=headers)).json()
    return [(n["kind"], n["match_id"], n["read"]) for n in data["items"]]


async def apply_and_decide(
    api: AsyncClient, host: dict[str, str], who: dict[str, str], mid: int, action: str
) -> None:
    await api.post(f"/api/v1/matches/{mid}/apply", headers=who)
    parts = (await api.get(f"/api/v1/matches/{mid}/participations", headers=host)).json()
    pid = next(p["id"] for p in parts if p["status"] == "applied")
    res = await api.post(f"/api/v1/matches/{mid}/participations/{pid}/{action}", headers=host)
    assert res.status_code == 200


async def test_apply_accept_confirm(api: AsyncClient, venue_id: int) -> None:
    host, me, other = await login(api, 1), await login(api, 2), await login(api, 3)
    mid = await make_match(api, host, venue_id)
    await apply_and_decide(api, host, me, mid, "accept")
    assert await notes(api, host) == [("applied", mid, False)]  # 새 신청은 주최자에게
    assert await notes(api, me) == [("accepted", mid, False)]
    assert (await api.post(f"/api/v1/matches/{mid}/confirm", headers=host)).status_code == 200
    assert await notes(api, me) == [("confirmed", mid, False), ("accepted", mid, False)]
    assert await notes(api, host) == [("applied", mid, False)]  # 확정한 본인에게는 안 간다
    assert await notes(api, other) == []


async def test_reject_notifies_applicant(api: AsyncClient, venue_id: int) -> None:
    host, me = await login(api, 1), await login(api, 2)
    mid = await make_match(api, host, venue_id)
    await apply_and_decide(api, host, me, mid, "reject")
    assert await notes(api, me) == [("rejected", mid, False)]


async def test_cancel_notifies_accepted_and_waiting_only(api: AsyncClient, venue_id: int) -> None:
    host, joined = await login(api, 1), await login(api, 2)
    waiting, left = await login(api, 3), await login(api, 4)
    mid = await make_match(api, host, venue_id, team_size=2)
    await apply_and_decide(api, host, joined, mid, "accept")
    await api.post(f"/api/v1/matches/{mid}/apply", headers=waiting)  # 아직 답을 못 받음
    await api.post(f"/api/v1/matches/{mid}/apply", headers=left)
    await api.delete(f"/api/v1/matches/{mid}/apply", headers=left)  # 스스로 취소함
    assert (await api.post(f"/api/v1/matches/{mid}/cancel", headers=host)).status_code == 200
    assert (await notes(api, joined))[0] == ("canceled", mid, False)
    assert (await notes(api, waiting))[0] == ("canceled", mid, False)
    assert await notes(api, left) == []
    assert all(kind == "applied" for kind, _, _ in await notes(api, host))


async def test_read_marks_only_mine(api: AsyncClient, venue_id: int) -> None:
    host, a, b = await login(api, 1), await login(api, 2), await login(api, 3)
    mid = await make_match(api, host, venue_id, team_size=2)
    for who in (a, b):
        await apply_and_decide(api, host, who, mid, "accept")
    assert (await api.post(f"{ME}/read", headers=a)).status_code == 204
    assert (await api.get(ME, headers=a)).json()["unread"] == 0
    assert (await api.get(ME, headers=b)).json()["unread"] == 1  # 남의 알림은 그대로


async def test_notifications_require_login(api: AsyncClient) -> None:
    assert (await api.get(ME)).status_code == 401
    assert (await api.post(f"{ME}/read")).status_code == 401
    assert (await api.put("/api/v1/matches/1/host-block")).status_code == 401


async def test_block_host_hides_matches_from_list(api: AsyncClient, venue_id: int) -> None:
    host, me, other = await login(api, 1), await login(api, 2), await login(api, 3)
    mid = await make_match(api, host, venue_id)

    async def listed(headers: dict[str, str]) -> bool:
        found = (await api.get("/api/v1/matches?limit=50", headers=headers)).json()
        return mid in [m["id"] for m in found]

    assert await listed(me)
    res = await api.put(f"/api/v1/matches/{mid}/host-block", headers=me)
    assert res.status_code == 204 and res.content == b""  # 주최자 id를 돌려주지 않는다
    assert not await listed(me)
    assert await listed(other) and await listed(host)  # 다른 사람에게는 그대로 보인다
    blocked = (await api.get("/api/v1/me/blocks", headers=me)).json()
    assert [b["nickname"] for b in blocked] == ["user1"]
    await api.delete(f"/api/v1/me/blocks/{blocked[0]['user_id']}", headers=me)
    assert await listed(me)


async def test_block_host_errors(api: AsyncClient, venue_id: int) -> None:
    host = await login(api, 1)
    mid = await make_match(api, host, venue_id)
    assert (await api.put(f"/api/v1/matches/{mid}/host-block", headers=host)).status_code == 422
    assert (await api.put("/api/v1/matches/999999/host-block", headers=host)).status_code == 404


async def test_only_admin_sees_flag_and_creates_venue(
    api: AsyncClient, session: AsyncSession
) -> None:
    user = await login(api, 1)
    body = {"name": "새 구장", "address": "가상 주소", "lat": 37.5, "lng": 127.0}
    body["sports"] = ["football"]  # type: ignore[assignment]
    assert (await api.get("/api/v1/auth/me", headers=user)).json()["is_admin"] is False
    assert (await api.post("/api/v1/venues", json=body, headers=user)).status_code == 403
    await session.execute(
        update(User).where(User.email == "user1@example.com").values(role=Role.ADMIN)
    )
    assert (await api.get("/api/v1/auth/me", headers=user)).json()["is_admin"] is True
    assert (await api.post("/api/v1/venues", json=body, headers=user)).status_code == 201
