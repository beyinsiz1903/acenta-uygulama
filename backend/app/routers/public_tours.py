from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse

from app.db import get_db

router = APIRouter(prefix="/api/public/tours", tags=["public-tours"])


@router.get("/search")
async def public_search_tours(
    org: str = Query(..., min_length=1, description="Organization id (tenant)"),
    q: Optional[str] = Query(None, description="Free-text search on tour name or destination"),
    destination: Optional[str] = Query(None, description="Destination filter"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    db=Depends(get_db),
) -> JSONResponse:
    filt: Dict[str, Any] = {"organization_id": org}
    if q:
        filt["name"] = {"$regex": q.strip(), "$options": "i"}
    if destination:
        filt["destination"] = {"$regex": destination.strip(), "$options": "i"}

    skip = (page - 1) * page_size

    total = await db.tours.count_documents(filt)
    cursor = db.tours.find(filt).sort("created_at", -1).skip(skip).limit(page_size)
    docs = await cursor.to_list(length=page_size)

    items: List[Dict[str, Any]] = []
    for doc in docs:
        items.append(
            {
                "id": str(doc.get("_id")),
                "name": doc.get("name") or "",
                "destination": doc.get("destination") or "",
                "base_price_cents": int(float(doc.get("base_price") or 0.0) * 100),
                "currency": (doc.get("currency") or "EUR").upper(),
            }
        )

    payload = {"items": items, "page": page, "page_size": page_size, "total": total}
    return JSONResponse(status_code=200, content=payload)


@router.get("/{tour_id}")
async def public_get_tour(
    tour_id: str,
    org: str = Query(..., min_length=1, description="Organization id (tenant)"),
    db=Depends(get_db),
) -> JSONResponse:
    from bson import ObjectId
    from bson.errors import InvalidId
    
    try:
        # Convert string ID to ObjectId
        object_id = ObjectId(tour_id)
    except InvalidId:
        return JSONResponse(status_code=404, content={"code": "TOUR_NOT_FOUND", "message": "Tur bulunamadı"})
    
    doc = await db.tours.find_one({"_id": object_id, "organization_id": org})
    if not doc:
        return JSONResponse(status_code=404, content={"code": "TOUR_NOT_FOUND", "message": "Tur bulunamadı"})

    payload = {
        "id": str(doc.get("_id")),
        "name": doc.get("name") or "",
        "description": doc.get("description") or "",
        "destination": doc.get("destination") or "",
        "base_price": float(doc.get("base_price") or 0.0),
        "currency": (doc.get("currency") or "EUR").upper(),
        "status": doc.get("status") or "active",
    }
    return JSONResponse(status_code=200, content=payload)
