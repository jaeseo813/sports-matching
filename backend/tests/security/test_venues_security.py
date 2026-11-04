# ruff: noqa: F401, F811  (pytest 픽스처를 test_venues_api에서 가져와 쓴다)
from httpx import AsyncClient

from tests.test_auth_api import FakeUserRepo
from tests.test_venues_api import CREATE, FakeVenueRepo, _headers, api, repos


async def test_venue_endpoints_require_login(api: AsyncClient) -> None:
    assert (
        await api.get("/api/v1/venues/nearby", params={"lat": 37.5, "lng": 127.0})
    ).status_code == 401
    assert (await api.get("/api/v1/venues/1")).status_code == 401
    assert (await api.post("/api/v1/venues", json=CREATE)).status_code == 401


async def test_normal_user_cannot_create_venue(
    api: AsyncClient, repos: tuple[FakeUserRepo, FakeVenueRepo]
) -> None:
    headers = await _headers(api, repos[0], admin=False)
    res = await api.post("/api/v1/venues", json=CREATE, headers=headers)
    assert res.status_code == 403
    assert repos[1].rows == {}


async def test_create_rejects_unknown_sport_and_extra_fields(
    api: AsyncClient, repos: tuple[FakeUserRepo, FakeVenueRepo]
) -> None:
    headers = await _headers(api, repos[0], admin=True)
    bad_sport = await api.post(
        "/api/v1/venues", json={**CREATE, "sports": ["curling"]}, headers=headers
    )
    assert bad_sport.status_code == 422
    extra = await api.post("/api/v1/venues", json={**CREATE, "is_active": False}, headers=headers)
    assert extra.status_code == 422


async def test_sql_injection_text_in_sport_is_rejected(
    api: AsyncClient, repos: tuple[FakeUserRepo, FakeVenueRepo]
) -> None:
    headers = await _headers(api, repos[0], admin=False)
    res = await api.get(
        "/api/v1/venues/nearby",
        params={"lat": 37.5, "lng": 127.0, "sport": "x' OR '1'='1"},
        headers=headers,
    )
    assert res.status_code == 422
