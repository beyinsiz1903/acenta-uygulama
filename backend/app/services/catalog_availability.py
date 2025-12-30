from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, List, Optional

from bson import ObjectId

from app.utils import now_utc


def expand_dates(start: str, end: Optional[str]) -> List[str]:
    """Expand start/end (YYYY-MM-DD) to a list of day strings (inclusive).

    If end is None, returns [start]. Raises ValueError on invalid dates.
    """

    if not start:
        raise ValueError("start is required")

    try:
        s = date.fromisoformat(start)
    except Exception as exc:  # pragma: no cover - defensive
        raise ValueError("INVALID_START_DATE") from exc

    if end:
        try:
            e = date.fromisoformat(end)
        except Exception as exc:  # pragma: no cover
            raise ValueError("INVALID_END_DATE") from exc
    else:
        e = s

    if e < s:
        raise ValueError("END_BEFORE_START")

    days: List[str] = []
    cur = s
    from datetime import timedelta

    while cur <= e:
        days.append(cur.isoformat())
        cur += timedelta(days=1)
    return days


def compute_units(mode: str, pax: int) -> int:
    mode = (mode or "pax").lower()
    if mode == "bookings":
        return 1
    # default pax-based
    try:
        p = int(pax or 0)
    except Exception:
        p = 0
    return max(p, 0)


async def compute_used_units(
    db,
    *,
    org_id: str,
    agency_id: str,
    product_oid: ObjectId,
    variant_oid: ObjectId,
    days: List[str],
    mode: str,
) -> Dict[str, int]:
    """Compute already used units per day for given variant and days.

    - Counts only bookings with status in ("new", "approved").
    - Uses `allocation` snapshot if present; otherwise falls back to dates+pax.
    """

    target_days = set(days)
    if not target_days:
        return {}

    used: Dict[str, int] = {}

    cursor = db.agency_catalog_booking_requests.find(
        {
            "organization_id": org_id,
            "agency_id": agency_id,
            "product_id": product_oid,
            "variant_id": variant_oid,
            "status": {"$in": ["new", "approved"]},
        }
    )

    async for doc in cursor:
        alloc = doc.get("allocation") or {}
        alloc_days: Optional[List[str]] = alloc.get("days")  # type: ignore[assignment]
        alloc_units: Optional[int] = alloc.get("units")

        if alloc_days and alloc_units is not None:
            u = int(alloc_units)
            for d in alloc_days:
                if d in target_days:
                    used[d] = used.get(d, 0) + u
            continue

        # Fallback for old bookings without allocation snapshot
        b_dates = doc.get("dates") or {}
        start = (b_dates.get("start") or "").strip()
        end = (b_dates.get("end") or None)
        if not start:
            continue
        try:
            booking_days = expand_dates(start, end)
        except ValueError:
            continue

        pax = int(doc.get("pax") or 0)
        u = compute_units(mode, pax)
        if u <= 0:
            continue
        for d in booking_days:
            if d in target_days:
                used[d] = used.get(d, 0) + u

    return used


async def compute_availability(
    db,
    *,
    org_id: str,
    agency_id: str,
    product_oid: ObjectId,
    variant: Dict[str, Any],
    days: List[str],
    pax: int,
) -> Dict[str, Any]:
    """Compute availability summary for given variant, days and pax.

    Returns dict with per-day details and overall summary.
    """

    capacity = variant.get("capacity") or {}
    mode_raw = (capacity.get("mode") or "pax").lower()
    mode = mode_raw if mode_raw in {"pax", "bookings"} else "pax"

    requested_units = compute_units(mode, pax)

    max_per_day_val = capacity.get("max_per_day")
    max_per_day: Optional[int]
    if max_per_day_val is None:
        max_per_day = None
    else:
        try:
            max_per_day = int(max_per_day_val)
        except Exception:
            max_per_day = None

    overbook = bool(capacity.get("overbook", False))

    used_map = await compute_used_units(
        db,
        org_id=org_id,
        agency_id=agency_id,
        product_oid=product_oid,
        variant_oid=variant["_id"],
        days=days,
        mode=mode,
    )

    day_results: List[Dict[str, Any]] = []
    overall_can_book = True
    blocking_day: Optional[str] = None

    for d in days:
        used = int(used_map.get(d, 0))
        if max_per_day is None:
            remaining = None
            can_book_day = True
        else:
            remaining = max_per_day - used
            if overbook:
                can_book_day = True
            else:
                can_book_day = remaining >= requested_units

        day_results.append(
            {
                "day": d,
                "used": used,
                "max": max_per_day,
                "remaining": remaining,
                "can_book": can_book_day,
            }
        )

        if not can_book_day and overall_can_book:
            overall_can_book = False
            blocking_day = d

    summary = {"can_book": overall_can_book, "blocking_day": blocking_day}

    return {
        "mode": mode,
        "requested_units": requested_units,
        "days": day_results,
        "summary": summary,
    }
