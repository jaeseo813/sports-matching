from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response

from app.api.deps import (
    CurrentUser,
    MatchRepo,
    ProfileRepo,
    RecommendRepo,
    ReviewRepo,
    TeamRepo,
    UserRepo,
    VenueRepo,
)
from app.core.ratelimit import RateLimiter
from app.models.enums import MatchStatus, ParticipationStatus
from app.schemas.match import (
    ApplyIn,
    AttendanceIn,
    ManualTeamsIn,
    MatchCreateIn,
    MatchOut,
    ParticipationOut,
    RateOut,
    RecommendedOut,
    ReviewIn,
    TeamsOut,
)
from app.services import matches as match_service
from app.services import recommend as recommend_service
from app.services import reviews as review_service
from app.services import teams as team_service

router = APIRouter(prefix="/matches", tags=["matches"])

apply_limiter = RateLimiter(limit=10, window_seconds=60)  # 매치 신청 10/분


@router.post("", response_model=MatchOut, status_code=201)
async def create_match(
    data: MatchCreateIn, user: CurrentUser, matches: MatchRepo, users: UserRepo, venues: VenueRepo
) -> MatchOut:
    return await match_service.create_match(matches, users, venues, user, data)


@router.get("", response_model=list[MatchOut])
async def list_matches(
    user: CurrentUser,
    matches: MatchRepo,
    users: UserRepo,
    venues: VenueRepo,
    sport: Annotated[str | None, Query(max_length=20)] = None,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
    offset: Annotated[int, Query(ge=0, le=10_000)] = 0,
) -> list[MatchOut]:
    return await match_service.list_matches(
        matches, users, venues, sport=sport, limit=limit, offset=offset, viewer_id=user.id
    )


@router.get("/recommended", response_model=list[RecommendedOut])
async def recommended(
    user: CurrentUser,
    profiles: ProfileRepo,
    recs: RecommendRepo,
    matches: MatchRepo,
    users: UserRepo,
    venues: VenueRepo,
    sport: Annotated[str, Query(max_length=20)],
    distance_priority: Annotated[float | None, Query(ge=0, le=1)] = None,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
) -> list[RecommendedOut]:
    return await recommend_service.recommend(
        user=user,
        sport=sport,
        distance_priority=distance_priority,
        limit=limit,
        profiles=profiles,
        recs=recs,
        matches=matches,
        users=users,
        venues=venues,
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
    match_id: int, user: CurrentUser, matches: MatchRepo, body: ApplyIn | None = None
) -> dict[str, ParticipationStatus]:
    position = body.position if body else None
    return {"status": await match_service.apply(matches, user, match_id, position)}


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


@router.post("/{match_id}/start", response_model=dict[str, MatchStatus])
async def start(match_id: int, user: CurrentUser, matches: MatchRepo) -> dict[str, MatchStatus]:
    return {"status": await match_service.start_match(matches, user, match_id)}


@router.post("/{match_id}/complete", response_model=dict[str, MatchStatus])
async def complete(match_id: int, user: CurrentUser, matches: MatchRepo) -> dict[str, MatchStatus]:
    return {"status": await match_service.complete_match(matches, user, match_id)}


@router.post("/{match_id}/teams/balance", response_model=TeamsOut)
async def balance_teams(
    match_id: int, user: CurrentUser, matches: MatchRepo, teams: TeamRepo
) -> TeamsOut:
    return await team_service.auto_balance(matches, teams, user, match_id)


@router.get("/{match_id}/teams", response_model=TeamsOut)
async def get_teams(
    match_id: int, user: CurrentUser, matches: MatchRepo, teams: TeamRepo
) -> TeamsOut:
    return await team_service.get_teams(matches, teams, user, match_id)


@router.put("/{match_id}/teams", response_model=TeamsOut)
async def set_teams(
    match_id: int, data: ManualTeamsIn, user: CurrentUser, matches: MatchRepo, teams: TeamRepo
) -> TeamsOut:
    return await team_service.set_manual(matches, teams, user, match_id, data)


@router.put("/{match_id}/attendance", status_code=204)
async def set_attendance(
    match_id: int, data: AttendanceIn, user: CurrentUser, matches: MatchRepo, reviews: ReviewRepo
) -> Response:
    await review_service.set_attendance(matches, reviews, user, match_id, data)
    return Response(status_code=204)


@router.post("/{match_id}/reviews", status_code=204)
async def submit_review(
    match_id: int, data: ReviewIn, user: CurrentUser, matches: MatchRepo, reviews: ReviewRepo
) -> Response:
    await review_service.submit_review(matches, reviews, user, match_id, data)
    return Response(status_code=204)


@router.post("/{match_id}/rate", response_model=RateOut)
async def rate(
    match_id: int, user: CurrentUser, matches: MatchRepo, reviews: ReviewRepo
) -> RateOut:
    return await review_service.apply_ratings(matches, reviews, user, match_id)
