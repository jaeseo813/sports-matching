import pytest

from app.models.enums import MatchStatus as S
from app.services.match_state import can_transition, status_after_headcount


@pytest.mark.parametrize(
    ("current", "target"),
    [
        (S.OPEN, S.FULL),
        (S.OPEN, S.CONFIRMED),
        (S.OPEN, S.CANCELED),
        (S.FULL, S.OPEN),
        (S.FULL, S.CONFIRMED),
        (S.CONFIRMED, S.PLAYING),
        (S.PLAYING, S.COMPLETED),
    ],
)
def test_allowed_transitions(current: S, target: S) -> None:
    assert can_transition(current, target)


@pytest.mark.parametrize(
    ("current", "target"),
    [
        (S.OPEN, S.PLAYING),
        (S.OPEN, S.COMPLETED),
        (S.CONFIRMED, S.OPEN),
        (S.PLAYING, S.CANCELED),
        (S.COMPLETED, S.OPEN),
        (S.CANCELED, S.OPEN),
        (S.CANCELED, S.CONFIRMED),
    ],
)
def test_forbidden_transitions(current: S, target: S) -> None:
    assert not can_transition(current, target)


def test_open_becomes_full_at_capacity() -> None:
    assert status_after_headcount(S.OPEN, 4, 4) is S.FULL
    assert status_after_headcount(S.OPEN, 3, 4) is S.OPEN


def test_full_reopens_when_someone_leaves() -> None:
    assert status_after_headcount(S.FULL, 3, 4) is S.OPEN
    assert status_after_headcount(S.FULL, 4, 4) is S.FULL


@pytest.mark.parametrize("status", [S.CONFIRMED, S.PLAYING, S.COMPLETED, S.CANCELED])
def test_other_statuses_are_untouched(status: S) -> None:
    assert status_after_headcount(status, 0, 4) is status
    assert status_after_headcount(status, 4, 4) is status
