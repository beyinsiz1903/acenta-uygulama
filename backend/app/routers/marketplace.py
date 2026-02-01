from __future__ import annotations

from datetime import datetime, timezone, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional

from bson import ObjectId
from bson.decimal128 import Decimal128
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field

from app.auth import get_current_user
from app.db import get_db
from app.tenant_context import enforce_tenant_org
from app.utils import now_utc, serialize_doc

router = APIRouter(prefix="/marketplace", tags=["marketplace"])

CURRENCY_TRY = "TRY"


class SupplierInfo(BaseModel):
    name: Optional[str] = None
    external_ref: Optional[str] = None
    payload: Optional[Dict[str, Any]] = None


class MarketplaceListingBase(BaseModel):
    title: str
    description: Optional[str] = None
    category: Optional[str] = None
    currency: str = CURRENCY_TRY
    base_price: str
    pricing_hint: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None
    supplier: Optional[SupplierInfo] = None


class MarketplaceListingCreate(MarketplaceListingBase):
    pass


class MarketplaceListingUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    currency: Optional[str] = None
    base_price: Optional[str] = None
    pricing_hint: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None


class MarketplaceAccessGrant(BaseModel):
    seller_tenant_id: Optional[str] = None
    buyer_tenant_id: Optional[str] = None
    seller_tenant_key: Optional[str] = None
    buyer_tenant_key: Optional[str] = None


def _parse_price(value: str) -> Decimal:
    try:
        dec = Decimal(value)
    except (InvalidOperation, TypeError):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="INVALID_PRICE",
        )
    if dec < Decimal("0"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="INVALID_PRICE",
        )
    return dec


async def _get_seller_listing(db, org_id: str, listing_id: str) -> Dict[str, Any]:
    try:
        oid = ObjectId(listing_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="LISTING_NOT_FOUND")

    doc = await db.marketplace_listings.find_one({"_id": oid, "organization_id": org_id})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="LISTING_NOT_FOUND")
    return doc


@router.post("/listings", status_code=status.HTTP_201_CREATED)
async def create_listing(
    payload: MarketplaceListingCreate,
    request: Request,
    user=Depends(get_current_user),
) -> Dict[str, Any]:
    db = await get_db()
    org_id = user["organization_id"]

    if payload.currency != CURRENCY_TRY:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="UNSUPPORTED_CURRENCY",
        )

    tenant_id = getattr(request.state, "tenant_id", None)

    price_dec = _parse_price(payload.base_price)

    now = now_utc()
    doc: Dict[str, Any] = {
        "organization_id": org_id,
        "tenant_id": tenant_id,
        "status": "draft",
        "title": payload.title,
        "description": payload.description,
        "category": payload.category,
        "currency": CURRENCY_TRY,
        "base_price": Decimal128(str(price_dec)),
        "pricing_hint": payload.pricing_hint or {},
        "tags": payload.tags or [],
        "created_at": now,
        "updated_at": now,
    }

    if payload.supplier is not None:
        doc["supplier"] = {
            "name": payload.supplier.name,
            "external_ref": payload.supplier.external_ref,
            "payload": payload.supplier.payload or {},
        }

    # supplier_mapping will be populated lazily during supplier resolve / booking flows

    res = await db.marketplace_listings.insert_one(doc)
    created = await db.marketplace_listings.find_one({"_id": res.inserted_id})
    return serialize_doc(created)


@router.get("/listings")
async def list_listings(
    request: Request,
    status_filter: Optional[str] = Query(None, alias="status"),
    user=Depends(get_current_user),
) -> List[Dict[str, Any]]:
    db = await get_db()
    org_id = user["organization_id"]

    # org scope enforced; tenant scope: if tenant context present, only its listings
    base_filter: Dict[str, Any] = {"organization_id": org_id}
    base_filter = enforce_tenant_org(base_filter, request)

    tenant_id = getattr(request.state, "tenant_id", None)
    if tenant_id:
        base_filter["tenant_id"] = tenant_id

    if status_filter:
        base_filter["status"] = status_filter

    cursor = db.marketplace_listings.find(base_filter).sort([
        ("updated_at", -1),
        ("_id", -1),
    ])
    docs = await cursor.to_list(length=500)
    return [serialize_doc(d) for d in docs]


@router.get("/listings/{listing_id}")
async def get_listing(listing_id: str, request: Request, user=Depends(get_current_user)) -> Dict[str, Any]:
    db = await get_db()
    org_id = user["organization_id"]
    listing = await _get_seller_listing(db, org_id, listing_id)

    tenant_id = getattr(request.state, "tenant_id", None)
    if tenant_id and listing.get("tenant_id") != tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="LISTING_NOT_FOUND")

    return serialize_doc(listing)


@router.patch("/listings/{listing_id}")
async def update_listing(
    listing_id: str,
    payload: MarketplaceListingUpdate,
    request: Request,
    user=Depends(get_current_user),
) -> Dict[str, Any]:
    db = await get_db()
    org_id = user["organization_id"]

    listing = await _get_seller_listing(db, org_id, listing_id)

    tenant_id = getattr(request.state, "tenant_id", None)
    if tenant_id and listing.get("tenant_id") != tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="LISTING_NOT_FOUND")

    update_fields: Dict[str, Any] = {}

    if payload.title is not None:
        update_fields["title"] = payload.title
    if payload.description is not None:
        update_fields["description"] = payload.description
    if payload.category is not None:
        update_fields["category"] = payload.category
    if payload.currency is not None and payload.currency != CURRENCY_TRY:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="UNSUPPORTED_CURRENCY",
        )
    if payload.base_price is not None:
        price_dec = _parse_price(payload.base_price)
        update_fields["base_price"] = Decimal128(str(price_dec))
    if payload.pricing_hint is not None:
        update_fields["pricing_hint"] = payload.pricing_hint
    if payload.tags is not None:
        update_fields["tags"] = payload.tags

    if not update_fields:
        return serialize_doc(listing)

    update_fields["updated_at"] = now_utc()

    await db.marketplace_listings.update_one({"_id": listing["_id"]}, {"$set": update_fields})
    updated = await _get_seller_listing(db, org_id, listing_id)
    return serialize_doc(updated)


async def _change_status(db, org_id: str, listing_id: str, request: Request, new_status: str) -> Dict[str, Any]:
    listing = await _get_seller_listing(db, org_id, listing_id)

    tenant_id = getattr(request.state, "tenant_id", None)
    if tenant_id and listing.get("tenant_id") != tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="LISTING_NOT_FOUND")

    await db.marketplace_listings.update_one(
        {"_id": listing["_id"]},
        {"$set": {"status": new_status, "updated_at": now_utc()}},
    )
    updated = await _get_seller_listing(db, org_id, listing_id)

    # Audit v1 minimal
    from app.services.audit import write_audit_log

    await write_audit_log(
        db,
        organization_id=org_id,
        actor={"actor_type": "user"},
        request=request,
        action="MARKETPLACE_LISTING_PUBLISHED" if new_status == "published" else "MARKETPLACE_LISTING_ARCHIVED",
        target_type="marketplace_listing",
        target_id=str(listing["_id"]),
        before=listing,
        after=updated,
        meta={},
    )

    return serialize_doc(updated)


@router.post("/listings/{listing_id}/publish")
async def publish_listing(listing_id: str, request: Request, user=Depends(get_current_user)) -> Dict[str, Any]:
    db = await get_db()
    org_id = user["organization_id"]
    return await _change_status(db, org_id, listing_id, request, "published")


@router.post("/listings/{listing_id}/archive")
async def archive_listing(listing_id: str, request: Request, user=Depends(get_current_user)) -> Dict[str, Any]:
    db = await get_db()
    org_id = user["organization_id"]
    return await _change_status(db, org_id, listing_id, request, "archived")


@router.post("/access/grant", status_code=status.HTTP_201_CREATED)
async def grant_access(payload: MarketplaceAccessGrant, request: Request, user=Depends(get_current_user)) -> Dict[str, Any]:
    db = await get_db()
    org_id = user["organization_id"]

    # org scope enforcement (even if someone sends different org in body later)
    filter_base = enforce_tenant_org({"organization_id": org_id}, request)

    # Backwards compatible: if explicit IDs provided, use them as-is
    seller_tenant_id = payload.seller_tenant_id
    buyer_tenant_id = payload.buyer_tenant_id

    # Optional convenience: resolve from tenant_key if IDs are not provided
    if (not seller_tenant_id or not buyer_tenant_id) and (payload.seller_tenant_key or payload.buyer_tenant_key):
        keys: list[str] = [k for k in [payload.seller_tenant_key, payload.buyer_tenant_key] if k]
        # Resolve by keys within same org; support both "tenant_key" and legacy "key" fields
        tenants = await db.tenants.find(
            {
                "organization_id": filter_base["organization_id"],
                "$or": [
                    {"tenant_key": {"$in": keys}},
                    {"key": {"$in": keys}},
                ],
            }
        ).to_list(length=20)

        key_to_id: dict[str, str] = {}
        for t in tenants:
            tk = t.get("tenant_key") or t.get("key")
            if tk:
                key_to_id[tk] = str(t["_id"])

        if payload.seller_tenant_key and not seller_tenant_id:
            seller_tenant_id = key_to_id.get(payload.seller_tenant_key)
            if not seller_tenant_id:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="TENANT_NOT_FOUND")

        if payload.buyer_tenant_key and not buyer_tenant_id:
            buyer_tenant_id = key_to_id.get(payload.buyer_tenant_key)
            if not buyer_tenant_id:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="TENANT_NOT_FOUND")

    if not seller_tenant_id or not buyer_tenant_id:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="TENANT_IDS_REQUIRED")

    now = now_utc()
    doc = {
        "organization_id": filter_base["organization_id"],
        "seller_tenant_id": seller_tenant_id,
        "buyer_tenant_id": buyer_tenant_id,
        "created_at": now,
    }

    await db.marketplace_access.update_one(
        {
            "organization_id": filter_base["organization_id"],
            "seller_tenant_id": seller_tenant_id,
            "buyer_tenant_id": buyer_tenant_id,
        },
        {"$set": doc},
        upsert=True,
    )

    from app.services.audit import write_audit_log

    await write_audit_log(
        db,
        organization_id=filter_base["organization_id"],
        actor={"actor_type": "user"},
        request=request,
        action="MARKETPLACE_ACCESS_GRANTED",
        target_type="marketplace_access",
        target_id=f"{payload.seller_tenant_id}->{payload.buyer_tenant_id}",
        before=None,
        after=doc,
        meta={},
    )

    return serialize_doc(doc)


@router.post("/access/revoke", status_code=status.HTTP_200_OK)
async def revoke_access(payload: MarketplaceAccessGrant, request: Request, user=Depends(get_current_user)) -> Dict[str, Any]:
    db = await get_db()
    org_id = user["organization_id"]

    filter_base = enforce_tenant_org({"organization_id": org_id}, request)

    res = await db.marketplace_access.delete_one(
        {
            "organization_id": filter_base["organization_id"],
            "seller_tenant_id": payload.seller_tenant_id,
            "buyer_tenant_id": payload.buyer_tenant_id,
        }
    )

    from app.services.audit import write_audit_log

    await write_audit_log(
        db,
        organization_id=filter_base["organization_id"],
        actor={"actor_type": "user"},
        request=request,
        action="MARKETPLACE_ACCESS_REVOKED",
        target_type="marketplace_access",
        target_id=f"{payload.seller_tenant_id}->{payload.buyer_tenant_id}",
        before=None,
        after={"deleted_count": res.deleted_count},
        meta={},
    )

    return {"ok": True, "deleted": res.deleted_count}


@router.get("/access")
async def list_access(
    request: Request,
    buyer_tenant_id: Optional[str] = Query(None),
    user=Depends(get_current_user),
) -> List[Dict[str, Any]]:
    db = await get_db()
    org_id = user["organization_id"]

    filter_base: Dict[str, Any] = {"organization_id": org_id}
    filter_base = enforce_tenant_org(filter_base, request)

    ctx_buyer = getattr(request.state, "tenant_id", None)
    # v1: if tenant context exists and buyer_tenant_id specified, enforce equality
    if ctx_buyer and buyer_tenant_id and buyer_tenant_id != ctx_buyer:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="CROSS_TENANT_FORBIDDEN")

    if buyer_tenant_id:
        filter_base["buyer_tenant_id"] = buyer_tenant_id
    elif ctx_buyer:
        filter_base["buyer_tenant_id"] = ctx_buyer

    cursor = db.marketplace_access.find(filter_base).sort([("created_at", -1)])
    docs = await cursor.to_list(length=500)
    return [serialize_doc(d) for d in docs]


@router.post("/catalog/{listing_id}/create-storefront-session")
async def create_storefront_session_for_listing(
    listing_id: str,
    request: Request,
    user=Depends(get_current_user),
) -> Dict[str, Any]:
    """Bridge: from marketplace listing to seller's storefront session.

    - Requires buyer tenant context
    - Ensures listing is published and buyer has marketplace_access to seller tenant
    - Creates a storefront_sessions document under seller tenant with one offer snapshot
    - Returns redirect_url for B2C storefront UI
    """

    db = await get_db()
    org_id = user["organization_id"]

    buyer_tenant_id = getattr(request.state, "tenant_id", None)
    if not buyer_tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="TENANT_CONTEXT_REQUIRED")

    # Load listing and ensure it belongs to this org and is published
    try:
        oid = ObjectId(listing_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="LISTING_NOT_FOUND")

    listing = await db.marketplace_listings.find_one(
        {"_id": oid, "organization_id": org_id, "status": "published"}
    )
    if not listing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="LISTING_NOT_FOUND")

    seller_tenant_id = listing.get("tenant_id")
    if not seller_tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="LISTING_NOT_FOUND")

    # Check marketplace_access for this buyer
    access = await db.marketplace_access.find_one(
        {
            "organization_id": org_id,
            "seller_tenant_id": seller_tenant_id,
            "buyer_tenant_id": buyer_tenant_id,
        }
    )
    if not access:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="MARKETPLACE_ACCESS_FORBIDDEN")

    # Resolve seller tenant_key for redirect
    seller_tenant_doc = await db.tenants.find_one({"_id": ObjectId(seller_tenant_id)})
    if not seller_tenant_doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="TENANT_NOT_FOUND")

    seller_tenant_key = seller_tenant_doc.get("tenant_key")

    # Create storefront session for seller tenant
    from uuid import uuid4

    search_id = str(uuid4())
    now = now_utc()
    expires_at = now + timedelta(minutes=30)

    price = listing.get("base_price")
    if isinstance(price, Decimal128):
        total_amount = price
    else:
        total_amount = Decimal128(str(_parse_price(str(price or "0"))))

    offer = {
        "offer_id": f"MP-{listing_id}",
        "supplier": "marketplace",
        "currency": "TRY",
        "total_amount": total_amount,
        "raw_ref": {
            "source": "marketplace",
            "listing_id": listing_id,
            "seller_tenant_id": seller_tenant_id,
            "title": listing.get("title"),
            "category": listing.get("category"),
            "tags": listing.get("tags") or [],
        },
    }

    session_doc = {
        "tenant_id": seller_tenant_id,
        "search_id": search_id,
        "offers_snapshot": [offer],
        "expires_at": expires_at,
        "created_at": now,
    }

    await db.storefront_sessions.insert_one(session_doc)

    # Audit log
    from app.services.audit import write_audit_log

    await write_audit_log(
        db,
        organization_id=org_id,
        actor={"actor_type": "user"},
        request=request,
        action="MARKETPLACE_STOREFRONT_SESSION_CREATED",
        target_type="marketplace_listing",
        target_id=listing_id,
        before=None,
        after=session_doc,
        meta={
            "listing_id": listing_id,
            "seller_tenant_id": seller_tenant_id,
            "buyer_tenant_id": buyer_tenant_id,
            "search_id": search_id,
        },
    )

    redirect_url = f"/s/{seller_tenant_key}/search?search_id={search_id}"

    return {
        "seller_tenant_id": seller_tenant_id,
        "storefront_search_id": search_id,
        "expires_at": expires_at.isoformat(),
        "redirect_url": redirect_url,
    }


@router.get("/catalog")
async def marketplace_catalog(
    request: Request,
    q: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    tag: Optional[str] = Query(None),
    min_price: Optional[str] = Query(None),
    max_price: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    cursor: Optional[str] = Query(None),
    user=Depends(get_current_user),
) -> Dict[str, Any]:
    """Buyer-side catalog view.

    - Requires tenant context (buyer_tenant_id)
    - Only shows listings with status="published" where (seller_tenant_id, buyer_tenant_id)
      exists in marketplace_access for the same org.
    """

    db = await get_db()
    org_id = user["organization_id"]

    buyer_tenant_id = getattr(request.state, "tenant_id", None)
    if not buyer_tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="TENANT_CONTEXT_REQUIRED")

    # Resolve allowed seller tenant ids for this buyer
    access_filter: Dict[str, Any] = {"organization_id": org_id, "buyer_tenant_id": buyer_tenant_id}
    access_cursor = db.marketplace_access.find(access_filter)
    access_docs = await access_cursor.to_list(length=1000)
    seller_ids = {doc.get("seller_tenant_id") for doc in access_docs if doc.get("seller_tenant_id")}

    if not seller_ids:
        return {"items": [], "next_cursor": None}

    filter_: Dict[str, Any] = {
        "organization_id": org_id,
        "tenant_id": {"$in": list(seller_ids)},
        "status": "published",
    }

    if q:
        # simple case-insensitive search on title/description
        filter_["$or"] = [
            {"title": {"$regex": q, "$options": "i"}},
            {"description": {"$regex": q, "$options": "i"}},
        ]
    if category:
        filter_["category"] = category
    if tag:
        filter_["tags"] = tag

    price_filter: Dict[str, Any] = {}
    if min_price:
        price_filter.setdefault("$gte", _parse_price(min_price))
    if max_price:
        price_filter.setdefault("$lte", _parse_price(max_price))
    if price_filter:
        filter_["base_price"] = {
            k: Decimal128(str(v)) for k, v in price_filter.items()
        }

    sort_spec = [("updated_at", -1), ("_id", -1)]

    if cursor:
        # cursor format: timestamp_iso|hexid
        try:
            ts_str, hex_id = cursor.split("|")
            ts = datetime.fromisoformat(ts_str)
            oid = ObjectId(hex_id)
            filter_["$or"] = [
                {"updated_at": {"$lt": ts}},
                {"updated_at": ts, "_id": {"$lt": oid}},
            ]
        except Exception:
            # ignore invalid cursor
            pass

    cursor_db = db.marketplace_listings.find(filter_).sort(sort_spec).limit(limit + 1)
    docs = await cursor_db.to_list(length=limit + 1)

    next_cursor: Optional[str] = None
    if len(docs) > limit:
        last = docs[limit - 1]
        ts = last.get("updated_at")
        if isinstance(ts, datetime) and ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        oid = last.get("_id")
        next_cursor = f"{ts.isoformat()}|{oid}" if ts and oid else None
        docs = docs[:limit]

    items = []
    for d in docs:
        base_price = d.get("base_price")
        price_dec = Decimal(str(base_price.to_decimal())) if isinstance(base_price, Decimal128) else Decimal("0")
        items.append(
            {
                "id": str(d.get("_id")),
                "seller_tenant_id": d.get("tenant_id"),
                "title": d.get("title"),
                "category": d.get("category"),
                "price": str(price_dec),
                "currency": d.get("currency"),
                "tags": d.get("tags") or [],
            }
        )

    return {"items": items, "next_cursor": next_cursor}
