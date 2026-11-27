import pytest
from pydantic import ValidationError

from app.core.config import Settings

SAFE = {
    "jwt_secret": "x" * 32,
    "database_url": "mysql+asyncmy://teamup:strong-pass@db:3306/teamup",
    "cors_origins": ["https://teamup.example"],
}


def make(**kwargs: object) -> Settings:
    return Settings(_env_file=None, **{**SAFE, **kwargs})  # type: ignore[arg-type]


def test_local_allows_dev_defaults() -> None:
    assert Settings(_env_file=None).env == "local"  # type: ignore[call-arg]


@pytest.mark.parametrize("env", ["staging", "production"])
@pytest.mark.parametrize(
    "bad",
    [
        {"jwt_secret": "change-me"},
        {"jwt_secret": "short-but-not-default"},
        {"database_url": "mysql+asyncmy://teamup:change-me@db:3306/teamup"},
    ],
)
def test_outside_local_rejects_dev_values(env: str, bad: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        make(env=env, **bad)


def test_production_rejects_localhost_cors() -> None:
    with pytest.raises(ValidationError):
        make(env="production", cors_origins=["http://localhost:5173"])
    assert make(env="staging", cors_origins=["http://localhost:5173"]).env == "staging"


def test_production_accepts_safe_values() -> None:
    assert make(env="production").is_production
