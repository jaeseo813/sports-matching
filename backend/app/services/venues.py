from fastapi import HTTPException

from app.repositories.profile import ProfileRepository
from app.repositories.venue import VenueRepository, VenueRow
from app.schemas.venue import VenueCreateIn, VenueOut
from app.services.geo import bounding_box
from app.sports.registry import SPORTS


def _error(status: int, code: str, message: str) -> HTTPException:
    return HTTPException(status_code=status, detail={"code": code, "message": message})


def check_sport(sport: str) -> str:
    if sport not in SPORTS:
        raise _error(422, "UNKNOWN_SPORT", "지원하지 않는 종목입니다")
    return sport


def to_out(row: VenueRow) -> VenueOut:
    return VenueOut(
        id=row.id,
        name=row.name,
        address=row.address,
        lat=row.lat,
        lng=row.lng,
        sports=row.sports,
        distance_km=None if row.distance_m is None else round(row.distance_m / 1000, 1),
    )


async def create_venue(repo: VenueRepository, data: VenueCreateIn, user_id: int) -> VenueOut:
    sports = sorted({check_sport(s) for s in data.sports})
    row = await repo.create(
        name=data.name,
        address=data.address,
        lng=data.lng,
        lat=data.lat,
        sports=sports,
        user_id=user_id,
    )
    return to_out(row)


async def get_venue(repo: VenueRepository, venue_id: int) -> VenueOut:
    row = await repo.get(venue_id)
    if row is None:
        raise _error(404, "VENUE_NOT_FOUND", "구장을 찾을 수 없습니다")
    return to_out(row)


async def nearby_venues(
    repo: VenueRepository, *, lat: float, lng: float, radius_km: float, sport: str | None
) -> list[VenueOut]:
    if sport is not None:
        check_sport(sport)
    rows = await repo.nearby(
        lat=lat,
        lng=lng,
        radius_m=radius_km * 1000,
        bbox=bounding_box(lat, lng, radius_km),
        sport=sport,
    )
    return [to_out(r) for r in rows]


async def venues_near_me(
    profiles: ProfileRepository, repo: VenueRepository, user_id: int, *, sport: str | None
) -> list[VenueOut]:
    """등록한 활동 기준점 주변 구장. 좌표는 서버에서만 쓰고 클라이언트에서 받지 않는다."""
    if sport is not None:
        check_sport(sport)
    locations = await profiles.list_locations(user_id)
    if not locations:
        raise _error(409, "LOCATION_NOT_SET", "먼저 활동 기준점을 등록해 주세요")
    best: dict[int, VenueRow] = {}
    for loc in locations:
        lng, lat = loc.point  # POINT(lng, lat)
        radius_km = float(loc.max_distance_km)
        for row in await repo.nearby(
            lat=lat,
            lng=lng,
            radius_m=radius_km * 1000,
            bbox=bounding_box(lat, lng, radius_km),
            sport=sport,
        ):
            prev = best.get(row.id)
            if prev is None or (row.distance_m or 0) < (prev.distance_m or 0):
                best[row.id] = row  # 기준점이 여러 개면 가장 가까운 거리로
    return [to_out(r) for r in sorted(best.values(), key=lambda r: (r.distance_m or 0, r.id))]
