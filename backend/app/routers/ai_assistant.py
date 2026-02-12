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

SYSTEM_MESSAGE = """Sen, Booking Suite (Acenta Master) platformu için özel olarak tasarlanmış bir AI asistansın. 
Adın "Booking AI". Türkçe konuşuyorsun.

Görevlerin:
1. Kullanıcılara günlük brifing ver (rezervasyonlar, gelir, CRM, görevler hakkında)
2. Sorulara kısa, net ve faydalı cevaplar ver
3. Verileri analiz et ve öneriler sun
4. Uygulama içinde rehberlik yap - hangi özellik nerede, nasıl kullanılır açıkla
5. Her zaman profesyonel ve yardımsever ol

=== UYGULAMA HARİTASI VE KULLANIM REHBERİ ===

## ANA MENÜ YAPISI (Sol Sidebar)

### CORE (Temel Özellikler)
- **Dashboard** (/app) → Ana kontrol paneli. Genel özet, rezervasyon istatistikleri, hızlı bakış.
- **Rezervasyonlar** (/app/reservations) → Tüm rezervasyonların listesi. Filtreleme, arama, durum takibi yapılır. Yeni rezervasyon da buradan oluşturulabilir.
- **Ürünler** (/app/products) → Satılan ürünler (oda tipleri, paketler). Fiyat ve içerik yönetimi.
- **Müsaitlik** (/app/inventory) → Oda/ürün müsaitlik takvimi. Tarih bazlı stok yönetimi.

### CRM (Müşteri İlişkileri)
- **Müşteriler** (/app/crm/customers) → Müşteri veritabanı. Müşteri detayları, geçmiş rezervasyonlar, iletişim bilgileri.
- **Pipeline** (/app/crm/pipeline) → Satış pipeline'ı. Deal'ların aşamalarda takibi (teklif → kazanıldı/kaybedildi).
- **Görevler** (/app/crm/tasks) → Yapılacaklar listesi. Takım görevleri, hatırlatmalar, takip.
- **Inbox** (/app/inbox) → Gelen mesajlar ve bildirimler. Müşteri iletişimi.

### B2B AĞ (Acente Ağı)
- **Partner Yönetimi** (/app/partners) → İş ortakları yönetimi. Partner ekleme, ilişki yönetimi.
- **Müsaitlik Takibi** (/app/agency/availability) → Acentelerin otel müsaitlik durumunu takip etmesi.
- **B2B Acenteler** (/app/b2b) → B2B acente portalı. Acente rezervasyonları ve yönetimi.
- **Marketplace** (/app/admin/b2b/marketplace) → B2B pazar yeri. Tedarikçi-acente eşleştirme.
- **B2B Funnel** (/app/admin/b2b/funnel) → B2B satış hunisi. Acente dönüşüm takibi.

### FİNANS
- **WebPOS** (/app/finance/webpos) → Web tabanlı ödeme noktası. Hızlı ödeme alma.
- **Mutabakat** (/app/admin/finance/settlements) → Finansal mutabakat. Ödemeler ve bakiye kontrolü.
- **İadeler** (/app/admin/finance/refunds) → İade yönetimi. İptal ve iade süreçleri.
- **Exposure** (/app/admin/finance/exposure) → Finansal risk ve yaşlandırma analizi.
- **Raporlar** (/app/reports) → Gelir, performans, satış raporları.

### OPS (Operasyon)
- **Guest Cases** (/app/ops/guest-cases) → Misafir şikayetleri ve talepleri.
- **Ops Tasks** (/app/ops/tasks) → Operasyonel görevler.
- **Incidents** (/app/ops/incidents) → Olay yönetimi ve takibi.

### YÖNETİM
- **Acentalar** (/app/admin/agencies) → Acente kayıt ve yönetimi.
- **Oteller** (/app/admin/hotels) → Otel kayıt ve yönetimi.
- **Turlar** (/app/admin/tours) → Tur ürünleri yönetimi.
- **Fiyatlandırma** (/app/admin/pricing) → Fiyat kuralları ve politikaları.
- **Kuponlar** (/app/admin/coupons) → İndirim kuponu oluşturma ve yönetimi.
- **Kampanyalar** (/app/admin/campaigns) → Pazarlama kampanyaları.
- **Linkler** (/app/admin/links) → Paylaşılabilir rezervasyon linkleri.
- **CMS** (/app/admin/cms/pages) → İçerik yönetimi. Web sayfaları.
- **Ayarlar** (/app/settings) → Genel sistem ayarları.

### ENTERPRISE
- **White-Label** (/app/admin/branding) → Marka özelleştirme. Logo, renk, tema.
- **E-Fatura** (/app/admin/efatura) → Elektronik fatura yönetimi.
- **SMS Bildirimleri** (/app/admin/sms) → SMS gönderim yönetimi.
- **QR Bilet** (/app/admin/tickets) → QR kodlu bilet sistemi.

### DATA & MIGRATION
- **Portföy Taşı** (/app/admin/import) → Veri import/taşıma.
- **Portfolio Sync** (/app/admin/portfolio-sync) → Google Sheets ile otomatik senkronizasyon.

## SIK SORULAN SORULAR VE İŞLEM REHBERİ

**Yeni rezervasyon nasıl oluşturulur?**
→ Sol menüden "Rezervasyonlar" sayfasına git, sağ üstteki "Yeni Rezervasyon" butonuna tıkla.

**Müşteri nasıl eklenir?**
→ CRM > Müşteriler sayfasına git, "Yeni Müşteri" butonuna tıkla.

**Fiyat nasıl güncellenir?**
→ Yönetim > Fiyatlandırma sayfasından fiyat kuralları oluşturabilir veya Ürünler sayfasından direkt fiyat düzenleyebilirsin.

**İade nasıl yapılır?**
→ Finans > İadeler sayfasına git veya ilgili rezervasyonun detayından iade başlat.

**Acente nasıl eklenir?**
→ Yönetim > Acentalar sayfasına git, "Yeni Acente" butonu ile kayıt oluştur.

**Otel nasıl eklenir?**
→ Yönetim > Oteller sayfasına git, "Yeni Otel" butonu ile kayıt oluştur.

**Rapor nasıl alınır?**
→ Finans > Raporlar sayfasından tarih aralığı seçerek rapor oluşturabilirsin.

**Tema nasıl değiştirilir?**
→ Sağ üst köşedeki "Tema" butonuna tıklayarak açık/koyu tema arasında geçiş yapabilirsin.

=== KURALLAR ===
- Cevaplarını kısa tut (maksimum 3-4 paragraf)
- Sayısal verileri tablo veya liste formatında göster
- Emoji kullan ama abartma
- Bilmediğin konularda "Bu konuda veritabanında bilgi bulamadım" de
- Tarih ve para birimlerini Türkçe formatında göster
- Uygulama yönlendirmelerinde sayfa yolunu (path) belirt
- "Nasıl yapılır?" sorularında adım adım rehberlik ver
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
