from __future__ import annotations

from typing import Any, Dict, Optional

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

    # Re-evaluate B2B pricing for booking consistency using pricing graph
    from app.routers.offers import round_money
    from app.services.pricing_graph.graph import price_offer_with_graph, PricingGraphResult

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
    graph_result: Optional[PricingGraphResult] = None
    if check_in_date is not None and base_amount > 0:
        context = {"check_in": check_in_date, "product_type": "hotel", "product_id": None}
        try:
            graph_result = await price_offer_with_graph(
                db,
                organization_id=organization_id,
                buyer_tenant_id=payload.buyer_tenant_id,
                base_amount=base_amount,
                currency=currency,
                context=context,
            )
        except Exception:
            graph_result = None

    if graph_result is not None:
        final_amount = float(graph_result.final_price.get("amount") or 0.0)
        markup_pct = float(graph_result.applied_total_markup_pct or 0.0)
        pricing_rule_id = graph_result.pricing_rule_ids[0] if graph_result.pricing_rule_ids else None
    else:
        # Fail-open fallback: no markup change
        final_amount = round_money(base_amount, currency)
        markup_pct = 0.0
        pricing_rule_id = None

    actor = {
        "actor_type": "user",
        "actor_id": user["id"],
        "email": user["email"],
        "roles": user.get("roles", []),
    }

    stay = offer.get("stay") or {}

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
            # PR-20: enrich with pricing graph snapshot when available
            "model_version": getattr(graph_result, "model_version", None) if graph_result else None,
            "graph_path": getattr(graph_result, "graph_path", None) if graph_result else None,
            "pricing_rule_ids": getattr(graph_result, "pricing_rule_ids", None) if graph_result else None,
            "steps": [
                {
                    "level": s.level,
                    "tenant_id": s.tenant_id,
                    "node_type": s.node_type,
                    "rule_id": s.rule_id,
                    "markup_pct": s.markup_pct,
                    "base_amount": s.base_amount,
                    "delta_amount": s.delta_amount,
                    "amount_after": s.amount_after,
                    "currency": s.currency,
                    "notes": s.notes,
                }
                for s in (graph_result.steps if graph_result else [])
            ],
        },
        "created_at": now_utc(),
    }

    booking_id = await create_booking_draft(db, organization_id, actor, booking_payload, request)

    from app.repositories.booking_repository import BookingRepository
    from app.utils import serialize_doc
    from app.routers.offers import round_money
    from app.services.offers.search_session_service import get_search_session
    from app.services.audit import write_audit_log

    repo = BookingRepository(db)
    doc = await repo.get_by_id(organization_id, booking_id)
    if not doc:
        raise HTTPException(status_code=500, detail="BOOKING_PERSISTENCE_ERROR")

    # Audit repricing
    buyer_tenant_id = payload.buyer_tenant_id
    await write_audit_log(
        db,
        organization_id=organization_id,
        actor=actor,
        request=request,
        action="BOOKING_REPRICED",
        target_type="booking",
        target_id=booking_id,
        before=None,
        after=None,
        meta={
            "event_source": "booking_from_canonical_offer",
            "buyer_tenant_id": buyer_tenant_id,
            "booking_id": booking_id,
            "session_id": payload.session_id,
            "offer_token": payload.offer_token,
            "supplier_code": supplier_code,
            "supplier_offer_id": supplier_offer_id,
            "currency": currency,
            "base_amount": base_amount,
            "applied_markup_pct": float(markup_pct),
            "final_amount": final_amount,
            "pricing_rule_id": pricing_rule_id,
            # PR-20 enrichment
            "model_version": getattr(graph_result, "model_version", None) if graph_result else None,
            "graph_path": getattr(graph_result, "graph_path", None) if graph_result else None,
            "pricing_rule_ids": getattr(graph_result, "pricing_rule_ids", None) if graph_result else None,
            "effective_total_markup_pct": float(graph_result.applied_total_markup_pct)
            if graph_result and graph_result.applied_total_markup_pct is not None
            else float(markup_pct),
        },
    )

    # Mismatch detection (informational only)
    session_doc = await get_search_session(db, organization_id=organization_id, session_id=payload.session_id)
    overlay_index = (session_doc or {}).get("pricing_overlay_index") or {}
    overlay = overlay_index.get(payload.offer_token)
    if overlay:
        search_final = float(overlay.get("final_amount") or 0.0)
        booking_final = float(final_amount)
        delta_raw = abs(booking_final - search_final)
        delta = round_money(delta_raw, currency)
        tolerance = 0.01
        if delta > tolerance:
            await write_audit_log(
                db,
                organization_id=organization_id,
                actor=actor,
                request=request,
                action="PRICING_MISMATCH_DETECTED",
                target_type="booking",
                target_id=booking_id,
                before=None,
                after=None,
                meta={
                    "event_source": "booking_from_canonical_offer",
                    "buyer_tenant_id": buyer_tenant_id,
                    "booking_id": booking_id,
                    "session_id": payload.session_id,
                    "offer_token": payload.offer_token,
                    "currency": currency,
                    "search_final_amount": search_final,
                    "booking_final_amount": booking_final,
                    "delta": delta,
                    "tolerance": tolerance,
                    "search_pricing_rule_id": overlay.get("pricing_rule_id"),
                    "booking_pricing_rule_id": pricing_rule_id,
                    # PR-20 enrichment for mismatch
                    "search_model_version": overlay.get("model_version"),
                    "booking_model_version": getattr(graph_result, "model_version", None) if graph_result else None,
                    "search_graph_path": overlay.get("graph_path"),
                    "booking_graph_path": getattr(graph_result, "graph_path", None) if graph_result else None,
                    "search_pricing_rule_ids": overlay.get("pricing_rule_ids"),
                    "booking_pricing_rule_ids": getattr(graph_result, "pricing_rule_ids", None)
                    if graph_result
                    else None,
                },
            )

    return serialize_doc(doc)
