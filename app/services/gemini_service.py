import os
import httpx

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
BASE_URL = "https://generativelanguage.googleapis.com/v1beta"


def _to_contents(messages):
    contents = []
    for m in messages or []:
        role = m.get("role", "user")
        if role == "assistant":
            role = "model"
        text = m.get("content", "")
        contents.append({"role": role, "parts": [{"text": text}]})
    return contents


async def gemini_chat(messages, temperature=0.5, max_tokens=512):
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY missing")

    url = f"{BASE_URL}/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
    payload = {
        "contents": _to_contents(messages),
        "generationConfig": {"temperature": temperature, "maxOutputTokens": max_tokens},
    }

    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(url, json=payload)
        data = r.json()

    parts = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
    reply = "".join([p.get("text", "") for p in parts]).strip()
    return reply or "Sorry, I couldn't generate a reply."
