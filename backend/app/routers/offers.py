from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field

from app.schemas_offers import SupplierWarningOut

from app.auth import get_current_user, require_roles
from app.config import API_PREFIX
from app.context.org_context import get_current_org
from app.db import get_db
from app.errors import AppError
from app.services.offers.normalizers.mock_normalizer import normalize_mock_search_result
from app.services.offers.normalizers.paximum_normalizer import normalize_paximum_search_result
from app.services.offers.search_session_service import (
    create_search_session,
    find_offer_in_session,
    get_search_session,
)
from app.services.supplier_search_service import search_paximum_offers
from app.services.suppliers.mock_supplier_service import search_mock_offers
from app.services.pricing_graph.graph import price_offer_with_graph, PricingGraphResult
from app.services.supplier_warnings import SupplierWarning, sort_warnings, map_exception_to_warning


router = APIRouter(prefix=f"{API_PREFIX}/offers", tags=["offers"])


class CanonicalHotel(BaseModel):
    name: str
    city: Optional[str] = None
    country: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class CanonicalStay(BaseModel):
    check_in: str
    check_out: str
    nights: int
    adults: int
    children: int


class CanonicalRoom(BaseModel):
    room_name: Optional[str] = None
    board_type: Optional[str] = None


class CanonicalCancellationPolicy(BaseModel):
    refundable: Optional[bool] = None
    deadline: Optional[str] = None
    raw: Optional[Dict[str, Any]] = None


class CanonicalMoney(BaseModel):
    amount: float
    currency: str


class CanonicalHotelOfferOut(BaseModel):
    offer_token: str
    supplier_code: str
    supplier_offer_id: str
    product_type: str
    hotel: CanonicalHotel
    stay: CanonicalStay
    room: CanonicalRoom
    cancellation_policy: Optional[CanonicalCancellationPolicy]
    price: CanonicalMoney
    availability_token: Optional[str]
    raw_fingerprint: str
    b2b_pricing: Optional[Dict[str, Any]] = None


class OfferSearchRequest(BaseModel):
    destination: str
    check_in: date
    check_out: date
    adults: int = Field(2, ge=1, le=8)
    children: int = Field(0, ge=0, le=8)
    supplier_codes: Optional[List[str]] = None


class OfferSearchResponse(BaseModel):
    session_id: str
    expires_at: str
    offers: List[CanonicalHotelOfferOut] = Field(default_factory=list)
    warnings: Optional[List[SupplierWarningOut]] = None
    offers: List[CanonicalHotelOfferOut] = Field(default_factory=list)


def round_money(amount: float, currency: str) -> float:
    """Round money to 2 decimals for v1.

    NOTE: Currency-specific decimals can be added later; in this PR we keep
    behaviour simple and centralise the rounding decision.
    """

    return round(float(amount), 2)


@router.post("/search", response_model=OfferSearchResponse, dependencies=[Depends(require_roles(["agency_admin", "agency_agent"]))])
async def search_offers(
    payload: OfferSearchRequest,
    request: Request,
    user=Depends(get_current_user),
    org=Depends(get_current_org),
    db=Depends(get_db),
):
    """Canonical offers search endpoint.

    - Aggregates offers from mock + paximum suppliers (v1 subset)
    - Normalizes to CanonicalHotelOffer
    - Persists a short-lived search_session (TTL ~30 minutes)
    - Returns session_id + canonical offers
    """

    organization_id = str(org["id"])
    tenant_id = getattr(request.state, "tenant_id", None)

    if payload.check_out <= payload.check_in:
        raise AppError(422, "invalid_date_range", "Check-out must be after check-in", {})

    supplier_codes = [s.lower() for s in (payload.supplier_codes or ["mock", "paximum"])]

    canonical_offers: List[CanonicalHotelOfferOut] = []  # response models
    supplier_warnings: list[SupplierWarning] = []

    # Helper to compute B2B overlay using simple pricing rules
    from app.services.pricing_rules import PricingRulesService

    # Mock supplier
    if "mock" in supplier_codes:
        mock_payload = {
            "check_in": payload.check_in.strftime("%Y-%m-%d"),
            "check_out": payload.check_out.strftime("%Y-%m-%d"),
            "guests": payload.adults + payload.children,
            "city": payload.destination,
        }
        try:
            mock_raw = await search_mock_offers(mock_payload)
            # Normalize mock offers into canonical shape
        except AppError as exc:
            supplier_warnings.append(map_exception_to_warning("mock", exc))
            mock_raw = {"offers": [], "supplier": "mock"}
        
        from app.services.offers.normalizers.mock_normalizer import normalize_mock_search_result as _norm

        normalized = await _norm(mock_payload, mock_raw)
        for o in normalized:
            offer_out = CanonicalHotelOfferOut(
                offer_token=o.offer_token,
                supplier_code=o.supplier_code,
                supplier_offer_id=o.supplier_offer_id,
                product_type=o.product_type,
                hotel=CanonicalHotel(**o.hotel.__dict__),
                stay=CanonicalStay(**o.stay.__dict__),
                room=CanonicalRoom(**o.room.__dict__),
                cancellation_policy=CanonicalCancellationPolicy(**o.cancellation_policy.__dict__)
                if o.cancellation_policy
                else None,
                price=CanonicalMoney(**o.price.__dict__),
                availability_token=o.availability_token,
                raw_fingerprint=o.raw_fingerprint,
            )
            canonical_offers.append(offer_out)

    # Paximum supplier
    if "paximum" in supplier_codes:
        pax_payload = {
            "checkInDate": payload.check_in.strftime("%Y-%m-%d"),
            "checkOutDate": payload.check_out.strftime("%Y-%m-%d"),
            "destination": {"code": payload.destination},
            "rooms": [
                {"adult": payload.adults, "child": payload.children},
            ],
            "nationality": "TR",
            "currency": "TRY",
        }
        # NOTE: In canonical search we currently only use Paximum normalization
        # on top of the mock upstream client; failures from Paximum should not
        # break the overall canonical contract for other suppliers.
        try:
            pax_resp = await search_paximum_offers(organization_id, pax_payload)
        except AppError as exc:
            supplier_warnings.append(map_exception_to_warning("paximum", exc))
            pax_resp = {"offers": [], "supplier": "paximum"}
        
        from app.services.offers.normalizers.paximum_normalizer import normalize_paximum_search_result as _pn

        normalized = await _pn(pax_payload, pax_resp)
        for o in normalized:
            offer_out = CanonicalHotelOfferOut(
                offer_token=o.offer_token,
                supplier_code=o.supplier_code,
                supplier_offer_id=o.supplier_offer_id,
                product_type=o.product_type,
                hotel=CanonicalHotel(**o.hotel.__dict__),
                stay=CanonicalStay(**o.stay.__dict__),
                room=CanonicalRoom(**o.room.__dict__),
                cancellation_policy=CanonicalCancellationPolicy(**o.cancellation_policy.__dict__)
                if o.cancellation_policy
                else None,
                price=CanonicalMoney(**o.price.__dict__),
                availability_token=o.availability_token,
                raw_fingerprint=o.raw_fingerprint,
            )
            canonical_offers.append(offer_out)

    # Apply B2B pricing overlay if tenant context is present
    pricing_overlay_index: Dict[str, Any] = {}

    if tenant_id:
        from datetime import date as _date

        for offer in canonical_offers:
            base_price = offer.price
            check_in_date = payload.check_in if isinstance(payload.check_in, _date) else payload.check_in

            # Build minimal pricing context for rules engine
            context = {
                "check_in": check_in_date,
                "product_type": "hotel",
                "product_id": None,
            }

            graph: Optional[PricingGraphResult]
            try:
                graph = await price_offer_with_graph(
                    db,
                    organization_id=organization_id,
                    buyer_tenant_id=tenant_id,
                    base_amount=float(base_price.amount),
                    currency=base_price.currency,
                    context=context,
                )
            except Exception:
                graph = None

            if graph is None:
                # Fallback to no-overlay semantics
                offer.b2b_pricing = None
                continue

            # Map graph result into legacy b2b_pricing shape
            applied_pct = float(graph.applied_total_markup_pct or 0.0)
            final_amount = float(graph.final_price.get("amount") or 0.0)
            buyer_rule_id = graph.pricing_rule_ids[0] if graph.pricing_rule_ids else None

            offer.b2b_pricing = {
                "base_price": graph.base_price,
                "final_price": graph.final_price,
                "applied_markup_pct": applied_pct,
                "pricing_rule_id": buyer_rule_id,
                "pricing_trace": graph.pricing_trace,
                "pricing_graph": {
                    "model_version": graph.model_version,
                    "graph_path": graph.graph_path,
                    "pricing_rule_ids": graph.pricing_rule_ids,
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
                        for s in graph.steps
                    ],
                },
            }

            pricing_overlay_index[offer.offer_token] = {
                "final_amount": final_amount,
                "applied_markup_pct": applied_pct,
                "pricing_rule_id": buyer_rule_id,
                "pricing_rule_ids": graph.pricing_rule_ids,
                "graph_path": graph.graph_path,
                "model_version": graph.model_version,
                "currency": base_price.currency,
            }

    # Persist search session
    offers_dicts = [c.model_dump() for c in canonical_offers]

    session = await create_search_session(
        db,
        organization_id=organization_id,
        tenant_id=tenant_id,
        query={
            "destination": payload.destination,
            "check_in": payload.check_in.strftime("%Y-%m-%d"),
            "check_out": payload.check_out.strftime("%Y-%m-%d"),
            "adults": payload.adults,
            "children": payload.children,
            "supplier_codes": supplier_codes,
        },
        offers=offers_dicts,
        pricing_overlay_index=pricing_overlay_index if tenant_id else None,
    )

    # Audit pricing overlays for observability
    if tenant_id:
        from app.services.audit import write_audit_log
        actor = {"actor_type": "user", "email": user.get("email"), "roles": user.get("roles")}
        for offer in canonical_offers:
            b2b = offer.b2b_pricing
            if not b2b:
                continue
            bp = b2b.get("base_price") or {}
            fp = b2b.get("final_price") or {}
            pricing_graph = b2b.get("pricing_graph") or {}
            await write_audit_log(
                db,
                organization_id=organization_id,
                actor=actor,
                request=request,
                action="PRICING_OVERLAY_APPLIED",
                target_type="offer",
                target_id=offer.offer_token,
                before=None,
                after=None,
                meta={
                    "event_source": "offers_search",
                    "buyer_tenant_id": tenant_id,
                    "session_id": session["session_id"],
                    "offer_token": offer.offer_token,
                    "supplier_code": offer.supplier_code,
                    "supplier_offer_id": offer.supplier_offer_id,
                    "currency": bp.get("currency"),
                    "base_amount": float(bp.get("amount") or 0.0),
                    "applied_markup_pct": float(b2b.get("applied_markup_pct") or 0.0),
                    "final_amount": float(fp.get("amount") or 0.0),
                    "pricing_rule_id": b2b.get("pricing_rule_id"),
                    "pricing_trace": b2b.get("pricing_trace") or [],
                    # PR-20 enrichment
                    "model_version": pricing_graph.get("model_version"),
                    "graph_path": pricing_graph.get("graph_path"),
                    "pricing_rule_ids": pricing_graph.get("pricing_rule_ids"),
                    "steps_count": len(pricing_graph.get("steps") or []),
                    "effective_total_markup_pct": float(b2b.get("applied_markup_pct") or 0.0),
                },
            )

    # Convert supplier warnings to response format
    warnings_out = None
    if supplier_warnings:
        warnings_out = [
            SupplierWarningOut(
                supplier_code=w.supplier_code,
                warning_type=w.warning_type,
                message=w.message,
                details=w.details
            )
            for w in supplier_warnings
        ]

    return OfferSearchResponse(
        session_id=session["session_id"],
        expires_at=session["expires_at"].isoformat(),
        offers=canonical_offers,
        warnings=warnings_out,
    )


class OfferSearchSessionResponse(BaseModel):
    session_id: str
    expires_at: str
    offers: List[CanonicalHotelOfferOut]


@router.get("/search-sessions/{session_id}", response_model=OfferSearchSessionResponse, dependencies=[Depends(require_roles(["agency_admin", "agency_agent"]))])
async def get_search_session_offers(
    session_id: str,
    user=Depends(get_current_user),
    org=Depends(get_current_org),
    db=Depends(get_db),
):
    organization_id = str(org["id"])
    session = await get_search_session(db, organization_id=organization_id, session_id=session_id)
    if not session:
        # For simplicity and leak-safety we do not distinguish between missing
        # and expired sessions at the API surface.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SEARCH_SESSION_NOT_FOUND")

    offers = session.get("offers") or []
    expires_at = session.get("expires_at")
    if not expires_at:
        # Consider sessions without an expires_at as effectively not found
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SEARCH_SESSION_NOT_FOUND")

    return OfferSearchSessionResponse(
        session_id=session_id,
        expires_at=expires_at.isoformat(),
        offers=[CanonicalHotelOfferOut.model_validate(o) for o in offers],
    )
