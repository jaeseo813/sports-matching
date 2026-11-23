from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ChatMessageIn(BaseModel):
    """대화 이력은 클라이언트가 보낸다. system 역할은 받지 않는다 (시스템 프롬프트는 서버만 쓴다)."""

    model_config = ConfigDict(extra="forbid")

    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=2000)


class ChatIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sport: str | None = Field(default=None, max_length=20)  # 지금 보고 있는 종목 페이지
    messages: list[ChatMessageIn] = Field(min_length=1, max_length=20)
