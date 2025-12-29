from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Tuple

from app.db import get_db


def _date_range(start: date, end: date) -> List[date]:
    """Inclusive date range helper."""
    days: List[date] = []
    cur = start
    while cur <= end:
        days.append(cur)
        cur += timedelta(days=1)
    return days


def _matches_date_rule(rule: Dict[str, Any], d: date) -> bool:
    dr = rule.get("date_rule") or {}
    t = (dr.get("type") or "date_range").lower()

    if t == "weekend":
        return d.weekday() in (4, 5, 6)  # Fri, Sat, Sun
    if t == "weekday":
        return d.weekday() in (0, 1, 2, 3)  # Mon-Thu

    # date_range (inclusive)
    from_str = dr.get("from_date")
    to_str = dr.get("to_date")
    try:
        from_d = date.fromisoformat(from_str) if from_str else None
        to_d = date.fromisoformat(to_str) if to_str else None
    except Exception:  # noqa: BLE001
        from_d = None
        to_d = None

    if from_d and d < from_d:
        return False
    if to_d and d > to_d:
        return False
    return True


def _apply_rate_rules(
    *,
    base_price: float | None,
    base_currency: str | None,
    base_min_stay: int | None,
    d: date,
    rules: List[Dict[str, Any]],
) -> Tuple[float | None, str | None, int | None]:
    price = base_price
    currency = base_currency
    min_stay = base_min_stay

    for rule in rules:
        if not rule.get("active", True):
            continue
        scope = (rule.get("scope") or "both").lower()
        if scope not in ("rates", "both"):
            continue
        if not _matches_date_rule(rule, d):
            continue

        rr = rule.get("rate_rule") or {}
        rr_type = (rr.get("type") or "percent").lower()
        rr_val = rr.get("value", 0)

        # Base price fallback 0'a çekilebilir; bu durumda percent tipinde değişmez
        if price is None:
            price = 0.0

        if rr_type == "percent":
            try:
                price = float(price) * (1.0 + float(rr_val) / 100.0)
            except Exception:  # noqa: BLE001
                continue
        elif rr_type == "absolute":
            try:
                price = float(price) + float(rr_val)
            except Exception:  # noqa: BLE001
                continue

        # İleride min_stay, currency vb. buradan da güncellenebilir

    return price, currency, min_stay


def _apply_availability_rules(
    *,
    base_available: int | None,
    base_stop_sell: bool | None,
    d: date,
    rules: List[Dict[str, Any]],
) -> Tuple[int | None, bool | None]:
    available = base_available
    stop_sell = base_stop_sell

    for rule in rules:
        if not rule.get("active", True):
            continue
        scope = (rule.get("scope") or "both").lower()
        if scope not in ("availability", "both"):
            continue
        if not _matches_date_rule(rule, d):
            continue

        ar = rule.get("availability_rule") or {}
        ar_type = (ar.get("type") or "delta").lower()
        ar_val = ar.get("value", 0)

        if available is None:
            available = 0

        try:
            if ar_type == "delta":
                available = max(0, int(available) + int(ar_val))
            elif ar_type == "set":
                available = max(0, int(ar_val))
        except Exception:  # noqa: BLE001
            continue

        if "stop_sell" in rule and rule["stop_sell"] is not None:
            stop_sell = bool(rule["stop_sell"])

    return available, stop_sell


async def build_internal_canonical_ari(
    *,
    org_id: str,
    hotel_id: str,
    from_date: date,
    to_date: date,
) -> tuple[Dict[str, Any], Dict[str, Any]]:
    """Build canonical ARI from internal rules + PMS snapshots.

    - Reads:
      - internal_ari_rules (active=true)
      - pms_daily_rates
      - pms_daily_availability
    - Writes nothing; purely computes a canonical ARI payload.

    Returns (canonical, stats).
    """

    db = await get_db()

    rules_cursor = db.internal_ari_rules.find(
        {
            "organization_id": org_id,
            "hotel_id": hotel_id,
            "active": True,
        }
    ).sort("created_at", 1)

    rules: List[Dict[str, Any]] = [doc async for doc in rules_cursor]

    stats: Dict[str, Any] = {
        "rule_count": len(rules),
        "parsed_rate_days": 0,
        "parsed_availability_days": 0,
    }

    canonical: Dict[str, Any] = {"roomTypes": {}, "ratePlans": {}}

    if not rules:
        return canonical, stats

    days = _date_range(from_date, to_date)
    day_strings = [d.isoformat() for d in days]

    # Rates snapshot
    rate_docs = await db.pms_daily_rates.find(
        {
            "organization_id": org_id,
            "hotel_id": hotel_id,
            "date": {"$in": day_strings},
        }
    ).to_list(len(day_strings) * 10)

    for doc in rate_docs or []:
        pms_rate_id = str(doc.get("pms_rate_plan_id"))
        day_str = str(doc.get("date"))
        try:
            d = date.fromisoformat(day_str)
        except Exception:  # noqa: BLE001
            continue

        if d < from_date or d > to_date:
            continue

        base_price = doc.get("price")
        base_currency = doc.get("currency", "TRY")
        base_min_stay = doc.get("min_stay")

        new_price, new_currency, new_min_stay = _apply_rate_rules(
            base_price=base_price,
            base_currency=base_currency,
            base_min_stay=base_min_stay,
            d=d,
            rules=rules,
        )

        rp = canonical["ratePlans"].setdefault(pms_rate_id, {"dates": {}})
        rp["dates"][day_str] = {
            "price": new_price,
            "currency": new_currency,
            "min_stay": new_min_stay,
        }
        stats["parsed_rate_days"] += 1

    # Availability snapshot
    avail_docs = await db.pms_daily_availability.find(
        {
            "organization_id": org_id,
            "hotel_id": hotel_id,
            "date": {"$in": day_strings},
        }
    ).to_list(len(day_strings) * 10)

    for doc in avail_docs or []:
        pms_room_id = str(doc.get("pms_room_type_id"))
        day_str = str(doc.get("date"))
        try:
            d = date.fromisoformat(day_str)
        except Exception:  # noqa: BLE001
            continue

        if d < from_date or d > to_date:
            continue

        base_available = doc.get("available")
        base_stop_sell = doc.get("stop_sell")

        new_available, new_stop_sell = _apply_availability_rules(
            base_available=base_available,
            base_stop_sell=base_stop_sell,
            d=d,
            rules=rules,
        )

        rt = canonical["roomTypes"].setdefault(pms_room_id, {"dates": {}})
        rt["dates"][day_str] = {
            "available": new_available,
            "stop_sell": new_stop_sell,
        }
        stats["parsed_availability_days"] += 1

    return canonical, stats
