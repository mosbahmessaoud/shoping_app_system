# services/ai_chat.py
import os
import json
from groq import Groq

client = Groq(api_key=os.getenv("GROQ_API_KEY"))


def chat_with_gemini(  # keeping same function name so nothing else breaks
    messages: list,
    tool_functions: list,
    system_prompt: str,
) -> str:
    # Build tools schema from Python functions
    tools = []
    for fn in tool_functions:
        import inspect
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

    # Build message list
    groq_messages = [{"role": "system", "content": system_prompt}]
    for msg in messages:
        groq_messages.append({
            "role": msg["role"],
            "content": msg["content"],
        })

    fn_map = {fn.__name__: fn for fn in tool_functions}

    # Agentic loop — Groq calls tools until it has enough to answer
    for _ in range(5):
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=groq_messages,
            tools=tools if tools else None,
            tool_choice="auto" if tools else None,
            max_tokens=1024,
        )

        msg = response.choices[0].message

        # Done — return text
        if response.choices[0].finish_reason == "stop":
            return msg.content or "لم أتمكن من الرد."

        # Tool calls requested
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
