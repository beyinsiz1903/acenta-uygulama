"""Promotion Engine - Standalone promotion management and resolution.

Promotion types:
  - early_booking: % discount for bookings N+ days before check-in
  - flash_sale: Time-limited deep discount
  - campaign_discount: Named campaign with % or fixed discount
  - fixed_price_override: Override sell price completely

Promotions are stored in `promotions` collection and resolved
by the Pricing Distribution Engine during price calculation.
"""
from __future__ import annotations

import uuid
from typing import Any, Optional

from app.db import get_db
from app.utils import now_utc, serialize_doc

PROMO_TYPES = ("early_booking", "flash_sale", "campaign_discount", "fixed_price_override")


async def create_promotion(
    organization_id: str,
    name: str,
    promo_type: str,
    discount_pct: float = 0.0,
    fixed_price: Optional[float] = None,
    promo_code: str = "",
    scope: Optional[dict] = None,
    valid_from: Optional[str] = None,
    valid_to: Optional[str] = None,
    min_days_before: int = 0,
    max_uses: int = 0,
    created_by: str = "",
) -> dict[str, Any]:
    """Create a new promotion rule."""
    db = await get_db()
    now = now_utc()
    rule_id = f"promo_{uuid.uuid4().hex[:8]}"

    doc = {
        "rule_id": rule_id,
        "organization_id": organization_id,
        "name": name,
        "promo_type": promo_type,
        "discount_pct": discount_pct,
        "fixed_price": fixed_price,
        "promo_code": promo_code,
        "scope": scope or {},
        "valid_from": valid_from,
        "valid_to": valid_to,
        "min_days_before": min_days_before,
        "max_uses": max_uses,
        "current_uses": 0,
        "active": True,
        "created_by": created_by,
        "created_at": now,
        "updated_at": now,
    }
    await db.promotions.insert_one(doc)
    return serialize_doc(doc)


async def list_promotions(
    organization_id: str,
    active_only: bool = False,
    promo_type: Optional[str] = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """List promotions for an organization."""
    db = await get_db()
    query: dict[str, Any] = {"organization_id": organization_id}
    if active_only:
        query["active"] = True
    if promo_type:
        query["promo_type"] = promo_type

    docs = await db.promotions.find(query, {"_id": 0}).sort("created_at", -1).to_list(limit)
    return [serialize_doc(d) for d in docs]


async def update_promotion(
    organization_id: str,
    rule_id: str,
    updates: dict[str, Any],
) -> Optional[dict[str, Any]]:
    """Update a promotion."""
    db = await get_db()
    updates["updated_at"] = now_utc()
    result = await db.promotions.find_one_and_update(
        {"organization_id": organization_id, "rule_id": rule_id},
        {"$set": updates},
        return_document=True,
    )
    return serialize_doc(result) if result else None


async def delete_promotion(organization_id: str, rule_id: str) -> bool:
    """Delete a promotion."""
    db = await get_db()
    result = await db.promotions.delete_one({"organization_id": organization_id, "rule_id": rule_id})
    return result.deleted_count > 0


async def toggle_promotion(organization_id: str, rule_id: str, active: bool) -> Optional[dict[str, Any]]:
    """Toggle promotion active status."""
    return await update_promotion(organization_id, rule_id, {"active": active})
