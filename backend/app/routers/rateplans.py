from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.auth import get_current_user
from app.db import get_db
from app.schemas import RatePlanIn
from app.utils import now_utc, serialize_doc

router = APIRouter(prefix="/api/rateplans", tags=["rateplans"])


@router.post("", dependencies=[Depends(get_current_user)])
async def create_rateplan(payload: RatePlanIn, user=Depends(get_current_user)):
    db = await get_db()
    # Validate product exists
    prod = await db.products.find_one({"organization_id": user["organization_id"], "_id": payload.product_id})
    if not prod:
        raise HTTPException(status_code=404, detail="Ürün bulunamadı")

    doc = payload.model_dump()
    doc.update(
        {
            "organization_id": user["organization_id"],
            "created_at": now_utc(),
            "updated_at": now_utc(),
            "created_by": user.get("email"),
            "updated_by": user.get("email"),
        }
    )
    res = await db.rate_plans.insert_one(doc)
    saved = await db.rate_plans.find_one({"_id": res.inserted_id})
    return serialize_doc(saved)


@router.get("", dependencies=[Depends(get_current_user)])
async def list_rateplans(product_id: str | None = None, user=Depends(get_current_user)):
    db = await get_db()
    query: dict[str, object] = {"organization_id": user["organization_id"]}
    if product_id:
        query["product_id"] = product_id
    docs = await db.rate_plans.find(query).sort("created_at", -1).to_list(200)
    return [serialize_doc(d) for d in docs]


@router.put("/{rateplan_id}", dependencies=[Depends(get_current_user)])
async def update_rateplan(rateplan_id: str, payload: RatePlanIn, user=Depends(get_current_user)):
    db = await get_db()
    existing = await db.rate_plans.find_one({"organization_id": user["organization_id"], "_id": rateplan_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Rate plan bulunamadı")

    await db.rate_plans.update_one(
        {"_id": existing["_id"]},
        {"$set": {**payload.model_dump(), "updated_at": now_utc(), "updated_by": user.get("email")}},
    )
    doc = await db.rate_plans.find_one({"_id": existing["_id"]})
    return serialize_doc(doc)


@router.delete("/{rateplan_id}", dependencies=[Depends(get_current_user)])
async def delete_rateplan(rateplan_id: str, user=Depends(get_current_user)):
    db = await get_db()
    await db.rate_plans.delete_one({"organization_id": user["organization_id"], "_id": rateplan_id})
    return {"ok": True}
