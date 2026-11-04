from fastapi import HTTPException

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
