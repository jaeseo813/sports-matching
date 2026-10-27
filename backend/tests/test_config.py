import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_production_rejects_default_jwt_secret() -> None:
    with pytest.raises(ValidationError):
        Settings(env="production", jwt_secret="change-me", _env_file=None)  # type: ignore[call-arg]


def test_production_accepts_custom_jwt_secret() -> None:
    s = Settings(env="production", jwt_secret="x" * 32, _env_file=None)  # type: ignore[call-arg]
    assert s.is_production
