from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from app.auth import get_current_user, require_roles
from app.db import get_db
from app.utils import serialize_doc
from app.services.audit import write_audit_log, audit_snapshot


async def _load_agency_min(db, org_id: str, agency_id: str) -> Optional[Dict[str, Any]]:
    """Load minimal agency info for linking/summary.

    Accepts string or ObjectId-compatible id and scopes by organization.
    Returns a dict with _id and name or None when not found.
    """

    if not agency_id:
        return None

    # First try direct string _id
    doc = await db.agencies.find_one({"_id": agency_id, "organization_id": org_id}, {"name": 1})
    if doc:
        return doc

    try:
        oid = ObjectId(agency_id)
    except Exception:
        return None

    return await db.agencies.find_one({"_id": oid, "organization_id": org_id}, {"name": 1})


router = APIRouter(prefix="/api/admin/partners", tags=["admin_partners"])


AdminDep = Depends(require_roles(["super_admin", "admin", "ops"]))


class PartnerBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    contact_email: Optional[str] = Field(None, max_length=200)
    status: str = Field("pending", pattern="^(pending|approved|blocked)$")
    api_key_name: Optional[str] = Field(None, max_length=200)
    default_markup_percent: float = Field(0.0, ge=-100.0, le=500.0)
    linked_agency_id: Optional[str] = Field(
        None,
        max_length=64,
        description="Optional agency id from agencies collection linked to this partner",
    )
    notes: Optional[str] = Field(None, max_length=2000)


class PartnerCreateIn(PartnerBase):
    pass


class PartnerUpdateIn(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    contact_email: Optional[str] = Field(None, max_length=200)
    status: Optional[str] = Field(None, pattern="^(pending|approved|blocked)$")
    api_key_name: Optional[str] = Field(None, max_length=200)
    default_markup_percent: Optional[float] = Field(None, ge=-100.0, le=500.0)
    linked_agency_id: Optional[str] = Field(
        None,
        max_length=64,
        description="Optional agency id from agencies collection linked to this partner",
    )
    notes: Optional[str] = Field(None, max_length=2000)


class PartnerOut(BaseModel):
    id: str
    name: str
    contact_email: Optional[str] = None
    status: str
    api_key_name: Optional[str] = None
    default_markup_percent: float
    linked_agency_id: Optional[str] = None
    notes: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    class Config:
        orm_mode = True


@router.get("", dependencies=[AdminDep])
async def list_partners(
    status: Optional[str] = Query(None, pattern="^(pending|approved|blocked)$"),
    q: Optional[str] = Query(None, max_length=200),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db=Depends(get_db),
    user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    org_id = user["organization_id"]
    query: Dict[str, Any] = {"organization_id": org_id}
    if status:
        query["status"] = status
    if q:
        regex = {"$regex": q, "$options": "i"}
        query["$or"] = [
            {"name": regex},
            {"contact_email": regex},
        ]

    skip = (page - 1) * limit
    cursor = db.partner_profiles.find(query).sort("created_at", -1).skip(skip).limit(limit + 1)
    docs = await cursor.to_list(length=limit + 1)

    has_more = len(docs) > limit
    docs = docs[:limit]

    items: List[PartnerOut] = []
    for d in docs:
        data = serialize_doc(d)
        if "id" not in data and "_id" in d:
            data["id"] = str(d["_id"])
        items.append(PartnerOut(**data))

    return {"items": items, "has_more": has_more}


@router.post("", response_model=PartnerOut, dependencies=[AdminDep])
async def create_partner(
    payload: PartnerCreateIn,
    db=Depends(get_db),
    user: Dict[str, Any] = Depends(get_current_user),
) -> PartnerOut:
    org_id = user["organization_id"]
    now = datetime.now(timezone.utc).isoformat()

    doc: Dict[str, Any] = {
        "organization_id": org_id,
        "name": payload.name.strip(),
        "contact_email": (payload.contact_email or "").strip() or None,
        "status": payload.status,
        "api_key_name": (payload.api_key_name or "").strip() or None,
        "default_markup_percent": float(payload.default_markup_percent or 0.0),
        "linked_agency_id": (payload.linked_agency_id or "").strip() or None,
        "notes": (payload.notes or "").strip() or None,
        "created_at": now,
        "updated_at": now,
    }

    res = await db.partner_profiles.insert_one(doc)
    doc["_id"] = res.inserted_id
    data = serialize_doc(doc)
    data["id"] = data.pop("_id")
    return PartnerOut(**data)


@router.patch("/{partner_id}", response_model=PartnerOut, dependencies=[AdminDep])
async def update_partner(
    partner_id: str,
    payload: PartnerUpdateIn,
    request: Request,
    db=Depends(get_db),
    user: Dict[str, Any] = Depends(get_current_user),
) -> PartnerOut:
    org_id = user["organization_id"]

    try:
        oid = ObjectId(partner_id)
    except Exception:
        # Support string ids as well (in case of future changes)
        oid = partner_id

    data = payload.model_dump(exclude_unset=True)
    update: Dict[str, Any] = {}

    for field in ["name", "contact_email", "status", "api_key_name", "default_markup_percent", "linked_agency_id", "notes"]:
        if field in data:
            value = data[field]
            if isinstance(value, str):
                value = value.strip()
            update[field] = value

    if not update:
        doc = await db.partner_profiles.find_one({"_id": oid, "organization_id": org_id})
        if not doc:
            raise HTTPException(status_code=404, detail="PARTNER_NOT_FOUND")
        data = serialize_doc(doc)
        data["id"] = data.pop("_id")
        return PartnerOut(**data)

    update["updated_at"] = datetime.now(timezone.utc).isoformat()

    res = await db.partner_profiles.update_one({"_id": oid, "organization_id": org_id}, {"$set": update})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="PARTNER_NOT_FOUND")

    doc = await db.partner_profiles.find_one({"_id": oid, "organization_id": org_id})
    if not doc:
        raise HTTPException(status_code=404, detail="PARTNER_NOT_FOUND")

    data = serialize_doc(doc)
    data["id"] = data.pop("_id")
    return PartnerOut(**data)


class PartnerActivitySummaryOut(BaseModel):
    partner_id: str
    partner_name: str
    linked_agency_id: Optional[str] = None
    linked_agency_name: Optional[str] = None
    total_bookings: int
    total_amount_cents: int
    currency: str
    by_channel: Dict[str, int]
    by_product_type: Dict[str, int]
    first_booking_at: Optional[str] = None
    last_booking_at: Optional[str] = None


@router.get("/{partner_id}/summary", response_model=PartnerActivitySummaryOut, dependencies=[AdminDep])
async def get_partner_summary(
    partner_id: str,
    db=Depends(get_db),
    user: Dict[str, Any] = Depends(get_current_user),
) -> PartnerActivitySummaryOut:
    """Partner bazlı basit aktivite özeti.

    Şu alanları döner:
    - toplam rezervasyon sayısı
    - toplam ciro (amount_total_cents üzerinden)
    - kanal kırılımı (public/partner/public_tour/b2b vs.)
    - ürün tipi kırılımı (hotel/tour/diğer)
    """

    org_id = user["organization_id"]

    try:
        oid = ObjectId(partner_id)
    except Exception:
        oid = partner_id

    partner_doc = await db.partner_profiles.find_one({"_id": oid, "organization_id": org_id})
    if not partner_doc:
        raise HTTPException(status_code=404, detail="PARTNER_NOT_FOUND")

    partner_id_str = str(partner_doc.get("_id"))
    partner_name = partner_doc.get("name") or ""
    linked_agency_id = partner_doc.get("linked_agency_id") or None

    # Aggregate bookings that reference this partner via public_quote or channel
    match: Dict[str, Any] = {"organization_id": org_id}
    partner_or: list[Dict[str, Any]] = [
        {"public_quote.partner": partner_id_str},
        {"public_quote.partner": partner_id},
    ]

    # Also consider bookings created via partner channel in future
    partner_or.append({"channel": "partner", "partner": partner_id_str})

    match["$or"] = partner_or

    pipeline: List[Dict[str, Any]] = [
        {"$match": match},
        {
            "$group": {
                "_id": None,
                "count": {"$sum": 1},
                "amount_total_cents": {"$sum": {"$ifNull": ["$amount_total_cents", 0]}},
                "first_booking_at": {"$min": "$created_at"},
                "last_booking_at": {"$max": "$created_at"},
            }
        },
    ]

    agg = await db.bookings.aggregate(pipeline).to_list(length=1)
    if agg:
        row = agg[0]
        total_bookings = int(row.get("count") or 0)
        total_amount_cents = int(row.get("amount_total_cents") or 0)
        first_booking_at = row.get("first_booking_at")
        last_booking_at = row.get("last_booking_at")
    else:
        total_bookings = 0
        total_amount_cents = 0
        first_booking_at = None
        last_booking_at = None

    # Channel breakdown
    pipeline_channel: List[Dict[str, Any]] = [
        {"$match": match},
        {"$group": {"_id": "$source", "count": {"$sum": 1}}},
    ]
    rows_ch = await db.bookings.aggregate(pipeline_channel).to_list(length=None)
    by_channel: Dict[str, int] = {}
    for r in rows_ch:
        key = (r.get("_id") or "unknown").lower()
        by_channel[key] = int(r.get("count") or 0)

    # Product type breakdown
    pipeline_type: List[Dict[str, Any]] = [
        {"$match": match},
        {"$group": {"_id": "$product_type", "count": {"$sum": 1}}},
    ]
    rows_t = await db.bookings.aggregate(pipeline_type).to_list(length=None)
    by_product_type: Dict[str, int] = {}
    for r in rows_t:
        key = (r.get("_id") or "unknown").lower()
        by_product_type[key] = int(r.get("count") or 0)

    # Currency heuristic: first non-empty booking currency
    currency_doc = await db.bookings.find_one(match, {"currency": 1})
    currency = (currency_doc or {}).get("currency") or "EUR"

    linked_agency_name: Optional[str] = None
    if linked_agency_id:
        agency_doc = await _load_agency_min(db, org_id, str(linked_agency_id))
        if agency_doc:
            linked_agency_id = str(agency_doc.get("_id"))
            linked_agency_name = agency_doc.get("name") or None

    return PartnerActivitySummaryOut(
        partner_id=partner_id_str,
        partner_name=partner_name,
        linked_agency_id=str(linked_agency_id) if linked_agency_id else None,
        linked_agency_name=linked_agency_name,
        total_bookings=total_bookings,
        total_amount_cents=total_amount_cents,
        currency=currency,
        by_channel=by_channel,
        by_product_type=by_product_type,
        first_booking_at=first_booking_at.isoformat() if first_booking_at else None,
        last_booking_at=last_booking_at.isoformat() if last_booking_at else None,
    )
