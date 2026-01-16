from __future__ import annotations

from datetime import date
from typing import Any, Optional

from app.errors import AppError
from app.services.pricing_rules import PricingRulesService


async def compute_quote_for_booking(
    db,
    organization_id: str,
    *,
    base_price: float,
    currency: str,
    agency_id: Optional[str],
    product_id: Optional[str],
    product_type: str,
    check_in: Optional[date],
) -> dict[str, Any]:
    """Compute pricing breakdown for a booking using simple pricing rules.

    This mirrors the behaviour of the HTTP-level /api/pricing/quote endpoint
    but is designed for internal use in booking/checkout flows.

    Fallback semantics (never break booking flow):
    - On any error from PricingRulesService, fall back to 10% markup
    - Attach trace.error = "quote_failed_fallback_10" for observability
    """

    if base_price <= 0:
        # Guard against invalid input; we still allow booking flow to continue
        # but treat this as zero-priced booking with zero markup.
        base = 0.0
        markup_percent = 0.0
        final_price = 0.0
        breakdown = {"base": 0.0, "markup_amount": 0.0, "discount_amount": 0.0}
        trace = {
            "source": "simple_pricing_rules",
            "resolution": "winner_takes_all",
            "rule_id": None,
            "rule_name": None,
            "error": "invalid_base_price",
        }
        return {
            "currency": currency.upper(),
            "base_price": base,
            "markup_percent": markup_percent,
            "final_price": final_price,
            "breakdown": breakdown,
            "trace": trace,
        }

    svc = PricingRulesService(db)

    # Determine check_in date; if None, we allow the rules engine to still run
    # with today's date (keeps behaviour deterministic but lenient).
    ci: date = check_in or date.today()

    markup_percent: float
    trace_error: Optional[str] = None
    winner_rule: Optional[dict[str, Any]] = None
    try:
        winner_rule = await svc.resolve_winner_rule(
            organization_id=organization_id,
            agency_id=agency_id,
            product_id=product_id,
            product_type=product_type or "hotel",
            check_in=ci,
        )
        if winner_rule is not None:
            markup_percent = await svc.resolve_markup_percent(
                organization_id=organization_id,
                agency_id=agency_id,
                product_id=product_id,
                product_type=product_type or "hotel",
                check_in=ci,
            )
        else:
            markup_percent = 10.0
    except AppError:
        # Known application error from rules engine -> safe fallback
        markup_percent = 10.0
        trace_error = "quote_failed_fallback_10"
    except Exception:
        # Any unexpected error also falls back to 10%
        markup_percent = 10.0
        trace_error = "quote_failed_fallback_10"

    base = round(float(base_price), 2)
    final_price = round(base * (1.0 + (markup_percent or 0.0) / 100.0), 2)
    markup_amount = round(final_price - base, 2)

    breakdown = {
        "base": base,
        "markup_amount": markup_amount,
        "discount_amount": 0.0,
    }

    trace: dict[str, Any] = {
        "source": "simple_pricing_rules",
        "resolution": "winner_takes_all",
        "rule_id": None,
        "rule_name": None,
    }
    if trace_error:
        trace["error"] = trace_error

    return {
        "currency": currency.upper(),
        "base_price": base,
        "markup_percent": float(markup_percent or 0.0),
        "final_price": final_price,
        "breakdown": breakdown,
        "trace": trace,
    }
