"""가입한 사용자를 관리자로 지정한다 (구장 등록용). 관리자를 만드는 API는 두지 않는다.

cd backend && uv run python -m scripts.make_admin user@example.com
"""

import asyncio
import sys

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.core.config import get_settings
from app.models.enums import Role
from app.models.user import User


async def main(email: str) -> None:
    engine = create_async_engine(get_settings().database_url)
    async with AsyncSession(engine, expire_on_commit=False) as session:
        user = (await session.execute(select(User).where(User.email == email))).scalar_one_or_none()
        if user is None:
            sys.exit("가입한 사용자가 아닙니다")
        user.role = Role.ADMIN
        await session.commit()
        print(f"관리자로 지정했습니다: {user.nickname}")
    await engine.dispose()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("사용법: uv run python -m scripts.make_admin <이메일>")
    asyncio.run(main(sys.argv[1]))
