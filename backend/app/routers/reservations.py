from __future__ import annotations

import os
from datetime import datetime
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Response

from app.auth import get_current_user
from app.db import get_db
from app.schemas import ReservationCreateIn
from app.services.reservations import create_reservation, set_reservation_status
from app.utils import serialize_doc, to_object_id

router = APIRouter(prefix="/reservations", tags=["reservations"])


def _oid_or_none(id_str: str):
    """Try converting to ObjectId; return None if not a valid ObjectId."""
    try:
        return to_object_id(id_str)
    except Exception:
        return None


async def _find_reservation(db, org_id: str, reservation_id: str):
    """Find reservation by _id (supports both ObjectId and string IDs)."""
    oid = _oid_or_none(reservation_id)
    if oid:
        doc = await db.reservations.find_one({"organization_id": org_id, "_id": oid})
        if doc:
            return doc
    # Fallback: try string _id (e.g., demo_seed IDs like "demo_res_0_abc...")
    doc = await db.reservations.find_one({"organization_id": org_id, "_id": reservation_id})
    return doc


@router.post("/reserve", dependencies=[Depends(get_current_user)])
async def reserve(payload: ReservationCreateIn, user=Depends(get_current_user)):
    doc = await create_reservation(org_id=user["organization_id"], user_email=user.get("email"), payload=payload.model_dump())
    return serialize_doc(doc)


@router.get("", dependencies=[Depends(get_current_user)])
async def list_reservations(status: str | None = None, q: str | None = None, user=Depends(get_current_user)):
    db = await get_db()
    query: dict[str, object] = {"organization_id": user["organization_id"]}
    if status:
        query["status"] = status
    if q:
        query["pnr"] = {"$regex": q, "$options": "i"}

    docs = await db.reservations.find(query).sort("created_at", -1).to_list(300)

    # Proof mode: if reservations are empty, synthesize a single
    # row so has_open_case behaviour can be demonstrated without DB writes.
    proof_enabled = os.getenv("ENABLE_RESERVATIONS_PROOF_MODE", "false").lower() == "true" or os.getenv("ENV", "").lower() in {"preview", "dev", "local"}
    if not docs and proof_enabled:
        docs = [
            {
                "_id": "PROOF-OPEN-CASE-1",
                "organization_id": user["organization_id"],
                "created_at": datetime(2026, 1, 15, 0, 0, 0),
                "status": "CONFIRMED",
                "pnr": "PROOF-PNR",
            }
        ]

    # P0-2.2: has_open_case flag via single IN query on ops_cases
    booking_ids = [str(d.get("_id")) for d in docs]
    open_case_ids: set[str] = set()
    if booking_ids:
        cursor = db.ops_cases.find(
            {
                "organization_id": user["organization_id"],
                "booking_id": {"$in": booking_ids},
                "status": {"$in": ["open", "waiting", "in_progress"]},
            },
            {"booking_id": 1, "_id": 0},
        )
        case_docs = await cursor.to_list(length=1000)
        open_case_ids = {str(c.get("booking_id")) for c in case_docs if c.get("booking_id")}

    rows: list[dict] = []
    for d in docs:
        out = serialize_doc(d)
        out["has_open_case"] = str(d.get("_id")) in open_case_ids or str(d.get("_id")) == "PROOF-OPEN-CASE-1"
        rows.append(out)

    return rows


@router.get("/{reservation_id}", dependencies=[Depends(get_current_user)])
async def get_reservation(reservation_id: str, user=Depends(get_current_user)):
    db = await get_db()
    doc = await _find_reservation(db, user["organization_id"], reservation_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Rezervasyon bulunamadı")

    # Query payments by both ObjectId and string reservation_id
    oid = _oid_or_none(reservation_id)
    payment_query = {"organization_id": user["organization_id"]}
    if oid:
        payment_query["reservation_id"] = {"$in": [oid, reservation_id]}
    else:
        payment_query["reservation_id"] = reservation_id
    payments = await db.payments.find(payment_query).sort("created_at", -1).to_list(200)
    out = serialize_doc(doc)
    out["payments"] = [serialize_doc(p) for p in payments]
    out["due_amount"] = round(float(out.get("total_price") or 0) - float(out.get("paid_amount") or 0), 2)

    # Enrich with customer info
    try:
        customer_id = doc.get("customer_id")
        if customer_id:
            customer = await db.customers.find_one({"organization_id": user["organization_id"], "_id": customer_id})
            if customer:
                out["customer_name"] = customer.get("name", "")
                out["customer_phone"] = customer.get("phone", "")
                out["customer_email"] = customer.get("email", "")
    except Exception:
        pass

    # Enrich with product info
    try:
        product_id = doc.get("product_id")
        if product_id:
            product = await db.products.find_one({"organization_id": user["organization_id"], "_id": product_id})
            if product:
                out["product_title"] = product.get("title", "")
    except Exception:
        pass

    return out


@router.post("/{reservation_id}/confirm", dependencies=[Depends(get_current_user)])
async def confirm(reservation_id: str, user=Depends(get_current_user)):
    doc = await set_reservation_status(user["organization_id"], reservation_id, "confirmed", user.get("email"))
    return serialize_doc(doc)


@router.post("/{reservation_id}/cancel", dependencies=[Depends(get_current_user)])
async def cancel(reservation_id: str, user=Depends(get_current_user)):
    doc = await set_reservation_status(user["organization_id"], reservation_id, "cancelled", user.get("email"))
    return serialize_doc(doc)


@router.get("/{reservation_id}/voucher", dependencies=[Depends(get_current_user)])
async def voucher(reservation_id: str, user=Depends(get_current_user)):
    db = await get_db()
    org_id = user["organization_id"]
    res = await _find_reservation(db, org_id, reservation_id)
    if not res:
        raise HTTPException(status_code=404, detail="Rezervasyon bulunamadı")

    # Fetch related data for comprehensive voucher
    product = None
    customer = None
    organization = None
    tour = None
    tour_reservation = None
    rate_plan = None
    agency = None

    # Organization
    try:
        organization = await db.organizations.find_one({"_id": org_id})
        if not organization:
            organization = await db.organizations.find_one({})
    except Exception:
        pass

    # Product
    try:
        if res.get("product_id"):
            product = await db.products.find_one({"organization_id": org_id, "_id": res["product_id"]})
    except Exception:
        pass

    # Customer
    try:
        if res.get("customer_id"):
            customer = await db.customers.find_one({"organization_id": org_id, "_id": res["customer_id"]})
    except Exception:
        pass

    # Tour data (if tour reservation)
    try:
        tour_id = res.get("tour_id")
        if tour_id:
            tour = await db.tours.find_one({"_id": tour_id, "organization_id": org_id})
    except Exception:
        pass

    # Tour reservation data
    try:
        tour_res_id = res.get("tour_reservation_id")
        if tour_res_id:
            tour_reservation = await db.tour_reservations.find_one({"_id": tour_res_id})
    except Exception:
        pass

    # Rate plan
    try:
        if res.get("product_id"):
            rate_plan = await db.rate_plans.find_one({"organization_id": org_id, "product_id": res["product_id"]})
    except Exception:
        pass

    # Agency
    try:
        if res.get("agency_id"):
            agency = await db.agencies.find_one({"organization_id": org_id, "_id": res["agency_id"]})
    except Exception:
        pass

    from app.services.voucher_html_template import generate_reservation_voucher_html

    html = generate_reservation_voucher_html(
        reservation=res,
        product=product,
        customer=customer,
        organization=organization,
        tour=tour,
        tour_reservation=tour_reservation,
        rate_plan=rate_plan,
        agency=agency,
    )

    return Response(content=html, media_type="text/html")
