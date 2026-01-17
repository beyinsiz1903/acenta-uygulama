from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.db import get_db
from app.routers.public_checkout import PublicCheckoutGuest, PublicCheckoutPayment
from app.routers.public_search import public_search_catalog
from app.services.partner_auth import require_partner_key


router = APIRouter(prefix="/api/partner", tags=["partner_v1"])


class PartnerQuoteIn(BaseModel):
    product_id: str = Field(..., min_length=1)
    date_from: str
    date_to: str
    adults: int = Field(..., ge=1, le=10)
    children: int = Field(0, ge=0, le=10)
    rooms: int = Field(1, ge=1, le=10)
    currency: str = Field("EUR", min_length=3, max_length=3)


class PartnerBookingIn(BaseModel):
    quote_id: str = Field(..., min_length=1)
    guest: PublicCheckoutGuest
    payment: PublicCheckoutPayment
    idempotency_key: str = Field(..., min_length=8, max_length=128)


@router.get("/products/search")
async def partner_products_search(
    q: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    type: Optional[str] = Query(None),
    partner=Depends(require_partner_key(["products:read"])),
    db=Depends(get_db),
):
    # Delegate to a simplified tenant-scoped search over products.
    org_id = partner["organization_id"]

    from typing import Dict

    # Minimal filter: active hotel products for this org, optionally by name
    filt: Dict[str, Any] = {"organization_id": org_id, "status": "active"}
    if q:
        filt["name.tr"] = {"$regex": q}

    skip = (page - 1) * page_size
    cursor = db.products.find(
        filt,
        {"_id": 1, "type": 1, "name": 1, "default_currency": 1},
    ).skip(skip).limit(page_size)
    products = await cursor.to_list(length=page_size)

    items: List[Dict[str, Any]] = []
    for prod in products:
        name = prod.get("name") or {}
        title = name.get("tr") or name.get("en") or "Ürün"
        item = {
            "product_id": str(prod["_id"]),
            "type": prod.get("type") or "hotel",
            "title": title,
            "price": {
                "amount_cents": 0,
                "currency": (prod.get("default_currency") or "EUR").upper(),
            },
        }
        items.append(item)

    return {"items": items, "page": page, "page_size": page_size, "total": len(items)}


@router.get("/products/{product_id}")
async def partner_get_product(
    product_id: str,
    partner=Depends(require_partner_key(["products:read"])),
    db=Depends(get_db),
) -> Dict[str, Any]:
    org_id = partner["organization_id"]
    doc = await db.products.find_one(
        {"_id": product_id, "organization_id": org_id},
        {"_id": 0},
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Product not found")
    return doc


@router.post("/quotes")
async def partner_create_quote(
    payload: PartnerQuoteIn,
    partner=Depends(require_partner_key(["quotes:write"])),
    db=Depends(get_db),
) -> Dict[str, Any]:
    # Wrap /api/public/quote with org from partner context
    from datetime import date
    from app.routers.public_checkout import PublicQuoteRequest, public_quote

    org_id = partner["organization_id"]

    req = PublicQuoteRequest(
        org=org_id,
        product_id=payload.product_id,
        date_from=date.fromisoformat(payload.date_from),
        date_to=date.fromisoformat(payload.date_to),
        pax={"adults": payload.adults, "children": payload.children},
        rooms=payload.rooms,
        currency=payload.currency,
    )

    # Fake request object is not needed for core behavior; we pass a minimal stub
    class _DummyReq:
        client = None
        headers: Dict[str, Any] = {}

    return await public_quote(req, _DummyReq(), db)  # type: ignore[arg-type]


@router.post("/bookings")
async def partner_create_booking(
    payload: PartnerBookingIn,
    partner=Depends(require_partner_key(["bookings:write"])),
    db=Depends(get_db),
) -> Dict[str, Any]:
    from app.routers.public_checkout import PublicCheckoutRequest, public_checkout

    org_id = partner["organization_id"]

    req = PublicCheckoutRequest(
        org=org_id,
        quote_id=payload.quote_id,
        guest=payload.guest,
        payment=payload.payment,
        idempotency_key=payload.idempotency_key,
    )

    class _DummyReq:
        client = None
        headers: Dict[str, Any] = {}

    resp = await public_checkout(req, _DummyReq(), db)  # type: ignore[arg-type]
    return resp.model_dump()


@router.get("/bookings/{booking_id}")
async def partner_get_booking(
    booking_id: str,
    partner=Depends(require_partner_key(["bookings:read"])),
    db=Depends(get_db),
) -> Dict[str, Any]:
    org_id = partner["organization_id"]
    doc = await db.bookings.find_one(
        {"_id": booking_id, "organization_id": org_id},
        {"_id": 0},
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Booking not found")
    return doc


@router.get("/bookings/{booking_id}/documents")
async def partner_get_booking_documents(
    booking_id: str,
    partner=Depends(require_partner_key(["documents:read"])),
) -> Dict[str, Any]:
    org_id = partner["organization_id"]
    # For MVP, return voucher URL pattern; real doc generation already exists.
    voucher_url = f"/api/voucher/{booking_id}?org={org_id}"
    return {"voucher_url": voucher_url}
