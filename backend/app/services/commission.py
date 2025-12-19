from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from app.utils import now_utc


def month_from_check_in(check_in: str) -> str:
    # check_in is YYYY-MM-DD
    return (check_in or "")[:7]


def compute_commission(
    gross_total: float,
    commission_type: Optional[str],
    commission_value: Optional[float],
) -> tuple[str, float]:
    """Returns normalized commission_type and computed commission_amount."""
    ctype = (commission_type or "percent").strip()
    cval = float(commission_value or 0)

    if ctype == "percent":
        amount = round(float(gross_total) * (cval / 100.0), 2)
        return "percent", amount

    if ctype in {"fixed", "fixed_per_booking"}:
        amount = round(cval, 2)
        return "fixed_per_booking", amount

    # unknown => 0
    return ctype, 0.0


async def create_financial_entry(
    db,
    *,
    organization_id: str,
    booking_id: str,
    agency_id: str,
    hotel_id: str,
    entry_type: str,
    month: str,
    currency: str,
    gross_amount: float,
    commission_amount: float,
    net_amount: float,
    source_status: str,
    created_at: Optional[datetime] = None,
    settlement_status: str = "open",
) -> dict[str, Any]:
    now = created_at or now_utc()
    doc = {
        "_id": str(uuid.uuid4()),
        "organization_id": organization_id,
        "booking_id": booking_id,
        "agency_id": agency_id,
        "hotel_id": hotel_id,
        "type": entry_type,  # booking|reversal
        "month": month,
        "currency": currency,
        "gross_amount": round(float(gross_amount), 2),
        "commission_amount": round(float(commission_amount), 2),
        "net_amount": round(float(net_amount), 2),
        "source_status": source_status,
        "settlement_status": settlement_status,
        "created_at": now,
        "updated_at": now,
    }
    await db.booking_financial_entries.insert_one(doc)
    return doc
