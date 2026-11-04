"""팀 분배. DB 없는 순수 함수.

순서: 필수 포지션 배치(풋살은 팀당 GK 1) → rating 스네이크 드래프트 → 2-opt 스왑으로 팀 합 편차 최소화.
주최자가 수동으로 조정한 결과는 이 모듈이 다시 건드리지 않는다 (is_manual은 호출하는 쪽이 관리).
"""

from collections.abc import Sequence
from dataclasses import dataclass


class BalanceError(Exception):
    """제약을 만족하는 분배가 불가능하다 (예: GK가 팀 수보다 적다)."""


@dataclass(frozen=True)
class Player:
    user_id: int
    rating: float
    position: str | None = None


@dataclass(frozen=True)
class Assignment:
    teams: tuple[tuple[int, ...], ...]  # 팀별 user_id
    sums: tuple[float, ...]  # 팀별 rating 합
    spread: float  # 최대 합 - 최소 합


def _snake_order(team_count: int, rounds: int) -> list[int]:
    order: list[int] = []
    for r in range(rounds):
        seq = range(team_count) if r % 2 == 0 else range(team_count - 1, -1, -1)
        order.extend(seq)
    return order


def _capacities(total: int, team_count: int) -> list[int]:
    base, extra = divmod(total, team_count)
    return [base + (1 if i < extra else 0) for i in range(team_count)]


def _count(team: list[Player], position: str) -> int:
    return sum(1 for p in team if p.position == position)


def _spread(sums: Sequence[float]) -> float:
    return max(sums) - min(sums)


def _cost(sums: Sequence[float]) -> float:
    """스왑 판단 기준: 팀 합의 평균 제곱 편차. 팀이 2개면 spread 최소화와 같고,
    3개 이상에서도 최대-최소가 변하지 않는 구간에서 막히지 않는다."""
    mean = sum(sums) / len(sums)
    return sum((s - mean) ** 2 for s in sums)


def _swap_keeps_constraints(
    a: Player, b: Player, team_a: list[Player], team_b: list[Player], required: dict[str, int]
) -> bool:
    """a와 b를 맞바꿔도 두 팀이 필수 포지션 인원을 계속 채우는지 본다."""
    for pos, need in required.items():
        in_a = _count(team_a, pos) - (a.position == pos) + (b.position == pos)
        in_b = _count(team_b, pos) - (b.position == pos) + (a.position == pos)
        if in_a < need or in_b < need:
            return False
    return True


def balance(
    players: Sequence[Player], team_count: int = 2, required_per_team: dict[str, int] | None = None
) -> Assignment:
    required = required_per_team or {}
    if team_count < 2:
        raise BalanceError("팀은 2개 이상이어야 합니다")
    if len(players) < team_count:
        raise BalanceError("팀 수보다 참가자가 적습니다")
    if len({p.user_id for p in players}) != len(players):
        raise BalanceError("같은 참가자가 중복되었습니다")

    caps = _capacities(len(players), team_count)
    teams: list[list[Player]] = [[] for _ in range(team_count)]
    remaining = sorted(players, key=lambda p: (-p.rating, p.user_id))

    # 1) 필수 포지션: 포지션별로 팀마다 need명씩 먼저 채운다 (rating 높은 순을 스네이크로 배분)
    for pos, need in required.items():
        pool = [p for p in remaining if p.position == pos]
        if len(pool) < need * team_count:
            raise BalanceError(f"{pos} 포지션이 팀당 {need}명씩 필요하지만 {len(pool)}명뿐입니다")
        if need > min(caps):
            raise BalanceError("필수 포지션 인원이 팀 정원보다 많습니다")
        chosen = pool[: need * team_count]
        for p, t in zip(chosen, _snake_order(team_count, need), strict=True):
            teams[t].append(p)
        remaining = [p for p in remaining if p not in chosen]

    # 2) 나머지는 rating 순 스네이크 드래프트. 정원이 찬 팀은 건너뛴다
    t = 0
    direction = 1
    for p in remaining:
        guard = 0
        while len(teams[t]) >= caps[t]:
            t, direction = _advance(t, direction, team_count)
            guard += 1
            if guard > 2 * team_count:
                raise BalanceError("정원 계산 오류")
        teams[t].append(p)
        t, direction = _advance(t, direction, team_count)

    # 3) 2-opt: 두 팀에서 한 명씩 맞바꿔 편차(_cost)가 줄면 적용. 더 줄일 수 없을 때까지 반복
    improved = True
    while improved:
        improved = False
        sums = [sum(p.rating for p in team) for team in teams]
        current = _cost(sums)
        best: tuple[float, int, int, int, int] | None = None
        for i in range(team_count):
            for j in range(i + 1, team_count):
                for ai, a in enumerate(teams[i]):
                    for bi, b in enumerate(teams[j]):
                        if a.rating == b.rating:
                            continue
                        if not _swap_keeps_constraints(a, b, teams[i], teams[j], required):
                            continue
                        new_sums = list(sums)
                        new_sums[i] += b.rating - a.rating
                        new_sums[j] += a.rating - b.rating
                        new_cost = _cost(new_sums)
                        if new_cost < current - 1e-9 and (best is None or new_cost < best[0]):
                            best = (new_cost, i, ai, j, bi)
        if best is not None:
            _, i, ai, j, bi = best
            teams[i][ai], teams[j][bi] = teams[j][bi], teams[i][ai]
            improved = True

    sums = [sum(p.rating for p in team) for team in teams]
    return Assignment(
        teams=tuple(tuple(p.user_id for p in team) for team in teams),
        sums=tuple(sums),
        spread=_spread(sums),
    )


def _advance(t: int, direction: int, team_count: int) -> tuple[int, int]:
    """스네이크 진행: 끝 팀에서는 방향만 바꾸고 같은 팀이 한 번 더 뽑는다."""
    nxt = t + direction
    if 0 <= nxt < team_count:
        return nxt, direction
    return t, -direction


def closeness_level(sums: Sequence[float]) -> int:
    """접전도 게이지(1~5). 팀 합 차이가 전체 대비 작을수록 높다."""
    total = sum(sums)
    if total <= 0:
        return 1
    rel = _spread(sums) / (total / len(sums))
    for level, limit in ((5, 0.02), (4, 0.05), (3, 0.10), (2, 0.20)):
        if rel < limit:
            return level
    return 1
