from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.llm.client import OllamaError
from app.llm.router import llm_chat
from app.llm.tools import execute_tool, get_tool_schemas
from app.models.chat import ChatMessage, ChatSession

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are ShopAI, an AI business assistant for small retail shop owners.

You have tools that query the shop's REAL business data — revenue, profit, top products, low stock, monthly trends, and ML forecasts. ALWAYS use tools for any question about sales, revenue, profit, products, inventory, or forecasts. NEVER invent or guess business numbers.

Critical rules:
1. Today's date is {today}. Convert relative dates ("last month", "this week", "yesterday") to explicit YYYY-MM-DD ranges before calling tools.
2. Money formatting: always use the ₹ symbol (e.g., ₹5,520.00).
3. If a tool returns an error or empty data, clearly explain what's missing — do NOT fabricate numbers.
4. After tools return data, synthesize a helpful, concise answer. Do NOT dump raw JSON.
5. When listing multiple products or months, use a small markdown table for clarity.

Example:
User: "What was my revenue last month?"
You: (call get_revenue with start_date and end_date of last month) → respond: "Your net revenue last month was ₹5,520.00 across 8 transactions."
"""

MAX_TOOL_ITERATIONS = 3


def _build_messages(system_prompt, history, user_message, tool_messages):
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
    mode: str = "local",
) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    today = now.date().isoformat()
    system_prompt = SYSTEM_PROMPT.format(today=today)

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

    db.add(ChatMessage(session_id=session.id, role="user", content=user_message, created_at=now))
    db.commit()

    tools_schemas = get_tool_schemas()
    tool_messages: list[dict] = []
    tools_used: list[str] = []
    final_content = ""
    mode_used = "local"

    for _ in range(MAX_TOOL_ITERATIONS):
        messages = _build_messages(system_prompt, history, user_message, tool_messages)

        try:
            response, mode_used = llm_chat(
                messages=messages, tools=tools_schemas, mode=mode, temperature=0.2
            )
        except OllamaError as exc:
            logger.error(f"LLM call failed: {exc}")
            return {
                "answer": f"I couldn't reach the local AI model. Error: {exc}",
                "session_id": session.id,
                "tools_used": tools_used,
                "mode_used": "local",
            }

        assistant_msg = response.get("message", {})
        content = assistant_msg.get("content", "") or ""
        tool_calls = assistant_msg.get("tool_calls") or []

        if not tool_calls:
            final_content = content
            break

        tool_messages.append({"role": "assistant", "content": content, "tool_calls": tool_calls})

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

            tool_messages.append({
                "role": "tool",
                "name": tool_name,
                "content": json.dumps(result, default=str),
            })

    if not final_content:
        try:
            response, mode_used = llm_chat(
                messages=_build_messages(system_prompt, history, user_message, tool_messages),
                tools=None,
                mode=mode,
                temperature=0.2,
            )
            final_content = response.get("message", {}).get("content", "")
        except OllamaError:
            final_content = "I gathered the data but couldn't synthesize a response."

    db.add(ChatMessage(session_id=session.id, role="assistant", content=final_content, created_at=datetime.now(timezone.utc)))
    db.commit()

    return {
        "answer": final_content or "I could not generate an answer.",
        "session_id": session.id,
        "tools_used": tools_used,
        "mode_used": mode_used,
    }