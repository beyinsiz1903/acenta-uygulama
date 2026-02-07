"""SMS Notification service (B).

Handles template rendering, sending, logging.
"""
from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from app.db import get_db
from app.utils import now_utc, serialize_doc
from app.services.sms.provider import get_sms_provider


# Default templates
DEFAULT_TEMPLATES = {
    "reservation_confirmed": "Sayin {customer_name}, {product_name} rezervasyonunuz onaylandi. Kod: {booking_code}",
    "reservation_reminder": "Hatirlatma: {product_name} - {date} tarihli rezervasyonunuz yaklasiyorsa hazirlanin!",
    "payment_received": "Odemeniz alindi. Tutar: {amount} {currency}. Tesekkurler!",
    "check_in_reminder": "Check-in hatirlatmasi: {product_name} icin QR kodunuzu hazir bulundurun.",
    "custom": "{message}",
}


def render_template(template_key: str, variables: Dict[str, str]) -> str:
    template = DEFAULT_TEMPLATES.get(template_key, "{message}")
    try:
        return template.format(**variables)
    except KeyError:
        return template


async def send_sms_notification(
    tenant_id: str,
    org_id: str,
    to: str,
    template_key: str,
    variables: Dict[str, str],
    provider_name: str = "mock",
    created_by: str = "",
) -> Dict[str, Any]:
    db = await get_db()
    provider = get_sms_provider(provider_name)

    message = render_template(template_key, variables)
    result = await provider.send_sms(to, message)

    log_doc = {
        "_id": str(uuid.uuid4()),
        "tenant_id": tenant_id,
        "organization_id": org_id,
        "to": to,
        "template_key": template_key,
        "message": message,
        "provider": provider_name,
        "message_id": result.get("message_id"),
        "status": result.get("status", "unknown"),
        "created_by": created_by,
        "created_at": now_utc(),
    }
    await db.sms_logs.insert_one(log_doc)
    return serialize_doc(log_doc)


async def send_bulk_sms(
    tenant_id: str,
    org_id: str,
    recipients: List[str],
    template_key: str,
    variables: Dict[str, str],
    provider_name: str = "mock",
    created_by: str = "",
) -> Dict[str, Any]:
    db = await get_db()
    provider = get_sms_provider(provider_name)

    message = render_template(template_key, variables)
    result = await provider.send_bulk(recipients, message)

    log_doc = {
        "_id": str(uuid.uuid4()),
        "tenant_id": tenant_id,
        "organization_id": org_id,
        "recipients": recipients,
        "template_key": template_key,
        "message": message,
        "provider": provider_name,
        "batch_id": result.get("batch_id"),
        "count": result.get("count", 0),
        "status": result.get("status", "unknown"),
        "created_by": created_by,
        "created_at": now_utc(),
    }
    await db.sms_logs.insert_one(log_doc)
    return serialize_doc(log_doc)


async def list_sms_logs(
    org_id: str,
    tenant_id: str = None,
    limit: int = 50,
) -> List[Dict]:
    db = await get_db()
    q: Dict[str, Any] = {"organization_id": org_id}
    if tenant_id:
        q["tenant_id"] = tenant_id
    cursor = db.sms_logs.find(q).sort("created_at", -1).limit(limit)
    return [serialize_doc(d) for d in await cursor.to_list(length=limit)]


async def get_sms_templates() -> Dict[str, str]:
    return DEFAULT_TEMPLATES.copy()
