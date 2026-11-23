# ruff: noqa: F401, F811  (pytest 픽스처를 test_matches_api에서 가져와 쓴다)
"""챗봇. DeepSeek 대신 정해진 응답을 돌려주는 가짜 클라이언트로 검증한다 (CI에는 키가 없다)."""

import json
from typing import Any

import httpx
from httpx import AsyncClient
from openai import APIConnectionError
from openai.types.chat import ChatCompletion

from app.api.v1.chat import chat_limiter, get_llm
from app.main import app
from app.services import chatbot
from tests.test_matches_api import api, login, session, venue_id


def text_reply(text: str) -> ChatCompletion:
    return ChatCompletion.model_validate(
        {
            "id": "x",
            "object": "chat.completion",
            "created": 0,
            "model": "fake",
            "choices": [
                {
                    "index": 0,
                    "finish_reason": "stop",
                    "message": {"role": "assistant", "content": text},
                }
            ],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        }
    )


def tool_reply(name: str, args: dict[str, Any] | str, text: str = "") -> ChatCompletion:
    raw = args if isinstance(args, str) else json.dumps(args)
    call = {"id": "call_1", "type": "function", "function": {"name": name, "arguments": raw}}
    return ChatCompletion.model_validate(
        {
            "id": "x",
            "object": "chat.completion",
            "created": 0,
            "model": "fake",
            "choices": [
                {
                    "index": 0,
                    "finish_reason": "tool_calls",
                    "message": {"role": "assistant", "content": text, "tool_calls": [call]},
                }
            ],
        }
    )


class FakeLLM:
    """chat.completions.create만 흉내 낸다. 받은 요청을 calls에 남긴다."""

    def __init__(self, *replies: ChatCompletion | Exception) -> None:
        self.replies = list(replies)
        self.calls: list[dict[str, Any]] = []
        self.chat = self
        self.completions = self

    async def create(self, **kwargs: Any) -> ChatCompletion:
        self.calls.append(kwargs)
        reply = self.replies.pop(0) if len(self.replies) > 1 else self.replies[0]
        if isinstance(reply, Exception):
            raise reply
        return reply


def use_llm(fake: FakeLLM | None) -> None:
    app.dependency_overrides[get_llm] = lambda: fake
    chat_limiter.reset()
    chatbot.token_usage.clear()


def ask(text: str, sport: str | None = "badminton") -> dict[str, object]:
    return {"sport": sport, "messages": [{"role": "user", "content": text}]}


def events(body: str) -> list[dict[str, str]]:
    return [json.loads(line[6:]) for line in body.splitlines() if line.startswith("data: ")]


async def test_chat_unavailable_without_key(api: AsyncClient) -> None:
    use_llm(None)
    res = await api.post("/api/v1/chat", json=ask("안녕"), headers=await login(api, 1))
    assert res.status_code == 503
    assert res.json()["detail"]["code"] == "CHATBOT_UNAVAILABLE"


async def test_plain_answer_streams_message_then_done(api: AsyncClient) -> None:
    fake = FakeLLM(text_reply("안녕하세요! 무엇을 도와드릴까요?"))
    use_llm(fake)
    res = await api.post("/api/v1/chat", json=ask("안녕"), headers=await login(api, 1))
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("text/event-stream")
    got = events(res.text)
    assert [e["type"] for e in got] == ["message", "done"]
    assert got[0]["text"] == got[0]["history"] == "안녕하세요! 무엇을 도와드릴까요?"
    assert len(got[0]["sig"]) == 64  # 다음 요청에 이력으로 돌려보낼 때 쓰는 서명
    sent = fake.calls[0]["messages"]
    assert sent[0] == {"role": "system", "content": chatbot.SYSTEM_PROMPT}  # 캐시용 고정 접두사
    assert "배드민턴" in sent[1]["content"] and "1단계" in sent[1]["content"]  # 종목 맥락
    assert sent[-1] == {"role": "user", "content": "안녕"}
    assert fake.calls[0]["extra_body"] == {"thinking": {"type": "disabled"}}


async def test_tool_round_trip_shows_status_and_wraps_result_as_data(api: AsyncClient) -> None:
    fake = FakeLLM(tool_reply("get_my_profile", {}), text_reply("아직 등록한 종목이 없어요."))
    use_llm(fake)
    res = await api.post(
        "/api/v1/chat", json=ask("내 실력 몇 단계야?"), headers=await login(api, 1)
    )
    got = events(res.text)
    assert got[0] == {"type": "status", "text": "내 실력 단계를 확인하고 있어요"}
    assert got[-2]["type"] == "message"
    tool_msg = fake.calls[1]["messages"][-1]
    assert tool_msg["role"] == "tool" and tool_msg["tool_call_id"] == "call_1"
    assert tool_msg["content"].startswith("<data>") and tool_msg["content"].endswith("</data>")


async def test_search_without_onboarding_returns_reason_to_llm(api: AsyncClient) -> None:
    fake = FakeLLM(
        tool_reply("search_matches", {"sport": "badminton"}), text_reply("먼저 등록해 주세요.")
    )
    use_llm(fake)
    await api.post("/api/v1/chat", json=ask("배드민턴 찾아줘"), headers=await login(api, 1))
    assert "자기평가" in fake.calls[1]["messages"][-1]["content"]


async def test_suggest_action_emits_server_built_button(api: AsyncClient) -> None:
    fake = FakeLLM(
        tool_reply("suggest_action", {"kind": "view_match", "match_id": 7}),
        text_reply("버튼을 눌러 보세요."),
    )
    use_llm(fake)
    res = await api.post("/api/v1/chat", json=ask("7번 매치 보여줘"), headers=await login(api, 1))
    assert {"type": "action", "label": "매치 보러 가기", "href": "/matches/7"} in events(res.text)
    # 띄운 버튼은 이력에 적어 둔다 (후속 질문에서 매치 번호를 알 수 있게, 서명에 포함)
    msg = next(e for e in events(res.text) if e["type"] == "message")
    assert msg["history"] == "버튼을 눌러 보세요.\n[버튼: 매치 보러 가기 /matches/7]"


async def test_llm_failure_degrades_to_filter_message(api: AsyncClient) -> None:
    request = httpx.Request("POST", "https://api.deepseek.com/chat/completions")
    use_llm(FakeLLM(APIConnectionError(request=request)))
    res = await api.post("/api/v1/chat", json=ask("안녕"), headers=await login(api, 1))
    assert events(res.text)[0] == {
        "type": "error",
        "code": "CHATBOT_UNAVAILABLE",
        "message": chatbot.UNAVAILABLE,
    }


async def test_tool_rounds_are_capped(api: AsyncClient) -> None:
    fake = FakeLLM(tool_reply("get_my_profile", {}))  # 계속 도구만 부르는 모델
    use_llm(fake)
    await api.post("/api/v1/chat", json=ask("계속 확인해"), headers=await login(api, 1))
    assert len(fake.calls) == chatbot.MAX_TOOL_ROUNDS + 1
    assert fake.calls[-1]["tool_choice"] == "none"  # 마지막에는 답을 내게 한다


async def test_text_written_alongside_tool_call_is_kept(api: AsyncClient) -> None:
    # 실제 DeepSeek에서 확인한 패턴: 매치 설명과 버튼 제안을 한 응답에 같이 쓴다
    fake = FakeLLM(
        tool_reply(
            "suggest_action", {"kind": "view_match", "match_id": 7}, text="1. 저녁 복식 — 가까워요"
        ),
        text_reply("버튼을 띄워 뒀어요."),
    )
    use_llm(fake)
    res = await api.post("/api/v1/chat", json=ask("찾아줘"), headers=await login(api, 1))
    message = next(e for e in events(res.text) if e["type"] == "message")
    assert message["text"] == "1. 저녁 복식 — 가까워요\n\n버튼을 띄워 뒀어요."
