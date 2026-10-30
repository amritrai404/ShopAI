from __future__ import annotations

import logging
from typing import Any

from app.llm.client import OllamaError, get_ollama_client

logger = logging.getLogger(__name__)


def llm_chat(
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]] | None = None,
    mode: str = "local",
    temperature: float = 0.2,
) -> tuple[dict[str, Any], str]:
    """
    Local-only LLM router. `mode` param is accepted for API compatibility,
    but only "local" is supported. Returns (response, mode_used).
    """
    if mode not in ("local", "auto"):
        raise ValueError(
            f"Mode '{mode}' is not supported. This deployment is local-only. "
            f"Use mode='local'."
        )

    client = get_ollama_client()
    try:
        response = client.chat(messages, tools=tools, temperature=temperature)
        return response, "local"
    except OllamaError:
        raise
    except Exception as exc:
        raise OllamaError(f"Unexpected Ollama failure: {exc}") from exc