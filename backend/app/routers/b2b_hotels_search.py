from __future__ import annotations

from datetime import date
from typing import Any, List, Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field, conint

from app.auth import get_current_user, require_roles
from app.db import get_db
from app.errors import AppError

router = APIRouter(prefix="/api/b2b", tags=["b2b-hotels-search"])


class SearchOccupancy(BaseModel):
    adults: conint(ge=1, le=8) = 2
    children: conint(ge=0, le=8) = 0


class HotelSearchResponseItem(BaseModel):
    product_id: str
    rate_plan_id: str
    hotel_name: str
    city: str
    country: str
    board: str
    base_currency: str
    base_net: float
    selling_currency: str
    selling_total: float
    nights: int
    occupancy: SearchOccupancy


class HotelSearchResponse(BaseModel):
    items: List[HotelSearchResponseItem] = Field(default_factory=list)


@router.get("/hotels/search", response_model=HotelSearchResponse, dependencies=[Depends(require_roles(["agency_admin", "agency_agent"]))])
async def search_b2b_hotels(
    city: str = Query(..., min_length=1),
    check_in: date = Query(...),
    check_out: date = Query(...),
    adults: int = Query(2, ge=1, le=8),
    children: int = Query(0, ge=0, le=8),
    currency: Optional[str] = Query(None, min_length=3, max_length=3),
    limit: int = Query(20, ge=1, le=100),
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    """Simple catalog + static pricing bridge for P0.2 search.

    - Filters active hotel products by city (case-insensitive) and status.
    - Joins active EUR rate plans.
    - Applies a naive markup to derive selling price (placeholder until real B2B pricing rules).
    """

    if check_out <= check_in:
        raise AppError(422, "invalid_date_range", "Check-out must be after check-in", {})

    org_id = user.get("organization_id")
    agency_id = user.get("agency_id")
    if not agency_id:
        raise AppError(403, "forbidden", "User is not bound to an agency", {})

    # Normalize city for case-insensitive match
    q_city = (city or "").strip()
    if not q_city:
        raise AppError(422, "validation_error", "City is required", {"field": "city"})

    # Simple case-insensitive match via regex; limited to small catalog
    city_regex = {"$regex": f"^{q_city}$", "$options": "i"}

    product_cursor = db.products.find(
        {
            "organization_id": org_id,
            "type": "hotel",
            "status": "active",
            "location.city": city_regex,
        },
        {"_id": 1, "name": 1, "location": 1, "default_currency": 1},
    ).limit(limit)
    products = await product_cursor.to_list(length=limit)

    if not products:
        return HotelSearchResponse(items=[])

    product_ids = [p["_id"] for p in products]

    # Optional B2B Marketplace gating: if this agency is linked to an approved partner
    # (via partner_profiles.linked_agency_id), and that partner has explicit product
    # authorizations, only include products with is_enabled=True. If no linked partner
    # or no enabled products are found, we gracefully fall back to empty results.
    partner = await db.partner_profiles.find_one(
        {
            "organization_id": org_id,
            "linked_agency_id": {"$in": [str(agency_id), agency_id]},
            "status": "approved",
        },
        {"_id": 1},
    )

    if partner:
        partner_id_str = str(partner["_id"])
        auth_cursor = db.b2b_product_authorizations.find(
            {
                "organization_id": org_id,
                "partner_id": partner_id_str,
                "product_id": {"$in": product_ids},
                "is_enabled": True,
            },
            {"product_id": 1, "_id": 0},
        )
        auth_docs = await auth_cursor.to_list(length=None)
        enabled_ids = {doc["product_id"] for doc in auth_docs if doc.get("product_id")}
        if not enabled_ids:
            return HotelSearchResponse(items=[])
        # Narrow product_ids to enabled ones only
        product_ids = [pid for pid in product_ids if pid in enabled_ids]
        if not product_ids:
            return HotelSearchResponse(items=[])

    rp_cursor = db.rate_plans.find(
        {
            "organization_id": org_id,
            "product_id": {"$in": product_ids},
            "status": "active",
            "currency": "EUR",
        }
    )
    rate_plans = await rp_cursor.to_list(length=1000)

    if not rate_plans:
        return HotelSearchResponse(items=[])

    prod_map: dict[ObjectId, dict[str, Any]] = {p["_id"]: p for p in products}

    nights = (check_out - check_in).days
    nights = max(nights, 1)

    occ = SearchOccupancy(adults=adults, children=children)

    items: List[HotelSearchResponseItem] = []
    for rp in rate_plans:
        prod = prod_map.get(rp["product_id"])
        if not prod:
            continue

        base_currency = rp.get("currency", "EUR")
        base_net = float(rp.get("base_net_price") or 0.0)
        if base_net <= 0:
            # Skip non-priced plans for P0.2
            continue

        # Naive P0.2 pricing: per-night base_net * nights, then 10% markup placeholder
        base_total = round(base_net * nights, 2)
        selling_currency = currency or base_currency
        # FX integration TODO: for now, assume 1:1 if different currency requested
        sell_total = round(base_total * 1.1, 2)

        items.append(
            HotelSearchResponseItem(
                product_id=str(prod["_id"]),
                rate_plan_id=str(rp["_id"]),
                hotel_name=(prod.get("name") or {}).get("tr")
                or (prod.get("name") or {}).get("en")
                or "Hotel",
                city=(prod.get("location") or {}).get("city") or "",
                country=(prod.get("location") or {}).get("country") or "",
                board=rp.get("board") or "RO",
                base_currency=base_currency,
                base_net=base_total,
                selling_currency=selling_currency,
                selling_total=sell_total,
                nights=nights,
                occupancy=occ,
            )
        )

    # Deterministic order for demo: by hotel_name, then board
    items.sort(key=lambda x: (x.hotel_name.lower(), x.board))

    return HotelSearchResponse(items=items)
