from __future__ import annotations

import os
import uuid
import logging
from typing import Any, Optional

from dotenv import load_dotenv
load_dotenv()

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.auth import get_current_user
from app.services.ai_assistant_service import (
    gather_briefing_data,
    format_briefing_context,
    get_chat_history,
    save_chat_message,
    get_user_sessions,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ai-assistant", tags=["AI Assistant"])

SYSTEM_MESSAGE = """Sen, Booking Suite platformu için özel olarak tasarlanmış bir AI asistansın. 
Adın "Booking AI". Türkçe konuşuyorsun.

Görevlerin:
1. Kullanıcılara günlük brifing ver (rezervasyonlar, gelir, CRM, görevler hakkında)
2. Sorulara kısa, net ve faydalı cevaplar ver
3. Verileri analiz et ve öneriler sun
4. Her zaman profesyonel ve yardımsever ol

Kurallar:
- Cevaplarını kısa tut (maksimum 3-4 paragraf)
- Sayısal verileri tablo veya liste formatında göster
- Emoji kullan ama abartma
- Bilmediğin konularda "Bu konuda veritabanında bilgi bulamadım" de
- Tarih ve para birimlerini Türkçe formatında göster
"""


def _get_llm_key() -> str:
    key = os.environ.get("EMERGENT_LLM_KEY", "")
    if not key:
        raise HTTPException(status_code=500, detail="AI servisi yapılandırılmamış")
    return key


class BriefingRequest(BaseModel):
    pass


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    session_id: str


@router.post("/briefing")
async def get_daily_briefing(user: dict[str, Any] = Depends(get_current_user)):
    """Generate daily briefing using AI."""
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage

        org_id = user.get("organization_id", "")
        user_name = user.get("name", user.get("email", "Kullanıcı"))

        # Gather data from DB
        data = await gather_briefing_data(org_id)
        context = format_briefing_context(data)

        # Create briefing prompt
        briefing_prompt = f"""Merhaba, ben {user_name}. Bana bugünün günlük brifingini ver.

İşte güncel verilerim:
{context}

Bu verilere dayanarak kısa ve öz bir günlük brifing hazırla. Önemli noktaları vurgula, 
bekleyen işleri hatırlat ve varsa önerilerde bulun."""

        api_key = _get_llm_key()
        session_id = f"briefing-{org_id}-{uuid.uuid4().hex[:8]}"

        chat = LlmChat(
            api_key=api_key,
            session_id=session_id,
            system_message=SYSTEM_MESSAGE,
        )
        chat.with_model("gemini", "gemini-2.5-flash")

        user_msg = UserMessage(text=briefing_prompt)
        response = await chat.send_message(user_msg)

        return {
            "briefing": response,
            "raw_data": data,
            "generated_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Briefing generation error: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Brifing oluşturulamadı: {str(e)}")


@router.post("/chat", response_model=ChatResponse)
async def chat_with_ai(req: ChatRequest, user: dict[str, Any] = Depends(get_current_user)):
    """Chat with AI assistant."""
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage

        org_id = user.get("organization_id", "")
        user_id = user.get("id", user.get("email", ""))
        user_name = user.get("name", user.get("email", "Kullanıcı"))
        session_id = req.session_id or str(uuid.uuid4())

        # Save user message to DB
        await save_chat_message(
            session_id=session_id,
            organization_id=org_id,
            role="user",
            content=req.message,
            user_id=user_id,
        )

        # Build context with platform data for relevant questions
        data = await gather_briefing_data(org_id)
        context = format_briefing_context(data)

        # Get chat history for context
        history = await get_chat_history(session_id, org_id, limit=10)

        # Build full prompt with history context
        history_text = ""
        if history:
            history_lines = []
            for msg in history[-6:]:
                role_label = "Kullanıcı" if msg["role"] == "user" else "Asistan"
                history_lines.append(f"{role_label}: {msg['content']}")
            history_text = "\n\nÖnceki konuşma:\n" + "\n".join(history_lines)

        full_prompt = f"""Kullanıcı: {user_name}

Platform Verileri:
{context}
{history_text}

Kullanıcının sorusu: {req.message}"""

        api_key = _get_llm_key()

        chat = LlmChat(
            api_key=api_key,
            session_id=f"chat-{session_id}",
            system_message=SYSTEM_MESSAGE,
        )
        chat.with_model("gemini", "gemini-2.5-flash")

        user_msg = UserMessage(text=full_prompt)
        response = await chat.send_message(user_msg)

        # Save assistant response to DB
        await save_chat_message(
            session_id=session_id,
            organization_id=org_id,
            role="assistant",
            content=response,
            user_id=user_id,
        )

        return ChatResponse(response=response, session_id=session_id)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Chat error: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Chat hatası: {str(e)}")


@router.get("/chat-history/{session_id}")
async def get_history(session_id: str, user: dict[str, Any] = Depends(get_current_user)):
    """Get chat history for a session."""
    org_id = user.get("organization_id", "")
    messages = await get_chat_history(session_id, org_id)
    return {"messages": messages, "session_id": session_id}


@router.get("/sessions")
async def list_sessions(user: dict[str, Any] = Depends(get_current_user)):
    """List chat sessions for current user."""
    org_id = user.get("organization_id", "")
    user_id = user.get("id", user.get("email", ""))
    sessions = await get_user_sessions(org_id, user_id)
    return {"sessions": sessions}
