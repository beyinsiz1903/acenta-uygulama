from __future__ import annotations

from datetime import datetime, timedelta, timezone

from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import uuid4

from bson.decimal128 import Decimal128
from fastapi import APIRouter, HTTPException, Query, Request, status
from pydantic import BaseModel, EmailStr

from app.db import get_db
from app.services.suppliers.mock_supplier_service import search_mock_offers
from app.utils import now_utc
from app.services.pricing_service import calculate_price

router = APIRouter(prefix="/storefront", tags=["storefront"])


class StorefrontCustomerIn(BaseModel):
    full_name: str
    email: EmailStr
    phone: str


class StorefrontBookingCreateIn(BaseModel):
    search_id: str
    offer_id: str
    customer: StorefrontCustomerIn


def _tenant_context(request: Request) -> Dict[str, Optional[str]]:
    return {
        "tenant_id": getattr(request.state, "tenant_id", None),
        "tenant_org_id": getattr(request.state, "tenant_org_id", None),
        "tenant_key": getattr(request.state, "tenant_key", None),
    }


def _decimal_to_str(value: Decimal) -> str:
    # Normalize to string with no scientific notation
    return format(value, "f")


@router.get("/health")
async def storefront_health(request: Request) -> Dict[str, Any]:
    """Simple health endpoint that requires a resolved tenant."""

    ctx = _tenant_context(request)
    if not ctx["tenant_id"]:
        # Should normally be handled by middleware, but keep an explicit guard
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="TENANT_NOT_FOUND")

    return {"ok": True, "tenant_key": ctx["tenant_key"], "tenant_id": ctx["tenant_id"]}


@router.get("/search")
async def storefront_search(
    request: Request,
    check_in: Optional[str] = Query(None),
    check_out: Optional[str] = Query(None),
    guests: Optional[int] = Query(2),
    city: Optional[str] = Query("IST"),
) -> Dict[str, Any]:
    """Search offers using mock supplier and snapshot results into a session."""

    ctx = _tenant_context(request)
    tenant_id = ctx["tenant_id"]
    if not tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="TENANT_NOT_FOUND")

    # Build a tolerant payload for mock supplier
    payload: Dict[str, Any] = {
        "check_in": check_in or "2026-02-10",
        "check_out": check_out or "2026-02-12",
        "guests": guests or 2,
        "city": city or "IST",
    }

    offers_response = await search_mock_offers(payload)

    currency = offers_response.get("currency") or "TRY"
    if currency != "TRY":
        from app.errors import AppError

        raise AppError(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            code="UNSUPPORTED_CURRENCY",
            message="Only TRY is supported in storefront v1.",
        )

    items = offers_response.get("items") or []
    offers_snapshot: List[Dict[str, Any]] = []
    for item in items:
        offer_id = str(item.get("offer_id"))
        total_price = Decimal(str(item.get("total_price") or "0"))

        raw_ref = {
            "supplier": "mock_v1",
            "offer_id": offer_id,
            "check_in": payload["check_in"],
            "check_out": payload["check_out"],
            # For mock_v1 flow we still pass guests/city for compatibility
            "guests": payload["guests"],
            "city": payload["city"],
        }

        offers_snapshot.append(
            {
                "offer_id": offer_id,
                "supplier": "mock",
                "currency": "TRY",
                "total_amount": Decimal128(str(total_price)),
                "raw_ref": raw_ref,
            }
        )

    db = await get_db()

    search_id = str(uuid4())
    now = now_utc()
    expires_at = now + timedelta(minutes=30)

    await db.storefront_sessions.insert_one(
        {
            "tenant_id": tenant_id,
            "search_id": search_id,
            "offers_snapshot": offers_snapshot,
            "expires_at": expires_at,
            "created_at": now,
        }
    )

    return {
        "search_id": search_id,
        "expires_at": expires_at.isoformat(),
        "offers": [
            {
                "offer_id": o["offer_id"],
                "supplier": o["supplier"],
                "currency": o["currency"],
                "total_amount": _decimal_to_str(Decimal(str(o["total_amount"].to_decimal()))),
            }
            for o in offers_snapshot
        ],
    }


async def _load_session_or_expired(request: Request, search_id: str) -> Dict[str, Any]:
    ctx = _tenant_context(request)
    tenant_id = ctx["tenant_id"]
    if not tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="TENANT_NOT_FOUND")

    db = await get_db()
    session = await db.storefront_sessions.find_one({"tenant_id": tenant_id, "search_id": search_id})
    if not session:
        from app.errors import AppError

        raise AppError(
            status_code=status.HTTP_410_GONE,
            code="SESSION_EXPIRED",
            message="Storefront session expired or not found.",
        )

    now = now_utc()
    expires_at: datetime = session.get("expires_at")
    if expires_at:
        # Normalize to naive UTC if stored as aware, to avoid comparison issues
        if expires_at.tzinfo is not None:
            expires_at = expires_at.astimezone(timezone.utc).replace(tzinfo=None)
        now_naive = now.replace(tzinfo=None)
        if expires_at < now_naive:
            # Optional cleanup
            await db.storefront_sessions.delete_one({"_id": session["_id"]})
            from app.errors import AppError

            raise AppError(
                status_code=status.HTTP_410_GONE,
                code="SESSION_EXPIRED",
                message="Storefront session expired.",
            )

    return session


@router.get("/offers/{offer_id}")
async def get_storefront_offer(
    offer_id: str,
    request: Request,
    search_id: str = Query(...),
) -> Dict[str, Any]:
    """Return offer details from a storefront session snapshot."""

    session = await _load_session_or_expired(request, search_id)
    offers: List[Dict[str, Any]] = session.get("offers_snapshot") or []
    match = next((o for o in offers if str(o.get("offer_id")) == offer_id), None)
    if not match:
        from app.errors import AppError

        raise AppError(
            status_code=status.HTTP_404_NOT_FOUND,
            code="OFFER_NOT_FOUND",
            message="Offer not found in storefront session.",
        )

    total_amount_dec = Decimal(str(match["total_amount"].to_decimal()))

    return {
        "offer_id": match["offer_id"],
        "supplier": match["supplier"],
        "currency": match["currency"],
        "total_amount": _decimal_to_str(total_amount_dec),
    }


@router.post("/bookings", status_code=status.HTTP_201_CREATED)
async def create_storefront_booking(payload: StorefrontBookingCreateIn, request: Request) -> Dict[str, Any]:
    """Create a draft booking from a storefront session offer.

    - Requires resolved tenant
    - Uses internal booking draft flow (state=draft)
    - Upserts a storefront customer per (tenant_id, email)
    """

    ctx = _tenant_context(request)
    tenant_id = ctx["tenant_id"]
    tenant_org_id = ctx["tenant_org_id"]
    if not tenant_id or not tenant_org_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="TENANT_NOT_FOUND")

    session = await _load_session_or_expired(request, payload.search_id)
    offers: List[Dict[str, Any]] = session.get("offers_snapshot") or []
    match = next((o for o in offers if str(o.get("offer_id")) == payload.offer_id), None)
    if not match:
        from app.errors import AppError

        raise AppError(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            code="INVALID_OFFER",
            message="Offer not found in storefront session.",
        )

    db = await get_db()

    # Upsert customer
    now = now_utc()
    email_lc = payload.customer.email.lower()
    customer = await db.storefront_customers.find_one_and_update(
        {"tenant_id": tenant_id, "email": email_lc},
        {
            "$setOnInsert": {
                "tenant_id": tenant_id,
                "email": email_lc,
                "phone": payload.customer.phone,
                "full_name": payload.customer.full_name,
                "created_at": now,
            }
        },
        upsert=True,
        return_document=True,
    )

    # Create draft booking using internal booking service
    from app.services.booking_service import create_booking_draft

    actor = {
        "actor_type": "storefront",
        "actor_id": str(customer["_id"]),
        "email": email_lc,
        "roles": ["storefront"],
    }

    total_amount_dec = Decimal(str(match["total_amount"].to_decimal()))

    # Apply pricing engine v1
    pricing = await calculate_price(
        db,
        base_amount=total_amount_dec,
        organization_id=tenant_org_id,
        currency="TRY",
        tenant_id=tenant_id,
        agency_id=None,
        supplier=str(match.get("supplier")),
        now=now,
    )

    draft_payload: Dict[str, Any] = {
        # Store original base amount as string for legacy fields
        "amount": str(pricing["base_amount"]),
        "currency": "TRY",
        "offer_ref": {
            "search_id": payload.search_id,
            "offer_id": payload.offer_id,
            "supplier": match.get("supplier"),
        },
        "customer_email": email_lc,
        "customer_name": payload.customer.full_name,
        "pricing": {
            "base_amount": str(pricing["base_amount"]),
            "final_amount": str(pricing["final_amount"]),
            "commission_amount": str(pricing["commission_amount"]),
            "margin_amount": str(pricing["margin_amount"]),
            "currency": "TRY",
            "applied_rules": pricing["applied_rules"],
            "calculated_at": now,
        },
    }

    # organization_id is always taken from tenant context, never from payload
    booking_id = await create_booking_draft(db, tenant_org_id, actor, draft_payload, request)

    # Emit storefront specific audit
    from app.services.audit import write_audit_log

    await write_audit_log(
        db,
        organization_id=tenant_org_id,
        actor=actor,
        request=request,
        action="STOREFRONT_BOOKING_CREATED",
        target_type="booking",
        target_id=booking_id,
        before=None,
        after=None,
        meta={
            "tenant_id": tenant_id,
            "customer_id": str(customer["_id"]),
            "search_id": payload.search_id,
            "offer_id": payload.offer_id,
        },
    )

    # Pricing audit: idempotent emission based on booking flag
    from app.services.pricing_audit_service import emit_pricing_audit_if_needed

    await emit_pricing_audit_if_needed(db, booking_id, ctx["tenant_key"], tenant_org_id, actor, request)


    return {"booking_id": booking_id, "state": "draft"}
