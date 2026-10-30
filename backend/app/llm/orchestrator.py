from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.llm.client import OllamaError, get_ollama_client
from app.llm.tools import execute_tool, get_tool_schemas
from app.models.chat import ChatMessage, ChatSession

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are ShopAI, an AI business assistant for small retail shop owners.

You have access to tools that query the shop's real business data — revenue, profit, products, inventory, and forecasts. ALWAYS use the tools for any question involving sales, revenue, profit, products, inventory, or forecasts. NEVER invent or guess business numbers.

Guidelines:
- Today's date is {today}. Use it to interpret relative dates like "last month", "this week", "yesterday".
- Convert relative dates to explicit YYYY-MM-DD ranges before calling tools.
- If a tool returns an error or empty data, explain what's missing instead of fabricating numbers.
- Keep responses concise, use ₹ or the local currency symbol for money, and present numbers clearly.
- After tools return data, synthesize a helpful answer. Do not just echo raw JSON.
"""

MAX_TOOL_ITERATIONS = 3


def _resolve_date_range_defaults() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def _build_messages(
    system_prompt: str,
    history: list[ChatMessage],
    user_message: str,
    tool_messages: list[dict],
) -> list[dict]:
    messages: list[dict] = [{"role": "system", "content": system_prompt}]
    for msg in history[-10:]:
        messages.append({"role": msg.role, "content": msg.content})
    messages.append({"role": "user", "content": user_message})
    messages.extend(tool_messages)
    return messages


def handle_chat(
    user_message: str,
    session_id: str | None,
    db: Session,
) -> dict[str, Any]:
    """
    Full pipeline:
    1. Load or create session + fetch history
    2. LLM call with tool schemas
    3. If tool_calls, execute, append tool results, call LLM again (max 3 iterations)
    4. Save messages to DB
    5. Return final answer + tools_used
    """
    ollama = get_ollama_client()
    now = datetime.now(timezone.utc)
    today = now.date().isoformat()
    system_prompt = SYSTEM_PROMPT.format(today=today)

    # Session handling
    if session_id:
        session = db.get(ChatSession, session_id)
        if session is None:
            session = ChatSession(id=session_id, created_at=now)
            db.add(session)
            db.commit()
    else:
        session = ChatSession(created_at=now)
        db.add(session)
        db.commit()
        db.refresh(session)

    history = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session.id)
        .order_by(ChatMessage.created_at.asc())
        .all()
    )

    # Save user message
    db.add(ChatMessage(session_id=session.id, role="user", content=user_message, created_at=now))
    db.commit()

    tools_schemas = get_tool_schemas()
    tool_messages: list[dict] = []
    tools_used: list[str] = []
    final_content = ""

    for iteration in range(MAX_TOOL_ITERATIONS):
        messages = _build_messages(system_prompt, history, user_message, tool_messages)

        try:
            response = ollama.chat(messages=messages, tools=tools_schemas, temperature=0.2)
        except OllamaError as exc:
            logger.error(f"LLM call failed: {exc}")
            return {
                "answer": f"I couldn't reach the local AI model. Error: {exc}",
                "session_id": session.id,
                "tools_used": tools_used,
                "mode": "local",
            }

        assistant_msg = response.get("message", {})
        content = assistant_msg.get("content", "")
        tool_calls = assistant_msg.get("tool_calls") or []

        if not tool_calls:
            final_content = content
            break

        # Append assistant message (with tool_calls) so LLM sees its own plan
        tool_messages.append(
            {"role": "assistant", "content": content, "tool_calls": tool_calls}
        )

        for call in tool_calls:
            fn = call.get("function", {})
            tool_name = fn.get("name")
            raw_args = fn.get("arguments", {})

            if isinstance(raw_args, str):
                try:
                    args = json.loads(raw_args)
                except json.JSONDecodeError:
                    args = {}
            else:
                args = raw_args or {}

            tools_used.append(tool_name)
            result = execute_tool(tool_name, args, db)

            tool_messages.append(
                {
                    "role": "tool",
                    "name": tool_name,
                    "content": json.dumps(result, default=str),
                }
            )

    if not final_content:
        # Last iteration had tool calls but no final text — force one final synthesis
        try:
            final_response = ollama.chat(
                messages=_build_messages(system_prompt, history, user_message, tool_messages),
                tools=None,
                temperature=0.2,
            )
            final_content = final_response.get("message", {}).get("content", "")
        except OllamaError:
            final_content = "I gathered the data but couldn't synthesize a response."

    # Save assistant message
    db.add(
        ChatMessage(
            session_id=session.id,
            role="assistant",
            content=final_content,
            created_at=datetime.now(timezone.utc),
        )
    )
    db.commit()

    return {
        "answer": final_content or "I could not generate an answer.",
        "session_id": session.id,
        "tools_used": tools_used,
        "mode": "local",
    }