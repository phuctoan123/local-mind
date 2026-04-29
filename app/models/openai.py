from __future__ import annotations

import time
import uuid
from typing import Literal

from pydantic import BaseModel, Field


class OpenAIMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str


class ChatCompletionRequest(BaseModel):
    model: str | None = None
    messages: list[OpenAIMessage] = Field(..., min_length=1)
    stream: bool = False
    document_ids: list[str] | None = None
    top_k: int = Field(default=5, ge=1, le=20)

    @property
    def latest_user_message(self) -> str:
        for message in reversed(self.messages):
            if message.role == "user":
                return message.content
        return self.messages[-1].content


class ChatCompletionChoice(BaseModel):
    index: int = 0
    message: OpenAIMessage
    finish_reason: str = "stop"


class ChatCompletionResponse(BaseModel):
    id: str = Field(default_factory=lambda: f"chatcmpl-{uuid.uuid4()}")
    object: str = "chat.completion"
    created: int = Field(default_factory=lambda: int(time.time()))
    model: str
    choices: list[ChatCompletionChoice]
