from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.deps import CurrentUser, VenueRepo, require_admin
from app.models.user import User
from app.schemas.venue import Lat, Lng, VenueCreateIn, VenueOut
from app.services import venues as venue_service

router = APIRouter(prefix="/venues", tags=["venues"])


@router.get("/nearby", response_model=list[VenueOut])
async def nearby(
    _: CurrentUser,
    repo: VenueRepo,
    lat: Annotated[Lat, Query()],
    lng: Annotated[Lng, Query()],
    radius_km: Annotated[float, Query(ge=1, le=50)] = 10,
    sport: Annotated[str | None, Query(max_length=20)] = None,
) -> list[VenueOut]:
    return await venue_service.nearby_venues(
        repo, lat=lat, lng=lng, radius_km=radius_km, sport=sport
    )


@router.get("/{venue_id}", response_model=VenueOut)
async def get_venue(venue_id: int, _: CurrentUser, repo: VenueRepo) -> VenueOut:
    return await venue_service.get_venue(repo, venue_id)


@router.post("", response_model=VenueOut, status_code=201)
async def create_venue(
    data: VenueCreateIn, admin: Annotated[User, Depends(require_admin)], repo: VenueRepo
) -> VenueOut:
    return await venue_service.create_venue(repo, data, admin.id)
