from __future__ import annotations

from datetime import datetime
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
    limit: int = Query(50, ge=1, le=200),
    user: Dict[str, Any] = AgencyUserDep,
    db=Depends(get_db),
) -> BookingListResponse:
    """List B2B bookings for the current agency user.

    - Scope: current organization_id + agency_id
    - Default sort: created_at desc (newest first)
    - Default limit: 50, min=1, max=200
    - Status filter supports both single and repeated query params.
    """

    org_id = user.get("organization_id")
    agency_id = user.get("agency_id")
    if not org_id or not agency_id:
        raise AppError(403, "forbidden", "Only agency users can list B2B bookings")

    query: Dict[str, Any] = {
        "organization_id": org_id,
        "agency_id": ObjectId(str(agency_id)),
        # B2B bookings always have quote_id set
        "quote_id": {"$exists": True},
    }

    if status:
        normalized = [s.upper() for s in status if s]
        if normalized:
            if len(normalized) == 1:
                query["status"] = normalized[0]
            else:
                query["status"] = {"$in": normalized}

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

        # Product name: Phase 1 placeholder "-" (we don't join products here)
        product_name: Optional[str] = "-"

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
