# ruff: noqa: F401, F811  (pytest 픽스처를 test_auth_api에서 가져와 쓴다)
"""/metrics 접근 제한: METRICS_TOKEN이 있으면 Bearer 토큰이 맞아야 하고, 없으면 local에서만 열린다."""

from collections.abc import Iterator

import pytest
from httpx import AsyncClient

from app.core.config import Settings, get_settings
from app.main import app
from tests.test_auth_api import FakeUserRepo, api, repo  # noqa: F401


@pytest.fixture
def use_settings() -> Iterator[None]:
    yield
    app.dependency_overrides.pop(get_settings, None)


def _settings(**kwargs: str) -> None:
    app.dependency_overrides[get_settings] = lambda: Settings(**kwargs)  # type: ignore[arg-type]


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
