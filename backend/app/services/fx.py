from __future__ import annotations

"""FX Service (Phase 2C)

Minimal service to resolve FX rates and create idempotent snapshots
for booking context. Functional currency is assumed to be EUR.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

from pymongo.errors import DuplicateKeyError

from app.errors import AppError
from app.utils import now_utc


ORG_FUNCTIONAL_CCY = "EUR"


@dataclass
class FxRate:
  organization_id: str
  base: str
  quote: str
  rate: float
  as_of: datetime


class FXService:
  def __init__(self, db):
    self.db = db

  async def get_rate(
    self,
    organization_id: str,
    quote: str,
    as_of: Optional[datetime] = None,
  ) -> FxRate:
    """Return latest FX rate for base=EUR, given quote.

    - If as_of is None: use now() and pick latest rate with as_of <= now.
    - If no rate found: raise fx_rate_not_found.
    """
    base = ORG_FUNCTIONAL_CCY
    if not quote or quote.upper() == base:
      # No FX conversion needed; treat as 1:1
      return FxRate(
        organization_id=organization_id,
        base=base,
        quote=base,
        rate=1.0,
        as_of=now_utc(),
      )

    quote = quote.upper()

    if as_of is None:
      as_of = now_utc()

    cursor = (
      self.db.fx_rates
      .find(
        {
          "organization_id": organization_id,
          "base": base,
          "quote": quote,
          "as_of": {"$lte": as_of},
        }
      )
      .sort("as_of", -1)
      .limit(1)
    )
    docs = await cursor.to_list(length=1)
    if not docs:
      raise AppError(
        status_code=404,
        code="fx_rate_not_found",
        message=f"No FX rate found for {base}/{quote} as of {as_of.isoformat()}",
      )

    doc = docs[0]
    return FxRate(
      organization_id=organization_id,
      base=doc.get("base", base),
      quote=doc.get("quote", quote),
      rate=float(doc["rate"]),
      as_of=doc.get("as_of") or as_of,
    )

  async def snapshot_for_booking(
    self,
    organization_id: str,
    booking_id: str,
    quote: str,
    as_of: Optional[datetime] = None,
    created_by_email: str = "system",
  ) -> dict[str, Any]:
    """Ensure there is an FX snapshot for this booking context.

    Idempotent per (org, booking_id, base, quote).
    Returns a dict including rate, as_of and snapshot_id.
    """
    base = ORG_FUNCTIONAL_CCY
    quote = (quote or base).upper()

    if quote == base:
      now = now_utc()
      return {
        "snapshot_id": None,
        "base": base,
        "quote": base,
        "rate": 1.0,
        "as_of": now,
      }

    ctx = {"type": "booking", "id": booking_id}
    existing = await self.db.fx_rate_snapshots.find_one(
      {
        "organization_id": organization_id,
        "context.type": "booking",
        "context.id": booking_id,
        "base": base,
        "quote": quote,
      }
    )
    if existing:
      return {
        "snapshot_id": str(existing["_id"]),
        "base": existing["base"],
        "quote": existing["quote"],
        "rate": float(existing["rate"]),
        "as_of": existing["as_of"],
      }

    fx = await self.get_rate(organization_id, quote, as_of)
    now = now_utc()
    snapshot = {
      "organization_id": organization_id,
      "context": ctx,
      "base": fx.base,
      "quote": fx.quote,
      "rate": fx.rate,
      "rate_basis": "QUOTE_PER_EUR",  # 1 EUR = rate * quote
      "as_of": fx.as_of,
      "created_at": now,
      "created_by_email": created_by_email,
    }
    try:
      res = await self.db.fx_rate_snapshots.insert_one(snapshot)
      inserted_id = res.inserted_id
    except DuplicateKeyError:
      # Another concurrent request created the same snapshot; fetch and return it
      existing = await self.db.fx_rate_snapshots.find_one(
        {
          "organization_id": organization_id,
          "context.type": "booking",
          "context.id": booking_id,
          "base": base,
          "quote": quote,
        }
      )
      if existing:
        return {
          "snapshot_id": str(existing["_id"]),
          "base": existing["base"],
          "quote": existing["quote"],
          "rate": float(existing["rate"]),
          "as_of": existing["as_of"],
        }
      # If for some reason we still don't find it, bubble up
      raise

    return {
      "snapshot_id": str(inserted_id),
      "base": fx.base,
      "quote": fx.quote,
      "rate": fx.rate,
      "as_of": fx.as_of,
    }
