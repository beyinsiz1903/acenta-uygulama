from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field

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

    # Mock supplier
    if "mock" in supplier_codes:
        mock_payload = {
            "check_in": payload.check_in.strftime("%Y-%m-%d"),
            "check_out": payload.check_out.strftime("%Y-%m-%d"),
            "guests": payload.adults + payload.children,
            "city": payload.destination,
        }
        mock_raw = await search_mock_offers(mock_payload)
        from app.services.offers.normalizers.mock_normalizer import normalize_mock_search_result as _norm

        normalized = await _norm(mock_payload, mock_raw)
        for o in normalized:
            canonical_offers.append(
                CanonicalHotelOfferOut(
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
            )

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
        pax_resp = await search_paximum_offers(organization_id, pax_payload)
        from app.services.offers.normalizers.paximum_normalizer import normalize_paximum_search_result as _pn

        normalized = await _pn(pax_payload, pax_resp)
        for o in normalized:
            canonical_offers.append(
                CanonicalHotelOfferOut(
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
            )

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
        offers=offers_for_session,
    )

    return OfferSearchResponse(
        session_id=session["session_id"],
        expires_at=session["expires_at"].isoformat(),
        offers=canonical_offers,
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
