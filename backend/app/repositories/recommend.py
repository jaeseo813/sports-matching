from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import MatchStatus, ParticipationStatus
from app.models.match import Match, Participation
from app.models.matching_weight import MatchingWeight
from app.models.user import User, UserSkill
from app.services.matching import Weights

CANDIDATE_LIMIT = 200  # 기준점마다 후보 상한 (AGENTS.md 4절)


@dataclass(frozen=True)
class CandidateRow:
    match: Match
    host_manner: float
    host_games: int
    host_no_shows: int
    joined: int
    avg_rating: float | None


@dataclass(frozen=True)
class Commitment:
    """사용자가 이미 신청했거나 참가 중인 매치 (하드 필터용)."""

    match_id: int
    starts_at: datetime
    duration_min: int
    status: ParticipationStatus


class RecommendRepository(Protocol):
    async def active_weights(self) -> Weights | None: ...
    async def distances_near(
        self,
        *,
        sport: str,
        lat: float,
        lng: float,
        radius_m: float,
        bbox: tuple[float, float, float, float],
        min_start: datetime,
    ) -> dict[int, float]: ...
    async def candidate_rows(self, match_ids: list[int], sport: str) -> list[CandidateRow]: ...
    async def commitments(self, user_id: int) -> list[Commitment]: ...


# 후보 매치: 모집 중이고 늦지 않게 시작하는 매치 중 구장이 반경 안에 있는 것.
# 모든 값은 바인드 파라미터. POINT/POLYGON WKT는 (lng lat) 순서, SRID는 4326.
_NEAR = text(
    """
    SELECT m.id AS id, ST_Distance_Sphere(v.point, ST_GeomFromText(:center, 4326)) AS dist
    FROM matches m
    JOIN venues v ON v.id = m.venue_id
    WHERE m.sport = :sport
      AND m.status = :status
      AND m.starts_at >= :min_start
      AND v.is_active = 1
      AND MBRContains(ST_GeomFromText(:bbox, 4326), v.point)
    HAVING dist <= :radius_m
    ORDER BY dist
    LIMIT :limit
    """
)


def _polygon_wkt(box: tuple[float, float, float, float]) -> str:
    min_lng, min_lat, max_lng, max_lat = box
    return (
        f"POLYGON(({min_lng} {min_lat}, {max_lng} {min_lat}, "
        f"{max_lng} {max_lat}, {min_lng} {max_lat}, {min_lng} {min_lat}))"
    )


class SqlRecommendRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def active_weights(self) -> Weights | None:
        stmt = select(MatchingWeight).where(MatchingWeight.is_active.is_(True)).limit(1)
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        if row is None:
            return None
        return Weights(row.w_dist, row.w_skill, row.w_time, row.w_host, row.w_fill)

    async def distances_near(
        self,
        *,
        sport: str,
        lat: float,
        lng: float,
        radius_m: float,
        bbox: tuple[float, float, float, float],
        min_start: datetime,
    ) -> dict[int, float]:
        result = await self._session.execute(
            _NEAR,
            {
                "center": f"POINT({lng} {lat})",
                "bbox": _polygon_wkt(bbox),
                "sport": sport,
                "status": MatchStatus.OPEN.value,
                "min_start": min_start,
                "radius_m": radius_m,
                "limit": CANDIDATE_LIMIT,
            },
        )
        return {int(r.id): float(r.dist) for r in result.all()}

    async def candidate_rows(self, match_ids: list[int], sport: str) -> list[CandidateRow]:
        if not match_ids:
            return []
        matches = list(
            (await self._session.execute(select(Match).where(Match.id.in_(match_ids)))).scalars()
        )
        hosts = {
            u.id: u
            for u in (
                await self._session.execute(
                    select(User).where(User.id.in_({m.host_id for m in matches}))
                )
            ).scalars()
        }
        stats = await self._session.execute(
            select(
                Participation.match_id,
                func.count(),
                func.avg(UserSkill.rating),
            )
            .outerjoin(
                UserSkill,
                (UserSkill.user_id == Participation.user_id) & (UserSkill.sport == sport),
            )
            .where(
                Participation.match_id.in_(match_ids),
                Participation.status == ParticipationStatus.ACCEPTED,
            )
            .group_by(Participation.match_id)
        )
        by_match = {mid: (int(n), None if avg is None else float(avg)) for mid, n, avg in stats}
        rows = []
        for m in matches:
            host = hosts.get(m.host_id)
            if host is None:
                continue
            joined, avg = by_match.get(m.id, (0, None))
            rows.append(
                CandidateRow(
                    m, host.manner_score, host.games_played, host.no_show_count, joined, avg
                )
            )
        return rows

    async def commitments(self, user_id: int) -> list[Commitment]:
        stmt = (
            select(Match.id, Match.starts_at, Match.duration_min, Participation.status)
            .join(Participation, Participation.match_id == Match.id)
            .where(
                Participation.user_id == user_id,
                Participation.status != ParticipationStatus.CANCELED,
            )
        )
        return [Commitment(*row) for row in (await self._session.execute(stmt)).all()]
