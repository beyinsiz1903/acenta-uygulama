from __future__ import annotations

from datetime import date
from typing import Any, Optional, List

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from bson import ObjectId

from app.auth import require_roles
from app.db import get_db
from app.errors import AppError
from app.services.audit import write_audit_log
from app.services.pricing_quote_engine import compute_quote_for_booking
from app.utils import now_utc

router = APIRouter(prefix="/api/admin/b2b/pricing", tags=["admin_b2b_pricing"])


class PricingPreviewOccupancy(BaseModel):
    adults: int = Field(..., ge=1, le=10)
    children: int = Field(0, ge=0, le=10)
    rooms: int = Field(1, ge=1, le=5)


class PricingPreviewRequest(BaseModel):
    partner_id: str
    product_id: str
    checkin: date
    checkout: date
    occupancy: PricingPreviewOccupancy
    currency: Optional[str] = None
    channel_id: Optional[str] = None
    include_rules: bool = True
    include_breakdown: bool = True


class PricingRuleHit(BaseModel):
    rule_id: str
    code: Optional[str] = None
    priority: Optional[int] = None
    effect: Optional[str] = None
    scope: Optional[dict] = None
    action: Optional[dict] = None


class PricingPreviewBreakdown(BaseModel):
    nights: int
    base_price: float
    markup_percent: float
    markup_amount: float
    commission_rate: float
    commission_amount: float
    final_sell_price: float


class PricingPreviewResponse(BaseModel):
    partner_id: str
    product_id: str
    currency: str
    checkin: date
    checkout: date
    occupancy: PricingPreviewOccupancy
    breakdown: PricingPreviewBreakdown
    rule_hits: List[PricingRuleHit] = []
    notes: List[str] = []
    debug: Optional[dict[str, Any]] = None


@router.post("/preview", response_model=PricingPreviewResponse)
async def preview_pricing(
    payload: PricingPreviewRequest,
    request: Request,
    current_user=Depends(require_roles(["super_admin", "admin"])),
    db=Depends(get_db),
):
    org_id = current_user["organization_id"]

    if payload.checkout <= payload.checkin:
        raise AppError(400, "invalid_dates", "Checkout must be after checkin")

    nights = (payload.checkout - payload.checkin).days

    # Validate partner
    print(f"DEBUG: Looking for partner_id={payload.partner_id} in org_id={org_id}")
    print(f"DEBUG: db object: {db}")
    print(f"DEBUG: db.partner_profiles: {db.partner_profiles}")
    
    # Try to count all partners first
    total_partners = await db.partner_profiles.count_documents({})
    print(f"DEBUG: Total partners in collection: {total_partners}")
    
    partner = await db.partner_profiles.find_one({"_id": payload.partner_id, "organization_id": org_id})
    print(f"DEBUG: String lookup result: {partner}")
    if not partner:
        try:
            oid = ObjectId(payload.partner_id)
            print(f"DEBUG: Converted to ObjectId: {oid}")
        except Exception as e:
            print(f"DEBUG: ObjectId conversion failed: {e}")
            oid = None
        if oid is not None:
            partner = await db.partner_profiles.find_one({"_id": oid, "organization_id": org_id})
            print(f"DEBUG: ObjectId lookup result: {partner}")
    if not partner:
        print(f"DEBUG: Partner not found, raising error")
        raise AppError(404, "partner_not_found", "Partner not found")

    # Validate product
    try:
        product_oid: Any = ObjectId(payload.product_id)
    except Exception:
        product_oid = payload.product_id

    product = await db.products.find_one({"_id": product_oid, "organization_id": org_id})
    if not product:
        raise AppError(404, "product_not_found", "Product not found")

    # Determine base price (MVP fallback from product or zero)
    base_price = float(product.get("base_price") or 0.0)
    currency = (payload.currency or product.get("currency") or "EUR").upper()

    notes: List[str] = []
    debug: dict[str, Any] = {
        "product_id": str(product.get("_id")),
        "partner_id": str(partner.get("_id")),
        "nights": nights,
        "currency": currency,
        "base_price_source": None,
    }

    if base_price <= 0:
        notes.append("Base price kaynağı bulunamadı, 0 olarak varsayıldı.")
        debug["base_price_source"] = "missing"
    else:
        debug["base_price_source"] = "product.base_price"

    # Use simple pricing quote engine to resolve markup
    quote = await compute_quote_for_booking(
        db,
        organization_id=org_id,
        base_price=base_price,
        currency=currency,
        agency_id=None,
        product_id=str(product.get("_id")),
        product_type=str(product.get("type") or "hotel"),
        check_in=payload.checkin,
    )

    base_price_eff = quote["base_price"]
    markup_percent = quote["markup_percent"]
    final_sell_price = quote["final_price"]
    markup_amount = round(final_sell_price - base_price_eff, 2)

    # Commission: from b2b_product_authorizations if exists
    commission_rate = 0.0
    commission_amount = 0.0

    auth = await db.b2b_product_authorizations.find_one(
        {
            "organization_id": org_id,
            "partner_id": str(partner.get("_id")),
            "product_id": product.get("_id"),
        }
    )
    if auth and auth.get("commission_rate") is not None:
        commission_rate = float(auth.get("commission_rate") or 0.0)
        commission_amount = round(final_sell_price * commission_rate / 100.0, 2)
    else:
        notes.append("Bu partner/ürün için özel komisyon tanımı bulunamadı; commission_rate=0 uygulanıyor.")

    # Rule hits from pricing trace
    rule_hits: List[PricingRuleHit] = []
    trace = quote.get("trace") or {}
    trace_rule_id = trace.get("rule_id")
    trace_rule_name = trace.get("rule_name")
    if payload.include_rules and trace_rule_id:
        rule_hits.append(
            PricingRuleHit(
                rule_id=str(trace_rule_id),
                code=None,
                priority=None,
                effect=trace_rule_name,
                scope=None,
                action=None,
            )
        )

    breakdown = PricingPreviewBreakdown(
        nights=nights,
        base_price=base_price_eff,
        markup_percent=markup_percent,
        markup_amount=markup_amount,
        commission_rate=commission_rate,
        commission_amount=commission_amount,
        final_sell_price=round(final_sell_price, 2),
    )

    # Audit (best-effort)
    try:
        await write_audit_log(
            db,
            organization_id=org_id,
            actor={
                "actor_type": "user",
                "actor_id": current_user.get("id") or current_user.get("email"),
                "email": current_user.get("email"),
                "roles": current_user.get("roles") or [],
            },
            request=request,
            action="pricing_preview",
            target_type="b2b_pricing_preview",
            target_id=f"{payload.partner_id}:{payload.product_id}",
            before=None,
            after=None,
            meta={
                "partner_id": payload.partner_id,
                "product_id": payload.product_id,
                "currency": currency,
                "nights": nights,
            },
        )
    except Exception:
        # best-effort
        pass

    return PricingPreviewResponse(
        partner_id=str(partner.get("_id")),
        product_id=str(product.get("_id")),
        currency=currency,
        checkin=payload.checkin,
        checkout=payload.checkout,
        occupancy=payload.occupancy,
        breakdown=breakdown,
        rule_hits=rule_hits,
        notes=notes,
        debug=debug,
    )
