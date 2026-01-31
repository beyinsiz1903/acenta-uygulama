from __future__ import annotations

from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, List, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.errors import AppError
from app.services.currency_guard import ensure_try


def _q2(value: Decimal) -> Decimal:
    """Quantize to 2 decimal places with HALF_UP rounding."""
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


async def calculate_price(
    db: AsyncIOMotorDatabase,
    base_amount: Decimal,
    *,
    organization_id: str,
    currency: str,
    tenant_id: Optional[str] = None,
    agency_id: Optional[str] = None,
    supplier: Optional[str] = None,
    now: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Calculate final price and commission based on pricing rules.

    - Enforces TRY-only for now
    - Fetches applicable rules and applies them deterministically
    - Returns pricing breakdown suitable for persistence on booking
    """

    # TRY-only enforcement
    ensure_try(currency)

    now = now or datetime.utcnow()

    # Fetch rules for organization; further filtering done in Python for clarity
    cursor = db.pricing_rules.find({"organization_id": organization_id})
    rules: List[Dict[str, Any]] = await cursor.to_list(length=1000)

    applicable: List[Dict[str, Any]] = []
    for r in rules:
        # Time window
        vf = r.get("valid_from")
        vt = r.get("valid_to")
        if vf and now < vf:
            continue
        if vt and now > vt:
            continue

        # Tenant filter
        if r.get("tenant_id") is not None and r["tenant_id"] != tenant_id:
            continue

        # Agency filter (future use)
        if r.get("agency_id") is not None and r["agency_id"] != agency_id:
            continue

        # Supplier filter
        if r.get("supplier") is not None and r["supplier"] != supplier:
            continue

        applicable.append(r)

    # Sort: priority DESC, created_at ASC for deterministic tie-break
    def _sort_key(r: Dict[str, Any]) -> Any:
        return (-int(r.get("priority", 0)), r.get("created_at"))

    applicable.sort(key=_sort_key)

    current = _q2(base_amount)
    commission = Decimal("0.00")
    applied_rules: List[Dict[str, Any]] = []
    # Track non-stackable rule types so we skip same types later
    blocked_types: set[str] = set()

    for r in applicable:
        rule_type = r.get("rule_type") or ""
        if rule_type in blocked_types:
            continue

        value_raw = r.get("value")
        value_dec = Decimal(str(value_raw))
        stackable = bool(r.get("stackable", True))

        before = current

        if rule_type == "markup_pct":
            current = _q2(current * (Decimal("1.00") + value_dec / Decimal("100")))
        elif rule_type == "markup_fixed":
            current = _q2(current + value_dec)
        elif rule_type == "commission_pct":
            commission += _q2(base_amount * (value_dec / Decimal("100")))
        elif rule_type == "commission_fixed":
            commission += _q2(value_dec)
        else:
            # Unknown rule_type -> skip
            continue

        applied_rules.append(
            {
                "rule_id": str(r.get("_id")),
                "rule_type": rule_type,
                "value": str(value_dec),
                "priority": int(r.get("priority", 0)),
            }
        )

        if not stackable:
            blocked_types.add(rule_type)

    final_amount = current
    margin_amount = _q2(final_amount - base_amount)

    return {
        "base_amount": _q2(base_amount),
        "final_amount": final_amount,
        "commission_amount": commission,
        "margin_amount": margin_amount,
        "applied_rules": applied_rules,
    }
