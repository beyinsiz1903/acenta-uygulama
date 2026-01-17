from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import PlainTextResponse

from app.auth import get_current_user, require_feature, require_roles
from app.db import get_db
from app.services.audit import write_audit_log
from app.utils import now_utc
from app.utils_ids import build_id_filter
from app.csv_safe import to_safe_csv


router = APIRouter(prefix="/api/admin/statements", tags=["admin_statements"])

# Allow both org-wide admins and agency_admins
UserDep = Depends(require_roles(["super_admin", "admin", "agency_admin"]))
FeatureDep = Depends(require_feature("b2b_pro"))


ALLOWED_BOOKING_SOURCES = {"public", "b2b"}


def _parse_date_param(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        d = datetime.fromisoformat(value[:10])
        return datetime(d.year, d.month, d.day)
    except Exception:  # noqa: BLE001
        raise HTTPException(status_code=422, detail="INVALID_DATE")


@router.get("/", dependencies=[FeatureDep])
async def list_statements(
    request: Request,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    agency_id: Optional[str] = None,
    page: int = 1,
    limit: int = 200,
    format: str = "json",
    user=UserDep,
    db=Depends(get_db),
):
    """List financial statements for B2B PRO.

    Truth source: booking_payment_transactions, enriched with booking metadata.
    Single-query contract: JSON and CSV share the same query/pagination.
    """

    if page < 1:
        raise HTTPException(status_code=422, detail="INVALID_PAGE")
    if limit < 1 or limit > 1000:
        raise HTTPException(status_code=422, detail="INVALID_LIMIT")

    org_id = user["organization_id"]

    # Date range resolution (occurred_at)
    start = _parse_date_param(date_from)
    end = _parse_date_param(date_to)

    if not start and not end:
        end = now_utc()
        start = end - timedelta(days=7)

    if not start:
        start = (end or now_utc()) - timedelta(days=7)
    if not end:
        end = start + timedelta(days=7)

    # Normalise to full day
    start = datetime(start.year, start.month, start.day)
    end = datetime(end.year, end.month, end.day, 23, 59, 59)

    # Agency scoping
    effective_agency_id: Optional[str] = None
    roles = set(user.get("roles") or [])
    if "agency_admin" in roles:
        # Force to user's own agency_id regardless of query
        effective_agency_id = str(user.get("agency_id")) if user.get("agency_id") else None
    else:
        if agency_id:
            effective_agency_id = str(agency_id)

    flt: Dict[str, Any] = {
        "organization_id": org_id,
        "occurred_at": {"$gte": start, "$lte": end},
    }
    if effective_agency_id:
        flt.update(build_id_filter(effective_agency_id, field_name="agency_id"))

    # Total tx count before pagination (for UI)
    total = await db.booking_payment_transactions.count_documents(flt)

    cursor = (
        db.booking_payment_transactions.find(flt)
        .sort([("occurred_at", -1), ("_id", -1)])
        .skip((page - 1) * limit)
        .limit(limit)
    )
    txs = await cursor.to_list(length=limit)

    items: List[Dict[str, Any]] = []
    skipped_missing_booking_count = 0

    for tx in txs:
        # booking_id can be ObjectId or string
        raw_bid = tx.get("booking_id")
        booking_filter: Dict[str, Any] = {"organization_id": org_id}
        if isinstance(raw_bid, ObjectId):
            booking_filter["_id"] = raw_bid
        else:
            try:
                booking_filter["_id"] = ObjectId(str(raw_bid))
            except Exception:  # noqa: BLE001
                booking_filter["_id_str"] = str(raw_bid)

        booking = await db.bookings.find_one(booking_filter)
        if not booking:
            skipped_missing_booking_count += 1
            continue

        source = booking.get("source") or "public"
        if source not in ALLOWED_BOOKING_SOURCES:
            skipped_missing_booking_count += 1
            continue

        # Build statement row
        ts = tx.get("occurred_at") or tx.get("created_at") or now_utc()
        if hasattr(ts, "isoformat"):
            date_val = ts.isoformat()
        else:
            date_val = str(ts)

        guest = booking.get("guest") or {}
        amt_cents = int(tx.get("amount") or 0)
        currency = tx.get("currency") or booking.get("currency") or "TRY"

        item = {
            "date": date_val,
            "booking_id": str(booking.get("_id")),
            "booking_code": booking.get("booking_code"),
            "customer_name": guest.get("full_name"),
            "agency_id": str(booking.get("agency_id")) if booking.get("agency_id") else None,
            "amount_cents": amt_cents,
            "currency": currency,
            "payment_method": tx.get("provider") or "unknown",
            "channel": source,
        }
        items.append(item)

    returned_count = len(items)

    iso_from = start.isoformat()
    iso_to = end.isoformat()

    # Audit log (STATEMENT_VIEWED)
    try:
        await write_audit_log(
            db,
            organization_id=org_id,
            actor={
                "actor_type": "user",
                "email": user.get("email"),
                "roles": user.get("roles"),
            },
            request=request,
            action="STATEMENT_VIEWED",
            target_type="statement",
            target_id=effective_agency_id or "org",
            before=None,
            after=None,
            meta={
                "date_from": iso_from,
                "date_to": iso_to,
                "agency_id": effective_agency_id,
                "page": page,
                "limit": limit,
                "total_tx": total,
                "returned_count": returned_count,
                "skipped_missing_booking_count": skipped_missing_booking_count,
            },
        )
    except Exception:
        # Must not break main flow
        pass

    accept = request.headers.get("accept", "").lower()
    wants_csv = "text/csv" in accept or format.lower() == "csv"

    if wants_csv:
        fieldnames = [
            "date",
            "booking_id",
            "booking_code",
            "customer_name",
            "agency_id",
            "amount_cents",
            "currency",
            "payment_method",
            "channel",
        ]
        content = to_safe_csv(items, fieldnames=fieldnames)
        headers = {
            "Content-Disposition": 'attachment; filename="statements.csv"',
        }
        return PlainTextResponse(content, media_type="text/csv; charset=utf-8", headers=headers)

    return {
        "ok": True,
        "items": items,
        "page": page,
        "limit": limit,
        "total": total,
        "returned_count": returned_count,
        "skipped_missing_booking_count": skipped_missing_booking_count,
        "date_from": iso_from,
        "date_to": iso_to,
    }
