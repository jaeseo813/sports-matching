import json
from collections.abc import AsyncIterator
from functools import lru_cache
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from openai import AsyncOpenAI

from app.api.deps import CurrentUser, MatchRepo, ProfileRepo, RecommendRepo, UserRepo, VenueRepo
from app.core.config import get_settings
from app.core.ratelimit import RateLimiter
from app.schemas.chat import ChatIn
from app.services import chatbot

router = APIRouter(prefix="/chat", tags=["chat"])

chat_limiter = RateLimiter(limit=20, window_seconds=300)  # 챗봇 20/5분


@lru_cache
def _client(api_key: str, base_url: str) -> AsyncOpenAI:
    return AsyncOpenAI(api_key=api_key, base_url=base_url, timeout=30, max_retries=1)


def get_llm() -> AsyncOpenAI | None:
    """키가 없으면 None: 챗봇만 꺼지고 서비스는 필터 UI로 그대로 쓴다."""
    settings = get_settings()
    if not settings.deepseek_api_key:
        return None
    return _client(settings.deepseek_api_key, settings.deepseek_base_url)


async def _sse(events: AsyncIterator[dict[str, str]]) -> AsyncIterator[str]:
    async for event in events:
        yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
    yield 'data: {"type": "done"}\n\n'


@router.post("", dependencies=[Depends(chat_limiter)])
async def chat(
    data: ChatIn,
    user: CurrentUser,
    llm: Annotated[AsyncOpenAI | None, Depends(get_llm)],
    profiles: ProfileRepo,
    recs: RecommendRepo,
    matches: MatchRepo,
    users: UserRepo,
    venues: VenueRepo,
) -> StreamingResponse:
    if llm is None:
        raise HTTPException(
            status_code=503, detail={"code": "CHATBOT_UNAVAILABLE", "message": chatbot.UNAVAILABLE}
        )
    try:
        chatbot.validate_request(data)
    except chatbot.ChatRequestError as exc:
        raise HTTPException(
            status_code=422, detail={"code": exc.code, "message": exc.message}
        ) from None
    ctx = chatbot.ChatContext(user, profiles, recs, matches, users, venues)
    return StreamingResponse(
        _sse(chatbot.chat_events(llm, ctx, data)),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
