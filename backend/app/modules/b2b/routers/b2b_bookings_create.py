"""B2B booking creation routers (T009 / Task #3).

Extracted from `b2b_bookings.py` to keep each file under ~500 LOC.

Owns:
- POST /api/b2b/bookings              (create_b2b_booking)
- POST /api/b2b/bookings-from-marketplace (create_b2b_booking_from_marketplace)
- _get_visible_listing helper used by the marketplace flows.

External contract (URL paths, request/response shapes, status codes,
audit log entries, funnel events) is preserved bit-for-bit.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict, Optional

from bson import Decimal128, ObjectId
from fastapi import APIRouter, Depends, Header, Request
from fastapi.responses import JSONResponse

from app.auth import get_current_user, require_roles
from app.db import get_db
from app.errors import AppError
from app.repos_idempotency import IdempotencyRepo
from app.schemas_b2b_bookings import (
    B2BMarketplaceBookingCreateRequest,
    B2BMarketplaceBookingCreateResponse,
    BookingCreateRequest,
    BookingCreateResponse,
)
from app.services.audit import write_audit_log
from app.services.b2b_booking import B2BBookingService
from app.services.b2b_pricing import B2BPricingService
from app.services.funnel_events import log_funnel_event
from app.services.pricing_audit_service import emit_pricing_audit_if_needed
from app.services.pricing_service import calculate_price
from app.services.supplier_mapping_service import (
    apply_supplier_mapping,
    resolve_listing_supplier,
)
from app.utils import get_or_create_correlation_id, now_utc, serialize_doc

router = APIRouter(prefix="/api/b2b", tags=["b2b-bookings"])


def get_pricing_service(db=Depends(get_db)) -> B2BPricingService:
    return B2BPricingService(db)


def get_booking_service(db=Depends(get_db)) -> B2BBookingService:
    return B2BBookingService(db)


def get_idem_repo(db=Depends(get_db)) -> IdempotencyRepo:
    return IdempotencyRepo(db)


async def _get_visible_listing(
    db,
    *,
    organization_id: str,
    listing_id: str,
    buyer_tenant_id: str,
) -> Dict[str, Any]:
    try:
        oid = ObjectId(listing_id)
    except Exception:
        raise AppError(404, "LISTING_NOT_FOUND", "LISTING_NOT_FOUND")

    listing = await db.marketplace_listings.find_one(
        {"_id": oid, "organization_id": organization_id, "status": "published"}
    )
    if not listing:
        raise AppError(404, "LISTING_NOT_FOUND", "LISTING_NOT_FOUND")

    seller_tenant_id = listing.get("tenant_id")
    if not seller_tenant_id:
        raise AppError(404, "LISTING_NOT_FOUND", "LISTING_NOT_FOUND")

    access = await db.marketplace_access.find_one(
        {
            "organization_id": organization_id,
            "seller_tenant_id": seller_tenant_id,
            "buyer_tenant_id": buyer_tenant_id,
        }
    )
    if not access:
        raise AppError(403, "MARKETPLACE_ACCESS_FORBIDDEN", "MARKETPLACE_ACCESS_FORBIDDEN")

    return listing


@router.post(
    "/bookings",
    response_model=BookingCreateResponse,
    dependencies=[Depends(require_roles(["agency_agent", "agency_admin", "super_admin"]))],
)
async def create_b2b_booking(
    payload: BookingCreateRequest,
    request: Request,
    user=Depends(get_current_user),
    pricing: B2BPricingService = Depends(get_pricing_service),
    booking_svc: B2BBookingService = Depends(get_booking_service),
    idem: IdempotencyRepo = Depends(get_idem_repo),
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
):
    org_id = user.get("organization_id")
    agency_id = user.get("agency_id")
    correlation_id = get_or_create_correlation_id(request, None)

    source = (payload.source or "quote").strip().lower()

    # Legacy quote-based flow (P0.2)
    if source in {"", "quote"}:
        if not agency_id:
            raise AppError(403, "forbidden", "User is not bound to an agency")
        endpoint = "b2b_bookings_create"
        method = "POST"
        path = "/api/b2b/bookings"

        async def compute_quote():
            quote_doc = await pricing.ensure_quote_valid(
                organization_id=org_id,
                agency_id=agency_id,
                quote_id=payload.quote_id,
            )

            # Funnel: b2b.checkout.started
            try:
                await log_funnel_event(
                    await get_db(),
                    organization_id=org_id,
                    correlation_id=correlation_id,
                    event_name="b2b.checkout.started",
                    entity_type="quote",
                    entity_id=str(quote_doc.get("_id")) if quote_doc else None,
                    channel="b2b",
                    user={
                        "user_id": user.get("id"),
                        "email": user.get("email"),
                        "roles": user.get("roles") or [],
                    },
                    context={},
                    trace={
                        "idempotency_key": idempotency_key,
                    },
                )
            except Exception:
                pass

            # Context mismatch check (agency already enforced via query, channel optional here)
            booking = await booking_svc.create_booking_from_quote(
                organization_id=org_id,
                agency_id=agency_id,
                user_email=user.get("email"),
                quote_doc=quote_doc,
                booking_req=payload,
                request_id=idempotency_key,
            )

            # Funnel: b2b.booking.created
            try:
                await log_funnel_event(
                    await get_db(),
                    organization_id=org_id,
                    correlation_id=correlation_id,
                    event_name="b2b.booking.created",
                    entity_type="booking",
                    entity_id=booking.booking_id,
                    channel="b2b",
                    user={
                        "user_id": user.get("id"),
                        "email": user.get("email"),
                        "roles": user.get("roles") or [],
                    },
                    context={},
                    trace={
                        "idempotency_key": idempotency_key,
                    },
                )
            except Exception:
                pass

            return 200, booking.model_dump()

        status, body = await idem.store_or_replay(
            org_id=org_id,
            agency_id=agency_id,
            endpoint=endpoint,
            key=idempotency_key,
            method=method,
            path=path,
            request_body=payload.model_dump(),
            compute_response_fn=compute_quote,
        )

        if status == 200:
            return BookingCreateResponse(**body)

        return JSONResponse(status_code=status, content=body)

    # Marketplace flow (PR-10)
    if source == "marketplace":
        if not payload.listing_id:
            raise AppError(422, "INVALID_LISTING_ID", "INVALID_LISTING_ID")

        db = await get_db()
        buyer_tenant_id: Optional[str] = getattr(request.state, "tenant_id", None)
        if not buyer_tenant_id:
            raise AppError(403, "TENANT_CONTEXT_REQUIRED", "TENANT_CONTEXT_REQUIRED")

        listing = await _get_visible_listing(
            db,
            organization_id=org_id,
            listing_id=payload.listing_id,
            buyer_tenant_id=buyer_tenant_id,
        )

        # Supplier mapping (lazy resolve)
        supplier_mapping = (listing.get("supplier_mapping") or {})
        supplier_name: Optional[str] = None
        supplier_offer_id: Optional[str] = None

        if supplier_mapping.get("status") == "resolved":
            supplier_name = supplier_mapping.get("supplier")
            supplier_offer_id = supplier_mapping.get("offer_id")
        else:
            # Try to resolve via adapter; surface AppError codes as-is
            offer_ref = await resolve_listing_supplier(listing=listing, organization_id=org_id)
            listing = await apply_supplier_mapping(db, listing=listing, mapping=offer_ref)
            supplier_mapping = (listing.get("supplier_mapping") or {})
            if supplier_mapping.get("status") != "resolved":
                raise AppError(500, "SUPPLIER_RESOLVE_FAILED", "SUPPLIER_RESOLVE_FAILED")
            supplier_name = supplier_mapping.get("supplier")
            supplier_offer_id = supplier_mapping.get("offer_id")

        currency = listing.get("currency") or "TRY"
        if currency != "TRY":
            raise AppError(422, "UNSUPPORTED_CURRENCY", "UNSUPPORTED_CURRENCY")

        base_price = listing.get("base_price")
        if isinstance(base_price, Decimal128):
            base_amount_dec = base_price.to_decimal()
        else:
            base_amount_dec = Decimal(str(base_price or "0"))

        pricing_result = await calculate_price(
            db,
            base_amount=base_amount_dec,
            organization_id=org_id,
            currency=currency,
            tenant_id=buyer_tenant_id,
            supplier="marketplace",
        )

        now = now_utc()
        customer = payload.customer
        customer_email = customer.email.lower()
        customer_name = customer.full_name or customer.name
        if not customer_name:
            raise AppError(422, "INVALID_CUSTOMER_NAME", "INVALID_CUSTOMER_NAME")

        seller_tenant_id = listing.get("tenant_id")

        booking_doc: Dict[str, Any] = {
            "organization_id": org_id,
            "state": "draft",
            "source": "b2b_marketplace",
            "currency": currency,
            # Keep numeric amount as float to avoid changing legacy behaviour
            "amount": float(pricing_result["final_amount"]),
            "customer_email": customer_email,
            "customer_name": customer_name,
            "customer_phone": customer.phone,
            "offer_ref": {
                "source": "marketplace",
                "listing_id": payload.listing_id,
                "seller_tenant_id": seller_tenant_id,
                "buyer_tenant_id": buyer_tenant_id,
                "supplier": supplier_name,
                "supplier_offer_id": supplier_offer_id,
            },
            "pricing": {
                "base_amount": str(pricing_result["base_amount"]),
                "final_amount": str(pricing_result["final_amount"]),
                "commission_amount": str(pricing_result["commission_amount"]),
                "margin_amount": str(pricing_result["margin_amount"]),
                "currency": currency,
                "applied_rules": pricing_result["applied_rules"],
                "calculated_at": now,
            },
            "pricing_audit_emitted": False,
            "created_at": now,
            "updated_at": now,
        }

        res = await db.bookings.insert_one(booking_doc)
        booking_id = str(res.inserted_id)

        actor = {"actor_type": "user", "email": user.get("email"), "roles": user.get("roles")}

        await write_audit_log(
            db,
            organization_id=org_id,
            actor=actor,
            request=request,
            action="B2B_BOOKING_CREATED",
            target_type="booking",
            target_id=booking_id,
            before=None,
            after=serialize_doc(booking_doc),
            meta={
                "source": "marketplace",
                "listing_id": payload.listing_id,
                "buyer_tenant_id": buyer_tenant_id,
                "seller_tenant_id": seller_tenant_id,
            },
        )

        await emit_pricing_audit_if_needed(
            db,
            booking_id=booking_id,
            tenant_id=buyer_tenant_id,
            organization_id=org_id,
            actor=actor,
            request=request,
        )

        # Marketplace create returns 201 + minimal draft payload
        return JSONResponse(
            status_code=201,
            content={"booking_id": booking_id, "state": "draft"},
        )

    # Unknown source
    raise AppError(422, "UNSUPPORTED_SOURCE", "UNSUPPORTED_SOURCE")


@router.post(
    "/bookings-from-marketplace",
    status_code=201,
    response_model=B2BMarketplaceBookingCreateResponse,
    dependencies=[Depends(require_roles(["agency_agent", "agency_admin"]))],
)
async def create_b2b_booking_from_marketplace(
    payload: B2BMarketplaceBookingCreateRequest,
    request: Request,
    user=Depends(get_current_user),
    db=Depends(get_db),
) -> B2BMarketplaceBookingCreateResponse:
    """Create a B2B booking draft from a marketplace listing.

    - Requires buyer tenant context
    - Enforces marketplace_access visibility
    - Uses pricing engine with tenant_id = buyer_tenant_id
    """

    if payload.source != "marketplace":
        raise AppError(422, "UNSUPPORTED_SOURCE", "UNSUPPORTED_SOURCE")

    org_id: str = user.get("organization_id")
    buyer_tenant_id: Optional[str] = getattr(request.state, "tenant_id", None)

    if not buyer_tenant_id:
        raise AppError(403, "TENANT_CONTEXT_REQUIRED", "TENANT_CONTEXT_REQUIRED")

    listing = await _get_visible_listing(
        db,
        organization_id=org_id,
        listing_id=payload.listing_id,
        buyer_tenant_id=buyer_tenant_id,
    )

    # Lazy supplier mapping resolve (v1)
    supplier_mapping = (listing.get("supplier_mapping") or {})
    if supplier_mapping.get("status") != "resolved":
        try:
            offer_ref = await resolve_listing_supplier(listing, organization_id=org_id)
            listing = await apply_supplier_mapping(db, listing, offer_ref)
            supplier_mapping = (listing.get("supplier_mapping") or {})
        except AppError:
            raise

    currency = listing.get("currency") or "TRY"
    if currency != "TRY":
        raise AppError(422, "UNSUPPORTED_CURRENCY", "UNSUPPORTED_CURRENCY")

    base_price = listing.get("base_price")
    if isinstance(base_price, Decimal128):
        base_amount_dec = base_price.to_decimal()
    else:
        base_amount_dec = Decimal(str(base_price or "0"))

    # Pricing with tenant_id = buyer_tenant_id and supplier="marketplace"
    pricing_result = await calculate_price(
        db,
        base_amount=base_amount_dec,
        organization_id=org_id,
        currency=currency,
        tenant_id=buyer_tenant_id,
        supplier="marketplace",
    )

    # Compose booking document
    now = now_utc()
    customer_email = payload.customer.email.lower()

    seller_tenant_id = listing["tenant_id"]

    # Supplier mapping from listing (if resolved)
    offer_ref_supplier = supplier_mapping.get("supplier")
    offer_ref_supplier_id = supplier_mapping.get("offer_id")

    booking_doc: Dict[str, Any] = {
        "organization_id": org_id,
        "state": "draft",
        "source": "b2b_marketplace",
        "currency": currency,
        "amount": Decimal128(str(pricing_result["final_amount"])),
        "customer_email": customer_email,
        "customer_name": payload.customer.full_name,
        "customer_phone": payload.customer.phone,
        "offer_ref": {
            "source": "marketplace",
            "listing_id": payload.listing_id,
            "seller_tenant_id": seller_tenant_id,
            "buyer_tenant_id": buyer_tenant_id,
            "supplier": offer_ref_supplier,
            "supplier_offer_id": offer_ref_supplier_id,
        },
        "pricing": {
            "base_amount": str(pricing_result["base_amount"]),
            "final_amount": str(pricing_result["final_amount"]),
            "commission_amount": str(pricing_result["commission_amount"]),
            "margin_amount": str(pricing_result["margin_amount"]),
            "currency": currency,
            "applied_rules": pricing_result["applied_rules"],
            "calculated_at": now,
        },
        "pricing_audit_emitted": False,
        "created_at": now,
        "updated_at": now,
    }

    res = await db.bookings.insert_one(booking_doc)
    booking_id = str(res.inserted_id)

    actor = {"actor_type": "user", "email": user.get("email"), "roles": user.get("roles")}

    await write_audit_log(
        db,
        organization_id=org_id,
        actor=actor,
        request=request,
        action="B2B_BOOKING_CREATED",
        target_type="booking",
        target_id=booking_id,
        before=None,
        after=booking_doc,
        meta={
            "source": "marketplace",
            "listing_id": payload.listing_id,
            "buyer_tenant_id": buyer_tenant_id,
            "seller_tenant_id": seller_tenant_id,
        },
    )

    await emit_pricing_audit_if_needed(
        db,
        booking_id=booking_id,
        tenant_id=buyer_tenant_id,
        organization_id=org_id,
        actor=actor,
        request=request,
    )

    return B2BMarketplaceBookingCreateResponse(booking_id=booking_id, state="draft")
