from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from app.db import get_db
from app.errors import AppError
from app.repositories.membership_repository import MembershipRepository
from app.repositories.partner_relationship_repository import PartnerRelationshipRepository
from app.security.deps_b2b import CurrentB2BUser, current_b2b_user


router = APIRouter(prefix="/api/b2b", tags=["b2b-exchange"])


# --------------------------
# Helper / context
# --------------------------


class B2BTenantContext(BaseModel):
    tenant_id: str
    org_id: str
    user_id: str


async def get_b2b_tenant_context(
    request: Request,
    user: CurrentB2BUser = Depends(current_b2b_user),
) -> B2BTenantContext:
    """Resolve tenant from X-Tenant-Id for B2B APIs.

    We cannot rely on TenantResolutionMiddleware here because /api/b2b is
    whitelisted. So we perform a minimal tenant + membership check locally.
    """

    from bson import ObjectId
    from motor.motor_asyncio import AsyncIOMotorDatabase

    tenant_id_header = (request.headers.get("X-Tenant-Id") or "").strip()
    if not tenant_id_header:
        raise AppError(
            status_code=400,
            code="tenant_header_missing",
            message="X-Tenant-Id header is required for B2B endpoints.",
            details=None,
        )

    db: AsyncIOMotorDatabase = await get_db()

    # Resolve tenant
    tenant_lookup_id: Any = tenant_id_header
    try:
        tenant_lookup_id = ObjectId(tenant_id_header)
    except Exception:
        tenant_lookup_id = tenant_id_header

    tenant_doc = await db.tenants.find_one({"_id": tenant_lookup_id})
    if not tenant_doc:
        raise AppError(
            status_code=404,
            code="tenant_not_found",
            message="Tenant not found.",
            details={"tenant_id": tenant_id_header},
        )

    status_t = tenant_doc.get("status", "active")
    is_active_flag = tenant_doc.get("is_active", True)
    if not (status_t == "active" and bool(is_active_flag)):
        raise AppError(
            status_code=403,
            code="tenant_inactive",
            message="Tenant is inactive.",
            details={"tenant_id": tenant_id_header, "status": status_t},
        )

    org_id = str(tenant_doc.get("organization_id") or tenant_doc.get("org_id") or "")
    if org_id and user.organization_id and str(org_id) != str(user.organization_id):
        raise AppError(
            status_code=403,
            code="cross_org_tenant_forbidden",
            message="Tenant does not belong to the same organization as the user.",
            details={"tenant_org_id": org_id, "user_org_id": user.organization_id},
        )

    # Membership check (user must have access to this tenant)
    membership_repo = MembershipRepository(db)
    membership = await membership_repo.find_active_membership(
        user_id=user.id,
        tenant_id=str(tenant_doc["_id"]),
    )
    if not membership:
        raise AppError(
            status_code=403,
            code="tenant_access_forbidden",
            message="User does not have access to this tenant.",
            details={"tenant_id": str(tenant_doc["_id"])},
        )

    return B2BTenantContext(
        tenant_id=str(tenant_doc["_id"]),
        org_id=str(org_id),
        user_id=user.id,
    )


# --------------------------
# Schemas
# --------------------------


class B2BListingCreateIn(BaseModel):
    title: str
    base_price: float = Field(..., gt=0)
    provider_commission_rate: float = Field(..., ge=0, le=100)
    description: Optional[str] = None
    category: Optional[str] = None
    status: Optional[str] = "active"  # active|inactive


class B2BListingOut(BaseModel):
    id: str
    provider_tenant_id: str
    title: str
    description: Optional[str] = None
    category: Optional[str] = None
    base_price: float
    currency: str = "TRY"
    provider_commission_rate: float
    status: str
    created_at: datetime
    updated_at: datetime


class B2BMatchRequestCreateIn(BaseModel):
    listing_id: str
    requested_price: float = Field(..., gt=0)


class StatusHistoryEntry(BaseModel):
    status: str
    at: datetime
    by_user_id: Optional[str] = None


class B2BMatchRequestOut(BaseModel):
    id: str
    listing_id: str
    provider_tenant_id: str
    seller_tenant_id: str
    requested_price: float
    currency: str
    status: str
    platform_fee_rate: float
    platform_fee_amount: float
    status_history: List[StatusHistoryEntry] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


# --------------------------
# Utils
# --------------------------


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _serialize(doc: dict[str, Any]) -> dict[str, Any]:
    """Convert Mongo doc to plain dict with id instead of _id."""

    if not doc:
        return {}
    d = dict(doc)
    if "_id" in d:
        d["id"] = str(d.pop("_id"))
    return d


async def _get_listing(db, listing_id: str) -> Optional[dict[str, Any]]:
    from bson import ObjectId

    try:
        _id = ObjectId(listing_id)
        doc = await db.b2b_listings.find_one({"_id": _id})
    except Exception:
        doc = await db.b2b_listings.find_one({"id": listing_id})
    return doc


async def _get_match_request(db, match_id: str) -> Optional[dict[str, Any]]:
    from bson import ObjectId

    try:
        _id = ObjectId(match_id)
        doc = await db.b2b_match_requests.find_one({"_id": _id})
    except Exception:
        doc = await db.b2b_match_requests.find_one({"id": match_id})
    return doc


def _ensure_currency_try(currency: Optional[str]) -> str:
    c = currency or "TRY"
    if c != "TRY":
        raise AppError(400, "invalid_currency", "Sadece TRY destekleniyor.", {"currency": c})
    return c


# --------------------------
# Provider endpoints
# --------------------------


@router.post("/listings", response_model=B2BListingOut)
async def create_listing(  # type: ignore[no-untyped-def]
    body: B2BListingCreateIn,
    user: CurrentB2BUser = Depends(current_b2b_user),
    tenant_ctx: B2BTenantContext = Depends(get_b2b_tenant_context),
):
    db = await get_db()

    now = _now()
    doc = {
        "provider_tenant_id": tenant_ctx.tenant_id,
        "title": body.title,
        "description": body.description,
        "category": body.category,
        "base_price": float(body.base_price),
        "currency": "TRY",
        "provider_commission_rate": float(body.provider_commission_rate),
        "status": body.status or "active",
        "created_at": now,
        "updated_at": now,
    }
    res = await db.b2b_listings.insert_one(doc)
    inserted = await db.b2b_listings.find_one({"_id": res.inserted_id})
    assert inserted is not None
    return B2BListingOut(**_serialize(inserted))


@router.get("/listings/my", response_model=List[B2BListingOut])
async def list_my_listings(  # type: ignore[no-untyped-def]
    user: CurrentB2BUser = Depends(current_b2b_user),
    tenant_ctx: B2BTenantContext = Depends(get_b2b_tenant_context),
):
    db = await get_db()
    cursor = db.b2b_listings.find({"provider_tenant_id": tenant_ctx.tenant_id}).sort("created_at", -1)
    docs = await cursor.to_list(length=500)
    return [B2BListingOut(**_serialize(d)) for d in docs]


@router.patch("/listings/{listing_id}", response_model=B2BListingOut)
async def update_listing(  # type: ignore[no-untyped-def]
    listing_id: str,
    body: B2BListingCreateIn,
    user: CurrentB2BUser = Depends(current_b2b_user),
    tenant_ctx: B2BTenantContext = Depends(get_b2b_tenant_context),
):
    db = await get_db()
    listing = await _get_listing(db, listing_id)
    if not listing:
        raise AppError(404, "listing_not_found", "Listing not found.", {"id": listing_id})

    if listing.get("provider_tenant_id") != tenant_ctx.tenant_id:
        raise AppError(403, "forbidden", "Sadece kendi listing'lerinizi güncelleyebilirsiniz.", None)

    now = _now()
    update_doc = {
        "title": body.title,
        "description": body.description,
        "category": body.category,
        "base_price": float(body.base_price),
        "provider_commission_rate": float(body.provider_commission_rate),
        "status": body.status or listing.get("status", "active"),
        "updated_at": now,
    }
    await db.b2b_listings.update_one({"_id": listing["_id"]}, {"$set": update_doc})
    updated = await db.b2b_listings.find_one({"_id": listing["_id"]})
    assert updated is not None
    return B2BListingOut(**_serialize(updated))


# --------------------------
# Seller endpoints
# --------------------------


@router.get("/listings/available", response_model=List[B2BListingOut])
async def list_available_listings(  # type: ignore[no-untyped-def]
    user: CurrentB2BUser = Depends(current_b2b_user),
    tenant_ctx: B2BTenantContext = Depends(get_b2b_tenant_context),
):
    db = await get_db()
    rel_repo = PartnerRelationshipRepository(db)

    # Aktif partner ilişkileri: tenant seller veya buyer olabilir; karşı taraf provider olabilir.
    tenant_id = tenant_ctx.tenant_id

    # Kullanılabilir partner tenant id seti
    partner_ids: set[str] = set()

    # seller tarafı ilişkiler
    cursor = db.partner_relationships.find({"seller_tenant_id": tenant_id, "status": "active"})
    async for r in cursor:
        other = str(r.get("buyer_tenant_id"))
        if other and other != tenant_id:
            partner_ids.add(other)

    # buyer tarafı ilişkiler
    cursor_b = db.partner_relationships.find({"buyer_tenant_id": tenant_id, "status": "active"})
    async for r in cursor_b:
        other = str(r.get("seller_tenant_id"))
        if other and other != tenant_id:
            partner_ids.add(other)

    if not partner_ids:
        return []

    cursor_l = db.b2b_listings.find(
        {
            "provider_tenant_id": {"$in": list(partner_ids)},
            "status": "active",
        }
    ).sort("created_at", -1)
    docs = await cursor_l.to_list(length=500)
    return [B2BListingOut(**_serialize(d)) for d in docs]


@router.post("/match-request", response_model=B2BMatchRequestOut)
async def create_match_request(  # type: ignore[no-untyped-def]
    body: B2BMatchRequestCreateIn,
    user: CurrentB2BUser = Depends(current_b2b_user),
    tenant_ctx: B2BTenantContext = Depends(get_b2b_tenant_context),
):
    db = await get_db()
    listing = await _get_listing(db, body.listing_id)
    if not listing:
        raise AppError(404, "listing_not_found", "Listing not found.", {"id": body.listing_id})

    if listing.get("status") != "active":
        raise AppError(400, "listing_not_active", "Listing is not active.", {"id": body.listing_id})

    provider_tenant_id = str(listing.get("provider_tenant_id"))
    seller_tenant_id = tenant_ctx.tenant_id
    if provider_tenant_id == seller_tenant_id:
        raise AppError(400, "cannot_request_own_listing", "Kendi listing'iniz için talep oluşturamazsınız.", None)

    # Aktif partner ilişkisi var mı?
    rel = await db.partner_relationships.find_one(
        {
            "status": "active",
            "$or": [
                {"seller_tenant_id": seller_tenant_id, "buyer_tenant_id": provider_tenant_id},
                {"seller_tenant_id": provider_tenant_id, "buyer_tenant_id": seller_tenant_id},
            ],
        }
    )
    if not rel:
        raise AppError(
            403,
            "not_active_partner",
            "Bu listing için aktif bir partner ilişkisi bulunmuyor.",
            {"provider_tenant_id": provider_tenant_id, "seller_tenant_id": seller_tenant_id},
        )

    currency = _ensure_currency_try(listing.get("currency"))

    now = _now()
    history: List[Dict[str, Any]] = [
        {
            "status": "pending",
            "at": now,
            "by_user_id": tenant_ctx.user_id,
        }
    ]

    doc = {
        "listing_id": str(listing.get("_id")),
        "provider_tenant_id": provider_tenant_id,
        "seller_tenant_id": seller_tenant_id,
        "requested_price": float(body.requested_price),
        "currency": currency,
        "status": "pending",
        "platform_fee_rate": 0.01,
        "platform_fee_amount": 0.0,
        "status_history": history,
        "created_at": now,
        "updated_at": now,
    }

    res = await db.b2b_match_requests.insert_one(doc)
    inserted = await db.b2b_match_requests.find_one({"_id": res.inserted_id})
    assert inserted is not None

    return B2BMatchRequestOut(**_serialize(inserted))


@router.get("/match-request/my", response_model=List[B2BMatchRequestOut])
async def list_my_match_requests(  # type: ignore[no-untyped-def]
    user: CurrentB2BUser = Depends(current_b2b_user),
    tenant_ctx: B2BTenantContext = Depends(get_b2b_tenant_context),
):
    db = await get_db()
    cursor = db.b2b_match_requests.find({"seller_tenant_id": tenant_ctx.tenant_id}).sort("created_at", -1)
    docs = await cursor.to_list(length=500)
    return [B2BMatchRequestOut(**_serialize(d)) for d in docs]


# --------------------------
# Provider match management
# --------------------------


async def _append_status_history(db, match_doc: dict[str, Any], status: str, user_id: str) -> List[Dict[str, Any]]:
    history: List[Dict[str, Any]] = list(match_doc.get("status_history") or [])
    now = _now()
    history.append({"status": status, "at": now, "by_user_id": user_id})
    return history


@router.get("/match-request/incoming", response_model=List[B2BMatchRequestOut])
async def list_incoming_match_requests(  # type: ignore[no-untyped-def]
    user: CurrentB2BUser = Depends(current_b2b_user),
    tenant_ctx: B2BTenantContext = Depends(get_b2b_tenant_context),
):
    db = await get_db()
    cursor = db.b2b_match_requests.find({"provider_tenant_id": tenant_ctx.tenant_id}).sort("created_at", -1)
    docs = await cursor.to_list(length=500)
    return [B2BMatchRequestOut(**_serialize(d)) for d in docs]


async def _update_match_status(
    match_id: str,
    new_status: str,
    allowed_from: List[str],
    tenant_ctx: B2BTenantContext,
) -> B2BMatchRequestOut:
    db = await get_db()
    match_doc = await _get_match_request(db, match_id)
    if not match_doc:
        raise AppError(404, "match_request_not_found", "Match request not found.", {"id": match_id})

    if match_doc.get("provider_tenant_id") != tenant_ctx.tenant_id:
        raise AppError(403, "forbidden", "Sadece kendi listing taleplerinizde durum değiştirebilirsiniz.", None)

    current_status = match_doc.get("status")
    if current_status not in allowed_from:
        raise AppError(
            400,
            "invalid_status_transition",
            "Bu durumdan bu duruma geçişe izin verilmiyor.",
            {"from": current_status, "to": new_status},
        )

    history = await _append_status_history(db, match_doc, new_status, tenant_ctx.user_id)
    now = _now()

    update_fields: Dict[str, Any] = {
        "status": new_status,
        "status_history": history,
        "updated_at": now,
    }

    # Completion: compute platform fee
    if new_status == "completed":
        price = float(match_doc.get("requested_price") or 0.0)
        rate = float(match_doc.get("platform_fee_rate") or 0.01)
        update_fields["platform_fee_amount"] = price * rate

    await db.b2b_match_requests.update_one({"_id": match_doc["_id"]}, {"$set": update_fields})
    updated = await db.b2b_match_requests.find_one({"_id": match_doc["_id"]})
    assert updated is not None
    return B2BMatchRequestOut(**_serialize(updated))


@router.patch("/match-request/{match_id}/approve", response_model=B2BMatchRequestOut)
async def approve_match_request(  # type: ignore[no-untyped-def]
    match_id: str,
    user: CurrentB2BUser = Depends(current_b2b_user),
    tenant_ctx: B2BTenantContext = Depends(get_b2b_tenant_context),
):
    return await _update_match_status(match_id, "approved", ["pending"], tenant_ctx)


@router.patch("/match-request/{match_id}/reject", response_model=B2BMatchRequestOut)
async def reject_match_request(  # type: ignore[no-untyped-def]
    match_id: str,
    user: CurrentB2BUser = Depends(current_b2b_user),
    tenant_ctx: B2BTenantContext = Depends(get_b2b_tenant_context),
):
    return await _update_match_status(match_id, "rejected", ["pending"], tenant_ctx)


@router.patch("/match-request/{match_id}/complete", response_model=B2BMatchRequestOut)
async def complete_match_request(  # type: ignore[no-untyped-def]
    match_id: str,
    user: CurrentB2BUser = Depends(current_b2b_user),
    tenant_ctx: B2BTenantContext = Depends(get_b2b_tenant_context),
):
    return await _update_match_status(match_id, "completed", ["approved"], tenant_ctx)

