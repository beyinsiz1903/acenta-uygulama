from __future__ import annotations

from typing import Any, Dict, Optional

from bson import ObjectId
from fastapi import Request
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.services.audit import write_audit_log


async def emit_pricing_audit_if_needed(
    db: AsyncIOMotorDatabase,
    booking_id: str,
    tenant_id: Optional[str],
    organization_id: str,
    actor: Dict[str, Any],
    request: Request,
) -> None:
    """Emit PRICING_RULE_APPLIED audit once per booking.

    - Checks booking.pricing_audit_emitted flag to ensure idempotency
    - Meta payload derived from booking.pricing
    """

    # Load booking document
    doc = await db.bookings.find_one({"_id": ObjectId(booking_id)})
    if not doc:
        return

    if doc.get("pricing_audit_emitted"):
        return

    pricing = doc.get("pricing") or {}

    base_amount = pricing.get("base_amount")
    final_amount = pricing.get("final_amount")
    currency = pricing.get("currency") or "TRY"
    applied_rules = pricing.get("applied_rules") or []

    applied_rule_ids = [r.get("rule_id") for r in applied_rules if r.get("rule_id")]

    meta = {
        "tenant_id": tenant_id or str(doc.get("tenant_id")) if doc.get("tenant_id") else None,
        "organization_id": organization_id,
        "base_amount": base_amount,
        "final_amount": final_amount,
        "currency": currency,
        "applied_rule_ids": applied_rule_ids,
        "supplier": (doc.get("supplier_id") or doc.get("supplier")),
    }

    await write_audit_log(
        db,
        organization_id=organization_id,
        actor=actor,
        request=request,
        action="PRICING_RULE_APPLIED",
        target_type="booking",
        target_id=booking_id,
        before=None,
        after=None,
        meta=meta,
    )

    # Mark booking as audited to keep idempotent
    await db.bookings.update_one(
        {"_id": ObjectId(booking_id)},
        {"$set": {"pricing_audit_emitted": True}},
    )
