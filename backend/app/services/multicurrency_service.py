"""Multi-currency reconciliation service.

Supports EUR, USD, GBP, TRY with automatic exchange rate calculation.
Provides reconciliation reports and currency conversion.
"""
from __future__ import annotations

import logging
import uuid
from typing import Any

from app.db import get_db
from app.utils import now_utc
from app.constants.currencies import (
    DEFAULT_EXCHANGE_RATES,
    convert_amount,
    CURRENCY_SYMBOLS,
)

logger = logging.getLogger("multicurrency")


async def get_current_rates(organization_id: str) -> dict[str, float]:
    """Get current exchange rates. Falls back to defaults if no custom rates."""
    db = await get_db()
    custom = await db.fx_rates.find(
        {"organization_id": organization_id}
    ).sort("updated_at", -1).to_list(50)

    rates = dict(DEFAULT_EXCHANGE_RATES)
    for r in custom:
        key = f"{r.get('base')}_{r.get('quote')}"
        if r.get("rate"):
            rates[key] = float(r["rate"])

    return rates


async def convert_booking_amount(
    organization_id: str,
    amount: float,
    from_currency: str,
    to_currency: str,
) -> dict[str, Any]:
    """Convert a booking amount with tracked rate snapshot."""
    if from_currency == to_currency:
        return {
            "original_amount": amount,
            "converted_amount": amount,
            "from_currency": from_currency,
            "to_currency": to_currency,
            "rate": 1.0,
            "converted_at": now_utc(),
        }

    rates = await get_current_rates(organization_id)
    converted = convert_amount(amount, from_currency, to_currency, rates)
    rate_key = f"{from_currency}_{to_currency}"
    rate = rates.get(rate_key, 0)

    return {
        "original_amount": amount,
        "converted_amount": converted,
        "from_currency": from_currency,
        "to_currency": to_currency,
        "rate": rate,
        "converted_at": now_utc(),
    }


async def generate_reconciliation_report(
    organization_id: str,
    period_start: str,
    period_end: str,
    target_currency: str = "EUR",
) -> dict[str, Any]:
    """Generate multi-currency reconciliation report."""
    db = await get_db()
    rates = await get_current_rates(organization_id)

    # Get bookings in the period
    bookings = await db.bookings.find({
        "organization_id": organization_id,
        "created_at": {"$gte": period_start, "$lte": period_end},
    }).to_list(10000)

    # Group by currency
    by_currency: dict[str, dict[str, Any]] = {}
    for b in bookings:
        curr = b.get("currency") or "TRY"
        if curr not in by_currency:
            by_currency[curr] = {
                "currency": curr,
                "symbol": CURRENCY_SYMBOLS.get(curr, curr),
                "total_gross": 0.0,
                "total_net": 0.0,
                "total_commission": 0.0,
                "booking_count": 0,
            }
        entry = by_currency[curr]
        entry["total_gross"] += float(b.get("gross_amount") or 0)
        entry["total_net"] += float(b.get("net_amount") or 0)
        entry["total_commission"] += float(b.get("commission_amount") or 0)
        entry["booking_count"] += 1

    # Convert all to target currency
    consolidated = {
        "total_gross": 0.0,
        "total_net": 0.0,
        "total_commission": 0.0,
        "total_bookings": 0,
        "target_currency": target_currency,
    }

    for curr, data in by_currency.items():
        try:
            gross_converted = convert_amount(data["total_gross"], curr, target_currency, rates)
            net_converted = convert_amount(data["total_net"], curr, target_currency, rates)
            comm_converted = convert_amount(data["total_commission"], curr, target_currency, rates)
        except ValueError:
            gross_converted = data["total_gross"]
            net_converted = data["total_net"]
            comm_converted = data["total_commission"]

        data["converted_gross"] = gross_converted
        data["converted_net"] = net_converted
        data["converted_commission"] = comm_converted

        consolidated["total_gross"] += gross_converted
        consolidated["total_net"] += net_converted
        consolidated["total_commission"] += comm_converted
        consolidated["total_bookings"] += data["booking_count"]

    return {
        "period": {"start": period_start, "end": period_end},
        "by_currency": list(by_currency.values()),
        "consolidated": consolidated,
        "rates_used": {k: v for k, v in rates.items() if target_currency in k},
        "generated_at": str(now_utc()),
    }


async def update_exchange_rate(
    organization_id: str,
    base: str,
    quote: str,
    rate: float,
    source: str = "manual",
) -> dict[str, Any]:
    """Update or insert an exchange rate."""
    db = await get_db()
    now = now_utc()
    doc = {
        "_id": str(uuid.uuid4()),
        "organization_id": organization_id,
        "base": base.upper(),
        "quote": quote.upper(),
        "rate": rate,
        "source": source,
        "updated_at": now,
    }
    await db.fx_rates.insert_one(doc)
    return doc
