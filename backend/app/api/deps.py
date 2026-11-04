from typing import Annotated

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.security import TokenError, decode_token
from app.models.enums import Role
from app.models.user import User
from app.repositories.user import SqlUserRepository, UserRepository
from app.repositories.venue import SqlVenueRepository, VenueRepository

_bearer = HTTPBearer(auto_error=False)


def _unauthorized() -> HTTPException:
    return HTTPException(
        status_code=401,
        detail={"code": "UNAUTHORIZED", "message": "로그인이 필요합니다"},
    )


async def get_user_repo(session: Annotated[AsyncSession, Depends(get_session)]) -> UserRepository:
    return SqlUserRepository(session)


UserRepo = Annotated[UserRepository, Depends(get_user_repo)]


async def get_venue_repo(session: Annotated[AsyncSession, Depends(get_session)]) -> VenueRepository:
    return SqlVenueRepository(session)


VenueRepo = Annotated[VenueRepository, Depends(get_venue_repo)]


async def require_user(
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)], repo: UserRepo
) -> User:
    if creds is None:
        raise _unauthorized()
    try:
        claims = decode_token(creds.credentials, "access")
    except TokenError:
        raise _unauthorized() from None
    user = await repo.get_by_id(int(claims["sub"]))
    if user is None or not user.is_active:
        raise _unauthorized()
    return user


async def require_admin(user: Annotated[User, Depends(require_user)]) -> User:
    if user.role != Role.ADMIN:
        raise HTTPException(
            status_code=403,
            detail={"code": "FORBIDDEN", "message": "권한이 없습니다"},
        )
    return user


CurrentUser = Annotated[User, Depends(require_user)]

