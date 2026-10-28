from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_INSECURE_DEFAULT = "change-me"
_ROOT_ENV = Path(__file__).resolve().parents[3] / ".env"  # 레포 루트의 .env


class Settings(BaseSettings):
    # 환경변수는 이 클래스로만 읽는다 (os.environ 직접 접근 금지)
    model_config = SettingsConfigDict(env_file=_ROOT_ENV, extra="ignore")

    app_name: str = "TeamUp"  # 가칭 — 확정되면 AGENTS.md와 함께 수정
    env: Literal["local", "staging", "production"] = "local"
    cors_origins: list[str] = ["http://localhost:5173"]

    database_url: str = "mysql+asyncmy://teamup:change-me@localhost:3306/teamup"
    redis_url: str = "redis://localhost:6379/0"
    jwt_secret: str = _INSECURE_DEFAULT
    anthropic_api_key: str = ""
    kakao_map_key: str = ""

    @property
    def is_production(self) -> bool:
        return self.env == "production"

    @model_validator(mode="after")
    def _reject_default_secret_in_production(self) -> "Settings":
        if self.is_production and self.jwt_secret == _INSECURE_DEFAULT:
            raise ValueError("운영 환경에서는 JWT_SECRET을 반드시 변경해야 합니다")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
