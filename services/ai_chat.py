# services/ai_chat.py
import google.generativeai as genai
import os

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))


def chat_with_gemini(
    messages: list,
    tool_functions: list,
    system_prompt: str,
) -> str:
    """
    Send a chat message to Gemini with tool/function calling support.
    Gemini handles the tool-calling loop automatically.
    """
    model = genai.GenerativeModel(
        model_name="gemini-2.0-flash",
        system_instruction=system_prompt,
        tools=tool_functions,
    )

    # Convert history (all messages except the last one)
    history = []
    for msg in messages[:-1]:
        history.append({
            "role": "user" if msg["role"] == "user" else "model",
            "parts": [msg["content"]],
        })

    chat = model.start_chat(
        history=history,
        enable_automatic_function_calling=True,
    )

    last_message = messages[-1]["content"]

    try:
        response = chat.send_message(last_message)
        return response.text
    except Exception as e:
        print(f"Gemini error: {e}")
        return "Sorry, I encountered an error processing your request."
