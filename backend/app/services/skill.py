"""실력 모델: 상호 평가(better/similar/worse)를 Glicko-2 변형으로 반영한다. DB 없는 순수 함수.

한 경기의 리뷰는 한 번의 rating period로 묶는다. 숫자 레이팅은 사용자에게 노출하지 않고
티어 배지(tier_from_rating)와 추이(trend_of)만 보여준다.
"""

import math
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Literal

from app.models.enums import Verdict

_SCALE = 173.7178  # Glicko-2 내부 척도 변환 상수
_TAU = 0.5  # 변동성 변화 제약 (0.3~1.2 권장)
_EPS = 1e-6
_BASE_BY_TIER = {1: 900, 2: 1100, 3: 1300, 4: 1500, 5: 1700}

MAX_DELTA_PER_MATCH = 80  # 경기당 Δrating 상한
MIN_REVIEW_RATE = 0.5  # 리뷰 제출률이 이 미만이면 갱신 보류
PAIR_COOLDOWN_DAYS = 30  # 같은 쌍은 30일 내 1회만 반영
DEFAULT_VOLATILITY = 0.06

Trend = Literal["up", "same", "down"]


@dataclass(frozen=True)
class PlayerSkill:
    rating: float
    rd: float
    volatility: float = DEFAULT_VOLATILITY


@dataclass(frozen=True)
class Review:
    reviewer_id: int
    reviewee_id: int
    verdict: Verdict


def initial_skill(self_tier: int, years_played: int) -> PlayerSkill:
    """자기평가 티어(1~5)와 구력으로 초기값을 만든다. RD는 구력이 길수록 300에 가까워진다."""
    if self_tier not in _BASE_BY_TIER:
        raise ValueError("self_tier는 1~5여야 합니다")
    years = max(0, min(years_played, 5))
    return PlayerSkill(rating=_BASE_BY_TIER[self_tier] + years * 15, rd=350 - years * 10)


def tier_from_rating(rating: float) -> int:
    """티어 배지용. 구간 경계는 초기 티어 값(900/1100/…)의 중간이다."""
    for tier, upper in ((1, 1000), (2, 1200), (3, 1400), (4, 1600)):
        if rating < upper:
            return tier
    return 5


def trend_of(delta: float) -> Trend:
    """최근 변화량으로 ↑/→/↓ 추이를 정한다."""
    if delta >= 15:
        return "up"
    if delta <= -15:
        return "down"
    return "same"


def _g(phi: float) -> float:
    return 1 / math.sqrt(1 + 3 * phi**2 / math.pi**2)


def _expected(mu: float, mu_j: float, phi_j: float) -> float:
    return 1 / (1 + math.exp(-_g(phi_j) * (mu - mu_j)))


def glicko2_update(skill: PlayerSkill, games: Iterable[tuple[float, float, float]]) -> PlayerSkill:
    """Glicko-2 한 번의 rating period. games = (상대 rating, 상대 RD, 내 점수 0~1)."""
    mu = (skill.rating - 1500) / _SCALE
    phi = skill.rd / _SCALE
    sigma = skill.volatility
    results = [((r - 1500) / _SCALE, rd / _SCALE, s) for r, rd, s in games]

    if not results:  # 경기가 없으면 RD만 불확실성만큼 커진다
        return PlayerSkill(skill.rating, _SCALE * math.sqrt(phi**2 + sigma**2), sigma)

    v_inv = 0.0
    score_sum = 0.0
    for mu_j, phi_j, s in results:
        e = _expected(mu, mu_j, phi_j)
        v_inv += _g(phi_j) ** 2 * e * (1 - e)
        score_sum += _g(phi_j) * (s - e)
    v = 1 / v_inv
    delta = v * score_sum

    a = math.log(sigma**2)

    def f(x: float) -> float:
        ex = math.exp(x)
        return ex * (delta**2 - phi**2 - v - ex) / (2 * (phi**2 + v + ex) ** 2) - (x - a) / _TAU**2

    big_a = a
    if delta**2 > phi**2 + v:
        big_b = math.log(delta**2 - phi**2 - v)
    else:
        k = 1
        while f(a - k * _TAU) < 0:
            k += 1
        big_b = a - k * _TAU
    f_a, f_b = f(big_a), f(big_b)
    while abs(big_b - big_a) > _EPS:  # Illinois 알고리즘
        c = big_a + (big_a - big_b) * f_a / (f_b - f_a)
        f_c = f(c)
        if f_c * f_b <= 0:
            big_a, f_a = big_b, f_b
        else:
            f_a /= 2
        big_b, f_b = c, f_c
    new_sigma = math.exp(big_a / 2)

    phi_star = math.sqrt(phi**2 + new_sigma**2)
    new_phi = 1 / math.sqrt(1 / phi_star**2 + 1 / v)
    new_mu = mu + new_phi**2 * score_sum
    return PlayerSkill(_SCALE * new_mu + 1500, _SCALE * new_phi, new_sigma)


def verdict_score(verdict: Verdict) -> float:
    """평가자 입장의 점수. 상대가 더 낫다면 내가 진 것과 같다."""
    return {Verdict.BETTER: 0.0, Verdict.SIMILAR: 0.5, Verdict.WORSE: 1.0}[verdict]


def review_rate_ok(reviewers: int, players: int) -> bool:
    return players > 0 and reviewers / players >= MIN_REVIEW_RATE


def usable_reviews(
    reviews: Iterable[Review], recent_pairs: frozenset[tuple[int, int]]
) -> list[Review]:
    """자기 평가, 30일 내 이미 반영된 쌍, 같은 경기의 중복 쌍을 걸러낸다."""
    seen: set[tuple[int, int]] = set()
    kept = []
    for r in reviews:
        pair = (r.reviewer_id, r.reviewee_id)
        if r.reviewer_id == r.reviewee_id or pair in recent_pairs or pair in seen:
            continue
        seen.add(pair)
        kept.append(r)
    return kept


def rate_match(
    skills: dict[int, PlayerSkill],
    reviews: Iterable[Review],
    *,
    recent_pairs: frozenset[tuple[int, int]] = frozenset(),
) -> dict[int, PlayerSkill]:
    """한 경기의 리뷰를 모아 참가자별 새 실력을 계산한다. 갱신 대상이 없으면 빈 dict.

    모든 계산은 경기 전 값을 기준으로 하고(한 번의 rating period), 변화량은 ±80으로 자른다.
    리뷰 제출률이 50% 미만이면 갱신을 보류한다.
    """
    valid = [
        r
        for r in usable_reviews(reviews, recent_pairs)
        if r.reviewer_id in skills and r.reviewee_id in skills
    ]
    if not review_rate_ok(len({r.reviewer_id for r in valid}), len(skills)):
        return {}

    games: dict[int, list[tuple[float, float, float]]] = {pid: [] for pid in skills}
    for r in valid:
        score = verdict_score(r.verdict)
        me, other = skills[r.reviewer_id], skills[r.reviewee_id]
        games[r.reviewer_id].append((other.rating, other.rd, score))
        games[r.reviewee_id].append((me.rating, me.rd, 1 - score))

    updated: dict[int, PlayerSkill] = {}
    for pid, played in games.items():
        if not played:
            continue
        new = glicko2_update(skills[pid], played)
        delta = max(-MAX_DELTA_PER_MATCH, min(MAX_DELTA_PER_MATCH, new.rating - skills[pid].rating))
        updated[pid] = PlayerSkill(skills[pid].rating + delta, new.rd, new.volatility)
    return updated


def update_manner(score: float, flags_received: int, reviews_received: int) -> float:
    """매너 점수(0~5). 레이팅과 분리한다. 신고 1건당 -0.3, 신고 없는 리뷰 1건당 +0.05."""
    clean = max(reviews_received - flags_received, 0)
    return max(0.0, min(5.0, score - 0.3 * flags_received + 0.05 * clean))
