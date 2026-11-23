# ruff: noqa: F401, F811  (pytest 픽스처를 test_matches_api에서 가져와 쓴다)
"""챗봇 차단율의 분모: 챗봇 요청 수와 가드 검사 수 카운터."""

from httpx import AsyncClient
from prometheus_client import REGISTRY

from app.services.chat_guard import MAX_INPUT_CHARS, check_input, check_output
from tests.test_chat_api import ask, use_llm
from tests.test_matches_api import api, login, session, venue_id


def _value(name: str, labels: dict[str, str] | None = None) -> float:
    return REGISTRY.get_sample_value(name, labels or {}) or 0.0


async def test_guard_checks_are_counted_per_stage() -> None:
    before_in = _value("teamup_chat_guard_checks_total", {"stage": "input"})
    before_out = _value("teamup_chat_guard_checks_total", {"stage": "output"})
    await check_input("가" * (MAX_INPUT_CHARS + 1))  # 차단돼도 검사 1회
    await check_output("안녕하세요")
    assert _value("teamup_chat_guard_checks_total", {"stage": "input"}) == before_in + 1
    assert _value("teamup_chat_guard_checks_total", {"stage": "output"}) == before_out + 1


async def test_chat_requests_are_counted(api: AsyncClient) -> None:
    headers = await login(api, 1)
    use_llm(None)  # 키가 없어 503이어도 요청은 센다
    before = _value("teamup_chat_requests_total")
    await api.post("/api/v1/chat", json=ask("안녕"), headers=headers)
    assert _value("teamup_chat_requests_total") == before + 1
