# ruff: noqa: F401, F811  (pytest 픽스처를 test_matches_api에서 가져와 쓴다)
from httpx import AsyncClient

from tests.test_matches_api import api, login, make_match, session, venue_id
from tests.test_reviews_api import finish, review, start_game


async def test_review_endpoints_require_login(api: AsyncClient) -> None:
    for path in ("reviews", "rate"):
        assert (await api.post(f"/api/v1/matches/1/{path}")).status_code == 401
    assert (await api.put("/api/v1/matches/1/attendance")).status_code == 401


async def test_only_participants_can_review_and_only_participants_can_be_reviewed(
    api: AsyncClient, venue_id: int
) -> None:
    g = await start_game(api, venue_id)
    await finish(api, g)
    outsider = await login(api, 9)
    outsider_id = int((await api.get("/api/v1/auth/me", headers=outsider)).json()["id"])
    denied = await api.post(f"{g.base}/reviews", json=review(g.ids[1], "better"), headers=outsider)
    assert denied.status_code == 403
    ghost = await api.post(
        f"{g.base}/reviews", json=review(outsider_id, "better"), headers=g.users[0]
    )
    assert ghost.status_code == 404  # 참가자가 아닌 사람은 존재 여부도 알려주지 않는다


async def test_review_rules(api: AsyncClient, venue_id: int) -> None:
    g = await start_game(api, venue_id)
    early = await api.post(f"{g.base}/reviews", json=review(g.ids[2], "better"), headers=g.users[0])
    assert early.status_code == 409 and early.json()["detail"]["code"] == "MATCH_NOT_COMPLETED"
    await finish(api, g)
    me = g.ids[1]
    selfie = await api.post(f"{g.base}/reviews", json=review(me, "better"), headers=g.users[0])
    assert selfie.status_code == 422 and selfie.json()["detail"]["code"] == "SELF_REVIEW"
    assert (
        await api.post(f"{g.base}/reviews", json=review(g.ids[2], "better"), headers=g.users[0])
    ).status_code == 204
    dup = await api.post(f"{g.base}/reviews", json=review(g.ids[2], "worse"), headers=g.users[0])
    assert dup.status_code == 409 and dup.json()["detail"]["code"] == "ALREADY_REVIEWED"
    bad = await api.post(
        f"{g.base}/reviews", json={"reviewee_id": g.ids[2], "verdict": "great"}, headers=g.users[1]
    )
    assert bad.status_code == 422


async def test_only_host_can_rate_or_record_attendance(api: AsyncClient, venue_id: int) -> None:
    g = await start_game(api, venue_id)
    for step in ("confirm", "start"):
        await api.post(f"{g.base}/{step}", headers=g.host)
    body = {"attendances": [{"user_id": g.ids[1], "attended": False}]}
    assert (await api.put(f"{g.base}/attendance", json=body, headers=g.users[0])).status_code == 403
    await api.post(f"{g.base}/complete", headers=g.host)
    assert (await api.post(f"{g.base}/rate", headers=g.users[0])).status_code == 403


async def test_cannot_rate_before_completion_or_record_attendance_before_start(
    api: AsyncClient, venue_id: int
) -> None:
    g = await start_game(api, venue_id)
    body = {"attendances": [{"user_id": g.ids[1], "attended": True}]}
    early = await api.put(f"{g.base}/attendance", json=body, headers=g.host)
    assert early.status_code == 409 and early.json()["detail"]["code"] == "MATCH_NOT_STARTED"
    not_done = await api.post(f"{g.base}/rate", headers=g.host)
    assert (
        not_done.status_code == 409 and not_done.json()["detail"]["code"] == "MATCH_NOT_COMPLETED"
    )


async def test_attendance_rejects_unknown_participant(api: AsyncClient, venue_id: int) -> None:
    g = await start_game(api, venue_id)
    for step in ("confirm", "start"):
        await api.post(f"{g.base}/{step}", headers=g.host)
    body = {"attendances": [{"user_id": 999999, "attended": False}]}
    assert (await api.put(f"{g.base}/attendance", json=body, headers=g.host)).status_code == 404
