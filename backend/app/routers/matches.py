from __future__ import annotations

from datetime import timedelta
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.auth import get_current_user, require_roles
from app.db import get_db
from app.schemas import BookingPublicView
from app.utils import now_utc, build_booking_public_view

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
    cancel_rate: float
    last_booking_at: Optional[str] = None
    repeat_not_arrived_7: int = 0

    # Optional action fields (only populated when include_action=1)
    action_status: Optional[str] = None
    action_reason_code: Optional[str] = None
    action_updated_at: Optional[str] = None
    action_updated_by_email: Optional[str] = None


class MatchSummaryResponse(BaseModel):
    range: dict[str, Any]
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

    agency_name_map, hotel_name_map = await _resolve_names(db, org_id, list(set(agency_ids)), list(set(hotel_ids)))
    # Repeat not-arrived 7d aggregation
    repeat_counts: dict[str, int] = {}
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
                        "c": {"$sum": 1},
                    }
                },
            ]
            repeat_rows = await db.bookings.aggregate(repeat_pipeline).to_list(length=None)
            for rr in repeat_rows:
                kk = rr.get("_id") or {}
                ra = str(kk.get("agency_id") or "")
                rh = str(kk.get("hotel_id") or "")
                if ra and rh:
                    repeat_counts[f"{ra}__{rh}"] = int(rr.get("c") or 0)



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
        confirm_rate = float(confirmed) / total if total > 0 else 0.0
        cancel_rate = float(cancelled) / total if total > 0 else 0.0
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
                cancel_rate=round(cancel_rate, 3),
                last_booking_at=last_iso,
                action_status=action_status,
                action_reason_code=action_reason_code,
                action_updated_at=action_updated_at,
                action_updated_by_email=action_updated_by_email,
            )
        )

    return {
        "range": {"from": cutoff.isoformat(), "to": now_utc().isoformat(), "days": days},
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
