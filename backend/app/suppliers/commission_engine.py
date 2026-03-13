"""Commission & Markup Management Engine.

Supports different revenue models:
  - supplier_commission: commission received from supplier
  - platform_markup: platform adds its own margin
  - agency_markup: agency adds their own margin

Also includes smart markup rules:
  - by supplier
  - by destination
  - by season
  - by agency tier
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger("suppliers.commission_engine")

# Default markup rules
DEFAULT_MARKUP_RULES = {
    "platform_markup_pct": 3.0,    # 3% default platform markup
    "min_markup_amount": 5.0,       # minimum markup per booking
    "max_markup_pct": 15.0,         # max cap
}


async def get_markup_rules(db) -> list[dict[str, Any]]:
    """Get all active markup rules."""
    cursor = db["markup_rules"].find(
        {"active": True}, {"_id": 0}
    ).sort("priority", 1)
    rules = await cursor.to_list(length=200)
    if not rules:
        return _default_markup_rules()
    return rules


async def upsert_markup_rule(db, rule: dict[str, Any]) -> dict[str, Any]:
    """Create or update a markup rule."""
    rule_id = rule.get("rule_id", f"rule_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}")
    doc = {
        "rule_id": rule_id,
        "rule_type": rule.get("rule_type", "platform"),  # platform | supplier | destination | season | agency_tier
        "target": rule.get("target", "all"),
        "markup_pct": float(rule.get("markup_pct", 3.0)),
        "markup_fixed": float(rule.get("markup_fixed", 0)),
        "min_amount": float(rule.get("min_amount", 0)),
        "max_pct": float(rule.get("max_pct", 15.0)),
        "priority": int(rule.get("priority", 100)),
        "active": rule.get("active", True),
        "valid_from": rule.get("valid_from"),
        "valid_until": rule.get("valid_until"),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    await db["markup_rules"].update_one(
        {"rule_id": rule_id}, {"$set": doc}, upsert=True
    )
    return doc


async def delete_markup_rule(db, rule_id: str) -> bool:
    """Deactivate a markup rule."""
    result = await db["markup_rules"].update_one(
        {"rule_id": rule_id},
        {"$set": {"active": False, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    return result.modified_count > 0


async def calculate_markup(
    db,
    supplier_code: str,
    base_price: float,
    destination: str = "",
    agency_tier: str = "standard",
    booking_date: str | None = None,
) -> dict[str, Any]:
    """Calculate the applicable markup for a booking.

    Applies rules in priority order. First matching rule wins per type.
    """
    rules = await get_markup_rules(db)

    applied_rules = []
    total_markup = 0.0
    total_markup_pct = 0.0

    now_str = (booking_date or datetime.now(timezone.utc).isoformat())[:10]

    for rule in rules:
        if not rule.get("active", True):
            continue
        # Check validity period
        if rule.get("valid_from") and now_str < rule["valid_from"][:10]:
            continue
        if rule.get("valid_until") and now_str > rule["valid_until"][:10]:
            continue

        rt = rule.get("rule_type", "platform")
        target = rule.get("target", "all")
        matches = False

        if rt == "platform" and target == "all":
            matches = True
        elif rt == "supplier" and target == supplier_code:
            matches = True
        elif rt == "destination" and destination and target.lower() in destination.lower():
            matches = True
        elif rt == "agency_tier" and target == agency_tier:
            matches = True
        elif rt == "season":
            matches = True  # Season rules apply globally when in validity period

        if matches:
            pct = rule.get("markup_pct", 0)
            fixed = rule.get("markup_fixed", 0)
            rule_markup = max(base_price * pct / 100, fixed)
            max_pct = rule.get("max_pct", 15.0)
            rule_markup = min(rule_markup, base_price * max_pct / 100)

            total_markup += rule_markup
            total_markup_pct += pct
            applied_rules.append({
                "rule_id": rule.get("rule_id"),
                "rule_type": rt,
                "target": target,
                "markup_pct": pct,
                "markup_amount": round(rule_markup, 2),
            })

    # Enforce minimum
    min_amt = DEFAULT_MARKUP_RULES["min_markup_amount"]
    if total_markup < min_amt and base_price > min_amt * 10:
        total_markup = min_amt

    final_price = base_price + total_markup

    return {
        "base_price": round(base_price, 2),
        "total_markup": round(total_markup, 2),
        "total_markup_pct": round(total_markup_pct, 2),
        "final_price": round(final_price, 2),
        "applied_rules": applied_rules,
    }


async def record_commission(
    db,
    booking_id: str,
    supplier_code: str,
    organization_id: str,
    supplier_cost: float,
    sell_price: float,
    platform_commission: float = 0,
    platform_markup: float = 0,
    agency_markup: float = 0,
    currency: str = "TRY",
):
    """Record commission for a booking."""
    doc = {
        "booking_id": booking_id,
        "supplier_code": supplier_code,
        "organization_id": organization_id,
        "supplier_cost": round(supplier_cost, 2),
        "sell_price": round(sell_price, 2),
        "platform_commission": round(platform_commission, 2),
        "platform_markup": round(platform_markup, 2),
        "agency_markup": round(agency_markup, 2),
        "total_margin": round(platform_commission + platform_markup + agency_markup, 2),
        "margin_pct": round((platform_commission + platform_markup) / max(supplier_cost, 1) * 100, 2),
        "currency": currency,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        await db["commission_records"].insert_one(doc)
    except Exception as e:
        logger.warning("Commission record failed: %s", e)


async def get_commission_summary(db, days: int = 30) -> dict[str, Any]:
    """Aggregated commission summary."""
    from datetime import timedelta
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

    pipeline = [
        {"$match": {"created_at": {"$gte": cutoff}}},
        {"$group": {
            "_id": None,
            "total_supplier_cost": {"$sum": "$supplier_cost"},
            "total_sell_price": {"$sum": "$sell_price"},
            "total_platform_commission": {"$sum": "$platform_commission"},
            "total_platform_markup": {"$sum": "$platform_markup"},
            "total_agency_markup": {"$sum": "$agency_markup"},
            "total_margin": {"$sum": "$total_margin"},
            "booking_count": {"$sum": 1},
        }},
    ]
    cursor = db["commission_records"].aggregate(pipeline)
    raw = await cursor.to_list(length=1)

    if not raw:
        return {
            "total_supplier_cost": 0, "total_sell_price": 0,
            "total_platform_commission": 0, "total_platform_markup": 0,
            "total_agency_markup": 0, "total_margin": 0,
            "booking_count": 0, "avg_margin_pct": 0,
        }

    r = raw[0]
    cost = r.get("total_supplier_cost", 0)
    return {
        "total_supplier_cost": round(cost, 2),
        "total_sell_price": round(r.get("total_sell_price", 0), 2),
        "total_platform_commission": round(r.get("total_platform_commission", 0), 2),
        "total_platform_markup": round(r.get("total_platform_markup", 0), 2),
        "total_agency_markup": round(r.get("total_agency_markup", 0), 2),
        "total_margin": round(r.get("total_margin", 0), 2),
        "booking_count": r.get("booking_count", 0),
        "avg_margin_pct": round(r.get("total_margin", 0) / max(cost, 1) * 100, 2),
    }


def _default_markup_rules() -> list[dict[str, Any]]:
    """Default markup rules."""
    return [
        {
            "rule_id": "default_platform",
            "rule_type": "platform",
            "target": "all",
            "markup_pct": 3.0,
            "markup_fixed": 0,
            "min_amount": 5.0,
            "max_pct": 15.0,
            "priority": 1000,
            "active": True,
        },
        {
            "rule_id": "premium_destination_dubai",
            "rule_type": "destination",
            "target": "dubai",
            "markup_pct": 5.0,
            "markup_fixed": 0,
            "min_amount": 10.0,
            "max_pct": 15.0,
            "priority": 50,
            "active": True,
        },
        {
            "rule_id": "vip_agency_tier",
            "rule_type": "agency_tier",
            "target": "vip",
            "markup_pct": 1.5,
            "markup_fixed": 0,
            "min_amount": 0,
            "max_pct": 10.0,
            "priority": 30,
            "active": True,
        },
    ]
