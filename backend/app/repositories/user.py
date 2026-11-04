from typing import Protocol

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import Gender
from app.models.user import User


class DuplicateUserError(Exception):
    """이메일 또는 닉네임 유니크 제약 위반."""


class UserRepository(Protocol):
    async def get_by_email(self, email: str) -> User | None: ...
    async def get_by_id(self, user_id: int) -> User | None: ...
    async def create(
        self, *, email: str, password: str, nickname: str, gender: Gender, birth_year: int
    ) -> User: ...


class SqlUserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_email(self, email: str) -> User | None:
        result = await self._session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_by_id(self, user_id: int) -> User | None:
        return await self._session.get(User, user_id)

    async def create(
        self, *, email: str, password: str, nickname: str, gender: Gender, birth_year: int
    ) -> User:
        user = User(
            email=email, password=password, nickname=nickname, gender=gender, birth_year=birth_year
        )
        self._session.add(user)
        try:
            await self._session.commit()  # 유니크 제약이 중복 가입 경합의 최종 방어선
        except IntegrityError as exc:
            await self._session.rollback()
            raise DuplicateUserError from exc
        return user
