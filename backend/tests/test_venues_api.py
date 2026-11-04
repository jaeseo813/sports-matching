from collections.abc import AsyncIterator, Iterator

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.deps import get_user_repo, get_venue_repo
from app.core.ratelimit import login_limiter
from app.core.token_store import token_store
from app.main import app
from app.models.enums import Role
from app.repositories.venue import VenueRow
from tests.test_auth_api import SIGNUP, FakeUserRepo

CREATE = {
    "name": "모아 체육관",
    "address": "서울시 가상구 1",
    "lat": 37.5,
    "lng": 127.0,
    "sports": ["badminton"],
}


class FakeVenueRepo:
    def __init__(self) -> None:
        self.rows: dict[int, VenueRow] = {}
        self.last_nearby: dict[str, object] = {}

    async def create(
        self, *, name: str, address: str, lng: float, lat: float, sports: list[str], user_id: int
    ) -> VenueRow:
        row = VenueRow(len(self.rows) + 1, name, address, lng, lat, sports)
        self.rows[row.id] = row
        return row

    async def get(self, venue_id: int) -> VenueRow | None:
        return self.rows.get(venue_id)

    async def nearby(
        self,
        *,
        lat: float,
        lng: float,
        radius_m: float,
        bbox: tuple[float, float, float, float],
        sport: str | None,
    ) -> list[VenueRow]:
        self.last_nearby = {"radius_m": radius_m, "bbox": bbox, "sport": sport}
        return [VenueRow(1, "가까운 곳", "주소", lng, lat, ["badminton"], 2349.0)]


@pytest.fixture
def repos() -> Iterator[tuple[FakeUserRepo, FakeVenueRepo]]:
    users, venues = FakeUserRepo(), FakeVenueRepo()
    app.dependency_overrides[get_user_repo] = lambda: users
    app.dependency_overrides[get_venue_repo] = lambda: venues
    login_limiter.reset()
    token_store.__init__()  # type: ignore[misc]
    yield users, venues
    app.dependency_overrides.clear()


@pytest.fixture
async def api(repos: tuple[FakeUserRepo, FakeVenueRepo]) -> AsyncIterator[AsyncClient]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def _headers(api: AsyncClient, users: FakeUserRepo, *, admin: bool) -> dict[str, str]:
    await api.post("/api/v1/auth/signup", json=SIGNUP)
    if admin:
        users.users[1].role = Role.ADMIN
    res = await api.post(
        "/api/v1/auth/login", json={"email": SIGNUP["email"], "password": SIGNUP["password"]}
    )
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


async def test_admin_creates_and_user_reads(
    api: AsyncClient, repos: tuple[FakeUserRepo, FakeVenueRepo]
) -> None:
    headers = await _headers(api, repos[0], admin=True)
    created = await api.post("/api/v1/venues", json=CREATE, headers=headers)
    assert created.status_code == 201
    assert created.json()["sports"] == ["badminton"]
    got = await api.get("/api/v1/venues/1", headers=headers)
    assert got.status_code == 200
    assert (await api.get("/api/v1/venues/99", headers=headers)).status_code == 404


async def test_nearby_passes_bbox_and_rounds_distance(
    api: AsyncClient, repos: tuple[FakeUserRepo, FakeVenueRepo]
) -> None:
    headers = await _headers(api, repos[0], admin=False)
    res = await api.get(
        "/api/v1/venues/nearby",
        params={"lat": 37.5, "lng": 127.0, "radius_km": 5, "sport": "badminton"},
        headers=headers,
    )
    assert res.status_code == 200
    assert res.json()[0]["distance_km"] == 2.3
    assert repos[1].last_nearby["radius_m"] == 5000
    assert repos[1].last_nearby["sport"] == "badminton"


@pytest.mark.parametrize(
    "params",
    [
        {"lat": 10, "lng": 127.0},  # 국내 범위 밖 위도
        {"lat": 37.5, "lng": 140},  # 국내 범위 밖 경도
        {"lat": 37.5, "lng": 127.0, "radius_km": 500},
        {"lat": 37.5, "lng": 127.0, "sport": "curling"},
    ],
)
async def test_nearby_rejects_bad_input(
    api: AsyncClient, repos: tuple[FakeUserRepo, FakeVenueRepo], params: dict[str, object]
) -> None:
    headers = await _headers(api, repos[0], admin=False)
    res = await api.get("/api/v1/venues/nearby", params=params, headers=headers)
    assert res.status_code == 422
