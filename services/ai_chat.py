# services/ai_chat.py
import time
from google import genai
from google.genai import types
import os

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))


def chat_with_gemini(
    messages: list,
    tool_functions: list,
    system_prompt: str,
) -> str:
    history = []
    for msg in messages[:-1]:
        history.append(
            types.Content(
                role="user" if msg["role"] == "user" else "model",
                parts=[types.Part(text=msg["content"])],
            )
        )

    last_message = messages[-1]["content"]

    for attempt in range(3):
        try:
            response = client.chats.create(
                model="gemini-2.0-flash",
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    tools=tool_functions,
                ),
                history=history,
            ).send_message(last_message)

            return response.text or "لم أتمكن من الرد."

        except Exception as e:
            error_str = str(e)
            if "429" in error_str and attempt < 2:
                wait = 20 * (attempt + 1)
                print(
                    f"Rate limited, retrying in {wait}s... (attempt {attempt + 1}/3)")
                time.sleep(wait)
            else:
                print(f"Gemini error: {e}")
                return "عذراً، الخدمة مشغولة حالياً. يرجى المحاولة بعد لحظة."
