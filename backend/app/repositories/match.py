from datetime import datetime
from typing import Protocol

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import GenderPolicy, MatchStatus, ParticipationStatus
from app.models.match import Match, Participation
from app.models.user import User


class DuplicateParticipationError(Exception):
    """같은 매치에 이미 신청했다 (uq_participations_match_user)."""


class MatchRepository(Protocol):
    async def add_match(
        self,
        *,
        sport: str,
        host_id: int,
        venue_id: int,
        title: str,
        description: str | None,
        starts_at: datetime,
        duration_min: int,
        team_size: int,
        capacity: int,
        min_players: int,
        gender_policy: GenderPolicy,
        tier_min: int,
        tier_max: int,
    ) -> Match: ...
    async def get_match(self, match_id: int, *, for_update: bool = False) -> Match | None: ...
    async def list_open(self, *, sport: str | None, limit: int, offset: int) -> list[Match]: ...
    async def count_accepted(self, match_id: int) -> int: ...
    async def accepted_counts(self, match_ids: list[int]) -> dict[int, int]: ...
    async def get_participation(self, match_id: int, user_id: int) -> Participation | None: ...
    async def get_participation_by_id(
        self, match_id: int, participation_id: int
    ) -> Participation | None: ...
    async def add_participation(self, match_id: int, user_id: int) -> Participation: ...
    async def list_participations(self, match_id: int) -> list[tuple[Participation, str]]: ...
    async def list_upcoming_for_user(self, user_id: int, *, limit: int) -> list[Match]: ...
    async def count_upcoming_for_user(self, user_id: int) -> int: ...
    async def count_attended(self, user_id: int) -> int: ...
    async def commit(self) -> None: ...


# 내가 참가할 예정인 매치: 수락된 신청이 있고 아직 시작 전/확정 단계인 매치
_UPCOMING = (MatchStatus.OPEN, MatchStatus.FULL, MatchStatus.CONFIRMED)


class SqlMatchRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add_match(
        self,
        *,
        sport: str,
        host_id: int,
        venue_id: int,
        title: str,
        description: str | None,
        starts_at: datetime,
        duration_min: int,
        team_size: int,
        capacity: int,
        min_players: int,
        gender_policy: GenderPolicy,
        tier_min: int,
        tier_max: int,
    ) -> Match:
        match = Match(
            sport=sport,
            host_id=host_id,
            venue_id=venue_id,
            title=title,
            description=description,
            starts_at=starts_at,
            duration_min=duration_min,
            team_size=team_size,
            capacity=capacity,
            min_players=min_players,
            gender_policy=gender_policy,
            tier_min=tier_min,
            tier_max=tier_max,
            status=MatchStatus.OPEN,
        )
        self._session.add(match)
        await self._session.flush()
        return match

    async def get_match(self, match_id: int, *, for_update: bool = False) -> Match | None:
        stmt = select(Match).where(Match.id == match_id)
        if for_update:
            stmt = stmt.with_for_update()  # 정원 초과 경합 방지: 같은 매치의 수락을 직렬화한다
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def list_open(self, *, sport: str | None, limit: int, offset: int) -> list[Match]:
        stmt = select(Match).where(Match.status.in_([MatchStatus.OPEN, MatchStatus.FULL]))
        if sport is not None:
            stmt = stmt.where(Match.sport == sport)
        stmt = stmt.order_by(Match.starts_at, Match.id).limit(limit).offset(offset)
        return list((await self._session.execute(stmt)).scalars())

    async def count_accepted(self, match_id: int) -> int:
        stmt = select(func.count()).where(
            Participation.match_id == match_id,
            Participation.status == ParticipationStatus.ACCEPTED,
        )
        return int((await self._session.execute(stmt)).scalar_one())

    async def accepted_counts(self, match_ids: list[int]) -> dict[int, int]:
        if not match_ids:
            return {}
        stmt = (
            select(Participation.match_id, func.count())
            .where(
                Participation.match_id.in_(match_ids),
                Participation.status == ParticipationStatus.ACCEPTED,
            )
            .group_by(Participation.match_id)
        )
        return {mid: int(n) for mid, n in (await self._session.execute(stmt)).all()}

    async def get_participation(self, match_id: int, user_id: int) -> Participation | None:
        stmt = select(Participation).where(
            Participation.match_id == match_id, Participation.user_id == user_id
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def get_participation_by_id(
        self, match_id: int, participation_id: int
    ) -> Participation | None:
        # match_id까지 함께 걸어 다른 매치의 신청 id로 접근하지 못하게 한다 (객체 소유권 검사)
        stmt = select(Participation).where(
            Participation.id == participation_id, Participation.match_id == match_id
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def add_participation(self, match_id: int, user_id: int) -> Participation:
        part = Participation(match_id=match_id, user_id=user_id, status=ParticipationStatus.APPLIED)
        self._session.add(part)
        try:
            await self._session.flush()
        except IntegrityError as exc:
            await self._session.rollback()
            raise DuplicateParticipationError from exc
        return part

    async def list_participations(self, match_id: int) -> list[tuple[Participation, str]]:
        stmt = (
            select(Participation, User.nickname)
            .join(User, User.id == Participation.user_id)
            .where(Participation.match_id == match_id)
            .order_by(Participation.id)
        )
        return [(p, nick) for p, nick in (await self._session.execute(stmt)).all()]

    async def list_upcoming_for_user(self, user_id: int, *, limit: int) -> list[Match]:
        stmt = (
            select(Match)
            .join(Participation, Participation.match_id == Match.id)
            .where(
                Participation.user_id == user_id,
                Participation.status == ParticipationStatus.ACCEPTED,
                Match.status.in_(_UPCOMING),
            )
            .order_by(Match.starts_at, Match.id)
            .limit(limit)
        )
        return list((await self._session.execute(stmt)).scalars())

    async def count_upcoming_for_user(self, user_id: int) -> int:
        stmt = (
            select(func.count())
            .select_from(Participation)
            .join(Match, Match.id == Participation.match_id)
            .where(
                Participation.user_id == user_id,
                Participation.status == ParticipationStatus.ACCEPTED,
                Match.status.in_(_UPCOMING),
            )
        )
        return int((await self._session.execute(stmt)).scalar_one())

    async def count_attended(self, user_id: int) -> int:
        stmt = select(func.count()).where(
            Participation.user_id == user_id,
            Participation.status == ParticipationStatus.ATTENDED,
        )
        return int((await self._session.execute(stmt)).scalar_one())

    async def commit(self) -> None:
        await self._session.commit()
