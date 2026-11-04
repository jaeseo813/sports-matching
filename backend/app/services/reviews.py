from datetime import UTC, datetime, timedelta

from fastapi import HTTPException

from app.models.enums import MatchStatus, ParticipationStatus
from app.models.user import User
from app.repositories.match import MatchRepository
from app.repositories.review import DuplicateReviewError, ReviewRepository
from app.schemas.match import AttendanceIn, RateOut, ReviewIn
from app.services.skill import (
    PAIR_COOLDOWN_DAYS,
    PlayerSkill,
    Review,
    rate_match,
    trend_of,
    update_manner,
)

_PLAYED = (ParticipationStatus.ACCEPTED, ParticipationStatus.ATTENDED)
_TREND_CODE = {"down": -1, "same": 0, "up": 1}


def _error(status: int, code: str, message: str) -> HTTPException:
    return HTTPException(status_code=status, detail={"code": code, "message": message})


def _now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


async def submit_review(
    matches: MatchRepository, reviews: ReviewRepository, user: User, match_id: int, data: ReviewIn
) -> None:
    match = await matches.get_match(match_id)
    if match is None:
        raise _error(404, "MATCH_NOT_FOUND", "매치를 찾을 수 없습니다")
    statuses = await reviews.participant_statuses(match_id)
    if statuses.get(user.id) not in _PLAYED:  # 참가자만 평가할 수 있다
        raise _error(403, "FORBIDDEN", "경기에 참가한 사람만 평가할 수 있습니다")
    if match.status is not MatchStatus.COMPLETED:
        raise _error(409, "MATCH_NOT_COMPLETED", "끝난 경기만 평가할 수 있습니다")
    if match.rated_at is not None:
        raise _error(409, "REVIEW_CLOSED", "이미 레이팅에 반영된 경기입니다")
    if data.reviewee_id == user.id:
        raise _error(422, "SELF_REVIEW", "자신을 평가할 수 없습니다")
    if statuses.get(data.reviewee_id) not in _PLAYED:
        raise _error(404, "REVIEWEE_NOT_FOUND", "평가할 참가자를 찾을 수 없습니다")
    try:
        await reviews.add_review(
            match_id=match_id,
            reviewer_id=user.id,
            reviewee_id=data.reviewee_id,
            verdict=data.verdict,
            manner_flag=data.manner_flag,
        )
    except DuplicateReviewError:
        raise _error(409, "ALREADY_REVIEWED", "이미 평가한 참가자입니다") from None
    await reviews.commit()


async def set_attendance(
    matches: MatchRepository,
    reviews: ReviewRepository,
    host: User,
    match_id: int,
    data: AttendanceIn,
) -> None:
    match = await matches.get_match(match_id, for_update=True)
    if match is None:
        raise _error(404, "MATCH_NOT_FOUND", "매치를 찾을 수 없습니다")
    if match.host_id != host.id:
        raise _error(403, "FORBIDDEN", "주최자만 할 수 있습니다")
    if match.status not in (MatchStatus.PLAYING, MatchStatus.COMPLETED):
        raise _error(409, "MATCH_NOT_STARTED", "경기가 시작된 뒤에만 출석을 기록할 수 있습니다")
    if match.rated_at is not None:
        raise _error(409, "REVIEW_CLOSED", "이미 레이팅에 반영된 경기입니다")
    ids = {a.user_id for a in data.attendances}
    users = await reviews.users(ids)
    for item in data.attendances:
        part = await matches.get_participation(match_id, item.user_id)
        if part is None or part.status not in (*_PLAYED, ParticipationStatus.NO_SHOW):
            raise _error(404, "PARTICIPATION_NOT_FOUND", "참가자를 찾을 수 없습니다")
        new = ParticipationStatus.ATTENDED if item.attended else ParticipationStatus.NO_SHOW
        user = users[item.user_id]
        if new is ParticipationStatus.NO_SHOW and part.status is not ParticipationStatus.NO_SHOW:
            user.no_show_count += 1
        elif new is ParticipationStatus.ATTENDED and part.status is ParticipationStatus.NO_SHOW:
            user.no_show_count = max(0, user.no_show_count - 1)
        part.status = new
    await matches.commit()


async def apply_ratings(
    matches: MatchRepository, reviews: ReviewRepository, host: User, match_id: int
) -> RateOut:
    match = await matches.get_match(match_id, for_update=True)  # 동시에 두 번 반영되지 않게 잠근다
    if match is None:
        raise _error(404, "MATCH_NOT_FOUND", "매치를 찾을 수 없습니다")
    if match.host_id != host.id:
        raise _error(403, "FORBIDDEN", "주최자만 할 수 있습니다")
    if match.status is not MatchStatus.COMPLETED:
        raise _error(409, "MATCH_NOT_COMPLETED", "끝난 경기만 반영할 수 있습니다")
    if match.rated_at is not None:
        raise _error(409, "ALREADY_RATED", "이미 레이팅에 반영된 경기입니다")

    statuses = await reviews.participant_statuses(match_id)
    players = {uid for uid, st in statuses.items() if st in _PLAYED}
    rows = await reviews.skills(players, match.sport)
    stored = [r for r in await reviews.list_reviews(match_id) if r.reviewer_id and r.reviewee_id]
    since = _now() - timedelta(days=PAIR_COOLDOWN_DAYS)
    recent = await reviews.recent_pairs(players, since, match_id)
    before = {uid: PlayerSkill(s.rating, s.rd, s.volatility) for uid, s in rows.items()}
    updated = rate_match(
        before,
        [
            Review(r.reviewer_id, r.reviewee_id, r.verdict)
            for r in stored
            if r.reviewer_id in players and r.reviewee_id in players
        ],
        recent_pairs=recent,
    )
    if not updated:  # 제출률 미만이거나 반영할 리뷰가 없다: 나중에 다시 시도할 수 있다
        return RateOut(applied=False)

    for uid, new in updated.items():
        row = rows[uid]
        row.trend = _TREND_CODE[trend_of(new.rating - row.rating)]
        row.rating, row.rd, row.volatility = new.rating, new.rd, new.volatility
        row.games_rated += 1

    users = await reviews.users(players)
    received: dict[int, list[bool]] = {}
    for r in stored:
        if r.reviewee_id in players and r.reviewer_id in players and r.reviewer_id != r.reviewee_id:
            received.setdefault(r.reviewee_id, []).append(r.manner_flag)
    for uid, user in users.items():
        user.games_played += 1
        flags = received.get(uid, [])
        # 매너는 레이팅과 분리해서 신고 수와 리뷰 수로만 움직인다
        user.manner_score = update_manner(user.manner_score, sum(flags), len(flags))
    match.rated_at = _now()
    await matches.commit()
    return RateOut(applied=True, updated=len(updated))
