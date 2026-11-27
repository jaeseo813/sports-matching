from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_INSECURE_DEFAULT = "change-me"
_MIN_SECRET_LEN = 32  # HS256 키는 32바이트 이상 (RFC 7518 3.2)
_ROOT_ENV = Path(__file__).resolve().parents[3] / ".env"  # 레포 루트의 .env


class Settings(BaseSettings):
    # 환경변수는 이 클래스로만 읽는다 (os.environ 직접 접근 금지)
    model_config = SettingsConfigDict(env_file=_ROOT_ENV, extra="ignore")

    app_name: str = "TeamUp"  # 가칭 — 확정되면 AGENTS.md와 함께 수정
    env: Literal["local", "staging", "production"] = "local"
    cors_origins: list[str] = ["http://localhost:5173"]

    database_url: str = "mysql+asyncmy://teamup:change-me@localhost:3306/teamup"
    # pytest 전용. 개발 DB와 분리해 화면 확인용 데이터가 테스트를 깨뜨리지 않게 한다 (이름은 _test로 끝나야 한다)
    test_database_url: str = "mysql+asyncmy://teamup:change-me@localhost:3306/teamup_test"
    jwt_secret: str = _INSECURE_DEFAULT
    access_token_minutes: int = (
        60 * 24
    )  # refresh 토큰 없이 access 하나만 쓴다 (만료되면 다시 로그인)
    # 챗봇 LLM: DeepSeek (OpenAI 호환 API, openai 패키지의 AsyncOpenAI에 base_url만 바꿔 쓴다)
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-flash"
    kakao_map_key: str = ""
    # /metrics 보호: 있으면 Authorization: Bearer <값>이 맞아야 한다. 비우면 local에서만 열린다
    metrics_token: str = ""

    @property
    def is_production(self) -> bool:
        return self.env == "production"

    @model_validator(mode="after")
    def _reject_unsafe_values_outside_local(self) -> "Settings":
        """스테이징·운영에서 개발용 값이 남아 있으면 서버가 시작되지 않게 한다 (docs/deploy.md)."""
        if self.env == "local":
            return self
        if self.jwt_secret == _INSECURE_DEFAULT or len(self.jwt_secret) < _MIN_SECRET_LEN:
            raise ValueError(
                f"{self.env}: JWT_SECRET을 {_MIN_SECRET_LEN}자 이상 무작위 값으로 바꿔야 합니다"
            )
        if f":{_INSECURE_DEFAULT}@" in self.database_url:
            raise ValueError(f"{self.env}: DATABASE_URL의 기본 비밀번호를 바꿔야 합니다")
        if self.is_production and any("localhost" in o for o in self.cors_origins):
            raise ValueError("production: CORS_ORIGINS에 실제 화면 주소만 넣어야 합니다")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
