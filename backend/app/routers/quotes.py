from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.auth import get_current_user
from app.db import get_db
from app.schemas import QuoteConvertIn, QuoteIn
from app.services.pricing import calc_price_for_date
from app.services.reservations import create_reservation
from app.utils import now_utc, safe_float, serialize_doc

router = APIRouter(prefix="/api/quotes", tags=["quotes"])


def _calc_quote_total(items: list[dict]) -> float:
    total = 0.0
    for it in items:
        total += safe_float(it.get("total"), 0.0)
    return round(total, 2)


@router.post("", dependencies=[Depends(get_current_user)])
async def create_quote(payload: QuoteIn, user=Depends(get_current_user)):
    db = await get_db()
    cust = await db.customers.find_one({"organization_id": user["organization_id"], "_id": payload.customer_id})
    if not cust:
        raise HTTPException(status_code=404, detail="Müşteri bulunamadı")

    total = _calc_quote_total(payload.items)

    doc = payload.model_dump()
    doc.update(
        {
            "organization_id": user["organization_id"],
            "total": total,
            "created_at": now_utc(),
            "updated_at": now_utc(),
            "created_by": user.get("email"),
            "updated_by": user.get("email"),
        }
    )
    ins = await db.quotes.insert_one(doc)
    saved = await db.quotes.find_one({"_id": ins.inserted_id})
    return serialize_doc(saved)


@router.get("", dependencies=[Depends(get_current_user)])
async def list_quotes(status: str | None = None, user=Depends(get_current_user)):
    db = await get_db()
    q: dict[str, object] = {"organization_id": user["organization_id"]}
    if status:
        q["status"] = status
    docs = await db.quotes.find(q).sort("created_at", -1).to_list(300)
    return [serialize_doc(d) for d in docs]


@router.post("/convert", dependencies=[Depends(get_current_user)])
async def convert(payload: QuoteConvertIn, user=Depends(get_current_user)):
    db = await get_db()
    quote = await db.quotes.find_one({"organization_id": user["organization_id"], "_id": payload.quote_id})
    if not quote:
        raise HTTPException(status_code=404, detail="Teklif bulunamadı")

    if quote.get("status") == "converted":
        # return existing reservation if stored
        res_id = quote.get("converted_reservation_id")
        if res_id:
            res = await db.reservations.find_one({"organization_id": user["organization_id"], "_id": res_id})
            if res:
                return serialize_doc(res)

    if not quote.get("items"):
        raise HTTPException(status_code=400, detail="Teklifte kalem yok")

    # For v1 take first item
    item = (quote.get("items") or [])[0]
    required = ["product_id", "start_date", "customer_id", "pax"]
    for r in required:
        if not item.get(r) and r != "customer_id":
            raise HTTPException(status_code=400, detail=f"Eksik alan: {r}")

    reservation_payload = {
        "idempotency_key": payload.idempotency_key,
        "product_id": item.get("product_id"),
        "customer_id": quote.get("customer_id"),
        "start_date": item.get("start_date"),
        "end_date": item.get("end_date"),
        "pax": int(item.get("pax") or 1),
        "channel": "direct",
        "agency_id": None,
    }

    res_doc = await create_reservation(org_id=user["organization_id"], user_email=user.get("email"), payload=reservation_payload)

    await db.quotes.update_one(
        {"_id": quote["_id"]},
        {"$set": {"status": "converted", "converted_reservation_id": res_doc["_id"], "updated_at": now_utc()}},
    )

    return serialize_doc(res_doc)
