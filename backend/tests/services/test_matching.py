from datetime import datetime, timedelta

import pytest

from app.models.enums import Gender, GenderPolicy
from app.services.matching import (
    Candidate,
    UserContext,
    Weights,
    exclusion_reason,
    gender_allowed,
    rank,
    s_dist,
    s_dist_best,
    s_fill,
    s_host,
    s_skill,
    s_time,
    score_candidate,
    slot_of,
    target_rating,
    weights_for_slider,
)

NOW = datetime(2026, 11, 7, 9, 0)


def user(**over: object) -> UserContext:
    base: dict[str, object] = {
        "user_id": 1,
        "gender": Gender.MALE,
        "rating": 1300.0,
        "rd": 100.0,
        "location_labels": ("집", "학교"),
        "max_distance_km": (10.0, 10.0),
    }
    return UserContext(**{**base, **over})  # type: ignore[arg-type]


def cand(**over: object) -> Candidate:
    base: dict[str, object] = {
        "match_id": 10,
        "starts_at": NOW + timedelta(days=1, hours=10),  # 다음날 19시 → evening
        "duration_min": 90,
        "gender_policy": GenderPolicy.ANY,
        "tier_min": 1,
        "tier_max": 5,
        "capacity": 4,
        "joined": 3,
        "min_players": 2,
        "host_id": 99,
        "host_manner": 4.5,
        "host_games": 10,
        "host_no_shows": 0,
        "avg_rating": 1300.0,
        "distances_km": (2.0, 8.0),
    }
    return Candidate(**{**base, **over})  # type: ignore[arg-type]


# --- 개별 항 ---


def test_s_dist_curve() -> None:
    assert s_dist(0, 10) == 1.0
    assert s_dist(10, 10) == 0.0
    assert s_dist(25, 10) == 0.0
    assert s_dist(5, 10) == pytest.approx(1 - 0.5**1.5)
    assert s_dist(-1, 10) == 1.0
    assert s_dist(1, 0) == 0.0


def test_s_dist_best_takes_max_over_locations() -> None:
    score, idx = s_dist_best((8.0, 1.0), (10.0, 10.0))
    assert idx == 1 and score == pytest.approx(s_dist(1, 10))
    assert s_dist_best((50.0, 60.0), (10.0, 10.0)) == (0.0, 0)
    assert s_dist_best((), ()) == (0.0, 0)


def test_target_rating() -> None:
    assert target_rating(1234.0, 1, 5) == 1234.0
    assert target_rating(None, 2, 4) == (1100 + 1500) / 2


def test_s_skill_gaussian_and_tier_gate() -> None:
    assert s_skill(1300, 100, 1300, 1, 5) == 1.0
    far = s_skill(1300, 100, 1700, 1, 5)
    assert 0 < far < 0.2
    sigma = 150 + 100 * 0.5
    assert s_skill(1300, 100, 1400, 1, 5) == pytest.approx(
        2.718281828 ** (-(100**2) / (2 * sigma**2))
    )
    assert s_skill(1300, 100, 1300, 4, 5) == 0.0  # 티어 3인데 4~5 매치
    assert s_skill(1300, 100, 1300, 1, 2) == 0.0


def test_larger_rd_is_more_tolerant() -> None:
    assert s_skill(1300, 350, 1600, 1, 5) > s_skill(1300, 50, 1600, 1, 5)


@pytest.mark.parametrize(
    ("hour", "slot"),
    [(0, "dawn"), (5, "dawn"), (6, "morning"), (12, "afternoon"), (18, "evening"), (23, "evening")],
)
def test_slot_of(hour: int, slot: str) -> None:
    assert slot_of(datetime(2026, 1, 1, hour)) == slot


def test_s_time() -> None:
    evening = datetime(2026, 1, 1, 19)
    assert s_time(evening, frozenset()) == 1.0  # 선호 없음
    assert s_time(evening, frozenset({"evening"})) == 1.0
    assert s_time(evening, frozenset({"afternoon"})) == 0.3  # 인접
    assert s_time(evening, frozenset({"dawn"})) == 0.3  # 순환 인접
    assert s_time(evening, frozenset({"morning"})) == 0.0


def test_s_host() -> None:
    assert s_host(5.0, 2, 2) == 0.6  # 경기 3회 미만은 기본값
    assert s_host(5.0, 10, 0) == 1.0
    assert s_host(4.0, 10, 2) == pytest.approx(0.8 * 0.8)
    assert s_host(5.0, 4, 9) == 0.0  # 노쇼율은 1로 자른다
    assert s_host(9.0, 10, 0) == 1.0  # 범위 밖 매너 값도 자른다


@pytest.mark.parametrize(
    ("joined", "capacity", "expected"),
    [(0, 4, 0.5), (2, 4, 0.5), (3, 5, 1.0), (4, 4, 1.0), (1, 0, 0.5)],
)
def test_s_fill(joined: int, capacity: int, expected: float) -> None:
    assert s_fill(joined, capacity) == expected


# --- 가중치 ---


def test_slider_keeps_pair_sum() -> None:
    base = Weights()
    for s in (0.0, 0.3, 1.0):
        w = weights_for_slider(base, s)
        assert w.w_dist + w.w_skill == pytest.approx(0.65)
        assert w.total() == pytest.approx(1.0)
    assert weights_for_slider(base, 1.0).w_skill == 0.0
    assert weights_for_slider(base, 0.0).w_dist == 0.0
    assert weights_for_slider(base, 5).w_dist == pytest.approx(0.65)  # 범위 밖은 자른다


def test_default_weights_sum_to_one() -> None:
    assert Weights().total() == pytest.approx(1.0)


# --- 하드 필터 ---


@pytest.mark.parametrize(
    ("policy", "gender", "ok"),
    [
        (GenderPolicy.ANY, Gender.OTHER, True),
        (GenderPolicy.MALE_ONLY, Gender.MALE, True),
        (GenderPolicy.MALE_ONLY, Gender.FEMALE, False),
        (GenderPolicy.FEMALE_ONLY, Gender.FEMALE, True),
        (GenderPolicy.FEMALE_ONLY, Gender.OTHER, False),
    ],
)
def test_gender_allowed(policy: GenderPolicy, gender: Gender, ok: bool) -> None:
    assert gender_allowed(policy, gender) is ok


def test_exclusions() -> None:
    assert exclusion_reason(user(), cand(), NOW) is None
    assert (
        exclusion_reason(user(), cand(starts_at=NOW + timedelta(hours=1, minutes=59)), NOW)
        == "starts_soon"
    )
    assert exclusion_reason(user(), cand(starts_at=NOW + timedelta(hours=2)), NOW) is None
    assert (
        exclusion_reason(user(), cand(gender_policy=GenderPolicy.FEMALE_ONLY), NOW)
        == "gender_policy"
    )
    assert (
        exclusion_reason(user(excluded_match_ids=frozenset({10})), cand(), NOW)
        == "already_applied_or_rejected"
    )
    assert exclusion_reason(user(blocked_hosts=frozenset({99})), cand(), NOW) == "blocked_host"


def test_time_overlap_detection() -> None:
    c = cand()
    start = c.starts_at
    overlap = ((start + timedelta(minutes=30), start + timedelta(hours=3)),)
    adjacent = ((start - timedelta(hours=2), start),)  # 끝나자마자 시작은 겹침이 아니다
    assert exclusion_reason(user(busy=overlap), c, NOW) == "time_overlap"
    assert exclusion_reason(user(busy=adjacent), c, NOW) is None


# --- 합산과 정렬 ---


def test_score_is_weighted_sum_and_in_unit_range() -> None:
    s = score_candidate(user(), cand(), Weights())
    b = s.breakdown
    expected = 0.35 * b.dist + 0.30 * b.skill + 0.20 * b.time + 0.10 * b.host + 0.05 * b.fill
    assert s.score == pytest.approx(expected, abs=1e-4)
    assert 0.0 <= s.score <= 1.0
    for v in (b.dist, b.skill, b.time, b.host, b.fill):
        assert 0.0 <= v <= 1.0


def test_reasons_chips() -> None:
    r = score_candidate(user(preferred_slots=frozenset({"evening"})), cand(), Weights()).reasons
    assert r == [
        "집에서 약 2km",
        "실력대 비슷",
        "선호 시간대",
        "매너 좋은 주최자",
        "곧 정원이 차요",
    ]


def test_reasons_are_empty_when_nothing_stands_out() -> None:
    far = cand(distances_km=(40.0, 40.0), avg_rating=1700.0, host_games=0, joined=0)
    assert score_candidate(user(), far, Weights()).reasons == []


def test_distance_reason_is_rounded_and_never_zero() -> None:
    r = score_candidate(user(), cand(distances_km=(0.2, 9.0)), Weights()).reasons
    assert r[0] == "집에서 약 1km"


def test_rank_filters_sorts_and_breaks_ties() -> None:
    near = cand(match_id=1, distances_km=(1.0, 9.0))
    far = cand(match_id=2, distances_km=(9.0, 9.5))
    soon = cand(match_id=3, starts_at=NOW + timedelta(hours=1))  # 하드 필터
    twin_a = cand(match_id=5, distances_km=(5.0, 9.0), starts_at=NOW + timedelta(days=2))
    twin_b = cand(match_id=4, distances_km=(5.0, 9.0), starts_at=NOW + timedelta(days=2))
    ranked = rank(user(), [far, soon, twin_a, near, twin_b], Weights(), NOW)
    assert [s.match_id for s in ranked] == [1, 4, 5, 2]  # 동점은 id순
    assert [s.match_id for s in rank(user(), [far, near], Weights(), NOW, limit=1)] == [1]


def test_slider_changes_order() -> None:
    close_but_off_level = cand(match_id=1, distances_km=(0.5, 9.0), avg_rating=1700.0, tier_max=5)
    far_but_same_level = cand(match_id=2, distances_km=(8.0, 9.0), avg_rating=1300.0)
    u = user(rating=1300.0, rd=50.0)
    by_distance = rank(
        u, [close_but_off_level, far_but_same_level], weights_for_slider(Weights(), 1.0), NOW
    )
    by_skill = rank(
        u, [close_but_off_level, far_but_same_level], weights_for_slider(Weights(), 0.0), NOW
    )
    assert by_distance[0].match_id == 1
    assert by_skill[0].match_id == 2
