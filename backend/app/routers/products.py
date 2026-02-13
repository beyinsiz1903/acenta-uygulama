from __future__ import annotations

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException

from app.auth import get_current_user
from app.db import get_db
from app.schemas import ProductIn
from app.utils import now_utc, serialize_doc, to_object_id

router = APIRouter(prefix="/products", tags=["products"])


def _oid_or_400(id_str: str) -> ObjectId:
    try:
        return to_object_id(id_str)
    except Exception:
        raise HTTPException(status_code=400, detail="Geçersiz id")


@router.post("", dependencies=[Depends(get_current_user)])
async def create_product(payload: ProductIn, user=Depends(get_current_user)):
    db = await get_db()
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
    res = await db.products.insert_one(doc)
    saved = await db.products.find_one({"_id": res.inserted_id})
    return serialize_doc(saved)


@router.get("", dependencies=[Depends(get_current_user)])
async def list_products(type: str | None = None, q: str | None = None, user=Depends(get_current_user)):
    db = await get_db()
    query: dict[str, object] = {"organization_id": user["organization_id"]}
    if type:
        query["type"] = type
    if q:
        query["title"] = {"$regex": q, "$options": "i"}
    docs = await db.products.find(query).sort("created_at", -1).to_list(200)
    return [serialize_doc(d) for d in docs]


@router.get("/{product_id}", dependencies=[Depends(get_current_user)])
async def get_product(product_id: str, user=Depends(get_current_user)):
    db = await get_db()
    doc = await db.products.find_one({"organization_id": user["organization_id"], "_id": _oid_or_400(product_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Ürün bulunamadı")
    return serialize_doc(doc)


@router.put("/{product_id}", dependencies=[Depends(get_current_user)])
async def update_product(product_id: str, payload: ProductIn, user=Depends(get_current_user)):
    db = await get_db()
    existing = await db.products.find_one({"organization_id": user["organization_id"], "_id": _oid_or_400(product_id)})
    if not existing:
        raise HTTPException(status_code=404, detail="Ürün bulunamadı")

    await db.products.update_one(
        {"_id": existing["_id"]},
        {"$set": {**payload.model_dump(), "updated_at": now_utc(), "updated_by": user.get("email")}},
    )
    doc = await db.products.find_one({"_id": existing["_id"]})
    return serialize_doc(doc)


@router.delete("/{product_id}", dependencies=[Depends(get_current_user)])
async def delete_product(product_id: str, user=Depends(get_current_user)):
    db = await get_db()
    product_oid = _oid_or_400(product_id)
    await db.products.delete_one({"organization_id": user["organization_id"], "_id": product_oid})
    await db.rate_plans.delete_many({"organization_id": user["organization_id"], "product_id": product_oid})
    await db.inventory.delete_many({"organization_id": user["organization_id"], "product_id": product_oid})
    return {"ok": True}
