from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from pymongo import DESCENDING

from app.db import get_db

router = APIRouter(prefix="/api/public", tags=["public-search"])
from bson import ObjectId



def _parse_date(raw: Optional[str]) -> Optional[date]:
  if not raw:
    return None
  try:
    return date.fromisoformat(raw)


async def _resolve_partner_agency(db, organization_id: str, partner: str):
  """Resolve agency document for given partner id (used by iframe/public flows).

  Accepts either string _id or ObjectId-compatible hex string. Returns the
  agency document or None when not found.
  """

  if not partner:
    return None

  agency = await db.agencies.find_one({"_id": partner, "organization_id": organization_id})
  if agency:
    return agency

  try:
    oid = ObjectId(partner)
  except Exception:
    return None

  agency = await db.agencies.find_one({"_id": oid, "organization_id": organization_id})
  return agency

  except Exception:
    return None


@router.get("/search")
async def public_search_catalog(
  request: Request,
  org: str = Query(..., min_length=1, description="Organization id (tenant)"),
  q: Optional[str] = Query(None, description="Free-text search on product name"),
  page: int = Query(1, ge=1),
  page_size: int = Query(20, ge=1, le=50),
  sort: Optional[str] = Query("price_asc"),
  date_from: Optional[str] = Query(None),
  date_to: Optional[str] = Query(None),
  product_type: Optional[str] = Query(None, alias="type", description="Optional product type filter (e.g. hotel, tour)"),
  partner: Optional[str] = Query(None, description="Optional partner/agency id for B2B iframe pricing"),
  db=Depends(get_db),
) -> JSONResponse:
  """Public product search for booking engine v1.

  - Tenant-aware via explicit `org` query param
  - Only active products with at least one published version are returned
  - Rough "from" price derived from active rate plans (base_net_price)
  - PII-free response, cache-friendly headers
  """

  client_ip = request.client.host if request.client else None

  # Basic Mongo-based throttle per IP + org + minute bucket
  if client_ip:
    now = datetime.utcnow().replace(second=0, microsecond=0)
    key = {"ip": client_ip, "org": org, "minute": now}
    await db.public_search_telemetry.update_one(
      key,
      {"$inc": {"count": 1}, "$setOnInsert": {"first_seen_at": datetime.utcnow()}},
      upsert=True,
    )
    doc = await db.public_search_telemetry.find_one(key)
    if doc and int(doc.get("count", 0)) > 60:
      raise HTTPException(status_code=429, detail="RATE_LIMITED")

  # Parse date range to approximate nights for pricing
  df = _parse_date(date_from)
  dt = _parse_date(date_to)
  nights = 1
  if df and dt and dt > df:
    nights = max((dt - df).days, 1)

  # Base filter: active products for this org
  filt: Dict[str, Any] = {"organization_id": org, "status": "active"}
  if q:
    filt["name_search"] = {"$regex": q.strip().lower()}
  if product_type:
    filt["type"] = product_type

  # Optional partner/agency-based visibility filter
  agency_id = None
  if partner:
    agency = await _resolve_partner_agency(db, org, partner)
    if agency:
      agency_id = str(agency.get("_id"))

  if agency_id:
    # Simple v1: only show products that do NOT explicitly opt-out from this agency.
    # Future extension: explicit allow-list via b2b_contracts collection.
    filt["b2b_visibility"] = {"$nin": [agency_id]}

  total = await db.products.count_documents(filt)

  skip = (page - 1) * page_size
  cursor = db.products.find(
    filt,
    {"_id": 1, "type": 1, "name": 1, "location": 1, "default_currency": 1},
  ).sort("created_at", DESCENDING).skip(skip).limit(page_size)
  products: List[Dict[str, Any]] = await cursor.to_list(length=page_size)

  if not products:
    response = {"items": [], "page": page, "page_size": page_size, "total": total}
    resp = JSONResponse(status_code=200, content=response)
    resp.headers["Cache-Control"] = "public, max-age=60, stale-while-revalidate=300"
    return resp

  product_ids = [p["_id"] for p in products]

  # Fetch latest published product_version per product
  pv_cur = db.product_versions.find(
    {"organization_id": org, "product_id": {"$in": product_ids}, "status": "published"},
    {"product_id": 1, "version": 1, "content": 1},
  ).sort("version", DESCENDING)
  pv_list: List[Dict[str, Any]] = await pv_cur.to_list(length=2000)
  latest_version: Dict[str, Dict[str, Any]] = {}
  for pv in pv_list:
    pid = str(pv["product_id"])
    if pid not in latest_version:
      latest_version[pid] = pv

  # Fetch active rate plans per product to derive rough from-price
  rp_cur = db.rate_plans.find(
    {"organization_id": org, "product_id": {"$in": product_ids}, "status": "active"},
    {"product_id": 1, "currency": 1, "base_net_price": 1},
  )
  rp_list: List[Dict[str, Any]] = await rp_cur.to_list(length=2000)
  best_rate: Dict[Any, Dict[str, Any]] = {}
  for rp in rp_list:
    pid = rp["product_id"]
    cur_best = best_rate.get(pid)
    base_net = float(rp.get("base_net_price") or 0.0)
    if base_net <= 0:
      continue
    if not cur_best or base_net < float(cur_best.get("base_net_price") or 0.0):
      best_rate[pid] = rp

  items: List[Dict[str, Any]] = []
  for prod in products:
    pid = prod["_id"]
    pv = latest_version.get(str(pid))
    if not pv:
      # Skip products without a published version
      continue

    name = prod.get("name") or {}
    title = name.get("tr") or name.get("en") or "Ürün"
    summary = ""
    image_url = None

    content = (pv.get("content") or {})
    desc = content.get("description") or {}
    summary = desc.get("tr") or desc.get("en") or ""

    images = content.get("images") or []
    if images:
      first = images[0]
      image_url = first.get("url") or first.get("src")

    rate = best_rate.get(pid)
    price_obj: Dict[str, Any]
    if rate:
      currency = (rate.get("currency") or prod.get("default_currency") or "EUR").upper()
      base_net = float(rate.get("base_net_price") or 0.0)
      base_total = max(base_net * nights, 0.0)
      amount_cents = int(round(base_total * 100))
      price_obj = {"amount_cents": amount_cents, "currency": currency}
    else:
      currency = (prod.get("default_currency") or "EUR").upper()
      price_obj = {"amount_cents": 0, "currency": currency}

    item = {
      "product_id": str(pid),
      "type": prod.get("type") or "hotel",
      "title": title,
      "summary": summary,
      "price": price_obj,
      "availability": {"status": "available"},
      "image_url": image_url,
      "policy": {"refundable": True},
    }
    items.append(item)

  # Simple sorting: by price or title
  if sort == "price_desc":
    items.sort(key=lambda x: x["price"]["amount_cents"], reverse=True)
  elif sort == "title_asc":
    items.sort(key=lambda x: (x["title"] or "").lower())
  else:  # default price_asc
    items.sort(key=lambda x: x["price"]["amount_cents"])

  response = {"items": items, "page": page, "page_size": page_size, "total": total}
  resp = JSONResponse(status_code=200, content=response)
  resp.headers["Cache-Control"] = "public, max-age=60, stale-while-revalidate=300"
  return resp
