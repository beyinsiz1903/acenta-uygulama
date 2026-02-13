from __future__ import annotations

from typing import Any

from bson import ObjectId
from fastapi import HTTPException

from app.db import get_db
from app.services.inventory import consume_inventory, release_inventory
from app.services.pricing import calc_price_for_date
from app.utils import date_range_yyyy_mm_dd, generate_pnr, generate_voucher_no, now_utc, safe_float, to_object_id


async def create_reservation(*, org_id: str, user_email: str, payload: dict[str, Any]) -> dict[str, Any]:
    db = await get_db()

    idempotency_key = payload.get("idempotency_key")
    if idempotency_key:
        existing = await db.reservations.find_one({"organization_id": org_id, "idempotency_key": idempotency_key})
        if existing:
            return existing

    try:
        product_oid = to_object_id(payload["product_id"])
        customer_oid = to_object_id(payload["customer_id"])
    except Exception:
        raise HTTPException(status_code=400, detail="Geçersiz id")

    product = await db.products.find_one({"organization_id": org_id, "_id": product_oid})
    if not product:
        raise HTTPException(status_code=404, detail="Ürün bulunamadı")

    customer = await db.customers.find_one({"organization_id": org_id, "_id": customer_oid})
    if not customer:
        raise HTTPException(status_code=404, detail="Müşteri bulunamadı")

    rate_plan = await db.rate_plans.find_one({"organization_id": org_id, "product_id": product_oid})

    start_date = payload["start_date"]
    end_date = payload.get("end_date")
    pax = int(payload.get("pax") or 1)

    if end_date:
        dates = date_range_yyyy_mm_dd(start_date, end_date)
        if not dates:
            raise HTTPException(status_code=400, detail="Tarih aralığı geçersiz")
    else:
        dates = [start_date]

    consumed: list[str] = []
    for d in dates:
        ok = await consume_inventory(org_id, payload["product_id"], d, pax)
        if not ok:
            for rd in consumed:
                await release_inventory(org_id, product_oid, rd, pax)
            raise HTTPException(status_code=409, detail=f"Müsaitlik yok: {d}")
        consumed.append(d)

    currency = (rate_plan or {}).get("currency") or "TRY"
    total = 0.0
    price_items: list[dict[str, Any]] = []

    for d in dates:
        inv = await db.inventory.find_one({"organization_id": org_id, "product_id": product_oid, "date": d})
        if inv and inv.get("price") is not None:
            price = safe_float(inv.get("price"), 0.0)
        elif rate_plan:
            price = calc_price_for_date(rate_plan, d)
        else:
            price = 0.0

        line_total = round(price * pax, 2)
        price_items.append({"date": d, "unit_price": price, "pax": pax, "total": line_total})
        total += line_total

    channel = payload.get("channel") or "direct"
    agency_oid: ObjectId | None = None
    discount_amount = 0.0
    commission_amount = 0.0

    if payload.get("agency_id"):
        try:
            agency_oid = to_object_id(payload.get("agency_id"))
        except Exception:
            agency_oid = None

    if channel == "b2b" and agency_oid:
        agency = await db.agencies.find_one({"organization_id": org_id, "_id": agency_oid})
        if agency:
            discount_percent = safe_float(agency.get("discount_percent"), 0.0)
            commission_percent = safe_float(agency.get("commission_percent"), 0.0)
            discount_amount = round(total * (discount_percent / 100.0), 2)
            total = round(max(0.0, total - discount_amount), 2)
            commission_amount = round(total * (commission_percent / 100.0), 2)

    res_doc = {
        "organization_id": org_id,
        "pnr": generate_pnr(),
        "voucher_no": generate_voucher_no(),
        "idempotency_key": idempotency_key,
        "product_id": product_oid,
        "customer_id": customer_oid,
        "start_date": start_date,
        "end_date": end_date,
        "dates": dates,
        "pax": pax,
        "status": "pending",
        "currency": currency,
        "total_price": round(total, 2),
        "price_items": price_items,
        "discount_amount": discount_amount,
        "commission_amount": commission_amount,
        "paid_amount": 0.0,
        "channel": channel,
        "agency_id": agency_oid,
        "created_at": now_utc(),
        "updated_at": now_utc(),
        "created_by": user_email,
        "updated_by": user_email,
    }

    ins = await db.reservations.insert_one(res_doc)
    saved = await db.reservations.find_one({"_id": ins.inserted_id})
    assert saved

    # ── Sheet Write-Back Hook (best-effort, fire-and-forget) ──
    try:
        from app.services.sheet_writeback_service import on_reservation_created
        tenant_id = org_id  # tenant_id == org_id in current architecture
        await on_reservation_created(db, tenant_id, org_id, saved)
    except Exception as wb_err:
        import logging
        logging.getLogger("sheet_writeback").warning(
            "Write-back hook failed for reservation %s: %s", str(ins.inserted_id), wb_err
        )

    return saved


async def _find_reservation_by_id(db, org_id: str, reservation_id: str):
    """Find reservation by _id supporting both ObjectId and string IDs."""
    try:
        res_oid = to_object_id(reservation_id)
        doc = await db.reservations.find_one({"organization_id": org_id, "_id": res_oid})
        if doc:
            return doc
    except Exception:
        pass
    # Fallback: try string _id (e.g., demo_seed IDs)
    return await db.reservations.find_one({"organization_id": org_id, "_id": reservation_id})


async def set_reservation_status(org_id: str, reservation_id: str, status: str, user_email: str) -> dict[str, Any]:
    db = await get_db()
    res = await _find_reservation_by_id(db, org_id, reservation_id)
    if not res:
        raise HTTPException(status_code=404, detail="Rezervasyon bulunamadı")

    await db.reservations.update_one(
        {"_id": res["_id"]},
        {"$set": {"status": status, "updated_at": now_utc(), "updated_by": user_email}},
    )

    updated = await db.reservations.find_one({"_id": res["_id"]})
    assert updated

    if status == "cancelled":
        pax = int(updated.get("pax") or 1)
        for d in updated.get("dates") or []:
            await release_inventory(org_id, updated["product_id"], d, pax)

        # ── Sheet Write-Back Hook (cancellation) ──
        try:
            from app.services.sheet_writeback_service import on_reservation_cancelled
            tenant_id = org_id
            await on_reservation_cancelled(db, tenant_id, org_id, updated)
        except Exception as wb_err:
            import logging
            logging.getLogger("sheet_writeback").warning(
                "Write-back cancel hook failed: %s", wb_err
            )

    return updated


async def apply_payment(org_id: str, reservation_id: str, amount: float) -> dict[str, Any]:
    db = await get_db()
    try:
        res_oid = to_object_id(reservation_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Geçersiz id")

    res = await db.reservations.find_one({"organization_id": org_id, "_id": res_oid})
    if not res:
        raise HTTPException(status_code=404, detail="Rezervasyon bulunamadı")

    paid = safe_float(res.get("paid_amount"), 0.0) + safe_float(amount, 0.0)
    total = safe_float(res.get("total_price"), 0.0)
    status = res.get("status")
    if paid >= total and status in ["pending", "confirmed"]:
        status = "paid"

    await db.reservations.update_one(
        {"_id": res["_id"]},
        {"$set": {"paid_amount": round(paid, 2), "status": status, "updated_at": now_utc()}},
    )

    updated = await db.reservations.find_one({"_id": res["_id"]})
    assert updated
    return updated
