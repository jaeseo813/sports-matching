from dataclasses import dataclass
from typing import Protocol

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import ParticipationStatus
from app.models.match import Participation, TeamAssignment
from app.models.user import User, UserSkill


@dataclass(frozen=True)
class PlayerRow:
    user_id: int
    nickname: str
    rating: float | None  # 실력 등록이 없으면 None
    position: str | None


@dataclass(frozen=True)
class TeamRow:
    user_id: int
    nickname: str
    team_no: int
    position: str | None
    is_manual: bool
    rating: float | None


class TeamRepository(Protocol):
    async def accepted_players(self, match_id: int, sport: str) -> list[PlayerRow]: ...
    async def replace_teams(
        self, match_id: int, rows: list[tuple[int, int, str | None, bool]]
    ) -> None: ...
    async def list_teams(self, match_id: int, sport: str) -> list[TeamRow]: ...
    async def commit(self) -> None: ...


class SqlTeamRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def accepted_players(self, match_id: int, sport: str) -> list[PlayerRow]:
        stmt = (
            select(Participation.user_id, User.nickname, UserSkill.rating, Participation.position)
            .join(User, User.id == Participation.user_id)
            .outerjoin(
                UserSkill,
                (UserSkill.user_id == Participation.user_id) & (UserSkill.sport == sport),
            )
            .where(
                Participation.match_id == match_id,
                Participation.status == ParticipationStatus.ACCEPTED,
            )
            .order_by(Participation.id)
        )
        return [PlayerRow(*row) for row in (await self._session.execute(stmt)).all()]

    async def replace_teams(
        self, match_id: int, rows: list[tuple[int, int, str | None, bool]]
    ) -> None:
        await self._session.execute(
            delete(TeamAssignment).where(TeamAssignment.match_id == match_id)
        )
        self._session.add_all(
            TeamAssignment(
                match_id=match_id, user_id=uid, team_no=team_no, position=pos, is_manual=manual
            )
            for uid, team_no, pos, manual in rows
        )
        await self._session.flush()

    async def list_teams(self, match_id: int, sport: str) -> list[TeamRow]:
        stmt = (
            select(
                TeamAssignment.user_id,
                User.nickname,
                TeamAssignment.team_no,
                TeamAssignment.position,
                TeamAssignment.is_manual,
                UserSkill.rating,
            )
            .join(User, User.id == TeamAssignment.user_id)
            .outerjoin(
                UserSkill,
                (UserSkill.user_id == TeamAssignment.user_id) & (UserSkill.sport == sport),
            )
            .where(TeamAssignment.match_id == match_id)
            .order_by(TeamAssignment.team_no, TeamAssignment.id)
        )
        return [TeamRow(*row) for row in (await self._session.execute(stmt)).all()]

    async def commit(self) -> None:
        await self._session.commit()
