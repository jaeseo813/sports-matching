# ruff: noqa: F401, F811  (pytest 픽스처를 test_matches_api에서 가져와 쓴다)
"""대시보드 활동 요약(/me/summary)과 참가 예정 매치(/me/matches). 실제 MariaDB, 항상 롤백."""

from httpx import AsyncClient

from tests.test_matches_api import api, login, make_match, session, venue_id
from tests.test_reviews_api import finish, start_game


async def test_upcoming_lists_only_accepted_matches_in_start_order(
    api: AsyncClient, venue_id: int
) -> None:
    host, me = await login(api, 1), await login(api, 2)
    later = await make_match(api, host, venue_id, title="나중 매치")
    hosted = await make_match(api, me, venue_id, title="내가 연 매치")  # 주최자는 자동 수락
    applied_only = await make_match(api, host, venue_id, title="신청만 한 매치")
    await api.post(f"/api/v1/matches/{later}/apply", headers=me)
    await api.post(f"/api/v1/matches/{applied_only}/apply", headers=me)
    pid = (await api.get(f"/api/v1/matches/{later}/participations", headers=host)).json()[-1]["id"]
    await api.post(f"/api/v1/matches/{later}/participations/{pid}/accept", headers=host)

    res = await api.get("/api/v1/me/matches", headers=me)
    assert res.status_code == 200
    ids = [m["id"] for m in res.json()]
    assert set(ids) == {later, hosted}  # 승인 대기(applied)는 아직 예정이 아니다
    assert all(m["my_status"] == "accepted" for m in res.json())

    summary = (await api.get("/api/v1/me/summary", headers=me)).json()
    assert summary == {"upcoming": 2, "attended": 0, "manner_score": 3.0}


async def test_canceled_match_is_not_upcoming(api: AsyncClient, venue_id: int) -> None:
    me = await login(api, 1)
    mid = await make_match(api, me, venue_id)
    assert (await api.post(f"/api/v1/matches/{mid}/cancel", headers=me)).status_code == 200
    assert (await api.get("/api/v1/me/matches", headers=me)).json() == []
    assert (await api.get("/api/v1/me/summary", headers=me)).json()["upcoming"] == 0


async def test_attended_counts_after_completed_game(api: AsyncClient, venue_id: int) -> None:
    g = await start_game(api, venue_id)
    await finish(api, g)
    for headers in g.everyone:
        summary = (await api.get("/api/v1/me/summary", headers=headers)).json()
        assert summary["attended"] == 1
        assert summary["upcoming"] == 0
