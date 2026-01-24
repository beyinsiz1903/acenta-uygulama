from __future__ import annotations

from datetime import date
from typing import Any


async def resolve_commission_rate_for_product(
    db,
    *,
    organization_id: str,
    partner_id: str,
    product_id: str,
    check_in: date | None = None,
) -> float:
    """Resolve commission_rate percent for a given (partner, product).

    V1 semantics:
    - If there is a b2b_product_authorizations document with commission_rate set,
      use that value.
    - Otherwise, fall back to partner_profiles.default_markup_percent (legacy field).
    - If nothing is configured, return 0.0.

    NOTE: This function intentionally does not consider discount groups or coupons;
    it only resolves the *intended* commission percent for margin sharing.
    """

    # 1) Try explicit product authorization
    auth = await db.b2b_product_authorizations.find_one(
        {
            "organization_id": organization_id,
            "partner_id": partner_id,
            "product_id": {"$in": [product_id]},
        },
        {"commission_rate": 1, "_id": 0},
    )
    if auth is not None:
        rate = auth.get("commission_rate")
        if isinstance(rate, (int, float)):
            try:
                return float(rate)
            except Exception:
                return 0.0

    # 2) Fallback: partner default markup percent (used as default commission)
    partner = await db.partner_profiles.find_one(
        {"_id": partner_id, "organization_id": organization_id},
        {"default_markup_percent": 1, "_id": 0},
    )
    if partner is not None:
        rate = partner.get("default_markup_percent")
        if isinstance(rate, (int, float)):
            try:
                return float(rate)
            except Exception:
                return 0.0

    return 0.0
