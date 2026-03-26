from __future__ import annotations

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException

from app.auth import get_current_user
from app.db import get_db
from app.schemas import CustomerIn
from app.utils import now_utc, serialize_doc, to_object_id

router = APIRouter(prefix="/api/customers", tags=["customers"])


def _oid_or_400(id_str: str) -> ObjectId:
    try:
        return to_object_id(id_str)
    except Exception:
        raise HTTPException(status_code=400, detail="Geçersiz id")


@router.post("", dependencies=[Depends(get_current_user)])
async def create_customer(payload: CustomerIn, user=Depends(get_current_user)):
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
    res = await db.customers.insert_one(doc)
    saved = await db.customers.find_one({"_id": res.inserted_id})
    return serialize_doc(saved)


@router.get("", dependencies=[Depends(get_current_user)])
async def list_customers(q: str | None = None, user=Depends(get_current_user)):
    db = await get_db()
    query: dict[str, object] = {"organization_id": user["organization_id"]}
    if q:
        query["$or"] = [
            {"name": {"$regex": q, "$options": "i"}},
            {"email": {"$regex": q, "$options": "i"}},
            {"phone": {"$regex": q, "$options": "i"}},
        ]
    docs = await db.customers.find(query).sort("created_at", -1).to_list(200)
    return [serialize_doc(d) for d in docs]


@router.get("/{customer_id}", dependencies=[Depends(get_current_user)])
async def get_customer(customer_id: str, user=Depends(get_current_user)):
    db = await get_db()
    doc = await db.customers.find_one({"organization_id": user["organization_id"], "_id": _oid_or_400(customer_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Müşteri bulunamadı")
    return serialize_doc(doc)


@router.put("/{customer_id}", dependencies=[Depends(get_current_user)])
async def update_customer(customer_id: str, payload: CustomerIn, user=Depends(get_current_user)):
    db = await get_db()
    existing = await db.customers.find_one({"organization_id": user["organization_id"], "_id": _oid_or_400(customer_id)})
    if not existing:
        raise HTTPException(status_code=404, detail="Müşteri bulunamadı")

    await db.customers.update_one(
        {"_id": existing["_id"]},
        {"$set": {**payload.model_dump(), "updated_at": now_utc(), "updated_by": user.get("email")}},
    )
    doc = await db.customers.find_one({"_id": existing["_id"]})
    return serialize_doc(doc)


@router.delete("/{customer_id}", dependencies=[Depends(get_current_user)])
async def delete_customer(customer_id: str, user=Depends(get_current_user)):
    db = await get_db()
    await db.customers.delete_one({"organization_id": user["organization_id"], "_id": _oid_or_400(customer_id)})
    return {"ok": True}
