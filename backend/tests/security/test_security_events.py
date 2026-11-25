# ruff: noqa: F401, F811  (pytest 픽스처를 test_auth_api에서 가져와 쓴다)
from httpx import AsyncClient
from prometheus_client import REGISTRY

from app.core.config import get_settings
from app.services.chat_guard import MAX_INPUT_CHARS, check_input, check_output
from tests.test_auth_api import SIGNUP, FakeUserRepo, api, repo  # noqa: F401


def _count(event: str, code: str, route: str = "") -> float:
    labels = {"event": event, "code": code, "route": route}
    return REGISTRY.get_sample_value("teamup_security_events_total", labels) or 0.0


async def test_unauthorized_and_login_failure_are_counted(api: AsyncClient) -> None:
    before_me = _count("unauthorized", "UNAUTHORIZED", "/auth/me")
    before_login = _count("unauthorized", "INVALID_CREDENTIALS", "/auth/login")
    await api.get("/api/v1/auth/me")
    await api.post("/api/v1/auth/login", json={"email": SIGNUP["email"], "password": "bad"})
    assert _count("unauthorized", "UNAUTHORIZED", "/auth/me") == before_me + 1
    assert _count("unauthorized", "INVALID_CREDENTIALS", "/auth/login") == before_login + 1


async def test_metrics_endpoint_exposes_counter(api: AsyncClient) -> None:
    await api.get("/api/v1/auth/me")
    token = get_settings().metrics_token  # .env에 METRICS_TOKEN을 넣은 개발 환경에서도 통과하게
    res = await api.get("/metrics", headers={"authorization": f"Bearer {token}"} if token else {})
    assert res.status_code == 200
    assert "teamup_security_events_total" in res.text


async def test_chat_guard_blocks_too_long_input() -> None:
    before = _count("chat_input_blocked", "TOO_LONG")
    result = await check_input("가" * (MAX_INPUT_CHARS + 1))
    assert not result.allowed and result.code == "TOO_LONG"
    assert _count("chat_input_blocked", "TOO_LONG") == before + 1
    assert (await check_input("근처 풋살 매치 찾아줘")).allowed
    assert (await check_output("이번 주 토요일 매치가 있어요")).allowed
