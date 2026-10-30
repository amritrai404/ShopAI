from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    session_id: str | None = None
    mode: Literal["local"] = "local"


class ChatResponse(BaseModel):
    answer: str
    session_id: str
    tools_used: list[str] = []
    mode_used: str = "local"