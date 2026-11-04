from dataclasses import dataclass
from typing import Protocol

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.venue import Venue, VenueSport

NEARBY_CANDIDATE_LIMIT = 200  # 후보 상한 (AGENTS.md 4절)


@dataclass(frozen=True)
class VenueRow:
    id: int
    name: str
    address: str
    lng: float
    lat: float
    sports: list[str]
    distance_m: float | None = None


class VenueRepository(Protocol):
    async def create(
        self, *, name: str, address: str, lng: float, lat: float, sports: list[str], user_id: int
    ) -> VenueRow: ...
    async def get(self, venue_id: int) -> VenueRow | None: ...
    async def nearby(
        self,
        *,
        lat: float,
        lng: float,
        radius_m: float,
        bbox: tuple[float, float, float, float],
        sport: str | None,
    ) -> list[VenueRow]: ...


# 모든 값은 바인드 파라미터. POINT/POLYGON WKT는 (lng lat) 순서, SRID는 4326.
# MBRContains로 SPATIAL INDEX를 태워 후보를 줄인 뒤 ST_Distance_Sphere로 정밀 거리를 계산한다.
_NEARBY = text(
    """
    SELECT v.id, ST_Distance_Sphere(v.point, ST_GeomFromText(:center, 4326)) AS dist
    FROM venues v
    WHERE v.is_active = 1
      AND MBRContains(ST_GeomFromText(:bbox, 4326), v.point)
    HAVING dist <= :radius_m
    ORDER BY dist
    LIMIT :limit
    """
)
_NEARBY_BY_SPORT = text(
    """
    SELECT v.id, ST_Distance_Sphere(v.point, ST_GeomFromText(:center, 4326)) AS dist
    FROM venues v
    WHERE v.is_active = 1
      AND MBRContains(ST_GeomFromText(:bbox, 4326), v.point)
      AND EXISTS (SELECT 1 FROM venue_sports s WHERE s.venue_id = v.id AND s.sport = :sport)
    HAVING dist <= :radius_m
    ORDER BY dist
    LIMIT :limit
    """
)


def _polygon_wkt(box: tuple[float, float, float, float]) -> str:
    min_lng, min_lat, max_lng, max_lat = box
    return (
        f"POLYGON(({min_lng} {min_lat}, {max_lng} {min_lat}, "
        f"{max_lng} {max_lat}, {min_lng} {max_lat}, {min_lng} {min_lat}))"
    )


class SqlVenueRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def _sports_of(self, venue_ids: list[int]) -> dict[int, list[str]]:
        if not venue_ids:
            return {}
        rows = await self._session.execute(
            select(VenueSport.venue_id, VenueSport.sport)
            .where(VenueSport.venue_id.in_(venue_ids))
            .order_by(VenueSport.sport)
        )
        result: dict[int, list[str]] = {}
        for venue_id, sport in rows:
            result.setdefault(venue_id, []).append(sport)
        return result

    async def _load(self, ids: list[int], dist: dict[int, float] | None = None) -> list[VenueRow]:
        if not ids:
            return []
        venues = {
            v.id: v
            for v in (await self._session.execute(select(Venue).where(Venue.id.in_(ids)))).scalars()
        }
        sports = await self._sports_of(ids)
        rows = []
        for venue_id in ids:  # 입력 순서(거리순) 유지
            v = venues[venue_id]
            lng, lat = v.point
            rows.append(
                VenueRow(
                    v.id, v.name, v.address, lng, lat, sports.get(v.id, []),
                    dist[venue_id] if dist else None,
                )
            )  # fmt: skip
        return rows

    async def create(
        self, *, name: str, address: str, lng: float, lat: float, sports: list[str], user_id: int
    ) -> VenueRow:
        venue = Venue(name=name, address=address, point=(lng, lat), created_by=user_id)
        self._session.add(venue)
        await self._session.flush()
        venue_id = venue.id  # 커밋 후 만료된 속성을 읽지 않도록 먼저 꺼내 둔다
        self._session.add_all(VenueSport(venue_id=venue_id, sport=s) for s in sports)
        await self._session.commit()
        return (await self._load([venue_id]))[0]

    async def get(self, venue_id: int) -> VenueRow | None:
        rows = await self._load([venue_id])
        return rows[0] if rows else None

    async def nearby(
        self,
        *,
        lat: float,
        lng: float,
        radius_m: float,
        bbox: tuple[float, float, float, float],
        sport: str | None,
    ) -> list[VenueRow]:
        params: dict[str, object] = {
            "center": f"POINT({lng} {lat})",
            "bbox": _polygon_wkt(bbox),
            "radius_m": radius_m,
            "limit": NEARBY_CANDIDATE_LIMIT,
        }
        if sport is None:
            result = await self._session.execute(_NEARBY, params)
        else:
            result = await self._session.execute(_NEARBY_BY_SPORT, {**params, "sport": sport})
        found = result.all()
        dist = {int(r.id): float(r.dist) for r in found}
        return await self._load(list(dist), dist)
