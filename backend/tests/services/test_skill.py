import pytest

from app.models.enums import Verdict
from app.services.skill import (
    PlayerSkill,
    Review,
    glicko2_update,
    initial_skill,
    rate_match,
    review_rate_ok,
    tier_from_rating,
    trend_of,
    update_manner,
    usable_reviews,
    verdict_score,
)


def test_glicko2_matches_glickman_paper_example() -> None:
    # Glickman, "Example of the Glicko-2 system": 1500/200/0.06, τ=0.5 → 1464.06 / 151.52 / 0.05999
    new = glicko2_update(
        PlayerSkill(1500, 200, 0.06), [(1400, 30, 1.0), (1550, 100, 0.0), (1700, 300, 0.0)]
    )
    assert new.rating == pytest.approx(1464.06, abs=0.05)
    assert new.rd == pytest.approx(151.52, abs=0.05)
    assert new.volatility == pytest.approx(0.05999, abs=1e-4)


def test_no_games_only_grows_rd() -> None:
    new = glicko2_update(PlayerSkill(1500, 200, 0.06), [])
    assert new.rating == 1500
    assert new.rd > 200


@pytest.mark.parametrize(
    ("tier", "years", "rating", "rd"),
    [
        (1, 0, 900, 350),
        (3, 2, 1330, 330),
        (5, 5, 1775, 300),
        (5, 99, 1775, 300),
        (2, -3, 1100, 350),
    ],
)
def test_initial_skill(tier: int, years: int, rating: float, rd: float) -> None:
    s = initial_skill(tier, years)
    assert (s.rating, s.rd) == (rating, rd)


def test_initial_skill_rejects_bad_tier() -> None:
    with pytest.raises(ValueError):
        initial_skill(6, 0)


@pytest.mark.parametrize(
    ("rating", "tier"),
    [
        (0, 1),
        (999, 1),
        (1000, 2),
        (1199, 2),
        (1200, 3),
        (1399, 3),
        (1400, 4),
        (1599, 4),
        (1600, 5),
        (2500, 5),
    ],
)
def test_tier_from_rating(rating: float, tier: int) -> None:
    assert tier_from_rating(rating) == tier


@pytest.mark.parametrize(
    ("delta", "trend"),
    [(20, "up"), (15, "up"), (14, "same"), (0, "same"), (-14, "same"), (-15, "down")],
)
def test_trend(delta: float, trend: str) -> None:
    assert trend_of(delta) == trend


def test_verdict_score() -> None:
    assert verdict_score(Verdict.BETTER) == 0.0
    assert verdict_score(Verdict.SIMILAR) == 0.5
    assert verdict_score(Verdict.WORSE) == 1.0


def test_review_rate_threshold() -> None:
    assert review_rate_ok(5, 10)
    assert not review_rate_ok(4, 10)
    assert not review_rate_ok(0, 0)


def test_usable_reviews_filters_self_recent_and_duplicates() -> None:
    reviews = [
        Review(1, 1, Verdict.BETTER),  # 자기 평가
        Review(1, 2, Verdict.BETTER),
        Review(1, 2, Verdict.WORSE),  # 같은 쌍 중복
        Review(2, 3, Verdict.SIMILAR),  # 30일 내 이미 반영
        Review(3, 1, Verdict.SIMILAR),
    ]
    kept = usable_reviews(reviews, frozenset({(2, 3)}))
    assert [(r.reviewer_id, r.reviewee_id) for r in kept] == [(1, 2), (3, 1)]


def _skills(n: int = 4) -> dict[int, PlayerSkill]:
    return {i: PlayerSkill(1300, 300) for i in range(1, n + 1)}


def test_rate_match_holds_when_too_few_reviewers() -> None:
    assert rate_match(_skills(4), [Review(1, 2, Verdict.BETTER)]) == {}


def test_rate_match_moves_in_expected_direction() -> None:
    reviews = [Review(1, 2, Verdict.BETTER), Review(2, 1, Verdict.WORSE)]
    out = rate_match(_skills(4), reviews)
    assert out[2].rating > 1300  # 2번은 더 낫다고 평가됨
    assert out[1].rating < 1300
    assert 3 not in out and 4 not in out  # 평가에 얽히지 않은 사람은 건드리지 않는다


def test_rate_match_similar_keeps_ratings_close() -> None:
    reviews = [Review(1, 2, Verdict.SIMILAR), Review(2, 1, Verdict.SIMILAR)]
    out = rate_match(_skills(2), reviews)
    assert out[1].rating == pytest.approx(1300, abs=1e-6)
    assert out[1].rd < 300  # 정보가 생겨 불확실성은 줄어든다


def test_rate_match_caps_delta_per_match() -> None:
    skills = {1: PlayerSkill(1000, 350), **{i: PlayerSkill(1900, 40) for i in range(2, 8)}}
    reviews = [Review(1, i, Verdict.WORSE) for i in range(2, 8)] + [
        Review(i, 1, Verdict.BETTER) for i in range(2, 8)
    ]
    out = rate_match(skills, reviews)
    assert out[1].rating - 1000 == pytest.approx(80)  # 상한에 걸림


def test_rate_match_ignores_recent_pair() -> None:
    reviews = [Review(1, 2, Verdict.BETTER), Review(2, 1, Verdict.WORSE)]
    assert rate_match(_skills(2), reviews, recent_pairs=frozenset({(1, 2), (2, 1)})) == {}


def test_rate_match_ignores_unknown_players() -> None:
    reviews = [Review(1, 99, Verdict.BETTER), Review(2, 1, Verdict.SIMILAR)]
    out = rate_match(_skills(2), reviews)
    assert 99 not in out


@pytest.mark.parametrize(
    ("score", "flags", "reviews", "expected"),
    [
        (3.0, 0, 0, 3.0),
        (3.0, 0, 4, 3.2),
        (3.0, 1, 1, 2.7),
        (0.2, 2, 2, 0.0),  # 하한
        (4.95, 0, 5, 5.0),  # 상한
    ],
)
def test_update_manner(score: float, flags: int, reviews: int, expected: float) -> None:
    assert update_manner(score, flags, reviews) == pytest.approx(expected)
