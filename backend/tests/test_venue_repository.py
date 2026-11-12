"""실제 MariaDB로 공간 쿼리를 검증한다. DB에 연결할 수 없으면 건너뛴다. 트랜잭션은 항상 롤백한다."""

from collections.abc import AsyncIterator

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.core.config import get_settings
from app.models.venue import Venue, VenueSport
from app.repositories.venue import SqlVenueRepository
from app.services.geo import bounding_box

CENTER = (127.0, 37.5)  # (lng, lat)


@pytest.fixture
async def session() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine(get_settings().test_database_url)
    try:
        conn = await engine.connect()
    except Exception:
        await engine.dispose()
        pytest.skip("MariaDB에 연결할 수 없어 건너뜀")
    trans = await conn.begin()
    try:
        # venues 테이블이 비어 있지 않아도 되도록, 이 테스트 데이터만 본다
        await conn.execute(text("DELETE FROM venue_sports"))
        await conn.execute(text("DELETE FROM venues"))
        yield AsyncSession(bind=conn)
    finally:
        await trans.rollback()
        await conn.close()
        await engine.dispose()


async def _add(s: AsyncSession, name: str, lng: float, lat: float, sports: list[str]) -> int:
    v = Venue(name=name, address="가상 주소", point=(lng, lat))
    s.add(v)
    await s.flush()
    s.add_all(VenueSport(venue_id=v.id, sport=sp) for sp in sports)
    await s.flush()
    return v.id


async def test_nearby_filters_sorts_and_limits_by_distance(session: AsyncSession) -> None:
    near = await _add(session, "가까움", 127.01, 37.5, ["badminton"])  # 약 0.9km
    mid = await _add(session, "중간", 127.05, 37.5, ["badminton", "basketball"])  # 약 4.4km
    await _add(session, "멈", 127.5, 37.5, ["badminton"])  # 약 44km
    repo = SqlVenueRepository(session)
    rows = await repo.nearby(
        lat=CENTER[1],
        lng=CENTER[0],
        radius_m=10_000,
        bbox=bounding_box(37.5, 127.0, 10),
        sport=None,
    )
    assert [r.id for r in rows] == [near, mid]
    assert rows[0].distance_m is not None and 800 < rows[0].distance_m < 1000
    assert rows[1].sports == ["badminton", "basketball"]


async def test_nearby_filters_by_sport(session: AsyncSession) -> None:
    await _add(session, "배드민턴", 127.01, 37.5, ["badminton"])
    bb = await _add(session, "농구", 127.02, 37.5, ["basketball"])
    rows = await SqlVenueRepository(session).nearby(
        lat=CENTER[1],
        lng=CENTER[0],
        radius_m=10_000,
        bbox=bounding_box(37.5, 127.0, 10),
        sport="basketball",
    )
    assert [r.id for r in rows] == [bb]


async def test_box_corner_outside_circle_is_cut_by_precise_distance(session: AsyncSession) -> None:
    # 박스 모서리 근처(약 1.4배 거리)는 박스에는 들어와도 원 밖이라 정밀 필터가 걸러야 한다
    await _add(session, "모서리", 127.0 + 0.1, 37.5 + 0.09, ["badminton"])
    rows = await SqlVenueRepository(session).nearby(
        lat=CENTER[1],
        lng=CENTER[0],
        radius_m=10_000,
        bbox=bounding_box(37.5, 127.0, 10),
        sport=None,
    )
    assert rows == []


async def test_inactive_venue_is_excluded(session: AsyncSession) -> None:
    vid = await _add(session, "폐업", 127.01, 37.5, ["badminton"])
    await session.execute(text("UPDATE venues SET is_active = 0 WHERE id = :i"), {"i": vid})
    rows = await SqlVenueRepository(session).nearby(
        lat=CENTER[1],
        lng=CENTER[0],
        radius_m=10_000,
        bbox=bounding_box(37.5, 127.0, 10),
        sport=None,
    )
    assert rows == []


async def test_create_and_get_roundtrip(session: AsyncSession) -> None:
    repo = SqlVenueRepository(session)
    row = await repo.create(
        name="새 구장",
        address="가상 주소",
        lng=127.0,
        lat=37.5,
        sports=["badminton"],
        user_id=None,  # type: ignore[arg-type]
    )
    got = await repo.get(row.id)
    assert got is not None and (got.lng, got.lat) == (127.0, 37.5)  # (lng, lat) 순서 보존
