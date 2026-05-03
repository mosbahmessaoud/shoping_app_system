# services/ai_chat.py
import os
import json
import logging
from google import genai
from groq import Groq, RateLimitError

logger = logging.getLogger(__name__)

groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"), timeout=120.0)
gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

RATE_LIMIT_MESSAGE = (
    "عذراً، الخدمة مشغولة حالياً بسبب ارتفاع حجم الاستخدام. "
    "يرجى المحاولة مجدداً بعد بضع دقائق."
)

# gemma2-9b-it was decommissioned — replaced with mixtral and llama3
GROQ_MODELS = [
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
    "meta-llama/llama-4-scout-17b-16e-instruct",  # new Groq model
]


def _call_gemini_fallback(groq_messages: list) -> str:
    try:
        prompt = "\n".join(
            f"{m['role'].upper()}: {m['content']}"
            for m in groq_messages
            if m["role"] in ("system", "user", "assistant")
        )
        response = gemini_client.models.generate_content(
            model="gemini-2.0-flash",   # fix: correct model name for new SDK
            contents=prompt,
        )
        return response.text or "لم أتمكن من الرد."
    except Exception as e:
        logger.error("Gemini fallback also failed: %s", e)
        return RATE_LIMIT_MESSAGE


def _run_agentic_loop(model: str, groq_messages: list, tools: list, fn_map: dict) -> str:
    """Run the full tool-calling loop for a given model. Raises RateLimitError if hit."""
    for _ in range(5):
        response = groq_client.chat.completions.create(
            model=model,
            messages=groq_messages,
            tools=tools if tools else None,
            tool_choice="auto" if tools else None,
            max_tokens=1024,
        )

        msg = response.choices[0].message

        if response.choices[0].finish_reason == "stop":
            return msg.content or "لم أتمكن من الرد."

        if msg.tool_calls:
            groq_messages.append({
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

            for tc in msg.tool_calls:
                fn = fn_map.get(tc.function.name)
                if fn:
                    try:
                        raw = tc.function.arguments
                        # Bug fix: guard against None or empty arguments
                        if raw and raw.strip() not in ("", "null", "None"):
                            args = json.loads(raw)
                            # guard against AI passing None instead of a dict
                            if not isinstance(args, dict):
                                args = {}
                        else:
                            args = {}
                        result = fn(**args)
                    except Exception as e:
                        logger.warning("Tool %s error: %s",
                                       tc.function.name, e)
                        result = {"error": str(e)}
                else:
                    result = {"error": "unknown tool"}

                groq_messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(result, ensure_ascii=False),
                })
        else:
            return msg.content or "لم أتمكن من الرد."

    return "عذراً، لم أتمكن من معالجة طلبك."


def chat_with_gemini(
    messages: list,
    tool_functions: list,
    system_prompt: str,
) -> str:
    import inspect

    # Build tools schema
    tools = []
    for fn in tool_functions:
        sig = inspect.signature(fn)
        params = {}
        required = []
        for name, param in sig.parameters.items():
            params[name] = {"type": "string", "description": name}
            if param.default == inspect.Parameter.empty:
                required.append(name)
        tools.append({
            "type": "function",
            "function": {
                "name": fn.__name__,
                "description": fn.__doc__ or fn.__name__,
                "parameters": {
                    "type": "object",
                    "properties": params,
                    "required": required,
                },
            },
        })

    # Build messages
    groq_messages = [{"role": "system", "content": system_prompt}]
    for msg in messages:
        groq_messages.append({"role": msg["role"], "content": msg["content"]})

    fn_map = {fn.__name__: fn for fn in tool_functions}

    # Try each Groq model directly — no probe ping
    for model in GROQ_MODELS:
        try:
            logger.info("Trying Groq model: %s", model)
            return _run_agentic_loop(model, groq_messages.copy(), tools, fn_map)
        except RateLimitError:
            logger.warning("Model %s rate-limited, trying next...", model)
            continue
        except Exception as e:
            logger.error("Unexpected error with model %s: %s", model, e)
            continue

    # All Groq models exhausted — use Gemini
    logger.warning("All Groq models exhausted, falling back to Gemini.")
    return _call_gemini_fallback(groq_messages)
