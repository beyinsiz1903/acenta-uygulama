from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import PlainTextResponse

from app.auth import get_current_user, require_feature, require_roles
from app.db import get_db
from app.services.audit import write_audit_log


router = APIRouter(prefix="/api/admin/accounting", tags=["admin_accounting"])

AdminDep = Depends(require_roles(["super_admin", "admin"]))
FeatureDep = Depends(require_feature("accounting_export"))


def _parse_date_param(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        # Interpret as UTC date (YYYY-MM-DD)
        d = datetime.fromisoformat(value[:10])
        return datetime(d.year, d.month, d.day)
    except Exception:
        raise HTTPException(status_code=422, detail="INVALID_DATE")


def _pick_tx_timestamp(tx: Dict[str, Any]) -> datetime:
    """Choose which timestamp to use for reporting.

    Preference order:
    1) occurred_at (business event time)
    2) created_at (system insert time)
    """

    if tx.get("occurred_at"):
        return tx["occurred_at"]
    if tx.get("created_at"):
        return tx["created_at"]
    return datetime.utcnow()


@router.get("/transactions", dependencies=[AdminDep, FeatureDep])
async def list_accounting_transactions(
    request: Request,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    format: str = "json",
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    """List accounting transactions for B2C/public bookings.

    Truth source: booking_payment_transactions, enriched with booking metadata.
    """

    org_id = user["organization_id"]

    start = _parse_date_param(date_from)
    end = _parse_date_param(date_to)

    if not start and not end:
        # Default to last 7 days
        end = datetime.utcnow()
        start = end - timedelta(days=7)

    if not start:
        # If only end provided, set start to 7 days before end
        start = (end or datetime.utcnow()) - timedelta(days=7)
    if not end:
        # If only start provided, set end to start + 7 days
        end = start + timedelta(days=7)

    # Normalise to full-day boundaries
    start = datetime(start.year, start.month, start.day)
    end = datetime(end.year, end.month, end.day, 23, 59, 59)

    flt: Dict[str, Any] = {
        "organization_id": org_id,
        "occurred_at": {"$gte": start, "$lte": end},
    }

    cursor = db.booking_payment_transactions.find(flt).sort("occurred_at", 1)
    txs = await cursor.to_list(length=5000)

    items: List[Dict[str, Any]] = []

    for tx in txs:
        # booking_id can be either ObjectId or string; handle both.
        raw_bid = tx.get("booking_id")
        booking_filter: Dict[str, Any] = {"organization_id": org_id}
        if isinstance(raw_bid, ObjectId):
            booking_filter["_id"] = raw_bid
        else:
            # Try ObjectId first, then fall back to string _id
            try:
                booking_filter["_id"] = ObjectId(str(raw_bid))
            except Exception:
                booking_filter["_id_str"] = str(raw_bid)

        booking = await db.bookings.find_one(booking_filter)
        if not booking:
            # Some historical tx may not have a booking; skip for V1
            continue

        # Only include B2C/public bookings
        if (booking.get("source") or "public") != "public":
            continue

        ts = _pick_tx_timestamp(tx)
        amounts = booking.get("amounts") or {}
        guest = booking.get("guest") or {}

        item = {
            "date": ts.isoformat(),
            "booking_id": str(booking.get("_id")),
            "booking_code": booking.get("booking_code"),
            "customer_name": guest.get("full_name"),
            "product_type": booking.get("product_type") or "hotel",
            # For V1 we treat tx.amount as gross+net; VAT breakdown can be added later.
            "amount_gross_cents": int(tx.get("amount") or 0),
            "amount_net_cents": int(tx.get("amount") or 0),
            "vat_cents": 0,
            "currency": tx.get("currency") or booking.get("currency") or "TRY",
            "payment_method": tx.get("provider") or "unknown",
            "installments": booking.get("installments"),
            "channel": booking.get("source") or "public",
        }
        items.append(item)

    iso_from = start.isoformat()
    iso_to = end.isoformat()

    # Audit log for export view
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
            action="ACCOUNTING_EXPORT_VIEW",
            target_type="accounting_export",
            target_id="transactions",
            before=None,
            after=None,
            meta={
                "date_from": iso_from,
                "date_to": iso_to,
                "returned_count": len(items),
            },
        )
    except Exception:
        # Export must not fail due to audit issues
        pass

    # Determine final format (Accept header has priority over query param)
    accept = request.headers.get("accept", "").lower()
    wants_csv = "text/csv" in accept or format.lower() == "csv"

    if wants_csv:
        # Simple CSV: header + rows
        headers = [
            "date",
            "booking_id",
            "booking_code",
            "customer_name",
            "product_type",
            "amount_gross_cents",
            "amount_net_cents",
            "vat_cents",
            "currency",
            "payment_method",
            "installments",
            "channel",
        ]

        lines = [",".join(headers)]
        for it in items:
            row = [
                str(it.get("date") or ""),
                str(it.get("booking_id") or ""),
                str(it.get("booking_code") or ""),
                str(it.get("customer_name") or ""),
                str(it.get("product_type") or ""),
                str(it.get("amount_gross_cents") or 0),
                str(it.get("amount_net_cents") or 0),
                str(it.get("vat_cents") or 0),
                str(it.get("currency") or ""),
                str(it.get("payment_method") or ""),
                str(it.get("installments") or ""),
                str(it.get("channel") or ""),
            ]
            lines.append(",".join(row))

        content = "\n".join(lines)
        return PlainTextResponse(content, media_type="text/csv")

    return {"items": items, "date_from": iso_from, "date_to": iso_to}
