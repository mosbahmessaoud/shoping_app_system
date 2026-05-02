
# services/ai_chat.py
import os
import json
import logging
import google.generativeai as genai
from groq import Groq, RateLimitError

logger = logging.getLogger(__name__)

# ── Groq client ────────────────────────────────────────────────────────────────
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"), timeout=120.0)

# ── Gemini client ──────────────────────────────────────────────────────────────
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

RATE_LIMIT_MESSAGE = (
    "عذراً، الخدمة مشغولة حالياً بسبب ارتفاع حجم الاستخدام. "
    "يرجى المحاولة مجدداً بعد بضع دقائق."
)

GROQ_MODELS = [
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
    "gemma2-9b-it",
]


# ── Gemini fallback (no tool support, plain chat) ──────────────────────────────
def _call_gemini_fallback(groq_messages: list) -> str:
    """Call Gemini 1.5 Flash when all Groq models are exhausted."""
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        # Convert messages to a single prompt string
        prompt = "\n".join(
            f"{m['role'].upper()}: {m['content']}"
            for m in groq_messages
            if m["role"] in ("user", "assistant", "system")
        )
        response = model.generate_content(prompt)
        return response.text or "لم أتمكن من الرد."
    except Exception as e:
        logger.error("Gemini fallback also failed: %s", e)
        return RATE_LIMIT_MESSAGE


# ── Pick an available Groq model ───────────────────────────────────────────────
def _pick_groq_model() -> str | None:
    for model in GROQ_MODELS:
        try:
            groq_client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=1,
            )
            return model
        except RateLimitError:
            logger.warning("Groq model %s rate-limited, trying next...", model)
        except Exception:
            logger.warning("Groq model %s unavailable, trying next...", model)
    return None


# ── Main function ──────────────────────────────────────────────────────────────
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

    # Try Groq first
    active_model = _pick_groq_model()

    if active_model is None:
        logger.warning("All Groq models exhausted — switching to Gemini.")
        return _call_gemini_fallback(groq_messages)

    if active_model != GROQ_MODELS[0]:
        logger.info("Using Groq fallback model: %s", active_model)

    # Agentic loop
    for _ in range(5):
        try:
            response = groq_client.chat.completions.create(
                model=active_model,
                messages=groq_messages,
                tools=tools if tools else None,
                tool_choice="auto" if tools else None,
                max_tokens=1024,
            )
        except RateLimitError as e:
            logger.error("Rate limit mid-loop on %s: %s", active_model, e)
            # Try Gemini as last resort
            return _call_gemini_fallback(groq_messages)
        except Exception as e:
            logger.error("Unexpected Groq error: %s", e)
            return "عذراً، حدث خطأ غير متوقع. يرجى المحاولة لاحقاً."

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
                        args = json.loads(tc.function.arguments)
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


# # services/ai_chat.py
# # services/ai_chat.py
# import os
# import json
# from groq import Groq

# client = Groq(
#     api_key=os.getenv("GROQ_API_KEY"),
#     timeout=120.0,  # 2 minutes timeout
# )


# def chat_with_gemini(  # keeping same function name so nothing else breaks
#     messages: list,
#     tool_functions: list,
#     system_prompt: str,
# ) -> str:
#     # Build tools schema from Python functions
#     tools = []
#     for fn in tool_functions:
#         import inspect
#         sig = inspect.signature(fn)
#         params = {}
#         required = []
#         for name, param in sig.parameters.items():
#             params[name] = {"type": "string", "description": name}
#             if param.default == inspect.Parameter.empty:
#                 required.append(name)

#         tools.append({
#             "type": "function",
#             "function": {
#                 "name": fn.__name__,
#                 "description": fn.__doc__ or fn.__name__,
#                 "parameters": {
#                     "type": "object",
#                     "properties": params,
#                     "required": required,
#                 },
#             },
#         })

#     # Build message list
#     groq_messages = [{"role": "system", "content": system_prompt}]
#     for msg in messages:
#         groq_messages.append({
#             "role": msg["role"],
#             "content": msg["content"],
#         })

#     fn_map = {fn.__name__: fn for fn in tool_functions}

#     # Agentic loop — Groq calls tools until it has enough to answer
#     for _ in range(5):
#         response = client.chat.completions.create(
#             model="llama-3.3-70b-versatile",
#             messages=groq_messages,
#             tools=tools if tools else None,
#             tool_choice="auto" if tools else None,
#             max_tokens=1024,
#         )

#         msg = response.choices[0].message

#         # Done — return text
#         if response.choices[0].finish_reason == "stop":
#             return msg.content or "لم أتمكن من الرد."

#         # Tool calls requested
#         if msg.tool_calls:
#             groq_messages.append({
#                 "role": "assistant",
#                 "content": msg.content or "",
#                 "tool_calls": [
#                     {
#                         "id": tc.id,
#                         "type": "function",
#                         "function": {
#                             "name": tc.function.name,
#                             "arguments": tc.function.arguments,
#                         },
#                     }
#                     for tc in msg.tool_calls
#                 ],
#             })

#             for tc in msg.tool_calls:
#                 fn = fn_map.get(tc.function.name)
#                 if fn:
#                     try:
#                         args = json.loads(tc.function.arguments)
#                         result = fn(**args)
#                     except Exception as e:
#                         result = {"error": str(e)}
#                 else:
#                     result = {"error": "unknown tool"}

#                 groq_messages.append({
#                     "role": "tool",
#                     "tool_call_id": tc.id,
#                     "content": json.dumps(result, ensure_ascii=False),
#                 })
#         else:
#             return msg.content or "لم أتمكن من الرد."

#     return "عذراً، لم أتمكن من معالجة طلبك."
