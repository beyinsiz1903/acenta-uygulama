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


async def _get_scoped_booking(db, booking_id: str, org_id: str, agency_id: str) -> Dict[str, Any]:
    """Load booking and enforce B2B ownership.

    Returns booking doc or raises AppError 404 if not found or out of scope.
    """
    try:
        oid = ObjectId(booking_id)
    except Exception:
        raise AppError(404, "booking_not_found", "Booking not found", {"booking_id": booking_id})

    booking = await db.bookings.find_one({"_id": oid})
    if not booking:
        raise AppError(404, "booking_not_found", "Booking not found", {"booking_id": booking_id})

    if str(booking.get("organization_id")) != str(org_id) or str(booking.get("agency_id")) != str(agency_id):
        # Scope mismatch: hide existence behind 404
        raise AppError(404, "booking_not_found", "Booking not found", {"booking_id": booking_id})

    return booking


@router.get("/bookings/{booking_id}")
async def get_b2b_booking_detail(
    booking_id: str,
    user: Dict[str, Any] = AgencyUserDep,
    db=Depends(get_db),
) -> Dict[str, Any]:
    """Return minimal booking detail for B2B portal.

    Scope: current organization_id + agency_id; scope mismatch -> 404.
    """
    org_id = user.get("organization_id")
    agency_id = user.get("agency_id")
    if not org_id or not agency_id:
        raise AppError(403, "forbidden", "Only agency users can view B2B booking details")

    booking = await _get_scoped_booking(db, booking_id, org_id, agency_id)

    amounts = booking.get("amounts") or {}
    items_doc = booking.get("items") or []
    first_item: Dict[str, Any] = items_doc[0] if items_doc else {}

    customer = booking.get("customer") or {}
    guest = {
        "name": customer.get("name"),
        "email": customer.get("email"),
        "phone": customer.get("phone"),
    }

    product_name = first_item.get("product_name")
    if not product_name:
        pid = first_item.get("product_id")
        product_name = str(pid) if pid else "B2B Booking"

    product = {
        "name": product_name,
        "type": first_item.get("type"),
    }

    dates = {
        "check_in": first_item.get("check_in"),
        "check_out": first_item.get("check_out"),
    }

    amount = {
        "total": amounts.get("sell"),
        "currency": booking.get("currency"),
    }

    return {
        "booking_id": str(booking.get("_id")),
        "created_at": booking.get("created_at"),
        "status": booking.get("status"),
        "payment_status": booking.get("payment_status"),
        "guest": guest,
        "product": product,
        "dates": dates,
        "amount": amount,
        "agency_id": str(booking.get("agency_id")),
        "organization_id": str(booking.get("organization_id")),
    }


@router.get("/bookings/{booking_id}/cases")
async def list_b2b_booking_cases(
    booking_id: str,
    user: Dict[str, Any] = AgencyUserDep,
    db=Depends(get_db),
) -> Dict[str, Any]:
    """List ops_cases attached to a B2B booking for current agency user."""
    org_id = user.get("organization_id")
    agency_id = user.get("agency_id")
    if not org_id or not agency_id:
        raise AppError(403, "forbidden", "Only agency users can view B2B booking cases")

    # Enforce booking ownership (404 on mismatch)
    await _get_scoped_booking(db, booking_id, org_id, agency_id)

    from app.services.ops_cases import list_cases

    res = await list_cases(
        db,
        organization_id=str(org_id),
        booking_id=booking_id,
        page=1,
        page_size=50,
    )

    items: List[Dict[str, Any]] = []
    for c in res.get("items", []):
        items.append(
            {
                "case_id": c.get("case_id"),
                "type": c.get("type"),
                "status": c.get("status"),
                "waiting_on": c.get("waiting_on"),
                "title": c.get("title"),
                "note": c.get("note"),
                "source": c.get("source"),
                "created_at": c.get("created_at"),
                "updated_at": c.get("updated_at"),
            }
        )

    return {"items": items}


from pydantic import BaseModel
from fastapi import BackgroundTasks
from app.services.crm_events import log_crm_event


class B2BCaseCreateBody(BaseModel):
    type: str
    note: Optional[str] = None


@router.post("/bookings/{booking_id}/cases", status_code=201)
async def create_b2b_booking_case(
    booking_id: str,
    payload: B2BCaseCreateBody,
    background: BackgroundTasks,
    user: Dict[str, Any] = AgencyUserDep,
    db=Depends(get_db),
) -> Dict[str, Any]:
    """Create a new ops_case for a B2B booking with source=b2b_portal.

    - Scope: current organization_id + agency_id (404 on mismatch)
    - source is hard-coded server-side to "b2b_portal" regardless of client body.
    """
    org_id = user.get("organization_id")
    agency_id = user.get("agency_id")
    if not org_id or not agency_id:
        raise AppError(403, "forbidden", "Only agency users can create B2B cases")

    # Ensure booking belongs to this agency/org
    booking = await _get_scoped_booking(db, booking_id, org_id, agency_id)

    booking_code = booking.get("booking_code") or booking.get("code")

    from app.services.ops_cases import create_case

    actor = {
        "user_id": str(user.get("id") or user.get("_id")),
        "email": user.get("email"),
        "roles": user.get("roles") or [],
    }

    case_doc = await create_case(
        db,
        organization_id=str(org_id),
        booking_id=booking_id,
        type=payload.type,
        source="b2b_portal",  # server-side hard override
        status="open",
        waiting_on=None,
        note=payload.note,
        booking_code=booking_code,
        agency_id=str(agency_id),
        created_by=actor,
    )

    # Best-effort CRM event in background
    async def _log_event():
        try:
            await log_crm_event(
                db,
                str(org_id),
                entity_type="booking_case",
                entity_id=case_doc.get("case_id"),
                action="b2b.case.created",
                payload={
                    "booking_id": booking_id,
                    "type": payload.type,
                    "source": "b2b_portal",
                    "agency_id": str(agency_id),
                },
                actor=actor,
                source="b2b_portal",
            )
        except Exception:
            pass

    background.add_task(_log_event)

    return case_doc

