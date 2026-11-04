from datetime import UTC, datetime, timedelta

from fastapi import HTTPException

from app.models.enums import ParticipationStatus
from app.models.user import User
from app.repositories.match import MatchRepository
from app.repositories.profile import ProfileRepository
from app.repositories.recommend import RecommendRepository
from app.repositories.user import UserRepository
from app.repositories.venue import VenueRepository
from app.schemas.match import BreakdownOut, RecommendedOut
from app.services.geo import bounding_box
from app.services.matches import to_match_out
from app.services.matching import (
    MIN_LEAD_TIME,
    Candidate,
    UserContext,
    Weights,
    rank,
    weights_for_slider,
)
from app.sports.registry import SPORTS

_FAR_KM = 1e9  # 반경 밖 기준점은 아주 먼 것으로 취급해 S_dist가 0이 되게 한다
MAX_RESULTS = 50


def _error(status: int, code: str, message: str) -> HTTPException:
    return HTTPException(status_code=status, detail={"code": code, "message": message})


async def recommend(
    *,
    user: User,
    sport: str,
    distance_priority: float | None,
    limit: int,
    profiles: ProfileRepository,
    recs: RecommendRepository,
    matches: MatchRepository,
    users: UserRepository,
    venues: VenueRepository,
) -> list[RecommendedOut]:
    if sport not in SPORTS:
        raise _error(422, "UNKNOWN_SPORT", "지원하지 않는 종목입니다")
    skill = await profiles.get_skill(user.id, sport)
    if skill is None:
        raise _error(409, "SKILL_NOT_SET", "먼저 이 종목의 자기평가를 등록해 주세요")
    locations = await profiles.list_locations(user.id)
    if not locations:
        raise _error(409, "LOCATION_NOT_SET", "먼저 활동 기준점을 등록해 주세요")

    now = datetime.now(UTC).replace(tzinfo=None)
    min_start = now + MIN_LEAD_TIME

    # 기준점마다 반경 안의 후보를 모으고, 기준점별 거리를 후보에 붙인다
    per_location: list[dict[int, float]] = []
    for loc in locations:
        lng, lat = loc.point
        per_location.append(
            await recs.distances_near(
                sport=sport,
                lat=lat,
                lng=lng,
                radius_m=loc.max_distance_km * 1000,
                bbox=bounding_box(lat, lng, loc.max_distance_km),
                min_start=min_start,
            )
        )
    match_ids = sorted({mid for d in per_location for mid in d})
    rows = await recs.candidate_rows(match_ids, sport)

    candidates = [
        Candidate(
            match_id=r.match.id,
            starts_at=r.match.starts_at,
            duration_min=r.match.duration_min,
            gender_policy=r.match.gender_policy,
            tier_min=r.match.tier_min,
            tier_max=r.match.tier_max,
            capacity=r.match.capacity,
            joined=r.joined,
            min_players=r.match.min_players,
            host_id=r.match.host_id,
            host_manner=r.host_manner,
            host_games=r.host_games,
            host_no_shows=r.host_no_shows,
            avg_rating=r.avg_rating,
            distances_km=tuple(d.get(r.match.id, _FAR_KM * 1000) / 1000 for d in per_location),
        )
        for r in rows
    ]

    commitments = await recs.commitments(user.id)
    ctx = UserContext(
        user_id=user.id,
        gender=user.gender,
        rating=skill.rating,
        rd=skill.rd,
        location_labels=tuple(loc.label for loc in locations),
        max_distance_km=tuple(float(loc.max_distance_km) for loc in locations),
        # 신청했거나 참가 중이거나 거절된 매치는 다시 추천하지 않는다 (취소한 신청은 이미 제외됨)
        excluded_match_ids=frozenset(c.match_id for c in commitments),
        busy=tuple(
            (c.starts_at, c.starts_at + timedelta(minutes=c.duration_min))
            for c in commitments
            if c.status in (ParticipationStatus.APPLIED, ParticipationStatus.ACCEPTED)
        ),
        preferred_slots=frozenset(user.preferred_slots or []),
        blocked_hosts=frozenset(uid for uid, _ in await profiles.list_blocks(user.id)),
    )

    base = await recs.active_weights() or Weights()
    weights = base if distance_priority is None else weights_for_slider(base, distance_priority)
    ranked = rank(ctx, candidates, weights, now, limit=min(limit, MAX_RESULTS))

    by_id = {r.match.id: r for r in rows}
    out = []
    for s in ranked:
        row = by_id[s.match_id]
        match_out = await to_match_out(row.match, row.joined, users, venues)
        b = s.breakdown
        out.append(
            RecommendedOut(
                match=match_out,
                score=s.score,
                breakdown=BreakdownOut(
                    dist=round(b.dist, 3),
                    skill=round(b.skill, 3),
                    time=round(b.time, 3),
                    host=round(b.host, 3),
                    fill=round(b.fill, 3),
                ),
                reasons=s.reasons,
            )
        )
    return out
