from fastapi import HTTPException

from app.models.enums import MatchStatus
from app.models.match import Match
from app.models.user import User
from app.repositories.match import MatchRepository
from app.repositories.team import PlayerRow, TeamRepository
from app.schemas.match import ManualTeamsIn, TeamMemberOut, TeamOut, TeamsOut
from app.services.balancer import Assignment, BalanceError, Player, balance, closeness_level
from app.services.skill import tier_from_rating
from app.sports.registry import get_rules

_DEFAULT_RATING = 1300.0  # 실력을 등록하지 않은 참가자는 중간(티어 3)으로 본다
_TEAM_STATUSES = (MatchStatus.FULL, MatchStatus.CONFIRMED)


def _error(status: int, code: str, message: str) -> HTTPException:
    return HTTPException(status_code=status, detail={"code": code, "message": message})


async def _load_match(matches: MatchRepository, match_id: int, *, lock: bool = False) -> Match:
    match = await matches.get_match(match_id, for_update=lock)
    if match is None:
        raise _error(404, "MATCH_NOT_FOUND", "매치를 찾을 수 없습니다")
    return match


def _require_host(match: Match, user: User) -> None:
    if match.host_id != user.id:
        raise _error(403, "FORBIDDEN", "주최자만 할 수 있습니다")


def _out(
    rows: list[tuple[int, str, int, str | None, float | None]],
    rating_sums: list[float],
    manual: bool,
) -> TeamsOut:
    teams: dict[int, list[TeamMemberOut]] = {}
    for _, nick, team_no, pos, rating in rows:
        teams.setdefault(team_no, []).append(
            TeamMemberOut(
                nickname=nick,
                tier=tier_from_rating(rating if rating is not None else _DEFAULT_RATING),
                position=pos,
            )
        )
    return TeamsOut(
        teams=[TeamOut(team_no=n, members=m) for n, m in sorted(teams.items())],
        closeness=closeness_level(rating_sums),
        is_manual=manual,
    )


def _sums(
    rows: list[tuple[int, str, int, str | None, float | None]], team_count: int
) -> list[float]:
    sums = [0.0] * team_count
    for _, _, team_no, _, rating in rows:
        if 1 <= team_no <= team_count:
            sums[team_no - 1] += rating if rating is not None else _DEFAULT_RATING
    return sums


async def auto_balance(
    matches: MatchRepository, teams: TeamRepository, host: User, match_id: int
) -> TeamsOut:
    match = await _load_match(matches, match_id, lock=True)
    _require_host(match, host)
    if match.status not in _TEAM_STATUSES:
        raise _error(409, "MATCH_NOT_READY", "정원이 차거나 확정된 매치만 팀을 나눌 수 있습니다")
    rules = get_rules(match.sport)
    players = await teams.accepted_players(match_id, match.sport)
    try:
        result: Assignment = balance(
            [
                Player(p.user_id, p.rating if p.rating is not None else _DEFAULT_RATING, p.position)
                for p in players
            ],
            team_count=rules.team_count,
            required_per_team=rules.required_per_team,
        )
    except BalanceError as exc:
        raise _error(409, "TEAM_CONSTRAINT", str(exc)) from None
    by_id = {p.user_id: p for p in players}
    rows = [
        (uid, team_no, by_id[uid].position, False)
        for team_no, members in enumerate(result.teams, start=1)
        for uid in members
    ]
    await teams.replace_teams(match_id, rows)
    await teams.commit()
    return await get_teams(matches, teams, host, match_id)


async def get_teams(
    matches: MatchRepository, teams: TeamRepository, viewer: User, match_id: int
) -> TeamsOut:
    match = await _load_match(matches, match_id)
    players = await teams.accepted_players(match_id, match.sport)
    # 팀 구성은 주최자와 수락된 참가자만 볼 수 있다
    if match.host_id != viewer.id and viewer.id not in {p.user_id for p in players}:
        raise _error(403, "FORBIDDEN", "참가자만 볼 수 있습니다")
    found = await teams.list_teams(match_id, match.sport)
    if not found:
        raise _error(404, "TEAMS_NOT_FOUND", "아직 팀이 나뉘지 않았습니다")
    rows = [(t.user_id, t.nickname, t.team_no, t.position, t.rating) for t in found]
    rules = get_rules(match.sport)
    return _out(rows, _sums(rows, rules.team_count), any(t.is_manual for t in found))


def _check_manual(match: Match, players: list[PlayerRow], data: ManualTeamsIn) -> None:
    rules = get_rules(match.sport)
    ids = [a.user_id for a in data.assignments]
    if len(set(ids)) != len(ids) or set(ids) != {p.user_id for p in players}:
        raise _error(422, "INVALID_ASSIGNMENT", "수락된 참가자 전원을 한 번씩만 배정해야 합니다")
    if any(a.team_no > rules.team_count for a in data.assignments):
        raise _error(422, "INVALID_TEAM", "존재하지 않는 팀 번호입니다")
    team_nos = {a.team_no for a in data.assignments}
    if len(team_nos) != rules.team_count:
        raise _error(422, "EMPTY_TEAM", "모든 팀에 한 명 이상 배정해야 합니다")
    position = {p.user_id: p.position for p in players}
    for team_no in team_nos:
        for pos, need in rules.required_per_team.items():
            have = sum(
                1 for a in data.assignments if a.team_no == team_no and position[a.user_id] == pos
            )
            if have < need:
                raise _error(
                    422, "TEAM_CONSTRAINT", f"{team_no}번 팀에 {pos} 포지션이 {need}명 필요합니다"
                )


async def set_manual(
    matches: MatchRepository, teams: TeamRepository, host: User, match_id: int, data: ManualTeamsIn
) -> TeamsOut:
    match = await _load_match(matches, match_id, lock=True)
    _require_host(match, host)
    if match.status not in _TEAM_STATUSES:
        raise _error(409, "MATCH_NOT_READY", "정원이 차거나 확정된 매치만 팀을 나눌 수 있습니다")
    players = await teams.accepted_players(match_id, match.sport)
    _check_manual(match, players, data)
    position = {p.user_id: p.position for p in players}
    await teams.replace_teams(
        match_id, [(a.user_id, a.team_no, position[a.user_id], True) for a in data.assignments]
    )
    await teams.commit()
    return await get_teams(matches, teams, host, match_id)
