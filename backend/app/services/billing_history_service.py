from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.db import get_db


_ACTION_META: dict[str, dict[str, str]] = {
    "billing.checkout_completed": {"title": "Plan aktive edildi", "tone": "success"},
    "billing.plan_changed_now": {"title": "Plan hemen değiştirildi", "tone": "success"},
    "billing.plan_change_scheduled": {"title": "Plan değişikliği planlandı", "tone": "info"},
    "billing.subscription_cancel_scheduled": {"title": "Dönem sonu iptal planlandı", "tone": "warning"},
    "billing.subscription_reactivated": {"title": "Abonelik yeniden etkinleştirildi", "tone": "success"},
    "subscription.invoice_paid": {"title": "Fatura ödendi", "tone": "success"},
    "subscription.payment_failed": {"title": "Ödeme başarısız", "tone": "warning"},
    "subscription.canceled": {"title": "Abonelik sona erdi", "tone": "info"},
}

_PLAN_LABELS = {
    "trial": "Trial",
    "starter": "Starter",
    "pro": "Pro",
    "enterprise": "Enterprise",
}


def _iso_datetime(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc).isoformat()
    text = str(value).strip()
    return text or None


def _short_date(value: Any) -> str | None:
    text = _iso_datetime(value)
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        return parsed.astimezone(timezone.utc).strftime("%d.%m.%Y")
    except Exception:
        return text[:10]


def _plan_label(value: Any) -> str | None:
    text = str(value or "").strip().lower()
    return _PLAN_LABELS.get(text) or (text.upper() if text else None)


def _interval_label(value: Any) -> str | None:
    text = str(value or "").strip().lower()
    if text == "yearly":
        return "Yıllık"
    if text == "monthly":
        return "Aylık"
    return None


def _actor_label(value: Any) -> str:
    text = str(value or "").strip()
    if not text or text in {"system", "stripe_webhook"}:
        return "Sistem"
    return text


def _format_try_minor(amount_minor: Any) -> str | None:
    try:
        amount = float(amount_minor) / 100.0
    except Exception:
        return None
    formatted = f"{amount:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")
    return f"₺{formatted}"


def _description_for_action(action: str, before: Any, after: Any) -> str:
    before_data = before if isinstance(before, dict) else {}
    after_data = after if isinstance(after, dict) else {}

    before_plan = _plan_label(before_data.get("plan"))
    before_interval = _interval_label(before_data.get("interval"))
    after_plan = _plan_label(after_data.get("plan"))
    after_interval = _interval_label(after_data.get("interval"))

    if action == "billing.checkout_completed":
        if before_plan and after_plan and before_plan != after_plan:
            return f"{before_plan} planından {after_plan} planına geçildi. Yeni dönem {after_interval or 'standart'} olarak başladı."
        if after_plan and after_interval:
            return f"{after_plan} planı {after_interval.lower()} abonelik olarak aktifleştirildi."
        return "Stripe checkout tamamlandı ve planınız aktif hale getirildi."

    if action == "billing.plan_changed_now":
        if before_plan and after_plan:
            return f"{before_plan} ({before_interval or 'mevcut dönem'}) → {after_plan} ({after_interval or 'yeni dönem'}) geçişi hemen uygulandı."
        return "Plan değişikliği anında uygulandı."

    if action == "billing.plan_change_scheduled":
        effective_at = _short_date(after_data.get("effective_at"))
        if after_plan and effective_at:
            return f"{after_plan} planı {effective_at} tarihinde otomatik başlayacak."
        if after_plan:
            return f"{after_plan} planına geçiş bir sonraki yenileme dönemine planlandı."
        return "Plan değişikliği bir sonraki dönem için planlandı."

    if action == "billing.subscription_cancel_scheduled":
        period_end = _short_date(after_data.get("current_period_end"))
        if period_end:
            return f"Abonelik erişiminiz {period_end} tarihine kadar devam edecek, ardından dönem sonunda kapanacak."
        return "Abonelik dönem sonunda sona erecek şekilde işaretlendi."

    if action == "billing.subscription_reactivated":
        return "Dönem sonu iptal planı kaldırıldı ve abonelik aktif durumda tutuldu."

    if action == "subscription.invoice_paid":
        amount = _format_try_minor(after_data.get("amount"))
        if amount:
            return f"Son fatura başarıyla tahsil edildi ({amount})."
        return "Son fatura başarıyla tahsil edildi."

    if action == "subscription.payment_failed":
        grace_until = _short_date(after_data.get("grace_period_until"))
        if grace_until:
            return f"Ödeme alınamadı. Erişiminizin kesilmemesi için {grace_until} tarihine kadar ödeme yönteminizi güncelleyin."
        return "Ödeme alınamadı. Ödeme yönteminizi güncellemeniz gerekiyor."

    if action == "subscription.canceled":
        return "Abonelik sağlayıcı tarafında kapanmış olarak işaretlendi."

    return "Faturalama kaydı güncellendi."


class BillingHistoryService:
    async def list_events(self, tenant_id: str, *, limit: int = 20) -> list[dict[str, Any]]:
        db = await get_db()
        docs = await db.audit_logs.find(
            {
                "tenant_id": tenant_id,
                "scope": "billing",
                "action": {"$in": list(_ACTION_META.keys())},
            },
            {
                "_id": 0,
                "id": 1,
                "action": 1,
                "before": 1,
                "after": 1,
                "actor_email": 1,
                "created_at": 1,
            },
        ).sort("created_at", -1).limit(limit).to_list(limit)

        items: list[dict[str, Any]] = []
        for index, doc in enumerate(docs):
            action = str(doc.get("action") or "")
            if action not in _ACTION_META:
                continue
            meta = _ACTION_META[action]
            items.append(
                {
                    "id": str(doc.get("id") or f"billing-history-{index}"),
                    "action": action,
                    "title": meta["title"],
                    "description": _description_for_action(action, doc.get("before"), doc.get("after")),
                    "occurred_at": _iso_datetime(doc.get("created_at")),
                    "actor_label": _actor_label(doc.get("actor_email")),
                    "actor_type": "system" if _actor_label(doc.get("actor_email")) == "Sistem" else "user",
                    "tone": meta["tone"],
                }
            )
        return items


billing_history_service = BillingHistoryService()