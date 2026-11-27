# ruff: noqa: F401, F811  (pytest 픽스처를 test_auth_api에서 가져와 쓴다)
"""/metrics 접근 제한: METRICS_TOKEN이 있으면 Bearer 토큰이 맞아야 하고, 없으면 local에서만 열린다."""

from collections.abc import Iterator

import pytest
from httpx import AsyncClient
from prometheus_client import REGISTRY

from app.core.config import Settings, get_settings
from app.main import app
from tests.test_auth_api import FakeUserRepo, api, repo  # noqa: F401


@pytest.fixture
def use_settings() -> Iterator[None]:
    yield
    app.dependency_overrides.pop(get_settings, None)


# 스테이징·운영 설정은 개발용 값을 거부하므로(test_config) 안전한 값을 함께 넣는다
_SAFE = {
    "jwt_secret": "x" * 32,
    "database_url": "mysql+asyncmy://teamup:strong-pass@db:3306/teamup",
    "cors_origins": ["https://teamup.example"],
}


def _settings(**kwargs: str) -> None:
    merged = {**_SAFE, **kwargs} if kwargs.get("env") != "local" else kwargs
    app.dependency_overrides[get_settings] = lambda: Settings(**merged)  # type: ignore[arg-type]


async def test_metrics_requires_token_when_set(api: AsyncClient, use_settings: None) -> None:
    _settings(env="local", metrics_token="test-metrics-token")
    assert (await api.get("/metrics")).status_code == 401
    wrong = {"authorization": "Bearer nope"}
    assert (await api.get("/metrics", headers=wrong)).status_code == 401
    ok = await api.get("/metrics", headers={"authorization": "Bearer test-metrics-token"})
    assert ok.status_code == 200
    assert "teamup_security_events_total" in ok.text


async def test_metrics_401_uses_error_shape(api: AsyncClient, use_settings: None) -> None:
    _settings(env="local", metrics_token="test-metrics-token")
    res = await api.get("/metrics")
    assert res.json()["detail"]["code"] == "METRICS_UNAUTHORIZED"
    assert "teamup_" not in res.text


async def test_metrics_open_on_local_without_token(api: AsyncClient, use_settings: None) -> None:
    _settings(env="local", metrics_token="")
    assert (await api.get("/metrics")).status_code == 200


async def test_metrics_closed_outside_local_without_token(
    api: AsyncClient, use_settings: None
) -> None:
    _settings(env="staging", metrics_token="")
    assert (await api.get("/metrics")).status_code == 401


@pytest.mark.parametrize(
    "header", ["", "Bearer", "Bearer ", "Basic test-metrics-token", "test-metrics-token"]
)
async def test_metrics_rejects_malformed_auth(
    api: AsyncClient, use_settings: None, header: str
) -> None:
    _settings(env="local", metrics_token="test-metrics-token")
    headers = {"authorization": header} if header else {}
    assert (await api.get("/metrics", headers=headers)).status_code == 401


async def test_metrics_bearer_scheme_is_case_insensitive(
    api: AsyncClient, use_settings: None
) -> None:
    _settings(env="local", metrics_token="test-metrics-token")
    res = await api.get("/metrics", headers={"authorization": "bearer test-metrics-token"})
    assert res.status_code == 200


async def test_metrics_closed_in_production_without_token(
    api: AsyncClient, use_settings: None
) -> None:
    _settings(env="production", metrics_token="")
    assert (await api.get("/metrics")).status_code == 401


async def test_metrics_401_is_recorded_as_security_event(
    api: AsyncClient, use_settings: None
) -> None:
    labels = {"event": "unauthorized", "code": "METRICS_UNAUTHORIZED", "route": "/metrics"}
    before = REGISTRY.get_sample_value("teamup_security_events_total", labels) or 0.0
    _settings(env="local", metrics_token="test-metrics-token")
    await api.get("/metrics")
    assert REGISTRY.get_sample_value("teamup_security_events_total", labels) == before + 1
