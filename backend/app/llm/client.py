from __future__ import annotations

import logging
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class OllamaError(Exception):
    """Raised when Ollama is unreachable or returns an error."""


class OllamaClient:
    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        timeout: float = 120.0,
    ):
        self.base_url = (base_url or settings.ollama_base_url).rstrip("/")
        self.model = model or settings.ollama_model
        self.timeout = timeout

    def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        temperature: float = 0.3,
        stream: bool = False,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": stream,
            "options": {"temperature": temperature},
        }
        if tools:
            payload["tools"] = tools

        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(f"{self.base_url}/api/chat", json=payload)
                resp.raise_for_status()
                return resp.json()
        except httpx.HTTPStatusError as exc:
            body = exc.response.text[:500]
            raise OllamaError(
                f"Ollama returned {exc.response.status_code}: {body}"
            ) from exc
        except httpx.RequestError as exc:
            raise OllamaError(
                f"Cannot reach Ollama at {self.base_url}. "
                f"Is `ollama serve` running? Error: {exc}"
            ) from exc

    def is_available(self) -> bool:
        try:
            with httpx.Client(timeout=5.0) as client:
                resp = client.get(f"{self.base_url}/api/tags")
                return resp.status_code == 200
        except httpx.RequestError:
            return False


_client: OllamaClient | None = None


def get_ollama_client() -> OllamaClient:
    global _client
    if _client is None:
        _client = OllamaClient()
    return _client