import asyncio
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from httpx import ASGITransport, AsyncClient
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import get_settings
from app.main import app

_BACKEND = Path(__file__).resolve().parents[1]
# MariaDB: 1049 Unknown database, 1044 권한 없음(권한이 없으면 DB가 없어도 1044로 답한다)
_NO_TEST_DATABASE = {1044, 1049}
# 레포 루트에서 실행. 새 볼륨이면 docker/db-init/01-test-db.sql이 자동으로 실행된다
_CREATE_HINT = (
    "docker compose exec -T db sh -c 'mariadb -uroot -p\"$MARIADB_ROOT_PASSWORD\"' "
    "< docker/db-init/01-test-db.sql"
)


def _check_test_url(url: str) -> None:
    """테스트는 데이터를 넣고 지운다. 개발·운영 DB를 가리키면 시작 전에 멈춘다."""
    settings = get_settings()
    name = make_url(url).database or ""
    if not name.endswith("_test") or make_url(url) == make_url(settings.database_url):
        pytest.exit(f"TEST_DATABASE_URL은 개발 DB와 다른 *_test DB여야 합니다 (현재: {name})", 2)


async def _probe(url: str) -> int | None:
    """연결되면 None, 실패하면 MariaDB 오류 코드(알 수 없으면 0)."""
    engine = create_async_engine(url)
    try:
        async with engine.connect():
            return None
    except Exception as exc:  # noqa: BLE001 (DB가 꺼져 있으면 DB 테스트는 각자 건너뛴다)
        args = getattr(getattr(exc, "orig", None), "args", ())
        return args[0] if args and isinstance(args[0], int) else 0
    finally:
        await engine.dispose()


@pytest.fixture(scope="session", autouse=True)
def _test_database() -> None:
    """테스트 DB에 최신 스키마를 적용한다. DB 서버가 없으면 아무것도 하지 않는다."""
    url = get_settings().test_database_url
    _check_test_url(url)
    error = asyncio.run(_probe(url))
    if error in _NO_TEST_DATABASE:
        pytest.exit(
            f"테스트 DB(teamup_test)가 없거나 권한이 없습니다. 한 번만 만들어 주세요:\n  {_CREATE_HINT}",
            2,
        )
    if error is not None:
        return  # DB 서버 없음 → DB가 필요한 테스트는 각 픽스처에서 건너뛴다
    cfg = Config(str(_BACKEND / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", url.replace("%", "%%"))
    command.upgrade(cfg, "head")


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
