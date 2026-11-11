from datetime import UTC, datetime

from fastapi import HTTPException

from app.models.enums import Gender, GenderPolicy, MatchStatus, ParticipationStatus
from app.models.match import Match
from app.models.user import User
from app.repositories.match import DuplicateParticipationError, MatchRepository
from app.repositories.user import UserRepository
from app.repositories.venue import VenueRepository
from app.schemas.match import MatchCreateIn, MatchOut, MySummaryOut, ParticipationOut
from app.services.match_state import can_transition, status_after_headcount
from app.sports.registry import SPORTS

MAX_PAGE = 50


def _error(status: int, code: str, message: str) -> HTTPException:
    return HTTPException(status_code=status, detail={"code": code, "message": message})


def _now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)  # DB는 UTC naive로 저장한다


def _gender_allowed(policy: GenderPolicy, gender: Gender) -> bool:
    if policy is GenderPolicy.MALE_ONLY:
        return gender is Gender.MALE
    if policy is GenderPolicy.FEMALE_ONLY:
        return gender is Gender.FEMALE
    return True


async def to_match_out(
    match: Match,
    joined: int,
    users: UserRepository,
    venues: VenueRepository,
    my_status: ParticipationStatus | None = None,
) -> MatchOut:
    host = await users.get_by_id(match.host_id)
    venue = await venues.get(match.venue_id)
    return MatchOut(
        id=match.id,
        sport=match.sport,
        host_nickname=host.nickname if host else "탈퇴한 사용자",
        venue_id=match.venue_id,
        venue_name=venue.name if venue else "",
        title=match.title,
        description=match.description,
        starts_at=match.starts_at.replace(tzinfo=UTC),
        duration_min=match.duration_min,
        team_size=match.team_size,
        capacity=match.capacity,
        joined=joined,
        min_players=match.min_players,
        gender_policy=match.gender_policy,
        tier_min=match.tier_min,
        tier_max=match.tier_max,
        status=match.status,
        my_status=my_status,
    )


async def create_match(
    matches: MatchRepository,
    users: UserRepository,
    venues: VenueRepository,
    host: User,
    data: MatchCreateIn,
) -> MatchOut:
    rules = SPORTS.get(data.sport)
    if rules is None:
        raise _error(422, "UNKNOWN_SPORT", "지원하지 않는 종목입니다")
    if data.position is not None and data.position not in rules.positions:
        raise _error(422, "UNKNOWN_POSITION", "이 종목에 없는 포지션입니다")
    if data.team_size not in rules.players_per_team:
        raise _error(422, "INVALID_TEAM_SIZE", "이 종목에서 허용하지 않는 팀 인원입니다")
    venue = await venues.get(data.venue_id)
    if venue is None or data.sport not in venue.sports:
        raise _error(422, "VENUE_SPORT_MISMATCH", "이 종목을 지원하는 구장이 아닙니다")
    starts_at = data.starts_at.astimezone(UTC).replace(tzinfo=None)
    if starts_at <= _now():
        raise _error(422, "PAST_START", "시작 시각은 현재 이후여야 합니다")
    capacity = rules.team_count * data.team_size  # 정원은 클라이언트가 정하지 않는다
    min_players = data.min_players if data.min_players is not None else capacity
    if min_players > capacity:
        raise _error(422, "INVALID_MIN_PLAYERS", "최소 인원은 정원보다 클 수 없습니다")
    match = await matches.add_match(
        sport=data.sport,
        host_id=host.id,
        venue_id=data.venue_id,
        title=data.title,
        description=data.description,
        starts_at=starts_at,
        duration_min=data.duration_min,
        team_size=data.team_size,
        capacity=capacity,
        min_players=min_players,
        gender_policy=data.gender_policy,
        tier_min=data.tier_min,
        tier_max=data.tier_max,
    )
    # 주최자도 경기에 뛰는 참가자라 정원에 포함한다 (팀 분배·최소 인원 계산에도 들어간다)
    host_part = await matches.add_participation(match.id, host.id)
    host_part.status = ParticipationStatus.ACCEPTED
    host_part.position = data.position
    await matches.commit()
    return await to_match_out(match, 1, users, venues)


async def get_match(
    matches: MatchRepository,
    users: UserRepository,
    venues: VenueRepository,
    viewer: User,
    match_id: int,
) -> MatchOut:
    match = await matches.get_match(match_id)
    if match is None:
        raise _error(404, "MATCH_NOT_FOUND", "매치를 찾을 수 없습니다")
    part = await matches.get_participation(match_id, viewer.id)
    joined = await matches.count_accepted(match_id)
    return await to_match_out(match, joined, users, venues, part.status if part else None)


async def list_matches(
    matches: MatchRepository,
    users: UserRepository,
    venues: VenueRepository,
    *,
    sport: str | None,
    limit: int,
    offset: int,
) -> list[MatchOut]:
    if sport is not None and sport not in SPORTS:
        raise _error(422, "UNKNOWN_SPORT", "지원하지 않는 종목입니다")
    found = await matches.list_open(sport=sport, limit=min(limit, MAX_PAGE), offset=offset)
    counts = await matches.accepted_counts([m.id for m in found])
    return [await to_match_out(m, counts.get(m.id, 0), users, venues) for m in found]


async def my_upcoming(
    matches: MatchRepository,
    users: UserRepository,
    venues: VenueRepository,
    user: User,
    *,
    limit: int,
) -> list[MatchOut]:
    # 조회 대상은 항상 요청자 본인(JWT)이다. 사용자 id를 입력으로 받지 않는다
    found = await matches.list_upcoming_for_user(user.id, limit=min(limit, MAX_PAGE))
    counts = await matches.accepted_counts([m.id for m in found])
    return [
        await to_match_out(m, counts.get(m.id, 0), users, venues, ParticipationStatus.ACCEPTED)
        for m in found
    ]


async def my_summary(matches: MatchRepository, user: User) -> MySummaryOut:
    return MySummaryOut(
        upcoming=await matches.count_upcoming_for_user(user.id),
        attended=await matches.count_attended(user.id),
        manner_score=round(user.manner_score, 1),
    )


async def apply(
    matches: MatchRepository, user: User, match_id: int, position: str | None = None
) -> ParticipationStatus:
    match = await matches.get_match(match_id)
    if match is None:
        raise _error(404, "MATCH_NOT_FOUND", "매치를 찾을 수 없습니다")
    if position is not None and position not in SPORTS[match.sport].positions:
        raise _error(422, "UNKNOWN_POSITION", "이 종목에 없는 포지션입니다")
    if match.host_id == user.id:
        raise _error(409, "HOST_CANNOT_APPLY", "내가 연 매치에는 신청할 수 없습니다")
    if match.status is MatchStatus.FULL:
        raise _error(409, "MATCH_FULL", "정원이 가득 찼습니다")
    if match.status is not MatchStatus.OPEN or match.starts_at <= _now():
        raise _error(409, "MATCH_NOT_OPEN", "신청할 수 없는 매치입니다")
    if not _gender_allowed(match.gender_policy, user.gender):
        raise _error(403, "GENDER_POLICY", "성별 조건이 맞지 않는 매치입니다")
    existing = await matches.get_participation(match_id, user.id)
    if existing is not None:
        if existing.status is not ParticipationStatus.CANCELED:
            raise _error(409, "ALREADY_APPLIED", "이미 신청한 매치입니다")
        existing.status = ParticipationStatus.APPLIED  # 취소했던 신청은 다시 신청할 수 있다
        existing.position = position
    else:
        try:
            created = await matches.add_participation(match_id, user.id)
            created.position = position
        except DuplicateParticipationError:
            raise _error(409, "ALREADY_APPLIED", "이미 신청한 매치입니다") from None
    await matches.commit()
    return ParticipationStatus.APPLIED


async def list_participations(
    matches: MatchRepository, host: User, match_id: int
) -> list[ParticipationOut]:
    match = await matches.get_match(match_id)
    if match is None:
        raise _error(404, "MATCH_NOT_FOUND", "매치를 찾을 수 없습니다")
    _require_host(match, host)
    return [
        ParticipationOut(id=p.id, nickname=nick, status=p.status)
        for p, nick in await matches.list_participations(match_id)
    ]


def _require_host(match: Match, user: User) -> None:
    if match.host_id != user.id:
        raise _error(403, "FORBIDDEN", "주최자만 할 수 있습니다")  # 객체 소유권 검사


async def decide(
    matches: MatchRepository, host: User, match_id: int, participation_id: int, *, accept: bool
) -> ParticipationStatus:
    # 같은 매치의 수락을 직렬화해서 정원 초과 경합을 막는다 (SELECT ... FOR UPDATE)
    match = await matches.get_match(match_id, for_update=True)
    if match is None:
        raise _error(404, "MATCH_NOT_FOUND", "매치를 찾을 수 없습니다")
    _require_host(match, host)
    part = await matches.get_participation_by_id(match_id, participation_id)
    if part is None:
        raise _error(404, "PARTICIPATION_NOT_FOUND", "신청을 찾을 수 없습니다")
    if part.status is not ParticipationStatus.APPLIED:
        raise _error(409, "ALREADY_DECIDED", "이미 처리된 신청입니다")
    if not accept:
        part.status = ParticipationStatus.REJECTED
        await matches.commit()
        return part.status
    if match.status not in (MatchStatus.OPEN, MatchStatus.FULL):
        raise _error(409, "MATCH_NOT_OPEN", "신청을 받을 수 없는 매치입니다")
    accepted = await matches.count_accepted(match_id)
    if accepted >= match.capacity:
        raise _error(409, "MATCH_FULL", "정원이 가득 찼습니다")
    part.status = ParticipationStatus.ACCEPTED
    match.status = status_after_headcount(match.status, accepted + 1, match.capacity)
    await matches.commit()
    return part.status


async def cancel_application(matches: MatchRepository, user: User, match_id: int) -> None:
    match = await matches.get_match(match_id, for_update=True)
    if match is None:
        raise _error(404, "MATCH_NOT_FOUND", "매치를 찾을 수 없습니다")
    part = await matches.get_participation(match_id, user.id)  # 본인 신청만 대상
    if part is None or part.status not in (
        ParticipationStatus.APPLIED,
        ParticipationStatus.ACCEPTED,
    ):
        raise _error(404, "PARTICIPATION_NOT_FOUND", "취소할 신청이 없습니다")
    if match.host_id == user.id:
        raise _error(409, "HOST_CANNOT_LEAVE", "주최자는 매치를 취소해야 합니다")
    if match.status in (MatchStatus.PLAYING, MatchStatus.COMPLETED):
        raise _error(409, "MATCH_NOT_OPEN", "진행 중이거나 끝난 매치는 취소할 수 없습니다")
    part.status = ParticipationStatus.CANCELED
    # 상태 변경은 다음 쿼리 전에 flush되므로 다시 세면 취소가 반영된 수락 인원이 나온다
    accepted = await matches.count_accepted(match_id)
    match.status = status_after_headcount(match.status, accepted, match.capacity)
    await matches.commit()


async def _transition(
    matches: MatchRepository, host: User, match_id: int, target: MatchStatus
) -> Match:
    match = await matches.get_match(match_id, for_update=True)
    if match is None:
        raise _error(404, "MATCH_NOT_FOUND", "매치를 찾을 수 없습니다")
    _require_host(match, host)
    if not can_transition(match.status, target):
        raise _error(409, "INVALID_TRANSITION", "현재 상태에서 할 수 없는 동작입니다")
    return match


async def confirm_match(matches: MatchRepository, host: User, match_id: int) -> MatchStatus:
    match = await _transition(matches, host, match_id, MatchStatus.CONFIRMED)
    if await matches.count_accepted(match_id) < match.min_players:
        raise _error(409, "NOT_ENOUGH_PLAYERS", "최소 인원이 모이지 않았습니다")
    match.status = MatchStatus.CONFIRMED
    await matches.commit()
    return match.status


async def cancel_match(matches: MatchRepository, host: User, match_id: int) -> MatchStatus:
    match = await _transition(matches, host, match_id, MatchStatus.CANCELED)
    match.status = MatchStatus.CANCELED
    await matches.commit()
    return match.status


async def start_match(matches: MatchRepository, host: User, match_id: int) -> MatchStatus:
    match = await _transition(matches, host, match_id, MatchStatus.PLAYING)
    match.status = MatchStatus.PLAYING
    await matches.commit()
    return match.status


async def complete_match(matches: MatchRepository, host: User, match_id: int) -> MatchStatus:
    match = await _transition(matches, host, match_id, MatchStatus.COMPLETED)
    match.status = MatchStatus.COMPLETED
    await matches.commit()
    return match.status
