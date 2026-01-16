from __future__ import annotations

from typing import Any, Dict, Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, Query

from app.auth import require_roles
from app.db import get_db
from app.errors import AppError

router = APIRouter(prefix="/api/admin/pricing/incidents", tags=["admin_pricing_incidents"])


async def _find_booking(db, organization_id: str, booking_id: str) -> Optional[Dict[str, Any]]:
  try:
    oid = ObjectId(booking_id)
  except Exception:
    # try string id fallback
    doc = await db.bookings.find_one({"organization_id": organization_id, "_id": booking_id})
    return doc

  return await db.bookings.find_one({"organization_id": organization_id, "_id": oid})


async def _find_rule(db, organization_id: str, rule_id: Optional[str]) -> Optional[Dict[str, Any]]:
  if not rule_id:
    return None
  try:
    oid = ObjectId(rule_id)
  except Exception:
    return None

  return await db.pricing_rules.find_one({"organization_id": organization_id, "_id": oid}, {"_id": 0})


@router.get("/debug-bundle")
async def get_pricing_debug_bundle(
  booking_id: Optional[str] = Query(default=None),
  quote_id: Optional[str] = Query(default=None),
  mode: str = Query(default="auto"),
  db=Depends(get_db),
  user: Dict[str, Any] = Depends(require_roles(["super_admin", "admin", "ops"])),
) -> Dict[str, Any]:
  """Return a debug bundle for pricing incidents.

  This endpoint is read-only and intended for ops/debug. It aggregates
  booking + quote + rule + trace into a single JSON blob that can be
  copy-pasted when investigating pricing incidents.
  """

  org_id = user["organization_id"]

  if not booking_id and not quote_id:
    raise AppError(422, "pricing_debug_invalid_params", "booking_id or quote_id is required")

  bundle: Dict[str, Any] = {
    "mode": mode or "auto",
    "requested": {
      "booking_id": booking_id,
      "quote_id": quote_id,
    },
    "found": {
      "booking": False,
      "quote": False,
      "rule": False,
      "public_checkout": False,
    },
    "booking": None,
    "quote": None,
    "rule": None,
    "pricing": None,
    "payments": None,
    "links": {},
    "explain": [],
    "checks": {},
  }

  booking_doc: Optional[Dict[str, Any]] = None
  quote_doc: Optional[Dict[str, Any]] = None
  rule_doc: Optional[Dict[str, Any]] = None

  # 1) Load booking if booking_id provided
  pricing: Dict[str, Any] = {}
  payments: Dict[str, Any] = {}

  if booking_id:
    booking_doc = await _find_booking(db, org_id, booking_id)
    if not booking_doc:
      raise AppError(404, "pricing_debug_not_found", "Booking not found", {"booking_id": booking_id})

    bundle["found"]["booking"] = True

    amounts = booking_doc.get("amounts") or {}
    applied_rules = booking_doc.get("applied_rules") or {}
    trace = applied_rules.get("trace") or {}

    bundle["booking"] = {
      "booking_id": str(booking_doc.get("_id")),
      "status": booking_doc.get("status"),
      "currency": booking_doc.get("currency"),
      "amounts": {
        "net": amounts.get("net"),
        "sell": amounts.get("sell"),
        "breakdown": amounts.get("breakdown") or {},
      },
      "applied_rules": {
        "markup_percent": applied_rules.get("markup_percent"),
        "trace": trace,
      },
    }

    # Seed canonical pricing from booking
    pricing_currency = booking_doc.get("currency") or amounts.get("currency") or "EUR"
    breakdown = amounts.get("breakdown") or {}
    net_val = amounts.get("net")
    sell_val = amounts.get("sell")
    base = breakdown.get("base")
    markup_amount = breakdown.get("markup_amount")
    discount_amount = breakdown.get("discount_amount") or 0.0

    # Derive markup_percent
    markup_percent = applied_rules.get("markup_percent")
    computed_sell_from_breakdown = None
    if base is not None and markup_amount is not None:
      computed_sell_from_breakdown = float(base) + float(markup_amount) - float(discount_amount or 0.0)

    computed_markup_percent_from_amounts = None
    try:
      if net_val not in (None, 0) and sell_val is not None:
        computed_markup_percent_from_amounts = (float(sell_val) / float(net_val) - 1.0) * 100.0
    except Exception:
      computed_markup_percent_from_amounts = None

    trace_rule_id = trace.get("rule_id")
    trace_rule_name = trace.get("rule_name")
    fallback = bool(trace.get("fallback"))

    pricing = {
      "source": booking_doc.get("source") or "public",
      "currency": pricing_currency,
      "amounts": {
        "net": net_val,
        "sell": sell_val,
        "breakdown": {
          "base": base,
          "markup_amount": markup_amount,
          "discount_amount": discount_amount,
        },
      },
      "trace": {
        "source": trace.get("source") or "simple_pricing_rules",
        "resolution": trace.get("resolution") or "winner_takes_all",
        "rule_id": trace_rule_id,
        "rule_name": trace_rule_name,
        "fallback": fallback,
      },
      "derived": {
        "markup_percent": applied_rules.get("markup_percent"),
        "computed_sell_from_breakdown": computed_sell_from_breakdown,
        "computed_markup_percent_from_amounts": computed_markup_percent_from_amounts,
      },
    }

    # 2) Try to resolve quote from booking.quote_id (if present)
    qid_from_booking = booking_doc.get("quote_id")
    if quote_id:
      # explicit quote_id overrides booking.quote_id
      try:
        oid = ObjectId(quote_id)
      except Exception:
        oid = None
      if oid:
        quote_doc = await db.price_quotes.find_one({"_id": oid, "organization_id": org_id})
    elif qid_from_booking:
      try:
        oid = ObjectId(str(qid_from_booking))
      except Exception:
        oid = None
      if oid:
        quote_doc = await db.price_quotes.find_one({"_id": oid, "organization_id": org_id})

    if quote_doc:
      bundle["found"]["quote"] = True
      offers = quote_doc.get("offers") or []
      first_offer = offers[0] if offers else {}
      qt = first_offer.get("trace") or {}

      bundle["quote"] = {
        "quote_id": str(quote_doc.get("_id")),
        "offers_preview": [
          {
            "net": first_offer.get("net"),
            "sell": first_offer.get("sell"),
            "currency": first_offer.get("currency"),
          }
        ] if offers else [],
        "winner_rule_id": qt.get("winner_rule_id"),
        "winner_rule_name": qt.get("winner_rule_name"),
        "pricing_trace": {
          "source": "simple_pricing_rules",
          "resolution": "winner_takes_all",
          "fallback": bool(qt.get("fallback")),
        },
      }

      # If booking trace is empty but quote has trace, prefer quote trace
      if not pricing.get("trace", {}).get("rule_id") and qt.get("winner_rule_id"):
        trace_rule_id = qt.get("winner_rule_id")
        trace_rule_name = qt.get("winner_rule_name")
        fallback = bool(qt.get("fallback"))
        pricing["trace"]["rule_id"] = trace_rule_id
        pricing["trace"]["rule_name"] = trace_rule_name
        pricing["trace"]["fallback"] = fallback

    # 3) Load rule document if we have rule_id and not DEFAULT_10
    rule_doc: Optional[Dict[str, Any]] = None
    if trace_rule_id:
      rule_doc = await _find_rule(db, org_id, trace_rule_id)

    bundle["rule"] = rule_doc

    # 4) Build explain + checks
    explain: list[str] = []

    if trace_rule_name:
      explain.append(f"Winner rule: {trace_rule_name} ({trace_rule_id})")
    if not fallback:
      amounts_bd = amounts.get("breakdown") or {}
      base = amounts_bd.get("base")
      markup_amount = amounts_bd.get("markup_amount")
      sell = amounts.get("sell")
      if base is not None and markup_amount is not None and sell is not None:
        explain.append(f"Markup: base={base:.2f} + markup={markup_amount:.2f} -> sell={sell:.2f}")
    else:
      explain.append("fallback=true (DEFAULT_10 kullanıldı veya rules match etmedi)")

    checks: Dict[str, Any] = {}
    checks["trace_rule_id_present"] = bool(trace_rule_id)
    # amounts_match_breakdown: base + markup_amount == sell (within 0.01)
    try:
      bd = amounts.get("breakdown") or {}
      base = float(bd.get("base") or 0.0)
      markup_amount = float(bd.get("markup_amount") or 0.0)
      sell = float(amounts.get("sell") or 0.0)
      checks["amounts_match_breakdown"] = abs((base + markup_amount) - sell) < 0.02
    except Exception:
      checks["amounts_match_breakdown"] = False

    # fallback_consistency: DEFAULT_10 <-> fallback flag
    checks["fallback_consistency"] = bool(fallback) == bool(trace_rule_name == "DEFAULT_10" or trace_rule_id is None)

    bundle["explain"] = explain
    bundle["checks"] = checks

  else:
    # booking_id missing but quote_id provided: handle minimal mode (quote-only)
    try:
      oid = ObjectId(str(quote_id))
    except Exception:
      raise AppError(404, "pricing_debug_not_found", "Quote not found", {"quote_id": quote_id})

    quote_doc = await db.price_quotes.find_one({"_id": oid, "organization_id": org_id})
    if not quote_doc:
      raise AppError(404, "pricing_debug_not_found", "Quote not found", {"quote_id": quote_id})

    offers = quote_doc.get("offers") or []
    first_offer = offers[0] if offers else {}
    qt = first_offer.get("trace") or {}

    bundle["quote"] = {
      "quote_id": str(quote_doc.get("_id")),
      "offers_preview": [
        {
          "net": first_offer.get("net"),
          "sell": first_offer.get("sell"),
          "currency": first_offer.get("currency"),
        }
      ] if offers else [],
      "winner_rule_id": qt.get("winner_rule_id"),
      "winner_rule_name": qt.get("winner_rule_name"),
      "pricing_trace": {
        "source": "simple_pricing_rules",
        "resolution": "winner_takes_all",
        "fallback": bool(qt.get("fallback")),
      },
    }

    trace_rule_id = qt.get("winner_rule_id")
    trace_rule_name = qt.get("winner_rule_name")
    fallback = bool(qt.get("fallback"))

    rule_doc = None
    if trace_rule_id:
      rule_doc = await _find_rule(db, org_id, trace_rule_id)
    bundle["rule"] = rule_doc

    explain: list[str] = []
    if trace_rule_name:
      explain.append(f"Winner rule: {trace_rule_name} ({trace_rule_id})")
    if fallback:
      explain.append("fallback=true (DEFAULT_10 kullanıldı veya rules match etmedi)")

    bundle["explain"] = explain
    bundle["checks"] = {
      "trace_rule_id_present": bool(trace_rule_id),
      "amounts_match_breakdown": None,
      "fallback_consistency": bool(fallback) == bool(trace_rule_name == "DEFAULT_10" or trace_rule_id is None),
    }

  return bundle
