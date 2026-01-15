from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, Query

from app.auth import get_current_user, require_roles
from app.db import get_db
from app.errors import AppError
from app.schemas_b2b_bookings import BookingListItem, BookingListResponse

router = APIRouter(prefix="/api/b2b", tags=["b2b-bookings-list"])


AgencyUserDep = Depends(require_roles(["agency_agent", "agency_admin"]))


@router.get("/bookings", response_model=BookingListResponse)
async def list_b2b_bookings_agency(
    status: Optional[List[str]] = Query(
        default=None,
        description="Repeatable booking status filter, e.g. status=CONFIRMED&status=VOUCHERED",
    ),
    from_: Optional[datetime] = Query(
        default=None,
        alias="from",
        description="Created_at >= from (ISO datetime)",
    ),
    to: Optional[datetime] = Query(
        default=None,
        alias="to",
        description="Created_at <= to (ISO datetime)",
    ),
    q: Optional[str] = Query(
        default=None,
        description="Search by booking id / guest name / product name",
    ),
    limit: int = Query(20, ge=1, le=100),
    user: Dict[str, Any] = AgencyUserDep,
    db=Depends(get_db),
) -> BookingListResponse:
    """List B2B bookings for the current agency user.

    - Scope: current organization_id + agency_id
    - Default sort: created_at desc (newest first)
    - Default limit: 20, min=1, max=100
    - Status filter supports both single and repeated query params.
    - Date range filter: defaults to last 30 days when not provided.
    - q filter: best-effort search on booking id / guest name / product name.
    """

    org_id = user.get("organization_id")
    agency_id = user.get("agency_id")
    if not org_id or not agency_id:
        raise AppError(403, "forbidden", "Only agency users can list B2B bookings")

    query: Dict[str, Any] = {
        "organization_id": org_id,
        "agency_id": agency_id,
        # B2B bookings always have quote_id set
        "quote_id": {"$exists": True},
    }

    # Date range: default last 30 days if not provided
    if not from_ and not to:
        to = datetime.utcnow()
        from_ = to - timedelta(days=30)

    if from_ or to:
        created_range: Dict[str, Any] = {}
        if from_:
            created_range["$gte"] = from_
        if to:
            created_range["$lte"] = to
        query["created_at"] = created_range

    if status:
        normalized = [s.upper() for s in status if s]
        if normalized:
            if len(normalized) == 1:
                query["status"] = normalized[0]
            else:
                query["status"] = {"$in": normalized}

    # Text search (best-effort) on id / customer.name / items[0].product_name
    if q:
        # We'll apply this filter in Python after fetching up to `limit` records,
        # because the existing schema does not have a dedicated text index.
        pass

    cursor = (
        db.bookings.find(query)
        .sort("created_at", -1)
        .limit(limit)
    )
    docs: List[Dict[str, Any]] = await cursor.to_list(length=limit)

    items: List[BookingListItem] = []
    for doc in docs:
        amounts = doc.get("amounts") or {}
        items_doc = doc.get("items") or []
        first_item: Dict[str, Any] = items_doc[0] if items_doc else {}

        # Dates: stored as strings (YYYY-MM-DD) in items
        check_in = first_item.get("check_in")
        check_out = first_item.get("check_out")

        # Primary guest name: prefer customer.name, fallback to first traveller
        customer = doc.get("customer") or {}
        primary_guest_name: Optional[str] = customer.get("name")
        if not primary_guest_name:
            travellers = doc.get("travellers") or []
            if travellers:
                t0 = travellers[0] or {}
                fn = (t0.get("first_name") or "").strip()
                ln = (t0.get("last_name") or "").strip()
                full = f"{fn} {ln}".strip()
                primary_guest_name = full or None

        # Product name: best-effort
        # 1) items[0].product_name
        # 2) items[0].product_id
        # 3) fallback label
        product_name: Optional[str] = first_item.get("product_name")
        if not product_name:
            pid = first_item.get("product_id")
            if pid:
                product_name = str(pid)
            else:
                product_name = "B2B Booking"

        # In-memory q filter (best-effort)
        if q:
            haystack = " ".join(
                [
                    str(doc.get("_id") or ""),
                    primary_guest_name or "",
                    product_name or "",
                ]
            ).lower()
            if q.lower() not in haystack:
                continue

        items.append(
            BookingListItem(
                booking_id=str(doc.get("_id")),
                status=str(doc.get("status") or ""),
                created_at=doc.get("created_at") or datetime.utcnow(),
                currency=doc.get("currency"),
                amount_sell=(amounts or {}).get("sell"),
                check_in=check_in,
                check_out=check_out,
                primary_guest_name=primary_guest_name,
                product_name=product_name,
            )
        )

    return BookingListResponse(items=items)
