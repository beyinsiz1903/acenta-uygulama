from __future__ import annotations

from datetime import date
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException

from app.auth import get_current_user
from app.db import get_db
from app.services.pricing_rules import PricingRulesService


router = APIRouter(prefix="/api/pricing", tags=["pricing_quote"])


class QuoteContextIn:
    """Lightweight context container (we'll validate manually for flexibility).

    Pydantic BaseModel is not strictly required here because the main
    constraints are simple and the project already uses dict-style models in
    several routers. To avoid importing an extra schema module just for this
    minimal endpoint, we keep it simple and parse from dict.
    """

    def __init__(
        self,
        agency_id: Optional[str] = None,
        product_id: Optional[str] = None,
        product_type: Optional[str] = "hotel",
        check_in: Optional[str] = None,
    ) -> None:
        self.agency_id = agency_id
        self.product_id = product_id
        self.product_type = product_type or "hotel"
        self.check_in = check_in


async def _parse_quote_payload(payload: dict[str, Any]) -> tuple[float, str, QuoteContextIn]:
    """Validate and normalise incoming quote request payload.

    Expected shape:
      {
        "base_price": 1000.0,
        "currency": "TRY",
        "context": { ... }
      }
    """

    if "base_price" not in payload:
        raise HTTPException(status_code=422, detail="base_price is required")

    try:
        base_price = float(payload.get("base_price"))
    except (TypeError, ValueError):
        raise HTTPException(status_code=422, detail="base_price must be a number")

    if base_price <= 0:
        raise HTTPException(status_code=422, detail="base_price must be > 0")

    currency = (payload.get("currency") or "TRY").upper()
    ctx_raw = payload.get("context") or {}
    if not isinstance(ctx_raw, dict):
        raise HTTPException(status_code=422, detail="context must be an object if provided")

    ctx = QuoteContextIn(
        agency_id=ctx_raw.get("agency_id"),
        product_id=ctx_raw.get("product_id"),
        product_type=ctx_raw.get("product_type") or "hotel",
        check_in=ctx_raw.get("check_in"),
    )

    # Basic check_in validation (if provided)
    if ctx.check_in is not None:
        try:
            date.fromisoformat(ctx.check_in[:10])
        except Exception:
            raise HTTPException(status_code=422, detail="check_in must be YYYY-MM-DD if provided")

    return base_price, currency, ctx


@router.post("/quote")
async def compute_quote(payload: dict[str, Any], user=Depends(get_current_user)) -> dict[str, Any]:
    """Deterministic quote endpoint using existing PricingRulesService.

    - organization_id is always derived from current user
    - Single winning rule via resolve_markup_percent (priority DESC)
    - If no rule matches or collection empty, we treat the default 10.0% as
      the applied markup (per existing service semantics).
    """

    base_price, currency, ctx = await _parse_quote_payload(payload)

    db = await get_db()
    org_id = user["organization_id"]

    svc = PricingRulesService(db)

    # Resolve markup_percent based on simple rules. Existing service already
    # applies org_id + status + validity + scope logic and falls back to 10.0
    # when no matching rule exists.
    check_in_date: date = date.today()
    if ctx.check_in is not None:
        check_in_date = date.fromisoformat(ctx.check_in[:10])

    winner = await svc.resolve_winner_rule(
        organization_id=org_id,
        agency_id=ctx.agency_id,
        product_id=ctx.product_id,
        product_type=ctx.product_type,
        check_in=check_in_date,
    )

    if winner is not None:
        markup_percent = await svc.resolve_markup_percent(
            organization_id=org_id,
            agency_id=ctx.agency_id,
            product_id=ctx.product_id,
            product_type=ctx.product_type,
            check_in=check_in_date,
        )
        fallback = False
        rule_id = str(winner.get("_id"))
        notes = (winner.get("notes") or "").strip() if isinstance(winner.get("notes"), str) else ""
        priority = winner.get("priority")
        rule_name = notes or (f"priority={priority}" if priority is not None else "simple_rule")
    else:
        # No matching rule -> default 10%
        markup_percent = 10.0
        fallback = True
        rule_id = None
        rule_name = "DEFAULT_10"

    # winner-takes-all semantics: single markup_percent applied on base_price
    final_price = round(base_price * (1.0 + (markup_percent or 0.0) / 100.0), 2)
    markup_amount = round(final_price - base_price, 2)

    trace = {
        "rule_id": rule_id,
        "rule_name": rule_name,
        "source": "simple_pricing_rules",
        "resolution": "winner_takes_all",
        "fallback": fallback,
    }

    breakdown = {
        "base": round(base_price, 2),
        "markup_amount": markup_amount,
        "discount_amount": 0.0,
    }

    return {
        "currency": currency,
        "base_price": round(base_price, 2),
        "markup_percent": float(markup_percent or 0.0),
        "final_price": final_price,
        "breakdown": breakdown,
        "trace": trace,
    }
