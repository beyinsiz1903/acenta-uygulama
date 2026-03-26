from __future__ import annotations

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException

from app.auth import get_current_user
from app.db import get_db
from app.schemas import PaymentCreateIn
from app.services.reservations import apply_payment
from app.utils import now_utc, serialize_doc, to_object_id

router = APIRouter(prefix="/payments", tags=["payments"])


def _oid_or_400(id_str: str) -> ObjectId:
    try:
        return to_object_id(id_str)
    except Exception:
        raise HTTPException(status_code=400, detail="Geçersiz id")


@router.post("", dependencies=[Depends(get_current_user)])
async def create_payment(payload: PaymentCreateIn, user=Depends(get_current_user)):
    db = await get_db()

    res_oid = _oid_or_400(payload.reservation_id)
    res = await db.reservations.find_one({"organization_id": user["organization_id"], "_id": res_oid})
    if not res:
        raise HTTPException(status_code=404, detail="Rezervasyon bulunamadı")

    doc = payload.model_dump()
    doc["reservation_id"] = res_oid
    doc.update(
        {
            "organization_id": user["organization_id"],
            "created_at": now_utc(),
            "updated_at": now_utc(),
            "created_by": user.get("email"),
            "updated_by": user.get("email"),
        }
    )

    ins = await db.payments.insert_one(doc)
    await apply_payment(user["organization_id"], payload.reservation_id, payload.amount)

    saved = await db.payments.find_one({"_id": ins.inserted_id})
    return serialize_doc(saved)
