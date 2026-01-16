from __future__ import annotations

from datetime import date
from typing import Any, Dict, Optional

from app.errors import AppError
from app.utils import now_utc


async def resolve_discount_group(
    db,
    organization_id: str,
    *,
    agency_id: Optional[str],
    product_id: Optional[str],
    product_type: Optional[str],
    check_in: Optional[date],
) -> Optional[Dict[str, Any]]:
    """Resolve active B2B discount group for given context.

    - Filters by organization_id, status=active
    - Optional validity window check
    - Optional scope match: agency_id / product_id / product_type
    - Orders by priority DESC, updated_at DESC and returns the first match.
    """

    q: Dict[str, Any] = {"organization_id": organization_id, "status": "active"}

    if product_type:
        q["scope.product_type"] = product_type

    # Validity window: from <= check_in <= to (inclusive bounds in v1)
    if check_in is not None:
        check_in_iso = check_in.isoformat()
        q["validity.from"] = {"$lte": check_in_iso}
        q["validity.to"] = {"$gte": check_in_iso}

    # Scope matches are best-effort; if agency/product filters are set on group,
    # they must match, otherwise group is ignored.
    or_filters = []
    if agency_id:
        or_filters.append({"scope.agency_id": {"$in": [None, agency_id]}})
    if product_id:
        or_filters.append({"scope.product_id": {"$in": [None, product_id]}})

    if or_filters:
        q["$and"] = or_filters

    cur = (
        db.b2b_discount_groups.find(q)
        .sort([("priority", -1), ("updated_at", -1)])
        .limit(1)
    )
    groups = await cur.to_list(1)
    if not groups:
        return None
    group = groups[0]
    group.pop("_id", None)
    return group


def apply_discount(
    *,
    base_net: float,
    base_sell: float,
    markup_percent: float,
    group: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """Apply B2B discount on top of markup.

    v1 semantics:
    - Only percent rules with applies_to="markup_only" are considered.
    - discount_amount = markup_amount * (discount_percent/100).
    - Clamp: 0 <= discount_percent <= 100, 0 <= discount_amount <= markup_amount.
    - final_sell >= base_net (never sell below net).
    """

    if not group or not group.get("rules"):
        markup_amount = round(base_sell - base_net, 2)
        return {
            "discount_amount": 0.0,
            "final_net": round(base_net, 2),
            "final_sell": round(base_sell, 2),
            "breakdown": {
                "base": round(base_net, 2),
                "markup_amount": markup_amount,
                "discount_amount": 0.0,
            },
            "trace_discount": None,
        }

    # v1: single first rule only
    rule = group["rules"][0]
    rule_type = rule.get("type")
    applies_to = rule.get("applies_to") or "markup_only"
    value = float(rule.get("value") or 0.0)

    if rule_type != "percent" or applies_to != "markup_only":
        # Unsupported in v1 – no-op
        markup_amount = round(base_sell - base_net, 2)
        return {
            "discount_amount": 0.0,
            "final_net": round(base_net, 2),
            "final_sell": round(base_sell, 2),
            "breakdown": {
                "base": round(base_net, 2),
                "markup_amount": markup_amount,
                "discount_amount": 0.0,
            },
            "trace_discount": None,
        }

    # Clamp percent
    if value < 0:
        value = 0.0
    if value > 100:
        value = 100.0

    markup_amount = max(0.0, round(base_sell - base_net, 2))
    discount_amount = round(markup_amount * (value / 100.0), 2)

    # Clamp discount to markup_amount
    if discount_amount > markup_amount:
        discount_amount = markup_amount

    final_sell = round(base_sell - discount_amount, 2)
    # Ensure final_sell is never below net
    if final_sell < base_net:
        final_sell = round(base_net, 2)

    breakdown = {
        "base": round(base_net, 2),
        "markup_amount": markup_amount,
        "discount_amount": discount_amount,
    }

    trace_discount = {
        "discount_group_id": str(group.get("_id")) if group.get("_id") else None,
        "discount_group_name": group.get("name"),
        "discount_percent": value,
        "discount_amount": discount_amount,
    }

    return {
        "discount_amount": discount_amount,
        "final_net": round(base_net, 2),
        "final_sell": final_sell,
        "breakdown": breakdown,
        "trace_discount": trace_discount,
    }
