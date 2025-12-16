from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.auth import get_current_user
from app.db import get_db
from app.schemas import LeadIn
from app.utils import now_utc, serialize_doc

router = APIRouter(prefix="/api/leads", tags=["leads"])


@router.post("", dependencies=[Depends(get_current_user)])
async def create_lead(payload: LeadIn, user=Depends(get_current_user)):
    db = await get_db()
    cust = await db.customers.find_one({"organization_id": user["organization_id"], "_id": payload.customer_id})
    if not cust:
        raise HTTPException(status_code=404, detail="Müşteri bulunamadı")

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
    ins = await db.leads.insert_one(doc)
    saved = await db.leads.find_one({"_id": ins.inserted_id})
    return serialize_doc(saved)


@router.get("", dependencies=[Depends(get_current_user)])
async def list_leads(status: str | None = None, user=Depends(get_current_user)):
    db = await get_db()
    q: dict[str, object] = {"organization_id": user["organization_id"]}
    if status:
        q["status"] = status
    docs = await db.leads.find(q).sort("created_at", -1).to_list(300)
    return [serialize_doc(d) for d in docs]


@router.put("/{lead_id}", dependencies=[Depends(get_current_user)])
async def update_lead(lead_id: str, payload: LeadIn, user=Depends(get_current_user)):
    db = await get_db()
    existing = await db.leads.find_one({"organization_id": user["organization_id"], "_id": lead_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Lead bulunamadı")

    await db.leads.update_one(
        {"_id": existing["_id"]},
        {"$set": {**payload.model_dump(), "updated_at": now_utc(), "updated_by": user.get("email")}},
    )
    doc = await db.leads.find_one({"_id": existing["_id"]})
    return serialize_doc(doc)
