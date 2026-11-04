from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response

from app.api.deps import CurrentUser, MatchRepo, UserRepo, VenueRepo
from app.core.ratelimit import RateLimiter
from app.models.enums import MatchStatus, ParticipationStatus
from app.schemas.match import MatchCreateIn, MatchOut, ParticipationOut
from app.services import matches as match_service

router = APIRouter(prefix="/matches", tags=["matches"])

apply_limiter = RateLimiter(limit=10, window_seconds=60)  # 매치 신청 10/분


@router.post("", response_model=MatchOut, status_code=201)
async def create_match(
    data: MatchCreateIn, user: CurrentUser, matches: MatchRepo, users: UserRepo, venues: VenueRepo
) -> MatchOut:
    return await match_service.create_match(matches, users, venues, user, data)


@router.get("", response_model=list[MatchOut])
async def list_matches(
    _: CurrentUser,
    matches: MatchRepo,
    users: UserRepo,
    venues: VenueRepo,
    sport: Annotated[str | None, Query(max_length=20)] = None,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
    offset: Annotated[int, Query(ge=0, le=10_000)] = 0,
) -> list[MatchOut]:
    return await match_service.list_matches(
        matches, users, venues, sport=sport, limit=limit, offset=offset
    )


@router.get("/{match_id}", response_model=MatchOut)
async def get_match(
    match_id: int, user: CurrentUser, matches: MatchRepo, users: UserRepo, venues: VenueRepo
) -> MatchOut:
    return await match_service.get_match(matches, users, venues, user, match_id)


@router.post(
    "/{match_id}/apply",
    response_model=dict[str, ParticipationStatus],
    status_code=201,
    dependencies=[Depends(apply_limiter)],
)
async def apply(
    match_id: int, user: CurrentUser, matches: MatchRepo
) -> dict[str, ParticipationStatus]:
    return {"status": await match_service.apply(matches, user, match_id)}


@router.delete("/{match_id}/apply", status_code=204)
async def cancel_application(match_id: int, user: CurrentUser, matches: MatchRepo) -> Response:
    await match_service.cancel_application(matches, user, match_id)
    return Response(status_code=204)


@router.get("/{match_id}/participations", response_model=list[ParticipationOut])
async def list_participations(
    match_id: int, user: CurrentUser, matches: MatchRepo
) -> list[ParticipationOut]:
    return await match_service.list_participations(matches, user, match_id)


@router.post(
    "/{match_id}/participations/{participation_id}/accept",
    response_model=dict[str, ParticipationStatus],
)
async def accept(
    match_id: int, participation_id: int, user: CurrentUser, matches: MatchRepo
) -> dict[str, ParticipationStatus]:
    status = await match_service.decide(matches, user, match_id, participation_id, accept=True)
    return {"status": status}


@router.post(
    "/{match_id}/participations/{participation_id}/reject",
    response_model=dict[str, ParticipationStatus],
)
async def reject(
    match_id: int, participation_id: int, user: CurrentUser, matches: MatchRepo
) -> dict[str, ParticipationStatus]:
    status = await match_service.decide(matches, user, match_id, participation_id, accept=False)
    return {"status": status}


@router.post("/{match_id}/confirm", response_model=dict[str, MatchStatus])
async def confirm(match_id: int, user: CurrentUser, matches: MatchRepo) -> dict[str, MatchStatus]:
    return {"status": await match_service.confirm_match(matches, user, match_id)}


@router.post("/{match_id}/cancel", response_model=dict[str, MatchStatus])
async def cancel(match_id: int, user: CurrentUser, matches: MatchRepo) -> dict[str, MatchStatus]:
    return {"status": await match_service.cancel_match(matches, user, match_id)}
