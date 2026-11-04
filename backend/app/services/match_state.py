"""매치 상태 전이 규칙. DB 없이 테스트하는 순수 함수."""

from app.models.enums import MatchStatus

_ALLOWED: dict[MatchStatus, frozenset[MatchStatus]] = {
    MatchStatus.OPEN: frozenset({MatchStatus.FULL, MatchStatus.CONFIRMED, MatchStatus.CANCELED}),
    # 정원이 찼다가 참가자가 빠지면 다시 모집 중으로 돌아간다
    MatchStatus.FULL: frozenset({MatchStatus.OPEN, MatchStatus.CONFIRMED, MatchStatus.CANCELED}),
    MatchStatus.CONFIRMED: frozenset({MatchStatus.PLAYING, MatchStatus.CANCELED}),
    MatchStatus.PLAYING: frozenset({MatchStatus.COMPLETED}),
    MatchStatus.COMPLETED: frozenset(),
    MatchStatus.CANCELED: frozenset(),
}


def can_transition(current: MatchStatus, target: MatchStatus) -> bool:
    return target in _ALLOWED[current]


def status_after_headcount(current: MatchStatus, accepted: int, capacity: int) -> MatchStatus:
    """수락 인원에 따라 OPEN ↔ FULL을 맞춘다. 그 밖의 상태는 건드리지 않는다."""
    if current is MatchStatus.OPEN and accepted >= capacity:
        return MatchStatus.FULL
    if current is MatchStatus.FULL and accepted < capacity:
        return MatchStatus.OPEN
    return current
