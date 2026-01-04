from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException, Query

from app.auth import get_current_user, require_roles
from app.db import get_db
from app.utils import serialize_doc

router = APIRouter(prefix="/api/reports", tags=["match-risk"])


def _parse_date_yyyy_mm_dd(value: str) -> datetime:
    try:
        y, m, d = value.split("-")
        return datetime(int(y), int(m), int(d), tzinfo=timezone.utc)
    except Exception:
        raise HTTPException(status_code=422, detail="INVALID_DATE_FORMAT")


@router.get(
    "/match-risk",
    dependencies=[Depends(require_roles(["super_admin"]))],
)
async def match_risk_summary(
    date_from: str = Query(..., alias="from"),
    date_to: str = Query(..., alias="to"),
    group_by: str = Query("pair"),
    min_matches: int = Query(0, ge=0),
    user=Depends(get_current_user),
):
    """Summary of match soft outcomes for risk/quality signal.

    - Outcome is statistical only, must not affect billing/fees.
    - Groups: pair (from_hotel->to_hotel), to_hotel, from_hotel.
    """

    db = await get_db()
    org_id = str(user.get("organization_id"))

    start = _parse_date_yyyy_mm_dd(date_from)
    end_inclusive = _parse_date_yyyy_mm_dd(date_to)
    end = end_inclusive + timedelta(days=1)

    # Load matches in range (using agency_catalog_booking_requests as proxy)
    match_filter: Dict[str, Any] = {
        "organization_id": org_id,
        "created_at": {"$gte": start, "$lt": end},
    }

    matches_cur = db.agency_catalog_booking_requests.find(
        match_filter,
        {"_id": 1, "hotel_id": 1, "from_hotel_id": 1, "to_hotel_id": 1, "created_at": 1, "reference_code": 1},
    )

    matches: List[Dict[str, Any]] = []
    async for m in matches_cur:
        matches.append(m)

    if not matches:
        return {
            "range": {"from": date_from, "to": date_to},
            "group_by": group_by,
            "items": [],
        }

    match_ids = [str(m["_id"]) for m in matches]

    # Load outcomes and build latest-outcome-per-match map
    outcomes_cur = db.match_outcomes.find(
        {
            "organization_id": org_id,
            "match_id": {"$in": match_ids},
            "marked_at": {"$gte": start, "$lt": end},
        },
        {"match_id": 1, "outcome": 1, "marked_at": 1},
    )

    latest_outcome: Dict[str, Dict[str, Any]] = {}
    async for o in outcomes_cur:
        mid = o.get("match_id")
        if not mid:
            continue
        prev = latest_outcome.get(mid)
        if not prev or o.get("marked_at") >= prev.get("marked_at"):
            latest_outcome[mid] = o

    # Group aggregation
    def group_key(m: Dict[str, Any]) -> Tuple:
        from_hid = str(m.get("from_hotel_id") or "")
        to_hid = str(m.get("hotel_id") or m.get("to_hotel_id") or "")
        if group_by == "to_hotel":
            return (to_hid,)
        if group_by == "from_hotel":
            return (from_hid,)
        # default pair
        return (from_hid, to_hid)

    groups: Dict[Tuple, List[Dict[str, Any]]] = {}
    for m in matches:
        k = group_key(m)
        groups.setdefault(k, []).append(m)

    items: List[Dict[str, Any]] = []
    for key, ms in groups.items():
        if len(ms) < min_matches:
            continue

        ms_sorted = sorted(ms, key=lambda x: x.get("created_at") or start, reverse=True)

        matches_total = len(ms_sorted)
        outcome_known = 0
        outcome_missing = 0
        not_arrived = 0

        # count latest outcome stats
        for m in ms_sorted:
            mid = str(m["_id"])
            o = latest_outcome.get(mid)
            if not o:
                outcome_missing += 1
                continue
            outcome_known += 1
            if o.get("outcome") == "not_arrived":
                not_arrived += 1

        if outcome_known > 0:
            not_arrived_rate = not_arrived / outcome_known
        else:
            not_arrived_rate = 0.0

        # last 7 matches not_arrived count
        last7 = ms_sorted[:7]
        repeat_not_arrived_7 = 0
        for m in last7:
            mid = str(m["_id"])
            o = latest_outcome.get(mid)
            if o and o.get("outcome") == "not_arrived":
                repeat_not_arrived_7 += 1

        record: Dict[str, Any] = {
            "matches_total": matches_total,
            "outcome_known": outcome_known,
            "outcome_missing": outcome_missing,
            "not_arrived": not_arrived,
            "not_arrived_rate": not_arrived_rate,
            "repeat_not_arrived_7": repeat_not_arrived_7,
        }

        if group_by == "to_hotel":
            record["to_hotel_id"] = key[0]
        elif group_by == "from_hotel":
            record["from_hotel_id"] = key[0]
        else:
            record["from_hotel_id"] = key[0]
            record["to_hotel_id"] = key[1]

        items.append(record)

    # Sort items with higher risk first: by not_arrived_rate then matches_total
    items.sort(key=lambda r: (r.get("not_arrived_rate", 0.0), r.get("matches_total", 0)), reverse=True)

    return {
        "range": {"from": date_from, "to": date_to},
        "group_by": group_by,
        "items": items,
    }


@router.get(
    "/match-risk/drilldown",
    dependencies=[Depends(require_roles(["super_admin"]))],
)
async def match_risk_drilldown(
    date_from: str = Query(..., alias="from"),
    date_to: str = Query(..., alias="to"),
    from_hotel_id: Optional[str] = None,
    to_hotel_id: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    user=Depends(get_current_user),
):
    """Drilldown per match with latest outcome.

    Returns latest outcome per match (or unknown) for inspection.
    """

    db = await get_db()
    org_id = str(user.get("organization_id"))

    start = _parse_date_yyyy_mm_dd(date_from)
    end_inclusive = _parse_date_yyyy_mm_dd(date_to)
    end = end_inclusive + timedelta(days=1)

    match_filter: Dict[str, Any] = {
        "organization_id": org_id,
        "created_at": {"$gte": start, "$lt": end},
    }
    if from_hotel_id:
        match_filter["from_hotel_id"] = from_hotel_id
    if to_hotel_id:
        match_filter["hotel_id"] = to_hotel_id

    matches_cur = db.agency_catalog_booking_requests.find(
        match_filter,
        {
            "_id": 1,
            "hotel_id": 1,
            "from_hotel_id": 1,
            "to_hotel_id": 1,
            "created_at": 1,
            "reference_code": 1,
        },
    ).sort("created_at", -1).limit(limit)

    matches: List[Dict[str, Any]] = []
    async for m in matches_cur:
        matches.append(m)

    if not matches:
        return {"items": []}

    match_ids = [str(m["_id"]) for m in matches]

    outcomes_cur = db.match_outcomes.find(
        {
            "organization_id": org_id,
            "match_id": {"$in": match_ids},
            "marked_at": {"$lt": end},
        },
        {"match_id": 1, "outcome": 1, "marked_at": 1, "note": 1},
    )

    latest_outcome: Dict[str, Dict[str, Any]] = {}
    async for o in outcomes_cur:
        mid = o.get("match_id")
        if not mid:
            continue
        prev = latest_outcome.get(mid)
        if not prev or o.get("marked_at") >= prev.get("marked_at"):
            latest_outcome[mid] = o

    items: List[Dict[str, Any]] = []
    for m in matches:
        mid = str(m["_id"])
        o = latest_outcome.get(mid)
        if o:
            outcome = o.get("outcome")
            outcome_marked_at = o.get("marked_at")
            outcome_note = o.get("note")
        else:
            outcome = "unknown"
            outcome_marked_at = None
            outcome_note = None

        created_at = m.get("created_at")
        if hasattr(created_at, "isoformat"):
            created_at_iso = created_at.isoformat()
        else:
            created_at_iso = str(created_at)

        if hasattr(outcome_marked_at, "isoformat"):
            outcome_marked_at_iso = outcome_marked_at.isoformat()
        else:
            outcome_marked_at_iso = outcome_marked_at

        items.append(
            {
                "match_id": mid,
                "created_at": created_at_iso,
                "from_hotel_id": str(m.get("from_hotel_id") or ""),
                "to_hotel_id": str(m.get("to_hotel_id") or m.get("hotel_id") or ""),
                "reference_code": m.get("reference_code"),
                "outcome": outcome,
                "outcome_marked_at": outcome_marked_at_iso,
                "outcome_note": outcome_note,
            }
        )

    return {"items": items}
