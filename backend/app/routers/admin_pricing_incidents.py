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
    if trace_rule_id:
      rule_doc = await _find_rule(db, org_id, trace_rule_id)
      if rule_doc:
        bundle["found"]["rule"] = True

    bundle["rule"] = rule_doc

    # 4) Payments + idempotency + finalize guard
    payment_intent_id = booking_doc.get("payment_intent_id")
    payment_status = booking_doc.get("payment_status") or "unknown"
    payment_provider = booking_doc.get("payment_provider") or "none"

    public_checkout = None
    if payment_intent_id:
      public_checkout = await db.public_checkouts.find_one(
        {"payment_intent_id": payment_intent_id, "organization_id": org_id},
        {"_id": 0},
      )
      if public_checkout:
        bundle["found"]["public_checkout"] = True

    idemp = {
      "public_checkout_registry_found": bool(public_checkout),
      "idempotency_key": public_checkout.get("idempotency_key") if public_checkout else None,
      "registry_status": public_checkout.get("status") if public_checkout else None,
      "reason": public_checkout.get("reason") if public_checkout else None,
    }

    # Finalize guard aggregation
    finalizations_cursor = None
    finalizations = []
    if payment_intent_id:
      finalizations_cursor = db.payment_finalizations.find(
        {"provider": "stripe", "payment_intent_id": payment_intent_id}
      ).sort("created_at", -1).limit(20)
      async for doc in finalizations_cursor:
        doc.pop("_id", None)
        finalizations.append(doc)

    last_decision = None
    last_reason = None
    if finalizations:
      last = finalizations[0]
      last_decision = last.get("decision")
      last_reason = last.get("reason")

    payments = {
      "provider": payment_provider,
      "status": payment_status,
      "payment_intent_id": payment_intent_id,
      "client_secret_present": bool(public_checkout and public_checkout.get("client_secret")),
      "idempotency": idemp,
      "finalize_guard": {
        "finalizations_found": len(finalizations),
        "last_decision": last_decision,
        "last_reason": last_reason,
      },
    }

    bundle["payments"] = payments

    # 5) Build explain + checks
    explain: list[str] = []

    if trace_rule_name:
      explain.append(f"Winner rule: {trace_rule_name} ({trace_rule_id})")
    if not fallback:
      if base is not None and markup_amount is not None and sell_val is not None:
        try:
          explain.append(
            f"Markup: base={float(base):.2f} + markup={float(markup_amount):.2f}"
            f" - discount={float(discount_amount or 0.0):.2f} -> sell={float(sell_val):.2f}"
          )
        except Exception:
          pass
    else:
      explain.append("fallback=true (DEFAULT_10 kullan1ldl veya rules match etmedi)")

    checks: Dict[str, Any] = {}
    checks["trace_present"] = bool(pricing.get("trace"))
    checks["trace_rule_id_present"] = bool(trace_rule_id)

    # amounts_match_breakdown: base + markup_amount - discount_amount == sell (within 0.01)
    try:
      if base is not None and markup_amount is not None and sell_val is not None:
        diff = (float(base) + float(markup_amount) - float(discount_amount or 0.0)) - float(sell_val)
        checks["amounts_present"] = True
        checks["amounts_match_breakdown"] = abs(diff) < 0.02
      else:
        checks["amounts_present"] = False
        checks["amounts_match_breakdown"] = False
    except Exception:
      checks["amounts_present"] = False
      checks["amounts_match_breakdown"] = False

    # fallback_consistency: DEFAULT_10 <-> fallback flag
    checks["fallback_consistency"] = bool(fallback) == bool(
      trace_rule_name == "DEFAULT_10" or trace_rule_id is None
    )

    # markup_percent_consistency
    try:
      if pricing["derived"]["computed_markup_percent_from_amounts"] is not None and pricing["derived"][
        "markup_percent"
      ] is not None:
        mp1 = float(pricing["derived"]["computed_markup_percent_from_amounts"])
        mp2 = float(pricing["derived"]["markup_percent"])
        checks["markup_percent_consistency"] = abs(mp1 - mp2) < 0.02
      else:
        checks["markup_percent_consistency"] = False
    except Exception:
      checks["markup_percent_consistency"] = False

    # currency_consistency: booking vs quote currency
    booking_currency = booking_doc.get("currency")
    quote_currency = None
    if bundle["quote"] and bundle["quote"].get("offers_preview"):
      quote_currency = bundle["quote"]["offers_preview"][0].get("currency")

    if booking_currency and quote_currency:
      checks["currency_consistency"] = booking_currency == quote_currency
    else:
      checks["currency_consistency"] = True  # best-effort

    # payment_correlation_present
    checks["payment_correlation_present"] = bool(payment_intent_id or idemp["public_checkout_registry_found"])

    bundle["pricing"] = pricing
    bundle["checks"] = checks

    # simple links for admin UI
    bundle["links"] = {
      "booking": f"/app/admin/bookings/{bundle['booking']['booking_id']}",
      "ops_case_search": f"/app/ops/guest-cases?booking_id={bundle['booking']['booking_id']}",
      "stripe_dashboard": None,
    }

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
