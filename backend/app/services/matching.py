"""추천 스코어링. DB 없는 순수 함수이며 순위는 여기서 정한다 (챗봇은 정하지 않는다).

total = w_dist·S_dist + w_skill·S_skill + w_time·S_time + w_host·S_host + w_fill·S_fill
모든 항은 [0, 1]이고, 응답에는 score·breakdown·reasons(추천 이유 칩)를 항상 함께 내보낸다.
"""

import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from app.models.enums import Gender, GenderPolicy
from app.services.skill import tier_from_rating

MIN_LEAD_TIME = timedelta(hours=2)  # 시작까지 이 시간 미만이면 추천에서 제외
NEW_HOST_GAMES = 3  # 이 경기 수 미만이면 주최자 점수는 기본값
NEW_HOST_SCORE = 0.6
_DIST_POWER = 1.5
_SKILL_BASE_SIGMA = 150.0
_SKILL_RD_FACTOR = 0.5
_FILL_GOOD = (0.6, 1.0)
_FILL_OTHER = 0.5
_ADJACENT_TIME = 0.3

# 시간대: 시작 시각(시)로 구분하고, 인접은 순환(밤↔새벽 포함)으로 본다
_SLOTS = ("dawn", "morning", "afternoon", "evening")  # 0-6, 6-12, 12-18, 18-24


@dataclass(frozen=True)
class Weights:
    w_dist: float = 0.35
    w_skill: float = 0.30
    w_time: float = 0.20
    w_host: float = 0.10
    w_fill: float = 0.05

    def total(self) -> float:
        return self.w_dist + self.w_skill + self.w_time + self.w_host + self.w_fill


@dataclass(frozen=True)
class UserContext:
    user_id: int
    gender: Gender
    rating: float
    rd: float
    location_labels: tuple[str, ...]  # 기준점 이름 (예: 집, 학교)
    max_distance_km: tuple[float, ...]  # 기준점별 d_max
    preferred_slots: frozenset[str] = frozenset()  # 비어 있으면 시간대 선호 없음
    blocked_hosts: frozenset[int] = frozenset()
    excluded_match_ids: frozenset[int] = frozenset()  # 이미 지원했거나 거절된 매치
    busy: tuple[tuple[datetime, datetime], ...] = ()  # 이미 잡힌 일정 (시작, 끝)


@dataclass(frozen=True)
class Candidate:
    match_id: int
    starts_at: datetime
    duration_min: int
    gender_policy: GenderPolicy
    tier_min: int
    tier_max: int
    capacity: int
    joined: int
    min_players: int
    host_id: int
    host_manner: float  # 0~5
    host_games: int
    host_no_shows: int
    avg_rating: float | None  # 참가자 평균 rating, 아무도 없으면 None
    distances_km: tuple[float, ...]  # user.location_* 과 같은 순서


@dataclass(frozen=True)
class Breakdown:
    dist: float
    skill: float
    time: float
    host: float
    fill: float


@dataclass(frozen=True)
class Scored:
    match_id: int
    score: float
    breakdown: Breakdown
    reasons: list[str] = field(default_factory=list)


# --- 개별 항 -------------------------------------------------------------------


def s_dist(distance_km: float, d_max_km: float) -> float:
    if d_max_km <= 0:
        return 0.0
    return max(0.0, 1 - math.pow(max(distance_km, 0.0) / d_max_km, _DIST_POWER))


def s_dist_best(distances_km: tuple[float, ...], d_max_km: tuple[float, ...]) -> tuple[float, int]:
    """기준점이 여러 개면 최대값. (점수, 가장 좋았던 기준점 인덱스)"""
    best, best_i = 0.0, 0
    for i, (d, d_max) in enumerate(zip(distances_km, d_max_km, strict=False)):
        s = s_dist(d, d_max)
        if s > best:
            best, best_i = s, i
    return best, best_i


def target_rating(avg_rating: float | None, tier_min: int, tier_max: int) -> float:
    """매치가 기대하는 실력. 참가자가 있으면 평균, 없으면 티어 범위의 가운데."""
    if avg_rating is not None:
        return avg_rating
    mid = {1: 900, 2: 1100, 3: 1300, 4: 1500, 5: 1700}
    return (mid[tier_min] + mid[tier_max]) / 2


def s_skill(rating: float, rd: float, target: float, tier_min: int, tier_max: int) -> float:
    """티어 범위 밖이면 0 (하드 필터가 아니라 점수로 반영)."""
    if not tier_min <= tier_from_rating(rating) <= tier_max:
        return 0.0
    sigma = _SKILL_BASE_SIGMA + rd * _SKILL_RD_FACTOR
    return math.exp(-((rating - target) ** 2) / (2 * sigma**2))


def slot_of(when: datetime) -> str:
    return _SLOTS[when.hour // 6]


def s_time(when: datetime, preferred: frozenset[str]) -> float:
    """선호 시간대와 일치 1.0 / 인접 0.3 / 불일치 0. 선호가 없으면 1.0 (제약 없음)."""
    if not preferred:
        return 1.0
    slot = slot_of(when)
    if slot in preferred:
        return 1.0
    i = _SLOTS.index(slot)
    neighbors = {_SLOTS[(i - 1) % len(_SLOTS)], _SLOTS[(i + 1) % len(_SLOTS)]}
    return _ADJACENT_TIME if neighbors & preferred else 0.0


def s_host(manner: float, games: int, no_shows: int) -> float:
    if games < NEW_HOST_GAMES:
        return NEW_HOST_SCORE
    no_show_rate = min(max(no_shows / games, 0.0), 1.0)
    return max(0.0, min(manner, 5.0)) / 5 * (1 - no_show_rate)


def s_fill(joined: int, capacity: int) -> float:
    ratio = joined / capacity if capacity else 0.0
    return 1.0 if _FILL_GOOD[0] <= ratio <= _FILL_GOOD[1] else _FILL_OTHER


# --- 가중치 --------------------------------------------------------------------


def weights_for_slider(base: Weights, slider: float) -> Weights:
    """거리↔실력 슬라이더(0=실력 우선, 1=거리 우선). 두 가중치의 합은 그대로 유지한다."""
    s = max(0.0, min(1.0, slider))
    pair = base.w_dist + base.w_skill
    return Weights(pair * s, pair * (1 - s), base.w_time, base.w_host, base.w_fill)


# --- 하드 필터 -----------------------------------------------------------------


def gender_allowed(policy: GenderPolicy, gender: Gender) -> bool:
    if policy is GenderPolicy.MALE_ONLY:
        return gender is Gender.MALE
    if policy is GenderPolicy.FEMALE_ONLY:
        return gender is Gender.FEMALE
    return True


def exclusion_reason(user: UserContext, c: Candidate, now: datetime) -> str | None:
    """추천에서 빼야 하면 사유를, 아니면 None을 돌려준다."""
    if c.starts_at - now < MIN_LEAD_TIME:
        return "starts_soon"
    if not gender_allowed(c.gender_policy, user.gender):
        return "gender_policy"
    if c.match_id in user.excluded_match_ids:
        return "already_applied_or_rejected"
    if c.host_id in user.blocked_hosts:
        return "blocked_host"
    end = c.starts_at + timedelta(minutes=c.duration_min)
    if any(c.starts_at < b_end and b_start < end for b_start, b_end in user.busy):
        return "time_overlap"
    return None


# --- 점수와 이유 ---------------------------------------------------------------


def _reasons(user: UserContext, c: Candidate, bd: Breakdown, loc_i: int) -> list[str]:
    reasons = []
    if bd.dist >= 0.5 and loc_i < len(user.location_labels):
        km = max(1, round(c.distances_km[loc_i]))  # 거리는 반올림해서만 노출한다
        reasons.append(f"{user.location_labels[loc_i]}에서 약 {km}km")
    if bd.skill >= 0.7:
        reasons.append("실력대 비슷")
    if user.preferred_slots and bd.time == 1.0:
        reasons.append("선호 시간대")
    if c.host_games >= NEW_HOST_GAMES and bd.host >= 0.8:
        reasons.append("매너 좋은 주최자")
    if c.capacity and c.joined / c.capacity >= 0.75:
        reasons.append("곧 정원이 차요")
    return reasons


def score_candidate(user: UserContext, c: Candidate, weights: Weights) -> Scored:
    dist, loc_i = s_dist_best(c.distances_km, user.max_distance_km)
    bd = Breakdown(
        dist=dist,
        skill=s_skill(
            user.rating,
            user.rd,
            target_rating(c.avg_rating, c.tier_min, c.tier_max),
            c.tier_min,
            c.tier_max,
        ),
        time=s_time(c.starts_at, user.preferred_slots),
        host=s_host(c.host_manner, c.host_games, c.host_no_shows),
        fill=s_fill(c.joined, c.capacity),
    )
    total = (
        weights.w_dist * bd.dist
        + weights.w_skill * bd.skill
        + weights.w_time * bd.time
        + weights.w_host * bd.host
        + weights.w_fill * bd.fill
    )
    return Scored(c.match_id, round(total, 4), bd, _reasons(user, c, bd, loc_i))


def rank(
    user: UserContext,
    candidates: list[Candidate],
    weights: Weights,
    now: datetime,
    *,
    limit: int | None = None,
) -> list[Scored]:
    """하드 필터를 통과한 후보를 점수순으로 정렬한다. 동점은 시작이 빠른 순, 그다음 id순."""
    starts = {c.match_id: c.starts_at for c in candidates}
    scored = [
        score_candidate(user, c, weights)
        for c in candidates
        if exclusion_reason(user, c, now) is None
    ]
    scored.sort(key=lambda s: (-s.score, starts[s.match_id], s.match_id))
    return scored[:limit] if limit is not None else scored
