from __future__ import annotations

"""Public booking summary API for /book/complete.

Provides a PII-minimal booking snapshot by booking_code + org, suitable for
showing a confirmation summary on the public funnel.
"""

from datetime import datetime
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse

from app.db import get_db
from app.utils import serialize_doc

router = APIRouter(prefix="/api/public/bookings", tags=["public-bookings"])


def _build_public_booking_summary(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Build a PII-minimal booking summary payload."""

    amounts = doc.get("amounts") or {}
    sell = float(amounts.get("sell", 0.0) or 0.0)
    currency = (doc.get("currency") or "EUR").upper()

    public_quote = doc.get("public_quote") or {}

    pax = public_quote.get("pax") or {}
    nights = public_quote.get("nights")

    summary: Dict[str, Any] = {
        "booking_code": doc.get("booking_code") or doc.get("code"),
        "status": doc.get("status") or "PENDING_PAYMENT",
        "date_from": public_quote.get("date_from"),
        "date_to": public_quote.get("date_to"),
        "nights": nights,
        "pax": {
            "adults": pax.get("adults"),
            "children": pax.get("children"),
            "rooms": pax.get("rooms"),
        },
        "product": {
            "title": doc.get("product_title") or "Rezervasyonunuz",
            "type": doc.get("product_type") or "hotel",
        },
        "price": {
            "amount_cents": int(round(sell * 100)),
            "currency": currency,
        },
        "created_at": doc.get("created_at"),
    }
    return summary


@router.get("/by-code/{booking_code}")
async def get_public_booking_by_code(
    booking_code: str,
    org: str = Query(..., min_length=1, description="Organization id (tenant)"),
    db=Depends(get_db),
) -> JSONResponse:
    """Return a PII-minimal booking summary for public confirmation.

    Security:
    - Scoped by organization_id AND booking_code (short code)
    - Does not return guest PII fields (email, phone, full_name)
    """

    criteria = {"organization_id": org, "booking_code": booking_code}
    booking = await db.bookings.find_one(criteria)
    if not booking:
        # enumeration-safe generic 404
        raise HTTPException(status_code=404, detail="NOT_FOUND")

    summary = _build_public_booking_summary(booking)
    payload = {"ok": True, "booking": serialize_doc(summary)}
    return JSONResponse(status_code=200, content=payload)
