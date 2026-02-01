from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict, Optional

from bson import Decimal128, ObjectId
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr

from app.auth import get_current_user
from app.db import get_db
from app.services.pricing_service import calculate_price
from app.services.pricing_audit_service import emit_pricing_audit_if_needed
from app.utils import now_utc, serialize_doc

router = APIRouter(tags=["b2b-bookings-marketplace"])


class CustomerIn(BaseModel):
  full_name: str
  email: EmailStr
  phone: str


class B2BBookingCreateRequest(BaseModel):
  source: str
  listing_id: str
  customer: CustomerIn


class B2BBookingCreateResponse(BaseModel):
  booking_id: str
  state: str


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
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="LISTING_NOT_FOUND")

  listing = await db.marketplace_listings.find_one(
    {"_id": oid, "organization_id": organization_id, "status": "published"}
  )
  if not listing:
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="LISTING_NOT_FOUND")

  seller_tenant_id = listing.get("tenant_id")
  if not seller_tenant_id:
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="LISTING_NOT_FOUND")

  access = await db.marketplace_access.find_one(
    {
      "organization_id": organization_id,
      "seller_tenant_id": seller_tenant_id,
      "buyer_tenant_id": buyer_tenant_id,
    }
  )
  if not access:
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="MARKETPLACE_ACCESS_FORBIDDEN")

  return listing


@router.post("/bookings", response_model=B2BBookingCreateResponse)
async def create_b2b_booking_from_marketplace(
  payload: B2BBookingCreateRequest,
  request: Request,
  user=Depends(get_current_user),
) -> B2BBookingCreateResponse:
  """Create a B2B booking draft from a marketplace listing.

  - Requires buyer tenant context
  - Enforces marketplace_access visibility
  - Uses pricing engine with tenant_id = buyer_tenant_id
  """

  if payload.source != "marketplace":
    raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="UNSUPPORTED_SOURCE")

  db = await get_db()
  org_id: str = user["organization_id"]
  buyer_tenant_id: Optional[str] = getattr(request.state, "tenant_id", None)

  if not buyer_tenant_id:
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="TENANT_CONTEXT_REQUIRED")

  listing = await _get_visible_listing(
    db,
    organization_id=org_id,
    listing_id=payload.listing_id,
    buyer_tenant_id=buyer_tenant_id,
  )

  currency = listing.get("currency") or "TRY"
  if currency != "TRY":
    raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="UNSUPPORTED_CURRENCY")

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

  # Emit audit trail for B2B booking + pricing rules applied
  from app.services.audit import write_audit_log

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

  return B2BBookingCreateResponse(booking_id=booking_id, state="draft")
