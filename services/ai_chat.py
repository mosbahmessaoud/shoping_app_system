# services/ai_chat.py
from google import genai
from google.genai import types
import os

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))


def chat_with_gemini(
    messages: list,
    tool_functions: list,
    system_prompt: str,
) -> str:
    # Convert history to genai format
    history = []
    for msg in messages[:-1]:
        history.append(
            types.Content(
                role="user" if msg["role"] == "user" else "model",
                parts=[types.Part(text=msg["content"])],
            )
        )

    last_message = messages[-1]["content"]

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
        print(f"Gemini error: {e}")
        return "Sorry, I encountered an error processing your request."
