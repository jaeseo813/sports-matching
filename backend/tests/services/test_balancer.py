import itertools

import pytest

from app.services.balancer import BalanceError, Player, balance, closeness_level


def players(ratings: list[float], positions: list[str | None] | None = None) -> list[Player]:
    positions = positions or [None] * len(ratings)
    return [
        Player(i + 1, r, pos) for i, (r, pos) in enumerate(zip(ratings, positions, strict=True))
    ]


def best_possible_spread(ps: list[Player], size: int) -> float:
    """전수 탐색으로 2팀 최소 spread를 구한다 (소규모 검증용)."""
    total = sum(p.rating for p in ps)
    return min(abs(total - 2 * sum(p.rating for p in c)) for c in itertools.combinations(ps, size))


def test_even_split_sizes_and_everyone_assigned() -> None:
    ps = players([1500, 1400, 1300, 1200, 1100, 1000, 900, 800, 700, 600])
    a = balance(ps)
    assert [len(t) for t in a.teams] == [5, 5]
    assert sorted(itertools.chain(*a.teams)) == [p.user_id for p in ps]


def test_odd_number_of_players_gets_one_extra_on_first_team() -> None:
    a = balance(players([1500, 1400, 1300, 1200, 1100]))
    assert sorted(len(t) for t in a.teams) == [2, 3]


def test_spread_is_optimal_for_small_inputs() -> None:
    cases = [
        [1700, 1100, 1300, 900, 1500, 1500],
        [1800, 1750, 900, 880, 870, 860, 850, 840],
        [1000, 1000, 1000, 1000],
        [1337, 1111, 1450, 1222, 1599, 987, 1303, 1250],
    ]
    for ratings in cases:
        ps = players(ratings)
        assert balance(ps).spread <= best_possible_spread(ps, len(ps) // 2) + 1e-9


def test_two_opt_improves_on_pure_snake() -> None:
    # 스네이크만 하면 [10,7,6,3]/[9,8,5,4]처럼 차이가 남는 입력
    ps = players([100, 90, 80, 70, 60, 50, 40, 30, 20, 10])
    a = balance(ps)
    assert a.spread <= 10


def test_required_position_one_gk_per_team() -> None:
    ps = players(
        [1500, 1400, 1300, 1200, 1100, 1000, 900, 800, 700, 600],
        ["GK", "FIELD", "FIELD", "FIELD", "FIELD", "GK", "FIELD", "FIELD", "FIELD", "FIELD"],
    )
    a = balance(ps, required_per_team={"GK": 1})
    by_id = {p.user_id: p for p in ps}
    for team in a.teams:
        assert sum(1 for uid in team if by_id[uid].position == "GK") == 1


def test_swaps_never_break_required_positions() -> None:
    # GK 레이팅 차이가 커서 스왑 유혹이 크다. 그래도 팀당 GK는 1명이어야 한다
    ps = players([2000, 500, 1500, 1400, 1300, 1200], ["GK", "GK", None, None, None, None])
    a = balance(ps, required_per_team={"GK": 1})
    by_id = {p.user_id: p for p in ps}
    assert [sum(1 for u in t if by_id[u].position == "GK") for t in a.teams] == [1, 1]


def test_not_enough_goalkeepers_raises() -> None:
    ps = players([1500, 1400, 1300, 1200], ["GK", None, None, None])
    with pytest.raises(BalanceError):
        balance(ps, required_per_team={"GK": 1})


def test_required_more_than_team_capacity_raises() -> None:
    ps = players([1, 2, 3, 4], ["GK"] * 4)
    with pytest.raises(BalanceError):
        balance(ps, required_per_team={"GK": 3})


@pytest.mark.parametrize("count", [0, 1])
def test_too_few_players_raises(count: int) -> None:
    with pytest.raises(BalanceError):
        balance(players([1500] * count))


def test_rejects_single_team_and_duplicate_ids() -> None:
    with pytest.raises(BalanceError):
        balance(players([1, 2, 3]), team_count=1)
    with pytest.raises(BalanceError):
        balance([Player(1, 1500), Player(1, 1400)])


def test_three_teams_is_best_effort() -> None:
    # 2-opt는 두 팀씩만 맞바꾸므로 3팀 이상은 국소 최적에서 멈출 수 있다 (모든 종목은 2팀)
    a = balance(players([1500, 1400, 1300, 1200, 1100, 1000, 900, 800, 700]), team_count=3)
    assert [len(t) for t in a.teams] == [3, 3, 3]
    assert a.spread <= 200


def test_is_deterministic() -> None:
    ps = players([1500, 1500, 1400, 1400, 1300, 1300])
    assert balance(ps) == balance(list(reversed(ps)))


def test_balance_does_not_mutate_input() -> None:
    ps = players([1500, 1400, 1300, 1200])
    snapshot = list(ps)
    balance(ps)
    assert ps == snapshot


@pytest.mark.parametrize(
    ("sums", "level"),
    [
        ((1000, 1000), 5),
        ((1000, 1030), 4),
        ((1000, 1080), 3),
        ((1000, 1180), 2),
        ((1000, 1500), 1),
        ((0, 0), 1),
    ],
)
def test_closeness_level(sums: tuple[float, float], level: int) -> None:
    assert closeness_level(sums) == level
