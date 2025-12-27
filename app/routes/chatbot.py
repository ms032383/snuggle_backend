from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Literal

from app.services.gemini_service import gemini_chat

router = APIRouter(prefix="/chatbot", tags=["Chatbot"])


class ChatMessage(BaseModel):
    role: Literal["user", "assistant", "model"] = "user"
    content: str


class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    temperature: float = 0.7
    max_tokens: int = 512


class ChatResponse(BaseModel):
    reply: str


@router.post("/reply", response_model=ChatResponse)
async def chatbot_reply(req: ChatRequest):
    try:
        msgs = [{"role": m.role, "content": m.content} for m in req.messages]
        reply = await gemini_chat(msgs, temperature=req.temperature, max_tokens=req.max_tokens)
        return {"reply": reply}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
