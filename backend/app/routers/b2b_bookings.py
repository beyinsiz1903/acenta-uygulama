from __future__ import annotations

from fastapi import APIRouter, Depends, Header, Request
from fastapi.responses import JSONResponse

from app.auth import get_current_user, require_roles
from app.db import get_db
from app.errors import AppError
from app.repos_idempotency import IdempotencyRepo
from app.schemas_b2b_bookings import BookingCreateRequest, BookingCreateResponse, B2BMarketplaceBookingCreateRequest, B2BMarketplaceBookingCreateResponse
from app.services.b2b_pricing import B2BPricingService
from app.services.b2b_booking import B2BBookingService
from app.services.booking_lifecycle import BookingLifecycleService
from app.services.booking_financials import BookingFinancialsService
from app.services.funnel_events import log_funnel_event
from app.utils import get_or_create_correlation_id, now_utc, serialize_doc
from app.services.pricing_service import calculate_price
from app.services.pricing_audit_service import emit_pricing_audit_if_needed
from app.services.audit import write_audit_log
from app.services.supplier_mapping_service import resolve_listing_supplier, apply_supplier_mapping
from app.services.credit_exposure_service import has_available_credit
from app.services.suppliers.registry import registry as supplier_registry
from app.services.suppliers.contracts import SupplierContext, ConfirmStatus, SupplierAdapterError, run_with_deadline
from app.services.suppliers.redaction import redact_sensitive_fields
from bson import Decimal128, ObjectId
from decimal import Decimal
from pydantic import BaseModel, EmailStr
from typing import Any, Dict, Optional

router = APIRouter(prefix="/api/b2b", tags=["b2b-bookings"])


def get_pricing_service(db=Depends(get_db)) -> B2BPricingService:
    return B2BPricingService(db)


def get_booking_service(db=Depends(get_db)) -> B2BBookingService:
    return B2BBookingService(db)


def get_idem_repo(db=Depends(get_db)) -> IdempotencyRepo:
    return IdempotencyRepo(db)


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

        pricing = await calculate_price(
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
            "amount": float(pricing["final_amount"]),
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
                "base_amount": str(pricing["base_amount"]),
                "final_amount": str(pricing["final_amount"]),
                "commission_amount": str(pricing["commission_amount"]),
                "margin_amount": str(pricing["margin_amount"]),
                "currency": currency,
                "applied_rules": pricing["applied_rules"],
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
    pricing = await calculate_price(
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
        "amount": Decimal128(str(pricing["final_amount"])),
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
            "base_amount": str(pricing["base_amount"]),
            "final_amount": str(pricing["final_amount"]),
            "commission_amount": str(pricing["commission_amount"]),
            "margin_amount": str(pricing["margin_amount"]),
            "currency": currency,
            "applied_rules": pricing["applied_rules"],
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





@router.post(
    "/bookings/{booking_id}/confirm",
    dependencies=[Depends(require_roles(["agency_agent", "agency_admin", "super_admin"]))],
)
async def confirm_b2b_booking(
    booking_id: str,
    request: Request,
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    """Confirm a draft B2B booking via supplier fulfilment (v1).

    Behaviour:
    - 404 BOOKING_NOT_FOUND if booking does not exist
    - If booking.status == CONFIRMED -> 200 idempotent response
    - If booking.status is anything else than PENDING (legacy) -> 422 BOOKING_NOT_CONFIRMABLE
    - For marketplace bookings (source == b2b_marketplace):
      - Requires tenant context (X-Tenant-Key)
      - buyer_tenant_id in offer_ref must match request.state.tenant_id
    - Requires offer_ref.supplier and offer_ref.supplier_offer_id; otherwise
      422 INVALID_SUPPLIER_MAPPING
    - On successful supplier fulfilment, appends BOOKING_CONFIRMED lifecycle
      event and emits B2B_BOOKING_CONFIRMED audit log.
    """

    from bson import ObjectId
    from uuid import uuid4

    org_id = user.get("organization_id")
    # agency_id is optional for v1; fall back to booking.agency_id if present

    try:
        oid = ObjectId(booking_id)
    except Exception:
        raise AppError(404, "BOOKING_NOT_FOUND", "BOOKING_NOT_FOUND")

    booking = await db.bookings.find_one({"_id": oid, "organization_id": org_id})
    if not booking:
        raise AppError(404, "BOOKING_NOT_FOUND", "BOOKING_NOT_FOUND")

    status_val = booking.get("status")
    if status_val == "CONFIRMED":
        # Idempotent confirm when projection is already CONFIRMED.
        # Ensure at least one BOOKING_CONFIRMED lifecycle event + audit exists,
        # but do not create duplicates on repeated calls.
        existing_event = await db.booking_events.find_one(
            {"organization_id": org_id, "booking_id": booking_id, "event": "BOOKING_CONFIRMED"}
        )
        existing_audit = await db.audit_logs.find_one(
            {
                "organization_id": org_id,
                "action": "B2B_BOOKING_CONFIRMED",
                "target.id": booking_id,
            }
        )
        if not existing_event or not existing_audit:
            from uuid import uuid4
            from app.services.booking_lifecycle import BookingLifecycleService

            attempt_id = str(uuid4())
            source = booking.get("source")
            offer_ref = (booking.get("offer_ref") or {})
            supplier_name = (offer_ref.get("supplier") or "").strip()
            supplier_offer_id = (offer_ref.get("supplier_offer_id") or "").strip()

            lifecycle = BookingLifecycleService(db)
            await lifecycle.append_event(
                organization_id=org_id,
                agency_id=booking.get("agency_id") or "",
                booking_id=booking_id,
                event="BOOKING_CONFIRMED",
                request_id=attempt_id,
                before={"status": status_val},
                after={"status": "CONFIRMED"},
                meta={
                    "source": source,
                    "supplier": supplier_name,
                    "supplier_offer_id": supplier_offer_id,
                },
            )

            actor = {"actor_type": "user", "email": user.get("email"), "roles": user.get("roles")}
            meta = {
                "source": "supplier_fulfilment",
                "supplier": supplier_name,
                "supplier_offer_id": supplier_offer_id,
                "tenant_id": offer_ref.get("buyer_tenant_id"),
                "attempt_id": attempt_id,
            }
            await write_audit_log(
                db,
                organization_id=org_id,
                actor=actor,
                request=request,
                action="B2B_BOOKING_CONFIRMED",
                target_type="booking",
                target_id=booking_id,
                before=None,
                after=None,
                meta=meta,
            )

        return {"booking_id": booking_id, "state": "confirmed"}

    if status_val not in {None, "PENDING"}:
        raise AppError(
            422,
            "BOOKING_NOT_CONFIRMABLE",
            "Booking is not in a confirmable state",
            details={"reason": "invalid_state", "status": status_val},
        )

    source = booking.get("source")
    offer_ref = (booking.get("offer_ref") or {})

    # Tenant context guard for marketplace
    if source == "b2b_marketplace":
        buyer_tenant_id = offer_ref.get("buyer_tenant_id")
        req_tenant_id = getattr(request.state, "tenant_id", None)
        if not req_tenant_id:
            raise AppError(403, "TENANT_CONTEXT_REQUIRED", "TENANT_CONTEXT_REQUIRED")
        if buyer_tenant_id and req_tenant_id != buyer_tenant_id:
            raise AppError(
                422,
                "BOOKING_NOT_CONFIRMABLE",
                "Booking tenant does not match current tenant context",
                details={"reason": "invalid_state"},
            )

    # Credit limit / exposure guard
    amount = float(booking.get("amount") or 0.0)
    if amount > 0:
        has_credit = await has_available_credit(db, organization_id=org_id, amount=amount)
        if not has_credit:
            raise AppError(
                409,
                "credit_limit_exceeded",
                "Credit limit exceeded for this organization.",
                details={"amount": amount},
            )

    # Risk engine (PR-19): evaluate booking risk before supplier fulfilment
    from app.services.risk.engine import evaluate_booking_risk, RiskDecision

    risk_result = await evaluate_booking_risk(db, organization_id=org_id, booking=booking)

    # Always emit RISK_EVALUATED audit
    actor = {"actor_type": "user", "email": user.get("email"), "roles": user.get("roles")}
    buyer_tenant_id = (booking.get("offer_ref") or {}).get("buyer_tenant_id")
    await write_audit_log(
        db,
        organization_id=org_id,
        actor=actor,
        request=request,
        action="RISK_EVALUATED",
        target_type="booking",
        target_id=booking_id,
        before=None,
        after=None,
        meta={
            "booking_id": booking_id,
            "organization_id": org_id,
            "buyer_tenant_id": buyer_tenant_id,
            "amount": amount,
            "score": float(risk_result.score),
            "decision": risk_result.decision.value,
            "reasons": list(risk_result.reasons),
            "model_version": risk_result.model_version,
        },
    )

    # Persist risk snapshot on booking for non-allow decisions
    risk_snapshot = {
        "score": float(risk_result.score),
        "decision": risk_result.decision.value,
        "reasons": list(risk_result.reasons),
        "model_version": risk_result.model_version,
    }

    if risk_result.decision is RiskDecision.BLOCK:
        # Store risk info but do not change booking state
        await db.bookings.update_one(
            {"_id": oid, "organization_id": org_id},
            {"$set": {"risk": risk_snapshot, "updated_at": now_utc()}},
        )

        await write_audit_log(
            db,
            organization_id=org_id,
            actor=actor,
            request=request,
            action="RISK_BLOCKED",
            target_type="booking",
            target_id=booking_id,
            before=None,
            after=None,
            meta={
                "booking_id": booking_id,
                "score": float(risk_result.score),
                "decision": "block",
            },
        )

        raise AppError(
            409,
            "risk_blocked",
            "Booking confirmation blocked by risk engine.",
            details={"score": float(risk_result.score), "decision": "block"},
        )

    if risk_result.decision is RiskDecision.REVIEW:
        # Set booking.status to RISK_REVIEW and persist risk snapshot
        await db.bookings.update_one(
            {"_id": oid, "organization_id": org_id},
            {"$set": {"status": "RISK_REVIEW", "risk": risk_snapshot, "updated_at": now_utc()}},
        )

        await write_audit_log(
            db,
            organization_id=org_id,
            actor=actor,
            request=request,
            action="RISK_REVIEW_REQUIRED",
            target_type="booking",
            target_id=booking_id,
            before=None,
            after=None,
            meta={
                "booking_id": booking_id,
                "score": float(risk_result.score),
                "decision": "review",
            },
        )

        # 202 with standard error envelope
        raise AppError(
            202,
            "risk_review_required",
            "Booking requires manual risk review.",
            details={"score": float(risk_result.score), "decision": "review"},
        )

    # Supplier resolution
    supplier_name = (offer_ref.get("supplier") or "").strip()
    supplier_offer_id = (offer_ref.get("supplier_offer_id") or "").strip()

    # Fallback: use booking.supplier.code if present
    supplier_doc = booking.get("supplier") or {}
    if not supplier_name:
        supplier_name = (supplier_doc.get("code") or "").strip()
        supplier_offer_id = supplier_offer_id or (supplier_doc.get("offer_id") or "").strip()

    # TODO v2: if still missing, try supplier_mapping via listing_id

    if not supplier_name:
        raise AppError(
            422,
            "INVALID_SUPPLIER_MAPPING",
            "Missing supplier on offer_ref for fulfilment",
            details={"reason": "missing_supplier"},
        )

    # Resolve adapter via registry (with alias support)
    try:
        adapter = supplier_registry.get(supplier_name)
    except SupplierAdapterError as exc:
        # adapter_not_found and similar registry-level errors
        raise AppError(
            502,
            "adapter_not_found",
            f"No supplier adapter registered for '{supplier_name}'.",
            details={"supplier_code": supplier_name, "adapter_error": exc.code},
        )

    attempt_id = str(uuid4())
    ctx = SupplierContext(
        request_id=attempt_id,
        organization_id=org_id,
        tenant_id=getattr(request.state, "tenant_id", None),
        user_id=str(user.get("id") or ""),
    )

    result = None
    try:
        result = await run_with_deadline(adapter.confirm_booking(ctx, booking), ctx)
    except SupplierAdapterError as exc:
        # Map adapter-level errors to HTTP responses and audit
        retryable = getattr(exc, "retryable", False)
        details = getattr(exc, "details", {})

        # Audit supplier confirm failure
        actor = {"actor_type": "user", "email": user.get("email"), "roles": user.get("roles")}
        await write_audit_log(
            db,
            organization_id=org_id,
            actor=actor,
            request=request,
            action="SUPPLIER_CONFIRM_FAILED",
            target_type="booking",
            target_id=booking_id,
            before=None,
            after=None,
            meta={
                "supplier": supplier_name,
                "supplier_code_canonical": supplier_doc.get("code") or supplier_name,
                "supplier_code_legacy": supplier_name,
                "retryable": retryable,
                "timeout_ms": ctx.timeout_ms,
                "error_code": exc.code,
            },
        )

        raise AppError(
            502 if retryable else 409,
            exc.code,
            exc.message,
            details={"retryable": retryable, **details},
        )

    # Map ConfirmStatus to HTTP / state transitions
    if result.status is ConfirmStatus.CONFIRMED:
        supplier_booking_id = result.supplier_booking_id
        update_fields: dict[str, Any] = {"updated_at": now_utc()}
        if supplier_booking_id:
            update_fields["offer_ref.supplier_booking_id"] = supplier_booking_id

        # Persist normalized supplier snapshot (with redacted confirm snapshot)
        update_fields["supplier.code"] = result.supplier_code
        update_fields["supplier.offer_id"] = supplier_offer_id
        update_fields["supplier.booking_id"] = supplier_booking_id
        update_fields["supplier.confirm_snapshot"] = redact_sensitive_fields(result.raw or {})

        await db.bookings.update_one(
            {"_id": oid, "organization_id": org_id},
            {"$set": update_fields},
        )

        # Append lifecycle BOOKING_CONFIRMED event
        from app.services.booking_lifecycle import BookingLifecycleService

        lifecycle = BookingLifecycleService(db)
        await lifecycle.append_event(
            organization_id=org_id,
            agency_id=booking.get("agency_id") or "",
            booking_id=booking_id,
            event="BOOKING_CONFIRMED",
            request_id=attempt_id,
            before={"status": status_val or "PENDING"},
            after={"status": "CONFIRMED"},
            meta={
                "source": source,
                # Preserve legacy supplier name in events for compatibility
                "supplier": supplier_name,
                "supplier_offer_id": supplier_offer_id,
                "supplier_code_canonical": result.supplier_code,
                "supplier_code_legacy": supplier_name,
                "timeout_ms": ctx.timeout_ms,
            },
        )

        # Audit log for B2B booking confirmation
        actor = {"actor_type": "user", "email": user.get("email"), "roles": user.get("roles")}
        meta = {
            "source": "supplier_fulfilment",
            # Preserve legacy supplier name in audit for compatibility
            "supplier": supplier_name,
            "supplier_offer_id": supplier_offer_id,
            "tenant_id": offer_ref.get("buyer_tenant_id"),
            "attempt_id": attempt_id,
            "supplier_code_canonical": result.supplier_code,
            "supplier_code_legacy": supplier_name,
            "retryable": False,
            "timeout_ms": ctx.timeout_ms,
        }
        if supplier_booking_id:
            meta["supplier_booking_id"] = supplier_booking_id

        await write_audit_log(
            db,
            organization_id=org_id,
            actor=actor,
            request=request,
            action="B2B_BOOKING_CONFIRMED",
            target_type="booking",
            target_id=booking_id,
            before=None,
            after=None,
            meta=meta,
        )

        return {"booking_id": booking_id, "state": "confirmed"}

    if result.status is ConfirmStatus.REJECTED:
        actor = {"actor_type": "user", "email": user.get("email"), "roles": user.get("roles")}
        await write_audit_log(
            db,
            organization_id=org_id,
            actor=actor,
            request=request,
            action="SUPPLIER_CONFIRM_ATTEMPT",
            target_type="booking",
            target_id=booking_id,
            before=None,
            after=None,
            meta={
                "status": "rejected",
                "supplier": supplier_name,
                "supplier_code_canonical": result.supplier_code,
                "supplier_code_legacy": supplier_name,
                "retryable": False,
                "timeout_ms": ctx.timeout_ms,
                "raw": redact_sensitive_fields(result.raw or {}),
            },
        )
        raise AppError(
            409,
            "supplier_rejected",
            "Supplier rejected booking confirm.",
            details={"supplier": supplier_name},
        )

    if result.status is ConfirmStatus.PENDING:
        actor = {"actor_type": "user", "email": user.get("email"), "roles": user.get("roles")}
        await write_audit_log(
            db,
            organization_id=org_id,
            actor=actor,
            request=request,
            action="SUPPLIER_CONFIRM_ATTEMPT",
            target_type="booking",
            target_id=booking_id,
            before=None,
            after=None,
            meta={
                "status": "pending",
                "supplier": supplier_name,
                "supplier_code_canonical": result.supplier_code,
                "supplier_code_legacy": supplier_name,
                "retryable": False,
                "timeout_ms": ctx.timeout_ms,
                "raw": redact_sensitive_fields(result.raw or {}),
            },
        )
        return AppError(
            202,
            "supplier_pending",
            "Supplier confirm is pending.",
            details={"supplier": supplier_name},
        ).to_dict()

    if result.status is ConfirmStatus.NOT_SUPPORTED:
        actor = {"actor_type": "user", "email": user.get("email"), "roles": user.get("roles")}
        await write_audit_log(
            db,
            organization_id=org_id,
            actor=actor,
            request=request,
            action="SUPPLIER_CONFIRM_ATTEMPT",
            target_type="booking",
            target_id=booking_id,
            before=None,
            after=None,
            meta={
                "status": "not_supported",
                "supplier": supplier_name,
                "supplier_code_canonical": result.supplier_code,
                "supplier_code_legacy": supplier_name,
                "retryable": False,
                "timeout_ms": ctx.timeout_ms,
                "raw": redact_sensitive_fields(result.raw or {}),
            },
        )
        raise AppError(
            501,
            "supplier_not_supported",
            "Supplier confirm is not supported.",
            details={"supplier": supplier_name},
        )

    # Fallback for unknown statuses
    raise AppError(
        500,
        "SUPPLIER_FULFILMENT_FAILED",
        "Unexpected supplier confirm status.",
        details={"supplier": supplier_name, "status": result.status},
    )

@router.post("/bookings/{booking_id}/refund-requests")
async def create_refund_request(
    booking_id: str,
    payload: dict,
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    """Agency-initiated refund request for a booking.

    - Does not change booking status.
    - Creates a refund_case with computed amounts.
    """
    org_id = user.get("organization_id")
    agency_id = user.get("agency_id")
    if not agency_id:
        raise AppError(
            status_code=403,
            code="forbidden",
            message="User is not bound to an agency",
        )

    requested_amount = payload.get("amount")
    requested_message = payload.get("message")
    reason = payload.get("reason", "customer_request")

    from app.services.refund_cases import RefundCaseService

    svc = RefundCaseService(db)
    case = await svc.create_refund_request(
        organization_id=org_id,
        booking_id=booking_id,
        agency_id=agency_id,
        requested_amount=requested_amount,
        requested_message=requested_message,
        reason=reason,
        created_by=user.get("email"),
    )
    return case



@router.post(
    "/bookings/{booking_id}/cancel",
    dependencies=[Depends(require_roles(["agency_agent", "agency_admin"]))],
)
async def cancel_b2b_booking(
    booking_id: str,
    payload: dict | None = None,
    user=Depends(get_current_user),
    db=Depends(get_db),
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
):
    """Cancel a CONFIRMED booking (after-sales v1).

    - Idempotent: if booking is already CANCELLED, returns current state.
    - Creates BOOKING_CANCELLED ledger posting as exact reversal of
      BOOKING_CONFIRMED in EUR.
    """
    org_id = user.get("organization_id")
    agency_id = user.get("agency_id")
    if not agency_id:
        raise AppError(403, "forbidden", "User is not bound to an agency")

    from bson import ObjectId

    try:
        oid = ObjectId(booking_id)
    except Exception:
        raise AppError(404, "booking_not_found", "Booking not found", {"booking_id": booking_id})

    booking = await db.bookings.find_one(
        {"_id": oid, "organization_id": org_id, "agency_id": agency_id}
    )
    if not booking:
        raise AppError(404, "booking_not_found", "Booking not found", {"booking_id": booking_id})

    from app.utils import now_utc

    lifecycle = BookingLifecycleService(db)
    decision = await lifecycle.assert_can_cancel(booking)
    if decision == "already_cancelled":
        # Idempotent behaviour: return current state
        return {
            "booking_id": booking_id,
            "status": booking.get("status"),
            "refund_status": "COMPLETED",
        }

    reason = (payload or {}).get("reason", "customer_request")

    now = now_utc()

    # Post BOOKING_CANCELLED event to ledger
    from app.services.booking_finance import BookingFinanceService

    bfs = BookingFinanceService(db)
    await bfs.post_booking_cancelled(
        organization_id=org_id,
        booking_id=booking_id,
        agency_id=agency_id,
        occurred_at=now,
    )

    # Ensure booking_financials snapshot exists and mirrors latest booking totals
    # so that refund / penalty calculations and ops views are consistent.
    booking_after = await db.bookings.find_one({"_id": ObjectId(booking_id), "organization_id": org_id})
    if booking_after:
        bf_service = BookingFinancialsService(db)
        await bf_service.ensure_financials(org_id, booking_after)

    # Update booking_financials refunded_total / penalty_total using current values
    bf = await db.booking_financials.find_one(
        {"organization_id": org_id, "booking_id": booking_id}
    )

    meta = {
        "reason": reason,
        "refund_eur": float(bf.get("refunded_total", 0.0)) if bf else None,
        "penalty_eur": float(bf.get("penalty_total", 0.0)) if bf else None,
    }
    await lifecycle.append_event(
        organization_id=org_id,
        agency_id=agency_id,
        booking_id=booking_id,
        event="BOOKING_CANCELLED",
        occurred_at=now,
        request_id=idempotency_key,
        before={"status": "CONFIRMED"},
        after={"status": "CANCELLED"},
        meta=meta,
    )

    resp = {
        "booking_id": booking_id,
        "status": "CANCELLED",
        "refund_status": "COMPLETED",
    }
    if meta["refund_eur"] is not None:
        resp["refund_eur"] = meta["refund_eur"]
    if meta["penalty_eur"] is not None:
        resp["penalty_eur"] = meta["penalty_eur"]

    return resp



@router.post(
    "/bookings/{booking_id}/amend/quote",
    dependencies=[Depends(require_roles(["agency_agent", "agency_admin"]))],
)
async def amend_booking_quote(
    booking_id: str,
    payload: dict,
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    """Generate a pricing proposal for a booking date change.

    - Idempotent per (organization_id, booking_id, request_id).
    - Does NOT change booking or financials.
    """
    org_id = user.get("organization_id")
    agency_id = user.get("agency_id")
    if not agency_id:
        raise AppError(403, "forbidden", "User is not bound to an agency")

    from datetime import date
    from app.schemas.booking_amendments import BookingAmendQuoteRequest
    from app.services.booking_amendments import BookingAmendmentsService

    try:
        req = BookingAmendQuoteRequest(
            check_in=date.fromisoformat(str(payload.get("check_in"))),
            check_out=date.fromisoformat(str(payload.get("check_out"))),
            request_id=str(payload.get("request_id")),
        )
    except Exception as e:
        raise AppError(422, "validation_error", f"Invalid amend quote payload: {e}")

    svc = BookingAmendmentsService(db)
    doc = await svc.create_quote(
        organization_id=org_id,
        agency_id=agency_id,
        booking_id=booking_id,
        request_id=req.request_id,
        new_check_in=req.check_in,
        new_check_out=req.check_out,
        user_email=user.get("email"),
    )

    # Serialize for API (hide internal _id)
    doc_out = {
        "amend_id": str(doc.get("_id")),
        "booking_id": doc.get("booking_id"),
        "status": doc.get("status"),
        "before": doc.get("before"),
        "after": doc.get("after"),
        "delta": doc.get("delta"),
    }
    return doc_out


@router.post(
    "/bookings/{booking_id}/amend/confirm",
    dependencies=[Depends(require_roles(["agency_agent", "agency_admin"]))],
)
async def amend_booking_confirm(
    booking_id: str,
    payload: dict,
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    """Confirm a previously proposed booking amendment.

    - Idempotent per amend_id: repeated calls do not duplicate ledger postings.
    - Updates booking dates and financial mirrors, posts delta-only ledger event.
    """
    org_id = user.get("organization_id")
    agency_id = user.get("agency_id")
    if not agency_id:
        raise AppError(403, "forbidden", "User is not bound to an agency")

    amend_id = str(payload.get("amend_id") or "").strip()
    if not amend_id:
        raise AppError(422, "validation_error", "amend_id is required for confirm")

    from app.services.booking_amendments import BookingAmendmentsService

    svc = BookingAmendmentsService(db)
    doc = await svc.confirm_amendment(
        organization_id=org_id,
        agency_id=agency_id,
        booking_id=booking_id,
        amend_id=amend_id,
        user_email=user.get("email"),
    )

    doc_out = {
        "amend_id": str(doc.get("_id")),
        "booking_id": doc.get("booking_id"),
        "status": doc.get("status"),
        "before": doc.get("before"),
        "after": doc.get("after"),
        "delta": doc.get("delta"),
    }
    return doc_out


@router.get(
    "/bookings/{booking_id}/events",
    dependencies=[Depends(require_roles(["agency_agent", "agency_admin"]))],
)
async def get_booking_events(
    booking_id: str,
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    """Return booking lifecycle events (timeline) for debugging/ops.

    - Owner-guarded: only same organization/agency can see events.
    - Events ordered by occurred_at desc.
    """
    org_id = user.get("organization_id")
    agency_id = user.get("agency_id")
    if not agency_id:
        raise AppError(403, "forbidden", "User is not bound to an agency")

    from bson import ObjectId

    try:
        oid = ObjectId(booking_id)
    except Exception:
        raise AppError(404, "booking_not_found", "Booking not found", {"booking_id": booking_id})

    booking = await db.bookings.find_one(
        {"_id": oid, "organization_id": org_id, "agency_id": agency_id},
        {"_id": 0, "organization_id": 1, "agency_id": 1},
    )
    if not booking:
        raise AppError(404, "booking_not_found", "Booking not found", {"booking_id": booking_id})

    cursor = db.booking_events.find(
        {"organization_id": org_id, "booking_id": booking_id, "event": {"$exists": True}}
    ).sort("occurred_at", -1)
    events = []
    async for ev in cursor:
        ev.pop("_id", None)
        events.append(
            {
                "event": ev.get("event"),
                "occurred_at": ev.get("occurred_at"),
                "request_id": ev.get("request_id"),
                "before": ev.get("before", {}),
                "after": ev.get("after", {}),
                "meta": ev.get("meta", {}),
                "created_by": ev.get("created_by", {}),
            }
        )

    return {"booking_id": booking_id, "events": events}
