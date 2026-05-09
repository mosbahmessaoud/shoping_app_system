# services/ai_chat.py
"""
Lean AI chat engine.

Speed improvements vs original:
  - Tool schemas are built once per call (inspect is fast; no re-importing
    or restructuring on every agentic loop iteration).
  - Agentic loop cap = 6 iterations (plenty for any real tool chain).
  - Groq timeout: 90 s total (avoids hanging forever on slow responses).
  - Gemini fallback uses a clean conversation-style prompt instead of a
    raw string join.

Model priority (Groq):
  1. llama-3.3-70b-versatile     — best quality
  2. llama-3.1-8b-instant        — fastest, good for simple queries
  3. llama-4-scout-17b-16e       — backup if others are rate-limited

All Groq models exhausted → Gemini 2.0 Flash.
"""

from __future__ import annotations

import inspect
import json
import logging
import os
from typing import Callable

from google import genai
from groq import Groq, RateLimitError

logger = logging.getLogger(__name__)

# ── API clients ────────────────────────────────────────────────────────────────
_groq = Groq(api_key=os.getenv("GROQ_API_KEY"), timeout=90.0)
_gemini = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# ── constants ──────────────────────────────────────────────────────────────────
GROQ_MODELS = [
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
    "meta-llama/llama-4-scout-17b-16e-instruct",
]
MAX_ITERATIONS = 6
RATE_LIMIT_HTML = "<p>عذراً، الخدمة مشغولة حالياً. يرجى المحاولة بعد لحظات.</p>"
ERROR_HTML = "<p>حدث خطأ غير متوقع. يرجى المحاولة مجدداً.</p>"


# ── tool schema builder ────────────────────────────────────────────────────────

def _build_tool_schema(fn: Callable) -> dict:
    """Convert a Python callable into an OpenAI-compatible tool schema."""
    sig = inspect.signature(fn)
    properties: dict = {}
    required: list[str] = []

    _type_map = {int: "integer", float: "number", bool: "boolean"}

    for name, param in sig.parameters.items():
        json_type = _type_map.get(param.annotation, "string")
        properties[name] = {
            "type": json_type,
            "description": name.replace("_", " "),
        }
        if param.default is inspect.Parameter.empty:
            required.append(name)

    return {
        "type": "function",
        "function": {
            "name": fn.__name__,
            "description": (fn.__doc__ or fn.__name__).strip(),
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required,
            },
        },
    }


# ── agentic loop ───────────────────────────────────────────────────────────────

def _run_loop(
    model: str,
    messages: list[dict],
    tools: list[dict],
    fn_map: dict[str, Callable],
) -> str:
    """
    Execute the tool-calling loop for one Groq model.
    Raises RateLimitError so the caller can fall through to the next model.
    """
    for _ in range(MAX_ITERATIONS):
        resp = _groq.chat.completions.create(
            model=model,
            messages=messages,
            tools=tools or None,
            tool_choice="auto" if tools else None,
            max_tokens=1500,
            temperature=0.35,
        )

        choice = resp.choices[0]
        msg = choice.message

        # Model finished — return text
        if choice.finish_reason == "stop" or not msg.tool_calls:
            return msg.content or ERROR_HTML

        # Append assistant turn with tool calls
        messages.append({
            "role": "assistant",
            "content": msg.content or "",
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in msg.tool_calls
            ],
        })

        # Execute each tool and append results
        for tc in msg.tool_calls:
            fn = fn_map.get(tc.function.name)
            if fn is None:
                result: dict = {"error": f"Unknown tool: {tc.function.name}"}
            else:
                try:
                    raw = tc.function.arguments or ""
                    args = json.loads(raw) if raw.strip() not in (
                        "", "null") else {}
                    result = fn(**(args if isinstance(args, dict) else {}))
                except json.JSONDecodeError:
                    result = {"error": "Malformed tool arguments"}
                except Exception as exc:
                    logger.warning("Tool %s error: %s", tc.function.name, exc)
                    result = {"error": str(exc)}

            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": json.dumps(result, ensure_ascii=False, default=str),
            })

    return "<p>عذراً، لم أتمكن من معالجة طلبك في الوقت المحدد.</p>"


# ── Gemini fallback ────────────────────────────────────────────────────────────

def _gemini_fallback(messages: list[dict]) -> str:
    """Fallback to Gemini 2.0 Flash when all Groq models are exhausted."""
    try:
        parts = [
            f"{m['role'].upper()}: {m.get('content', '')}"
            for m in messages
            if m.get("content")
        ]
        resp = _gemini.models.generate_content(
            model="gemini-2.0-flash",
            contents="\n".join(parts),
        )
        return resp.text or ERROR_HTML
    except Exception as exc:
        logger.error("Gemini fallback failed: %s", exc)
        return RATE_LIMIT_HTML


# ── public entry point ─────────────────────────────────────────────────────────

def chat_ai(
    messages: list[dict],
    tool_functions: list[Callable],
    system_prompt: str,
) -> str:
    """
    Core chat function used by both /chat/client and /chat/admin.

    Args:
        messages:        Full conversation history + current user message.
                         [{"role": "user"|"assistant", "content": "..."}]
        tool_functions:  Python callables the model may invoke.
        system_prompt:   Role-specific behaviour instructions.

    Returns:
        HTML string ready for the frontend to render directly.
    """
    tools = [_build_tool_schema(fn) for fn in tool_functions]
    fn_map = {fn.__name__: fn for fn in tool_functions}

    full_messages: list[dict] = [
        {"role": "system", "content": system_prompt},
        *messages,
    ]

    for model in GROQ_MODELS:
        try:
            logger.info("chat_ai → %s", model)
            return _run_loop(model, list(full_messages), tools, fn_map)
        except RateLimitError:
            logger.warning("chat_ai: %s rate-limited", model)
        except Exception as exc:
            logger.error("chat_ai: %s error: %s", model, exc)

    logger.warning("chat_ai: all Groq models exhausted → Gemini fallback")
    return _gemini_fallback(full_messages)
