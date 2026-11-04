"""실제 MariaDB로 매치·신청 흐름을 검증한다. DB에 연결할 수 없으면 건너뛴다. 항상 롤백한다."""

from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.api.v1.matches import apply_limiter
from app.core.config import get_settings
from app.core.db import get_session
from app.core.ratelimit import login_limiter
from app.core.token_store import token_store
from app.main import app
from app.models.venue import Venue, VenueSport


@pytest.fixture
async def session() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine(get_settings().database_url)
    try:
        conn = await engine.connect()
    except Exception:
        await engine.dispose()
        pytest.skip("MariaDB에 연결할 수 없어 건너뜀")
    trans = await conn.begin()
    s = AsyncSession(
        bind=conn, join_transaction_mode="create_savepoint", expire_on_commit=False
    )  # 운영 세션(SessionLocal)과 같게
    try:
        yield s
    finally:
        await s.close()
        await trans.rollback()
        await conn.close()
        await engine.dispose()


@pytest.fixture
async def api(session: AsyncSession) -> AsyncIterator[AsyncClient]:
    async def _session() -> AsyncIterator[AsyncSession]:
        yield session

    app.dependency_overrides[get_session] = _session
    login_limiter.reset()
    apply_limiter.reset()
    token_store.__init__()  # type: ignore[misc]
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
async def venue_id(session: AsyncSession) -> int:
    v = Venue(name="테스트 체육관", address="가상 주소", point=(127.0, 37.5))
    session.add(v)
    await session.flush()
    session.add_all(VenueSport(venue_id=v.id, sport=s) for s in ("badminton", "basketball"))
    await session.flush()
    return v.id


async def login(api: AsyncClient, n: int, gender: str = "male") -> dict[str, str]:
    login_limiter.reset()  # 한 테스트에서 여러 사용자가 로그인하므로 분당 5회 한도를 비운다
    body = {
        "email": f"user{n}@example.com",
        "password": "pw-12345678",
        "nickname": f"user{n}",
        "gender": gender,
        "birth_year": 1999,
    }
    assert (await api.post("/api/v1/auth/signup", json=body)).status_code == 201
    res = await api.post(
        "/api/v1/auth/login", json={"email": body["email"], "password": body["password"]}
    )
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


def match_body(venue_id: int, **over: object) -> dict[str, object]:
    start = (datetime.now(UTC) + timedelta(days=2)).isoformat()
    base: dict[str, object] = {
        "sport": "badminton",
        "venue_id": venue_id,
        "title": "저녁 단식",
        "starts_at": start,
        "duration_min": 90,
        "team_size": 1,  # 단식: 정원 2
    }
    return {**base, **over}


async def make_match(api: AsyncClient, host: dict[str, str], venue_id: int, **over: object) -> int:
    res = await api.post("/api/v1/matches", json=match_body(venue_id, **over), headers=host)
    assert res.status_code == 201, res.text
    return int(res.json()["id"])


async def test_create_computes_capacity_and_rejects_client_capacity(
    api: AsyncClient, venue_id: int
) -> None:
    host = await login(api, 1)
    res = await api.post("/api/v1/matches", json=match_body(venue_id, team_size=2), headers=host)
    assert res.status_code == 201
    assert res.json()["capacity"] == 4
    assert res.json()["joined"] == 1  # 주최자 포함
    assert res.json()["host_nickname"] == "user1"
    forced = await api.post("/api/v1/matches", json=match_body(venue_id, capacity=99), headers=host)
    assert forced.status_code == 422


@pytest.mark.parametrize(
    "over",
    [
        {"team_size": 3},  # 배드민턴은 1 또는 2
        {"sport": "curling"},
        {"starts_at": (datetime.now(UTC) - timedelta(hours=1)).isoformat()},
        {"min_players": 9},
        {"tier_min": 4, "tier_max": 2},
    ],
)
async def test_create_rejects_invalid_input(
    api: AsyncClient, venue_id: int, over: dict[str, object]
) -> None:
    host = await login(api, 1)
    res = await api.post("/api/v1/matches", json=match_body(venue_id, **over), headers=host)
    assert res.status_code == 422


async def test_venue_must_support_sport(api: AsyncClient, venue_id: int) -> None:
    host = await login(api, 1)
    res = await api.post(
        "/api/v1/matches", json=match_body(venue_id, sport="football", team_size=5), headers=host
    )
    assert res.status_code == 422
    assert res.json()["detail"]["code"] == "VENUE_SPORT_MISMATCH"


async def test_full_flow_until_full_and_reopen(api: AsyncClient, venue_id: int) -> None:
    host = await login(api, 1)
    a, b = await login(api, 2), await login(api, 3)
    mid = await make_match(api, host, venue_id)  # 단식, 정원 2 (주최자 포함)
    for who in (a, b):
        assert (await api.post(f"/api/v1/matches/{mid}/apply", headers=who)).status_code == 201
    ids = {
        p["nickname"]: p["id"]
        for p in (await api.get(f"/api/v1/matches/{mid}/participations", headers=host)).json()
    }
    base = f"/api/v1/matches/{mid}/participations"
    assert (await api.post(f"{base}/{ids['user2']}/accept", headers=host)).status_code == 200
    detail = (await api.get(f"/api/v1/matches/{mid}", headers=host)).json()
    assert (detail["joined"], detail["status"]) == (2, "full")
    over = await api.post(f"{base}/{ids['user3']}/accept", headers=host)
    assert over.status_code == 409 and over.json()["detail"]["code"] == "MATCH_FULL"
    late = await api.post(f"/api/v1/matches/{mid}/apply", headers=await login(api, 4))
    assert late.status_code == 409 and late.json()["detail"]["code"] == "MATCH_FULL"
    assert (await api.delete(f"/api/v1/matches/{mid}/apply", headers=a)).status_code == 204
    detail = (await api.get(f"/api/v1/matches/{mid}", headers=host)).json()
    assert (detail["joined"], detail["status"]) == (1, "open")
    assert (await api.post(f"{base}/{ids['user3']}/accept", headers=host)).status_code == 200


async def test_host_cannot_leave_own_match(api: AsyncClient, venue_id: int) -> None:
    host = await login(api, 1)
    mid = await make_match(api, host, venue_id)
    res = await api.delete(f"/api/v1/matches/{mid}/apply", headers=host)
    assert res.status_code == 409 and res.json()["detail"]["code"] == "HOST_CANNOT_LEAVE"


async def test_apply_rules(api: AsyncClient, venue_id: int) -> None:
    host, other = await login(api, 1), await login(api, 2)
    mid = await make_match(api, host, venue_id)
    own = await api.post(f"/api/v1/matches/{mid}/apply", headers=host)
    assert own.status_code == 409 and own.json()["detail"]["code"] == "HOST_CANNOT_APPLY"
    assert (await api.post(f"/api/v1/matches/{mid}/apply", headers=other)).status_code == 201
    dup = await api.post(f"/api/v1/matches/{mid}/apply", headers=other)
    assert dup.status_code == 409 and dup.json()["detail"]["code"] == "ALREADY_APPLIED"
    assert (await api.get(f"/api/v1/matches/{mid}", headers=other)).json()["my_status"] == "applied"
    assert (await api.delete(f"/api/v1/matches/{mid}/apply", headers=other)).status_code == 204
    assert (
        await api.post(f"/api/v1/matches/{mid}/apply", headers=other)
    ).status_code == 201  # 재신청


async def test_gender_policy_blocks_application(api: AsyncClient, venue_id: int) -> None:
    host, man = await login(api, 1), await login(api, 2, "male")
    mid = await make_match(api, host, venue_id, gender_policy="female_only")
    res = await api.post(f"/api/v1/matches/{mid}/apply", headers=man)
    assert res.status_code == 403 and res.json()["detail"]["code"] == "GENDER_POLICY"
    woman = await login(api, 3, "female")
    assert (await api.post(f"/api/v1/matches/{mid}/apply", headers=woman)).status_code == 201


async def test_confirm_needs_min_players_and_cancel(api: AsyncClient, venue_id: int) -> None:
    host, a = await login(api, 1), await login(api, 2)
    mid = await make_match(api, host, venue_id, team_size=2, min_players=3)  # 정원 4
    short = await api.post(f"/api/v1/matches/{mid}/confirm", headers=host)
    assert short.status_code == 409 and short.json()["detail"]["code"] == "NOT_ENOUGH_PLAYERS"
    b = await login(api, 3)
    for who in (a, b):
        await api.post(f"/api/v1/matches/{mid}/apply", headers=who)
    for p in (await api.get(f"/api/v1/matches/{mid}/participations", headers=host)).json():
        if p["status"] == "applied":
            await api.post(f"/api/v1/matches/{mid}/participations/{p['id']}/accept", headers=host)
    assert (await api.post(f"/api/v1/matches/{mid}/confirm", headers=host)).json() == {
        "status": "confirmed"
    }
    assert (await api.post(f"/api/v1/matches/{mid}/cancel", headers=host)).json() == {
        "status": "canceled"
    }
    again = await api.post(f"/api/v1/matches/{mid}/cancel", headers=host)
    assert again.status_code == 409 and again.json()["detail"]["code"] == "INVALID_TRANSITION"


async def test_feed_lists_open_matches_by_sport(api: AsyncClient, venue_id: int) -> None:
    host = await login(api, 1)
    await make_match(api, host, venue_id)
    await make_match(api, host, venue_id, sport="basketball", team_size=3)
    feed = (await api.get("/api/v1/matches", params={"sport": "badminton"}, headers=host)).json()
    assert [m["sport"] for m in feed] == ["badminton"]
    assert (
        await api.get("/api/v1/matches", params={"sport": "curling"}, headers=host)
    ).status_code == 422
