from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

from app.auth import get_current_user, require_feature, require_roles
from app.db import get_db
from app.services.audit import write_audit_log
from app.utils import now_utc
from app.utils_ids import build_id_filter
from app.csv_safe import to_safe_csv


router = APIRouter(prefix="/api/admin/settlements", tags=["admin_settlements"])

UserDep = Depends(require_roles(["super_admin", "admin", "agency_admin"]))
FeatureDep = Depends(require_feature("b2b_pro"))


DEFAULT_ALLOWED_BOOKING_SOURCES = {"public", "b2b", "b2b_portal"}


def _parse_date(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        d = datetime.fromisoformat(value[:10])
        return datetime(d.year, d.month, d.day)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=422, detail="INVALID_DATE") from exc


class SettlementItem(BaseModel):
    date: str
    tx_id: str
    booking_id: Optional[str]
    booking_code: Optional[str]
    agency_id: Optional[str]
    gross_cents: int
    agency_cut_cents: int
    platform_cut_cents: int
    currency: str
    payment_method: str
    channel: str


@router.get("", dependencies=[FeatureDep])
async def list_settlements(
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
    """List B2B settlement rows for an organization.

    Truth source: booking_payment_transactions, enriched with booking + agency.
    """

    if page < 1:
        raise HTTPException(status_code=422, detail="INVALID_PAGE")
    if limit < 1 or limit > 1000:
        raise HTTPException(status_code=422, detail="INVALID_LIMIT")

    org_id = user["organization_id"]

    # Resolve allowed booking sources from org features (same pattern as statements)
    org_doc = await db.organizations.find_one({"_id": org_id})
    features = (org_doc or {}).get("features") or {}
    allowed_sources = set(features.get("b2b_pro_allowed_booking_sources") or DEFAULT_ALLOWED_BOOKING_SOURCES)

    start = _parse_date(date_from)
    end = _parse_date(date_to)

    if not start and not end:
        end = now_utc()
        start = end - timedelta(days=7)
    if not start:
        start = (end or now_utc()) - timedelta(days=7)
    if not end:
        end = start + timedelta(days=7)

    # Normalize to day boundaries
    start = datetime(start.year, start.month, start.day)
    end = datetime(end.year, end.month, end.day, 23, 59, 59)

    roles = set(user.get("roles") or [])
    effective_agency_id: Optional[str] = None
    if "agency_admin" in roles:
        effective_agency_id = str(user.get("agency_id")) if user.get("agency_id") else None
    elif agency_id:
        effective_agency_id = str(agency_id)

    flt: Dict[str, Any] = {
        "organization_id": org_id,
        "occurred_at": {"$gte": start, "$lte": end},
    }
    if effective_agency_id:
        flt.update(build_id_filter(effective_agency_id, field_name="agency_id"))

    total = await db.booking_payment_transactions.count_documents(flt)

    cursor = (
        db.booking_payment_transactions.find(flt)
        .sort([("occurred_at", -1), ("_id", -1)])
        .skip((page - 1) * limit)
        .limit(limit)
    )
    txs = await cursor.to_list(length=limit)

    items: List[SettlementItem] = []
    skipped_missing_booking_count = 0

    for tx in txs:
        tx_id = tx.get("_id")
        tx_amount = int(tx.get("amount") or 0)
        tx_currency = (tx.get("currency") or "TRY").upper()
        tx_method = tx.get("provider") or "unknown"

        # Enrich booking
        raw_bid = tx.get("booking_id")
        booking_filter: Dict[str, Any] = {"organization_id": org_id}
        if isinstance(raw_bid, ObjectId):
            booking_filter["_id"] = raw_bid
        elif raw_bid is not None:
            try:
                booking_filter["_id"] = ObjectId(str(raw_bid))
            except Exception:
                booking_filter["_id_str"] = str(raw_bid)

        booking = await db.bookings.find_one(booking_filter)
        if not booking:
            skipped_missing_booking_count += 1
            continue

        source = booking.get("source") or "public"
        if source not in allowed_sources:
            skipped_missing_booking_count += 1
            continue

        booking_id_str = str(booking.get("_id")) if booking.get("_id") is not None else None
        booking_code = booking.get("booking_code")
        agency_id_val = booking.get("agency_id") or tx.get("agency_id")
        agency_id_str = str(agency_id_val) if agency_id_val is not None else None

        # Resolve agency commission/discount
        commission_percent = 0.0
        discount_percent = 0.0
        if agency_id_str is not None:
            agency_flt: Dict[str, Any] = {"organization_id": org_id}
            agency_flt.update(build_id_filter(agency_id_str, field_name="_id"))
            agency_doc = await db.agencies.find_one(agency_flt)
            if agency_doc:
                commission_percent = float(agency_doc.get("commission_percent") or 0.0)
                discount_percent = float(agency_doc.get("discount_percent") or 0.0)

        gross_cents = tx_amount
        discount_cents = int(round(gross_cents * discount_percent / 100.0)) if gross_cents > 0 else 0
        net_gross = max(gross_cents - discount_cents, 0)
        agency_cut_cents = int(round(net_gross * commission_percent / 100.0)) if net_gross > 0 else 0
        platform_cut_cents = net_gross - agency_cut_cents

        ts = tx.get("occurred_at") or tx.get("created_at") or now_utc()
        if hasattr(ts, "isoformat"):
            date_val = ts.isoformat()
        else:
            date_val = str(ts)

        item = SettlementItem(
            date=date_val,
            tx_id=str(tx_id),
            booking_id=booking_id_str,
            booking_code=booking_code,
            agency_id=agency_id_str,
            gross_cents=gross_cents,
            agency_cut_cents=agency_cut_cents,
            platform_cut_cents=platform_cut_cents,
            currency=tx_currency,
            payment_method=tx_method,
            channel=source,
        )
        items.append(item)

    returned_count = len(items)

    iso_from = start.isoformat()
    iso_to = end.isoformat()

    accept = request.headers.get("accept", "").lower()
    wants_csv = "text/csv" in accept or format.lower() == "csv"
    out_format = "csv" if wants_csv else "json"

    # Audit log
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
            action="SETTLEMENT_VIEWED",
            target_type="settlement",
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
                "format": out_format,
            },
        )
    except Exception:
        # Audit failures must not break main flow
        pass

    if wants_csv:
        fieldnames = [
            "date",
            "tx_id",
            "booking_id",
            "booking_code",
            "agency_id",
            "gross_cents",
            "agency_cut_cents",
            "platform_cut_cents",
            "currency",
            "payment_method",
            "channel",
        ]
        rows = [item.model_dump() for item in items]
        content = to_safe_csv(rows, fieldnames=fieldnames)
        headers = {
            "Content-Disposition": 'attachment; filename="settlements.csv"',
        }
        return PlainTextResponse(content, media_type="text/csv; charset=utf-8", headers=headers)

    return {
        "ok": True,
        "items": [item.model_dump() for item in items],
        "page": page,
        "limit": limit,
        "total": total,
        "returned_count": returned_count,
        "skipped_missing_booking_count": skipped_missing_booking_count,
        "date_from": iso_from,
        "date_to": iso_to,
    }
