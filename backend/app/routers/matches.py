from __future__ import annotations

from datetime import timedelta
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.auth import get_current_user, require_roles
from app.db import get_db
from app.schemas import BookingPublicView
from app.utils import now_utc, build_booking_public_view
from app.services.risk_profile import load_risk_profile, is_high_risk

router = APIRouter(prefix="/api/admin/matches", tags=["admin-matches"])


class MatchSummaryItem(BaseModel):
    id: str
    agency_id: str
    agency_name: Optional[str] = None
    hotel_id: str
    hotel_name: Optional[str] = None
    total_bookings: int
    pending: int
    confirmed: int
    cancelled: int
    confirm_rate: float
    # cancel_rate is now the behavioral (non-operational) cancel rate (legacy)
    cancel_rate: float
    operational_cancel_rate: float
    behavioral_cancel_rate: float
    last_booking_at: Optional[str] = None
    # v1.5: no-show based metrics from booking_outcomes
    no_show_rate: float = 0.0
    repeat_no_show_7: int = 0
    # v2.1: verified-aware metrics
    verified_bookings_30d: int = 0
    verified_no_show_30d: int = 0
    verified_share: float = 0.0
    # Debug field for v1.2: how many operational cancels in last 7 days
    repeat_cancelled_operational_7: int = 0
    # Legacy field for behavioral cancels (repeat_not_arrived_7)
    repeat_not_arrived_7: int = 0
    # Unified risk flag (using RiskProfile)
    high_risk: bool = False
    high_risk_reasons: list[str] = []
    # debug: what inputs were used for risk
    risk_inputs: dict[str, Any] | None = None

    # Optional action fields (only populated when include_action=1)
    action_status: Optional[str] = None
    action_reason_code: Optional[str] = None
    action_updated_at: Optional[str] = None
    action_updated_by_email: Optional[str] = None


class MatchSummaryResponse(BaseModel):
    range: dict[str, Any]
    risk_profile: dict[str, Any]
    items: List[MatchSummaryItem]


class MatchMetrics(BaseModel):
    total_bookings: int
    pending: int
    confirmed: int
    cancelled: int
    confirm_rate: float
    cancel_rate: float
    avg_approval_hours: Optional[float] = None


class MatchDetailOut(BaseModel):
    id: str
    agency_id: str
    agency_name: Optional[str] = None
    hotel_id: str
    hotel_name: Optional[str] = None
    range: dict[str, Any]
    metrics: MatchMetrics
    bookings: List[BookingPublicView]


class MatchEventItem(BaseModel):
    booking_id: str
    created_at: str
    status: str
    cancel_reason: Optional[str] = None
    cancel_tag: str


class MatchEventsSummary(BaseModel):
    behavioral_cancel_count: int
    operational_cancel_count: int
    total_bookings_in_window: int


class MatchEventsResponse(BaseModel):
    ok: bool = True
    match_id: str
    window: dict[str, Any]
    summary: MatchEventsSummary
    items: list[MatchEventItem]



class MatchAction(BaseModel):
    match_id: str
    agency_id: str
    hotel_id: str
    status: str = "none"  # none|watchlist|manual_review|blocked
    reason_code: str | None = None
    note: str | None = None
    updated_at: Optional[str] = None
    updated_by_email: Optional[str] = None


class MatchActionResponse(BaseModel):
    ok: bool = True
    action: MatchAction



async def _resolve_names(db, org_id: str, agency_ids: list[str], hotel_ids: list[str]) -> tuple[dict[str, str], dict[str, str]]:
    """Helper to build {id -> name} maps for agencies and hotels."""
    agencies = await db.agencies.find({"organization_id": org_id, "_id": {"$in": agency_ids}}).to_list(length=None)
    hotels = await db.hotels.find({"organization_id": org_id, "_id": {"$in": hotel_ids}}).to_list(length=None)
    agency_name_map = {str(a["_id"]): a.get("name", "") for a in agencies}
    hotel_name_map = {str(h["_id"]): h.get("name", "") for h in hotels}
    return agency_name_map, hotel_name_map


@router.get("", response_model=MatchSummaryResponse, dependencies=[Depends(require_roles(["super_admin", "admin"]))])
async def list_matches(
    days: int = Query(30, ge=1, le=365),
    min_total: int = Query(3, ge=1, le=1000),
    include_action: bool = Query(False),
    only_high_risk: bool = Query(False),
    sort: str = Query("high_risk_first"),
    include_reasons: bool = Query(True),
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    """List agency–hotel pairs (matches) aggregated from bookings.

    This is a P4 v0-style risk aggregation backbone:
    - groups by (agency_id, hotel_id)
    - counts bookings by status
    - computes basic rates (confirm/cancel)
    """
    org_id = user.get("organization_id")
    cutoff = now_utc() - timedelta(days=days)

    pipeline = [
        {"$match": {"organization_id": org_id, "created_at": {"$gte": cutoff}}},
        {
            "$group": {
                "_id": {"agency_id": "$agency_id", "hotel_id": "$hotel_id"},
                "total": {"$sum": 1},
                "pending": {"$sum": {"$cond": [{"$eq": ["$status", "pending"]}, 1, 0]}},
                "confirmed": {"$sum": {"$cond": [{"$eq": ["$status", "confirmed"]}, 1, 0]}},
                "cancelled": {"$sum": {"$cond": [{"$eq": ["$status", "cancelled"]}, 1, 0]}},
                "operational_cancelled": {
                    "$sum": {
                        "$cond": [
                            {
                                "$and": [
                                    {"$eq": ["$status", "cancelled"]},
                                    {
                                        "$or": [
                                            {"$in": ["$cancel_reason", ["PRICE_CHANGED", "RATE_CHANGED"]]},
                                            {"$eq": ["$cancelled_by", "system"]},
                                        ]
                                    },
                                ]
                            },
                            1,
                            0,
                        ]
                    }
                },
                "last_booking_at": {"$max": "$created_at"},
            }
        },
        {"$sort": {"total": -1}},
    ]

    rows = await db.bookings.aggregate(pipeline).to_list(length=None)

    # filter by min_total
    filtered = [r for r in rows if int(r.get("total") or 0) >= min_total]

    agency_ids: list[str] = []
    hotel_ids: list[str] = []
    for r in filtered:
        key = r.get("_id") or {}
        a_id = str(key.get("agency_id") or "")
        h_id = str(key.get("hotel_id") or "")
        if a_id:
            agency_ids.append(a_id)
        if h_id:
            hotel_ids.append(h_id)

    # v1.5: load no-show metrics from booking_outcomes (7d window)
    no_show_rate_by_match: dict[str, float] = {}
    repeat_no_show_7_by_match: dict[str, int] = {}
    if filtered:
        outcomes_cursor = db.booking_outcomes.aggregate(
            [
                {
                    "$match": {
                        "organization_id": org_id,
                        "checkin_date": {"$gte": now_utc() - timedelta(days=7)},
                        "$or": [
                            {"agency_id": str((r.get("_id") or {}).get("agency_id") or ""), "hotel_id": str((r.get("_id") or {}).get("hotel_id") or "")}  # type: ignore
                            for r in filtered
                        ],
                    }
                },
                {
                    "$group": {
                        "_id": {"agency_id": "$agency_id", "hotel_id": "$hotel_id"},
                        "total": {"$sum": 1},
                        "no_show_count": {
                            "$sum": {"$cond": [{"$eq": ["$final_outcome", "no_show"]}, 1, 0]},
                        },
                    }
                },
            ]
        )
        outcomes_rows = await outcomes_cursor.to_list(length=None)
        for orow in outcomes_rows:
            kk = orow.get("_id") or {}
            aid = str(kk.get("agency_id") or "")
            hid = str(kk.get("hotel_id") or "")
            if not aid or not hid:
                continue
            key_id = f"{aid}__{hid}"
            total = int(orow.get("total") or 0)
            no_show_count = int(orow.get("no_show_count") or 0)
            rate = float(no_show_count) / total if total > 0 else 0.0
            no_show_rate_by_match[key_id] = rate
            repeat_no_show_7_by_match[key_id] = no_show_count


            hotel_ids.append(h_id)

    agency_name_map, hotel_name_map = await _resolve_names(db, org_id, list(set(agency_ids)), list(set(hotel_ids)))
    # Repeat not-arrived 7d aggregation (behavioral vs operational)
    repeat_behavioral: dict[str, int] = {}
    repeat_operational: dict[str, int] = {}
    if filtered:
        from app.utils import now_utc as _now_utc

        now = _now_utc()
        seven_days_ago = now - timedelta(days=7)
        pair_or_filters: list[dict[str, Any]] = []
        for r in filtered:
            key = r.get("_id") or {}
            a_id = str(key.get("agency_id") or "")
            h_id = str(key.get("hotel_id") or "")
            if a_id and h_id:
                pair_or_filters.append({"agency_id": a_id, "hotel_id": h_id})
        if pair_or_filters:
            match_stage: dict[str, Any] = {
                "organization_id": org_id,
                "status": "cancelled",  # treat cancelled as not_arrived proxy
                "created_at": {"$gte": seven_days_ago},
                "$or": pair_or_filters,
            }
            repeat_pipeline = [
                {"$match": match_stage},
                {
                    "$group": {
                        "_id": {"agency_id": "$agency_id", "hotel_id": "$hotel_id"},
                        "behavioral": {
                            "$sum": {
                                "$cond": [
                                    {
                                        "$and": [
                                            {"$eq": ["$status", "cancelled"]},
                                            {
                                                "$not": [
                                                    {
                                                        "$or": [
                                                            {"$in": ["$cancel_reason", ["PRICE_CHANGED", "RATE_CHANGED"]]},
                                                            {"$eq": ["$cancelled_by", "system"]},
                                                        ]
                                                    }
                                                ]
                                            },
                                        ]
                                    },
                                    1,
                                    0,
                                ]
                            }
                        },
                        "operational": {
                            "$sum": {
                                "$cond": [
                                    {
                                        "$and": [
                                            {"$eq": ["$status", "cancelled"]},
                                            {
                                                "$or": [
                                                    {"$in": ["$cancel_reason", ["PRICE_CHANGED", "RATE_CHANGED"]]},
                                                    {"$eq": ["$cancelled_by", "system"]},
                                                ]
                                            },
                                        ]
                                    },
                                    1,
                                    0,
                                ]
                            }
                        },
                    }
                },
            ]
            repeat_rows = await db.bookings.aggregate(repeat_pipeline).to_list(length=None)
            for rr in repeat_rows:
                kk = rr.get("_id") or {}
                ra = str(kk.get("agency_id") or "")
                rh = str(kk.get("hotel_id") or "")
                if ra and rh:
                    key_id = f"{ra}__{rh}"
                    repeat_behavioral[key_id] = int(rr.get("behavioral") or 0)
                    repeat_operational[key_id] = int(rr.get("operational") or 0)



    # Optional: load actions when requested to avoid extra cost by default
    actions_by_match_id: dict[str, dict[str, Any]] = {}
    if include_action and filtered:
        match_ids = []
        for r in filtered:
            key = r.get("_id") or {}
            a_id = str(key.get("agency_id") or "")
            h_id = str(key.get("hotel_id") or "")
            if a_id and h_id:
                match_ids.append(f"{a_id}__{h_id}")
        if match_ids:
            cursor = db.match_actions.find({"organization_id": org_id, "match_id": {"$in": match_ids}})
            docs = await cursor.to_list(length=None)
            for d in docs:
                mid = d.get("match_id")
                if not mid:
                    continue
                actions_by_match_id[mid] = d

    # Load unified risk profile (defaults if doc is missing)
    risk_profile_obj = await load_risk_profile(db, org_id)
    risk_profile_dict = risk_profile_obj.to_dict()

    items: list[MatchSummaryItem] = []
    for r in filtered:
        key = r.get("_id") or {}
        agency_id = str(key.get("agency_id") or "")
        hotel_id = str(key.get("hotel_id") or "")
        if not agency_id or not hotel_id:
            continue
        total = int(r.get("total") or 0)
        pending = int(r.get("pending") or 0)
        confirmed = int(r.get("confirmed") or 0)
        cancelled = int(r.get("cancelled") or 0)
        operational_cancelled = int(r.get("operational_cancelled") or 0)
        behavioral_cancelled = max(cancelled - operational_cancelled, 0)

        confirm_rate = float(confirmed) / total if total > 0 else 0.0
        operational_cancel_rate = float(operational_cancelled) / total if total > 0 else 0.0
        behavioral_cancel_rate = float(behavioral_cancelled) / total if total > 0 else 0.0

        last_ts = r.get("last_booking_at")
        last_iso = last_ts.isoformat() if hasattr(last_ts, "isoformat") else None

        match_id = f"{agency_id}__{hotel_id}"
        action_doc = actions_by_match_id.get(match_id) if include_action else None
        action_status = None
        action_reason_code = None
        action_updated_at = None
        action_updated_by_email = None
        if action_doc:
            action_status = action_doc.get("status") or "none"
            action_reason_code = action_doc.get("reason_code")
            ua = action_doc.get("updated_at")
            if hasattr(ua, "isoformat"):
                ua = ua.isoformat()
            action_updated_at = ua
            action_updated_by_email = action_doc.get("updated_by_email")

        repeat_7_behavioral = repeat_behavioral.get(match_id, 0)
        repeat_7_operational = repeat_operational.get(match_id, 0)

        # v1.5: use no-show metrics from booking_outcomes when available
        no_show_rate = float(no_show_rate_by_match.get(match_id, 0.0))
        repeat_no_show_7 = int(repeat_no_show_7_by_match.get(match_id, 0))

        # Unified high-risk decision + reasons based on no-show
        high_risk = is_high_risk(no_show_rate, repeat_no_show_7, risk_profile_obj)
        reasons: list[str] = []
        if include_reasons:
            if no_show_rate >= (risk_profile_obj.no_show_rate_threshold or risk_profile_obj.rate_threshold):
                reasons.append("rate")
            if repeat_no_show_7 >= (risk_profile_obj.repeat_no_show_threshold_7 or risk_profile_obj.repeat_threshold_7):
                reasons.append("repeat")

        risk_inputs = {
            "rate_source": "no_show",
            "repeat_source": "no_show",
        }

        items.append(
            MatchSummaryItem(
                id=match_id,
                agency_id=agency_id,
                agency_name=agency_name_map.get(agency_id),
                hotel_id=hotel_id,
                hotel_name=hotel_name_map.get(hotel_id),
                total_bookings=total,
                pending=pending,
                confirmed=confirmed,
                cancelled=cancelled,
                confirm_rate=round(confirm_rate, 3),
                # cancel_rate is defined as behavioral_cancel_rate for backward compatibility
                cancel_rate=round(behavioral_cancel_rate, 3),
                operational_cancel_rate=round(operational_cancel_rate, 3),
                behavioral_cancel_rate=round(behavioral_cancel_rate, 3),
                last_booking_at=last_iso,
                no_show_rate=round(no_show_rate, 3),
                repeat_no_show_7=repeat_no_show_7,
                repeat_not_arrived_7=repeat_7_behavioral,
                repeat_cancelled_operational_7=repeat_7_operational,
                high_risk=high_risk,
                high_risk_reasons=reasons,
                risk_inputs=risk_inputs,
                action_status=action_status,
                action_reason_code=action_reason_code,
                action_updated_at=action_updated_at,
                action_updated_by_email=action_updated_by_email,
            )
        )

    # Optional filter: only high risk
    if only_high_risk:
        items = [it for it in items if it.high_risk]

    # Sorting
    def sort_key_high_first(it: MatchSummaryItem):
        return (
            0 if it.high_risk else 1,
            -it.repeat_not_arrived_7,
            -it.cancel_rate,
            -it.total_bookings,
        )

    def sort_key_repeat_desc(it: MatchSummaryItem):
        return (-it.repeat_not_arrived_7, -it.cancel_rate)

    def sort_key_rate_desc(it: MatchSummaryItem):
        return (-it.cancel_rate, -it.repeat_not_arrived_7)

    def sort_key_total_desc(it: MatchSummaryItem):
        return (-it.total_bookings,)

    def sort_key_last_booking_desc(it: MatchSummaryItem):
        # None sonlarda kalsın
        return (0 if it.last_booking_at else 1, it.last_booking_at or "")

    if sort == "repeat_desc":
        items.sort(key=sort_key_repeat_desc)
    elif sort == "rate_desc":
        items.sort(key=sort_key_rate_desc)
    elif sort == "total_desc":
        items.sort(key=sort_key_total_desc)
    elif sort == "last_booking_desc":
        items.sort(key=sort_key_last_booking_desc, reverse=True)
    else:
        # default: high_risk_first
        items.sort(key=sort_key_high_first)

    return {
        "range": {"from": cutoff.isoformat(), "to": now_utc().isoformat(), "days": days},
        "risk_profile": risk_profile_dict,
        "items": items,
    }


def _parse_match_id(match_id: str) -> tuple[str, str]:
    try:
        agency_id, hotel_id = match_id.split("__", 1)
    except ValueError:
        raise HTTPException(status_code=400, detail="INVALID_MATCH_ID")
    if not agency_id or not hotel_id:
        raise HTTPException(status_code=400, detail="INVALID_MATCH_ID")
    return agency_id, hotel_id


@router.get("/{match_id}", response_model=MatchDetailOut, dependencies=[Depends(require_roles(["super_admin", "admin"]))])
async def get_match_detail(
    match_id: str,
    days: int = Query(90, ge=1, le=365),
    limit: int = Query(50, ge=1, le=200),
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    """Detailed view for a given agency–hotel pair.

    Returns:
    - metrics (counts, rates, avg approval hours)
    - latest bookings (normalized BookingPublicView list)
    """
    org_id = user.get("organization_id")
    agency_id, hotel_id = _parse_match_id(match_id)
    cutoff = now_utc() - timedelta(days=days)

    # ownership: ensure agency & hotel belong to this org
    agency = await db.agencies.find_one({"organization_id": org_id, "_id": agency_id})
    hotel = await db.hotels.find_one({"organization_id": org_id, "_id": hotel_id})
    if not agency or not hotel:
        raise HTTPException(status_code=404, detail="MATCH_NOT_FOUND")

    # aggregate metrics
    pipeline = [
        {
            "$match": {
                "organization_id": org_id,
                "agency_id": agency_id,
                "hotel_id": hotel_id,
                "created_at": {"$gte": cutoff},
            }
        },
        {
            "$group": {
                "_id": None,
                "total": {"$sum": 1},
                "pending": {"$sum": {"$cond": [{"$eq": ["$status", "pending"]}, 1, 0]}},
                "confirmed": {"$sum": {"$cond": [{"$eq": ["$status", "confirmed"]}, 1, 0]}},
                "cancelled": {"$sum": {"$cond": [{"$eq": ["$status", "cancelled"]}, 1, 0]}},
            }
        },
    ]
    agg = await db.bookings.aggregate(pipeline).to_list(length=1)
    if agg:
        row = agg[0]
        total = int(row.get("total") or 0)
        pending = int(row.get("pending") or 0)
        confirmed = int(row.get("confirmed") or 0)
        cancelled = int(row.get("cancelled") or 0)
    else:
        total = pending = confirmed = cancelled = 0

    # avg approval hours (confirmed only)
    approval_pipeline = [
        {
            "$match": {
                "organization_id": org_id,
                "agency_id": agency_id,
                "hotel_id": hotel_id,
                "status": "confirmed",
                "created_at": {"$gte": cutoff},
                "confirmed_at": {"$type": "date"},
            }
        },
        {
            "$project": {
                "approval_ms": {"$subtract": ["$confirmed_at", "$created_at"]},
            }
        },
        {
            "$group": {
                "_id": None,
                "avg_ms": {"$avg": "$approval_ms"},
            }
        },
    ]
    approval_rows = await db.bookings.aggregate(approval_pipeline).to_list(length=1)
    avg_approval_hours: Optional[float] = None
    if approval_rows:
        avg_ms = approval_rows[0].get("avg_ms")
        if avg_ms is not None:
            avg_approval_hours = float(avg_ms) / 1000.0 / 3600.0

    confirm_rate = float(confirmed) / total if total > 0 else 0.0
    cancel_rate = float(cancelled) / total if total > 0 else 0.0

    # latest bookings for drilldown
    cursor = (
        db.bookings.find(
            {
                "organization_id": org_id,
                "agency_id": agency_id,
                "hotel_id": hotel_id,
                "created_at": {"$gte": cutoff},
            }
        )
        .sort("created_at", -1)
        .limit(limit)
    )
    docs = await cursor.to_list(length=limit)
    bookings: list[BookingPublicView] = []
    for d in docs:
        bookings.append(BookingPublicView(**build_booking_public_view(d)))

    metrics = MatchMetrics(
        total_bookings=total,
        pending=pending,
        confirmed=confirmed,
        cancelled=cancelled,
        confirm_rate=round(confirm_rate, 3),
        cancel_rate=round(cancel_rate, 3),
        avg_approval_hours=None if avg_approval_hours is None else round(avg_approval_hours, 2),
    )

    return MatchDetailOut(
        id=f"{agency_id}__{hotel_id}",
        agency_id=agency_id,
        agency_name=agency.get("name"),
        hotel_id=hotel_id,
        hotel_name=hotel.get("name"),
        range={"from": cutoff.isoformat(), "to": now_utc().isoformat(), "days": days},
        metrics=metrics,
        bookings=bookings,
    )


@router.get("/{match_id}/events", response_model=MatchEventsResponse, dependencies=[Depends(require_roles(["super_admin"]))])
async def get_match_events(
    match_id: str,
    days: int = Query(7, ge=1, le=365),
    limit: int = Query(200, ge=1, le=1000),
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    """Return recent bookings for a match with behavioral/operational tagging.

    - window: last `days` days
    - items: latest bookings (created_at desc) up to `limit`
    """
    org_id = user.get("organization_id")
    agency_id, hotel_id = _parse_match_id(match_id)

    # ownership: ensure agency & hotel belong to this org (reuse detail logic)
    agency = await db.agencies.find_one({"organization_id": org_id, "_id": agency_id})
    hotel = await db.hotels.find_one({"organization_id": org_id, "_id": hotel_id})
    if not agency or not hotel:
        raise HTTPException(status_code=404, detail="MATCH_NOT_FOUND")

    now = now_utc()
    cutoff = now - timedelta(days=days)

    cursor = (
        db.bookings.find(
            {
                "organization_id": org_id,
                "agency_id": agency_id,
                "hotel_id": hotel_id,
                "created_at": {"$gte": cutoff},
            }
        )
        .sort("created_at", -1)
        .limit(limit)
    )
    docs = await cursor.to_list(length=limit)

    behavioral_count = 0
    operational_count = 0
    items: list[MatchEventItem] = []

    for d in docs:
        status = d.get("status") or "unknown"
        cancel_reason = d.get("cancel_reason")
        cancelled_by = d.get("cancelled_by")
        tag = "none"
        if status == "cancelled":
            # Use same rule as aggregation: operational if PRICE/RATE_CHANGED or cancelled_by system
            if (cancel_reason in ["PRICE_CHANGED", "RATE_CHANGED"]) or cancelled_by == "system":
                tag = "operational"
                operational_count += 1
            else:
                tag = "behavioral"
                behavioral_count += 1

        created_at = d.get("created_at")
        if hasattr(created_at, "isoformat"):
            created_str = created_at.isoformat()
        else:
            created_str = str(created_at)

        items.append(
            MatchEventItem(
                booking_id=str(d.get("_id")),
                created_at=created_str,
                status=status,
                cancel_reason=cancel_reason,
                cancel_tag=tag,
            )
        )

    summary = MatchEventsSummary(
        behavioral_cancel_count=behavioral_count,
        operational_cancel_count=operational_count,
        total_bookings_in_window=len(docs),
    )

    return MatchEventsResponse(
        ok=True,
        match_id=match_id,
        window={"days": days, "from": cutoff.isoformat(), "to": now.isoformat()},
        summary=summary,
        items=items,
    )


async def _load_match_action(db, org_id: str, match_id: str, agency_id: str, hotel_id: str) -> MatchAction:
    doc = await db.match_actions.find_one({"organization_id": org_id, "match_id": match_id})
    if not doc:
        return MatchAction(
            match_id=match_id,
            agency_id=agency_id,
            hotel_id=hotel_id,
            status="none",
            reason_code=None,
            note=None,
            updated_at=None,
            updated_by_email=None,
        )

    updated_at = doc.get("updated_at")
    if hasattr(updated_at, "isoformat"):
        updated_at = updated_at.isoformat()

    return MatchAction(
        match_id=doc.get("match_id", match_id),
        agency_id=doc.get("agency_id", agency_id),
        hotel_id=doc.get("hotel_id", hotel_id),
        status=doc.get("status", "none"),
        reason_code=doc.get("reason_code"),
        note=doc.get("note"),
        updated_at=updated_at,
        updated_by_email=doc.get("updated_by_email"),
    )


class MatchActionUpdateIn(BaseModel):
    status: str
    reason_code: Optional[str] = None
    note: Optional[str] = None


_VALID_STATUSES = {"none", "watchlist", "manual_review", "blocked"}


@router.get("/{match_id}/action", response_model=MatchActionResponse, dependencies=[Depends(require_roles(["super_admin"]))])
async def get_match_action(
    match_id: str,
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    org_id = user.get("organization_id")
    agency_id, hotel_id = _parse_match_id(match_id)

    # ensure match exists (same ownership checks as detail)
    agency = await db.agencies.find_one({"organization_id": org_id, "_id": agency_id})
    hotel = await db.hotels.find_one({"organization_id": org_id, "_id": hotel_id})
    if not agency or not hotel:
        raise HTTPException(status_code=404, detail="MATCH_NOT_FOUND")

    action = await _load_match_action(db, org_id, match_id, agency_id, hotel_id)
    return MatchActionResponse(ok=True, action=action)


@router.put("/{match_id}/action", response_model=MatchActionResponse, dependencies=[Depends(require_roles(["super_admin"]))])
async def upsert_match_action(
    match_id: str,
    payload: MatchActionUpdateIn,
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    org_id = user.get("organization_id")
    if payload.status not in _VALID_STATUSES:
        raise HTTPException(status_code=422, detail="INVALID_STATUS")

    agency_id, hotel_id = _parse_match_id(match_id)

    # ensure match exists (same ownership checks as detail)
    agency = await db.agencies.find_one({"organization_id": org_id, "_id": agency_id})
    hotel = await db.hotels.find_one({"organization_id": org_id, "_id": hotel_id})
    if not agency or not hotel:
        raise HTTPException(status_code=404, detail="MATCH_NOT_FOUND")

    # status=none => dokümanı sil ve none döndür (clean state)
    if payload.status == "none":
        await db.match_actions.delete_one({"organization_id": org_id, "match_id": match_id})
        action = await _load_match_action(db, org_id, match_id, agency_id, hotel_id)
        return MatchActionResponse(ok=True, action=action)

    now = now_utc()
    doc = {
        "organization_id": org_id,
        "match_id": match_id,
        "agency_id": agency_id,
        "hotel_id": hotel_id,
        "status": payload.status,
        "reason_code": payload.reason_code,
        "note": payload.note,
        "updated_at": now,
        "updated_by_user_id": user.get("id"),
        "updated_by_email": user.get("email"),
    }

    await db.match_actions.update_one(
        {"organization_id": org_id, "match_id": match_id},
        {"$set": doc, "$setOnInsert": {"created_at": now}},
        upsert=True,
    )

    action = await _load_match_action(db, org_id, match_id, agency_id, hotel_id)
    return MatchActionResponse(ok=True, action=action)
