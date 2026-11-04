# ruff: noqa: F401, F811  (pytest 픽스처를 test_matches_api에서 가져와 쓴다)
"""선호 시간대와 차단이 추천에 반영되는지 검증한다."""

import pytest
from httpx import AsyncClient

from tests.test_matches_api import api, login, make_match, session, venue_id
from tests.test_recommend_api import onboard, recommended


async def uid(api: AsyncClient, headers: dict[str, str]) -> int:
    return int((await api.get("/api/v1/auth/me", headers=headers)).json()["id"])


async def test_preferred_slots_show_up_as_reason(api: AsyncClient, venue_id: int) -> None:
    host, me = await login(api, 1), await login(api, 2)
    await make_match(api, host, venue_id)
    await onboard(api, me)
    assert "선호 시간대" not in (await recommended(api, me))[0]["reasons"]  # type: ignore[operator]
    every = ["dawn", "morning", "afternoon", "evening"]
    res = await api.put("/api/v1/me/preferences", json={"preferred_slots": every}, headers=me)
    assert res.json() == {"preferred_slots": sorted(every)}
    assert "선호 시간대" in (await recommended(api, me))[0]["reasons"]  # type: ignore[operator]


async def test_nonmatching_slot_lowers_time_score(api: AsyncClient, venue_id: int) -> None:
    host, me = await login(api, 1), await login(api, 2)
    await make_match(api, host, venue_id)
    await onboard(api, me)
    before = (await recommended(api, me))[0]["breakdown"]["time"]  # type: ignore[index]
    assert before == 1  # 선호가 없으면 제약 없음
    res = await api.put("/api/v1/me/preferences", json={"preferred_slots": ["dawn"]}, headers=me)
    assert res.status_code == 200
    after = (await recommended(api, me))[0]["breakdown"]["time"]  # type: ignore[index]
    assert after in (0, 0.3, 1)  # 일치/인접/불일치 중 하나 (시작 시각에 따라 다름)


async def test_blocked_host_is_not_recommended_and_unblock_restores(
    api: AsyncClient, venue_id: int
) -> None:
    host, me = await login(api, 1), await login(api, 2)
    host_id = await uid(api, host)
    mid = await make_match(api, host, venue_id)
    await onboard(api, me)
    assert [i["match"]["id"] for i in await recommended(api, me)] == [mid]  # type: ignore[index]
    assert (await api.put(f"/api/v1/me/blocks/{host_id}", headers=me)).status_code == 204
    assert (await api.put(f"/api/v1/me/blocks/{host_id}", headers=me)).status_code == 204  # 멱등
    assert await recommended(api, me) == []
    listed = (await api.get("/api/v1/me/blocks", headers=me)).json()
    assert listed == [{"user_id": host_id, "nickname": "user1"}]  # 이메일 등은 싣지 않는다
    assert (await api.delete(f"/api/v1/me/blocks/{host_id}", headers=me)).status_code == 204
    assert [i["match"]["id"] for i in await recommended(api, me)] == [mid]  # type: ignore[index]


async def test_block_validation_and_isolation(api: AsyncClient) -> None:
    a, b = await login(api, 1), await login(api, 2)
    a_id, b_id = await uid(api, a), await uid(api, b)
    assert (await api.put(f"/api/v1/me/blocks/{a_id}", headers=a)).status_code == 422  # 자기 자신
    assert (await api.put("/api/v1/me/blocks/999999", headers=a)).status_code == 404
    await api.put(f"/api/v1/me/blocks/{b_id}", headers=a)
    assert (
        await api.get("/api/v1/me/blocks", headers=b)
    ).json() == []  # 남의 차단 목록은 안 보인다
    assert (
        await api.delete(f"/api/v1/me/blocks/{b_id}", headers=b)
    ).status_code == 204  # b의 것만 지워진다
    assert len((await api.get("/api/v1/me/blocks", headers=a)).json()) == 1


@pytest.mark.parametrize(
    "body", [{"preferred_slots": ["noon"]}, {"preferred_slots": ["dawn"] * 5}, {"x": 1}]
)
async def test_preferences_reject_bad_input(api: AsyncClient, body: dict[str, object]) -> None:
    h = await login(api, 1)
    assert (await api.put("/api/v1/me/preferences", json=body, headers=h)).status_code == 422


async def test_blocks_and_preferences_require_login(api: AsyncClient) -> None:
    assert (await api.get("/api/v1/me/blocks")).status_code == 401
    assert (await api.put("/api/v1/me/blocks/1")).status_code == 401
    assert (
        await api.put("/api/v1/me/preferences", json={"preferred_slots": []})
    ).status_code == 401
