# ruff: noqa: F401, F811  (pytest 픽스처를 test_matches_api에서 가져와 쓴다)
"""온보딩(실력·기준점)과 추천 API. 실제 MariaDB로 검증하고 항상 롤백한다."""

from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import UserSkill
from tests.test_matches_api import api, login, make_match, session, venue_id

SKILL = {"self_tier": 3, "years_played": 2}
HOME = {"label": "집", "lat": 37.5, "lng": 127.0, "max_distance_km": 10}  # 구장과 같은 위치


async def onboard(
    api: AsyncClient, headers: dict[str, str], *, location: dict[str, object] | None = HOME
) -> None:
    assert (
        await api.put("/api/v1/me/skills/badminton", json=SKILL, headers=headers)
    ).status_code == 200
    if location is not None:
        assert (
            await api.put("/api/v1/me/locations/1", json=location, headers=headers)
        ).status_code == 200


async def recommended(
    api: AsyncClient, headers: dict[str, str], **params: object
) -> list[dict[str, object]]:
    res = await api.get(
        "/api/v1/matches/recommended", params={"sport": "badminton", **params}, headers=headers
    )
    assert res.status_code == 200, res.text
    body: list[dict[str, object]] = res.json()
    return body


async def test_onboarding_hides_rating_and_coordinates(api: AsyncClient) -> None:
    h = await login(api, 1)
    skill = await api.put("/api/v1/me/skills/badminton", json=SKILL, headers=h)
    assert skill.json() == {
        "sport": "badminton",
        "tier": 3,
        "years_played": 2,
        "positions": None,
        "trend": "same",
    }
    assert "rating" not in skill.text
    loc = await api.put("/api/v1/me/locations/1", json=HOME, headers=h)
    assert loc.json() == {"slot": 1, "label": "집", "max_distance_km": 10}
    assert "37.5" not in loc.text and "127" not in loc.text
    listed = await api.get("/api/v1/me/locations", headers=h)
    assert "37.5" not in listed.text


async def test_changing_self_assessment_keeps_learned_rating(
    api: AsyncClient, session: AsyncSession
) -> None:
    h = await login(api, 1)
    await api.put("/api/v1/me/skills/badminton", json=SKILL, headers=h)
    row = (await session.execute(select(UserSkill))).scalar_one()
    row.rating = 1555.0  # 경기를 하며 올라간 값
    await session.flush()
    await api.put(
        "/api/v1/me/skills/badminton", json={"self_tier": 1, "years_played": 0}, headers=h
    )
    assert (await session.execute(select(UserSkill.rating))).scalar_one() == 1555.0


@pytest.mark.parametrize(
    ("path", "body"),
    [
        ("/api/v1/me/skills/curling", SKILL),
        ("/api/v1/me/skills/badminton", {**SKILL, "positions": ["GK"]}),  # 배드민턴엔 포지션이 없다
        ("/api/v1/me/skills/badminton", {"self_tier": 6, "years_played": 0}),
        ("/api/v1/me/locations/3", HOME),
        ("/api/v1/me/locations/1", {**HOME, "lat": 10}),  # 국내 범위 밖
        ("/api/v1/me/locations/1", {**HOME, "max_distance_km": 99}),
    ],
)
async def test_onboarding_rejects_bad_input(
    api: AsyncClient, path: str, body: dict[str, object]
) -> None:
    h = await login(api, 1)
    assert (await api.put(path, json=body, headers=h)).status_code == 422


async def test_recommended_needs_onboarding(api: AsyncClient) -> None:
    h = await login(api, 1)
    res = await api.get("/api/v1/matches/recommended", params={"sport": "badminton"}, headers=h)
    assert res.status_code == 409 and res.json()["detail"]["code"] == "SKILL_NOT_SET"
    await api.put("/api/v1/me/skills/badminton", json=SKILL, headers=h)
    res = await api.get("/api/v1/matches/recommended", params={"sport": "badminton"}, headers=h)
    assert res.status_code == 409 and res.json()["detail"]["code"] == "LOCATION_NOT_SET"


async def test_recommendation_has_score_breakdown_and_reasons(
    api: AsyncClient, venue_id: int
) -> None:
    host, me = await login(api, 1), await login(api, 2)
    mid = await make_match(api, host, venue_id)
    await onboard(api, me)
    items = await recommended(api, me)
    assert [i["match"]["id"] for i in items] == [mid]  # type: ignore[index]
    item = items[0]
    assert 0 < item["score"] <= 1  # type: ignore[operator]
    assert set(item["breakdown"]) == {"dist", "skill", "time", "host", "fill"}  # type: ignore[call-overload]
    assert "집에서 약 1km" in item["reasons"]  # type: ignore[operator]
    assert "rating" not in str(item)


async def test_excluded_when_applied_or_own_or_too_soon_or_far(
    api: AsyncClient, venue_id: int
) -> None:
    host, me, far = await login(api, 1), await login(api, 2), await login(api, 3)
    mid = await make_match(api, host, venue_id)
    soon = (datetime.now(UTC) + timedelta(hours=1)).isoformat()
    await make_match(api, host, venue_id, starts_at=soon)  # 2시간 이내 시작
    await onboard(api, me)
    await onboard(api, host)
    await onboard(api, far, location={**HOME, "label": "부산", "lat": 35.1, "lng": 129.0})
    assert [i["match"]["id"] for i in await recommended(api, me)] == [mid]  # type: ignore[index]
    assert await recommended(api, host) == []  # 내가 연 매치는 제외
    assert await recommended(api, far) == []  # 반경 밖
    await api.post(f"/api/v1/matches/{mid}/apply", headers=me)
    assert await recommended(api, me) == []  # 이미 신청한 매치는 제외
    await api.delete(f"/api/v1/matches/{mid}/apply", headers=me)
    assert [i["match"]["id"] for i in await recommended(api, me)] == [mid]  # 취소하면 다시 후보


async def test_tier_range_outside_user_scores_zero_skill(api: AsyncClient, venue_id: int) -> None:
    host, me = await login(api, 1), await login(api, 2)
    await make_match(api, host, venue_id, tier_min=5, tier_max=5)
    await onboard(api, me)  # 티어 3
    item = (await recommended(api, me))[0]
    assert item["breakdown"]["skill"] == 0  # type: ignore[index]  # 하드 필터가 아니라 점수 0


async def test_distance_priority_bounds(api: AsyncClient) -> None:
    h = await login(api, 1)
    await onboard(api, h)
    res = await api.get(
        "/api/v1/matches/recommended",
        params={"sport": "badminton", "distance_priority": 2},
        headers=h,
    )
    assert res.status_code == 422
    res = await api.get("/api/v1/matches/recommended", params={"sport": "curling"}, headers=h)
    assert res.status_code == 422
    assert (await recommended(api, h, distance_priority=1)) == []


async def test_recommended_requires_login(api: AsyncClient) -> None:
    assert (
        await api.get("/api/v1/matches/recommended", params={"sport": "badminton"})
    ).status_code == 401
    assert (await api.put("/api/v1/me/skills/badminton", json=SKILL)).status_code == 401
    assert (await api.put("/api/v1/me/locations/1", json=HOME)).status_code == 401


async def test_users_cannot_see_or_delete_each_others_locations(api: AsyncClient) -> None:
    a, b = await login(api, 1), await login(api, 2)
    await onboard(api, a)
    assert (await api.get("/api/v1/me/locations", headers=b)).json() == []
    assert (
        await api.delete("/api/v1/me/locations/1", headers=b)
    ).status_code == 204  # b의 1번만 지워진다
    assert len((await api.get("/api/v1/me/locations", headers=a)).json()) == 1
