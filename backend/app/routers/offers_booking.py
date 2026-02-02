from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

from app.auth import get_current_user, require_roles
from app.config import API_PREFIX
from app.context.org_context import get_current_org
from app.db import get_db
from app.services.booking_service import create_booking_draft
from app.services.offers.search_session_service import find_offer_in_session
from app.utils import now_utc


router = APIRouter(prefix=f"{API_PREFIX}/bookings", tags=["bookings-offers"])


class BookingFromCanonicalOfferRequest(BaseModel):
    session_id: str
    offer_token: str
    buyer_tenant_id: str | None = None
    customer: Dict[str, Any] | None = None


@router.post(
    "/from-canonical-offer",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(["agency_admin", "agency_agent"]))],
)
async def create_booking_from_canonical_offer(
    payload: BookingFromCanonicalOfferRequest,
    request: Request,
    db=Depends(get_db),
    user=Depends(get_current_user),
    org=Depends(get_current_org),
) -> Dict[str, Any]:
    """Create a draft booking from a canonical offer token.

    - Loads search_session and offer by (session_id, offer_token).
    - Writes booking in draft state with canonical supplier refs:
      offer_ref.supplier = supplier_code
      offer_ref.supplier_offer_id = supplier_offer_id
      offer_ref.search_session_id, offer_ref.offer_token for traceability.
    - Does NOT confirm booking; confirm is handled via existing B2B confirm flow (PR-17).
    """

    organization_id = str(org["id"])

    offer = await find_offer_in_session(
        db,
        organization_id=organization_id,
        session_id=payload.session_id,
        offer_token=payload.offer_token,
    )
    if not offer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="OFFER_NOT_FOUND_IN_SESSION")

    supplier_code = str(offer.get("supplier_code") or "").strip()
    supplier_offer_id = str(offer.get("supplier_offer_id") or "").strip()
    if not supplier_code or not supplier_offer_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="INVALID_CANONICAL_OFFER")

    # Re-evaluate B2B pricing for booking consistency
    from app.routers.offers import round_money
    from app.services.pricing_rules import PricingRulesService

    rules_svc = PricingRulesService(db)
    base_price = offer.get("price") or {}
    base_amount = float(base_price.get("amount") or 0.0)
    currency = base_price.get("currency") or "TRY"

    from datetime import date as _date

    stay = offer.get("stay") or {}
    check_in_str = stay.get("check_in")
    check_in_date = None
    if isinstance(check_in_str, str):
        try:
            check_in_date = _date.fromisoformat(check_in_str)
        except ValueError:
            check_in_date = None

    markup_pct = 0.0
    pricing_rule_id = None
    if check_in_date is not None:
        winner_rule = await rules_svc.resolve_winner_rule(
            organization_id=organization_id,
            agency_id=payload.buyer_tenant_id,
            product_id=None,
            product_type="hotel",
            check_in=check_in_date,
        )
        if winner_rule is not None:
            markup_pct = await rules_svc.resolve_markup_percent(
                organization_id,
                agency_id=payload.buyer_tenant_id,
                product_id=None,
                product_type="hotel",
                check_in=check_in_date,
            )
            if winner_rule.get("_id") is not None:
                pricing_rule_id = str(winner_rule.get("_id"))

    final_amount = round_money(base_amount * (1 + float(markup_pct) / 100), currency)

    actor = {
        "actor_type": "user",
        "actor_id": user["id"],
        "email": user["email"],
        "roles": user.get("roles", []),
    }

    stay = offer.get("stay") or {}
    price = offer.get("price") or {}

    booking_payload: Dict[str, Any] = {
        "source": "b2b_marketplace",  # v1: reuse B2B marketplace semantics for canonical offers
        "currency": currency,
        "amount": final_amount,
        "offer_ref": {
            "supplier": supplier_code,
            "supplier_offer_id": supplier_offer_id,
            "search_session_id": payload.session_id,
            "offer_token": payload.offer_token,
            "buyer_tenant_id": payload.buyer_tenant_id,
        },
        "customer": payload.customer or {},
        "stay": {
            "check_in": stay.get("check_in"),
            "check_out": stay.get("check_out"),
            "nights": stay.get("nights"),
        },
        "pricing": {
            "base_amount": base_amount,
            "final_amount": final_amount,
            "applied_markup_pct": float(markup_pct),
            "pricing_rule_id": pricing_rule_id,
            "currency": currency,
        },
        "created_at": now_utc(),
    }

    booking_id = await create_booking_draft(db, organization_id, actor, booking_payload, request)

    from app.repositories.booking_repository import BookingRepository
    from app.utils import serialize_doc

    repo = BookingRepository(db)
    doc = await repo.get_by_id(organization_id, booking_id)
    if not doc:
        raise HTTPException(status_code=500, detail="BOOKING_PERSISTENCE_ERROR")

    return serialize_doc(doc)
