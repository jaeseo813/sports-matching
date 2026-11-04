from typing import Protocol

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserBlock, UserLocation, UserSkill


class ProfileRepository(Protocol):
    async def list_skills(self, user_id: int) -> list[UserSkill]: ...
    async def get_skill(self, user_id: int, sport: str) -> UserSkill | None: ...
    async def add_skill(self, skill: UserSkill) -> UserSkill: ...
    async def list_locations(self, user_id: int) -> list[UserLocation]: ...
    async def get_location(self, user_id: int, slot: int) -> UserLocation | None: ...
    async def add_location(self, location: UserLocation) -> UserLocation: ...
    async def delete_location(self, user_id: int, slot: int) -> None: ...
    async def list_blocks(self, user_id: int) -> list[tuple[int, str]]: ...
    async def user_exists(self, user_id: int) -> bool: ...
    async def add_block(self, blocker_id: int, blocked_id: int) -> None: ...
    async def remove_block(self, blocker_id: int, blocked_id: int) -> None: ...
    async def commit(self) -> None: ...


class SqlProfileRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_skills(self, user_id: int) -> list[UserSkill]:
        stmt = select(UserSkill).where(UserSkill.user_id == user_id).order_by(UserSkill.sport)
        return list((await self._session.execute(stmt)).scalars())

    async def get_skill(self, user_id: int, sport: str) -> UserSkill | None:
        stmt = select(UserSkill).where(UserSkill.user_id == user_id, UserSkill.sport == sport)
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def add_skill(self, skill: UserSkill) -> UserSkill:
        self._session.add(skill)
        await self._session.flush()
        return skill

    async def list_locations(self, user_id: int) -> list[UserLocation]:
        stmt = (
            select(UserLocation).where(UserLocation.user_id == user_id).order_by(UserLocation.slot)
        )
        return list((await self._session.execute(stmt)).scalars())

    async def get_location(self, user_id: int, slot: int) -> UserLocation | None:
        stmt = select(UserLocation).where(
            UserLocation.user_id == user_id, UserLocation.slot == slot
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def add_location(self, location: UserLocation) -> UserLocation:
        self._session.add(location)
        await self._session.flush()
        return location

    async def delete_location(self, user_id: int, slot: int) -> None:
        await self._session.execute(
            delete(UserLocation).where(UserLocation.user_id == user_id, UserLocation.slot == slot)
        )

    async def list_blocks(self, user_id: int) -> list[tuple[int, str]]:
        stmt = (
            select(User.id, User.nickname)
            .join(UserBlock, UserBlock.blocked_id == User.id)
            .where(UserBlock.blocker_id == user_id)
            .order_by(User.id)
        )
        return [(uid, nick) for uid, nick in (await self._session.execute(stmt)).all()]

    async def user_exists(self, user_id: int) -> bool:
        stmt = select(User.id).where(User.id == user_id, User.is_active.is_(True))
        return (await self._session.execute(stmt)).scalar_one_or_none() is not None

    async def add_block(self, blocker_id: int, blocked_id: int) -> None:
        exists = await self._session.get(UserBlock, (blocker_id, blocked_id))
        if exists is None:  # 이미 차단했으면 그대로 둔다 (멱등)
            self._session.add(UserBlock(blocker_id=blocker_id, blocked_id=blocked_id))
            await self._session.flush()

    async def remove_block(self, blocker_id: int, blocked_id: int) -> None:
        await self._session.execute(
            delete(UserBlock).where(
                UserBlock.blocker_id == blocker_id, UserBlock.blocked_id == blocked_id
            )
        )

    async def commit(self) -> None:
        await self._session.commit()
