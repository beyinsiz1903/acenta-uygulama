from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Dict, List, Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query

from app.auth import require_roles
from app.db import get_db
from app.utils import now_utc, to_object_id

router = APIRouter(prefix="/api/agency/catalog/overbooks", tags=["agency:catalog:overbooks"])


def _sid(x: Any) -> str:
  return str(x)


def _oid(id_str: Optional[str]) -> Optional[ObjectId]:
  if not id_str:
    return None
  try:
    return to_object_id(id_str)
  except Exception:
    return None


@router.get("")
async def list_catalog_overbooks(
  start: Optional[str] = Query(default=None),
  end: Optional[str] = Query(default=None),
  variant_id: Optional[str] = Query(default=None),
  product_id: Optional[str] = Query(default=None),
  status: Optional[str] = Query(default=None),
  q: Optional[str] = Query(default=None),
  limit: int = Query(default=50, ge=1, le=200),
  offset: int = Query(default=0, ge=0),
  db=Depends(get_db),
  user: Dict[str, Any] = Depends(require_roles(["agency_admin", "agency_agent"])),
):
  """List overbooked catalog bookings for an agency.

  - Filters on allocation.overbook == True
  - Date range uses allocation.days overlap with [start, end]
  - Default date range: today..today+30 (if not provided)
  """

  org_id = _sid(user.get("organization_id"))
  agency_id = _sid(user.get("agency_id"))
  if not agency_id:
    raise HTTPException(
      status_code=400,
      detail={"code": "USER_NOT_IN_AGENCY", "message": "Kullanıcı bir acentaya bağlı değil."},
    )

  # Date range handling
  today = now_utc().date()
  if start:
    try:
      start_date = date.fromisoformat(start)
    except Exception:
      raise HTTPException(
        status_code=400,
        detail={"code": "INVALID_DATES", "message": "Geçersiz başlangıç tarihi."},
      )
  else:
    start_date = today

  if end:
    try:
      end_date = date.fromisoformat(end)
    except Exception:
      raise HTTPException(
        status_code=400,
        detail={"code": "INVALID_DATES", "message": "Geçersiz bitiş tarihi."},
      )
  else:
    end_date = start_date + timedelta(days=30)

  if end_date < start_date:
    raise HTTPException(
      status_code=400,
      detail={"code": "INVALID_DATES", "message": "Bitiş tarihi başlangıç tarihinden önce olamaz."},
    )

  start_str = start_date.isoformat()
  end_str = end_date.isoformat()

  query: Dict[str, Any] = {
    "organization_id": org_id,
    "agency_id": agency_id,
    "allocation.overbook": True,
    "allocation.days": {"$elemMatch": {"$gte": start_str, "$lte": end_str}},
  }

  # Optional filters
  if product_id:
    prod_oid = _oid(product_id)
    if not prod_oid:
      raise HTTPException(
        status_code=404,
        detail={"code": "CATALOG_PRODUCT_NOT_FOUND", "message": "Ürün bulunamadı."},
      )
    query["product_id"] = prod_oid

  if variant_id:
    var_oid = _oid(variant_id)
    if not var_oid:
      raise HTTPException(
        status_code=404,
        detail={"code": "CATALOG_VARIANT_NOT_FOUND", "message": "Variant bulunamadı."},
      )
    query["variant_id"] = var_oid

  # Status filter: default new+approved
  if status and status.lower() != "all":
    statuses = [s.strip().lower() for s in status.split(",") if s.strip()]
    if statuses:
      query["status"] = {"$in": statuses}
  else:
    # default
    query["status"] = {"$in": ["new", "approved"]}

  # Text search in guest fields
  if q:
    regex = {"$regex": q, "$options": "i"}
    query["$or"] = [
      {"guest.full_name": regex},
      {"guest.email": regex},
      {"guest.phone": regex},
    ]

  # Count total
  total = await db.agency_catalog_booking_requests.count_documents(query)

  cursor = (
    db.agency_catalog_booking_requests.find(query, {"_id": 1})
    .sort("allocation.overbook_at", -1)
    .skip(offset)
    .limit(limit)
  )

  ids: List[ObjectId] = [doc["_id"] async for doc in cursor]
  items: List[Dict[str, Any]] = []

  if ids:
    # Fetch full docs
    full_cursor = db.agency_catalog_booking_requests.find(
      {"_id": {"$in": ids}},
      {"_id": 1, "status": 1, "product_id": 1, "variant_id": 1, "guest": 1, "dates": 1, "pax": 1, "allocation": 1, "pricing": 1},
    )
    async for doc in full_cursor:
      d: Dict[str, Any] = {
        "id": str(doc.get("_id")),
        "status": doc.get("status"),
        "product_id": str(doc.get("product_id")) if doc.get("product_id") else None,
        "variant_id": str(doc.get("variant_id")) if doc.get("variant_id") else None,
        "guest": doc.get("guest") or {},
        "dates": doc.get("dates") or {},
        "pax": doc.get("pax"),
        "allocation": doc.get("allocation") or {},
      }
      pricing = doc.get("pricing") or {}
      d["pricing"] = {
        "total": pricing.get("total"),
        "currency": pricing.get("currency"),
      }
      items.append(d)

  return {
    "items": items,
    "meta": {
      "start": start_str,
      "end": end_str,
      "limit": limit,
      "offset": offset,
      "total": total,
    },
  }
