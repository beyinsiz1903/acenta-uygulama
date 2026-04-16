from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse

from app.db import get_db
from app.errors import AppError

logger = logging.getLogger(__name__)


def _safe_email_regex(email: str) -> str:
    return f"^{re.escape(email)}$"

router = APIRouter(prefix="/api/portal", tags=["customer-portal"])


async def _get_portal_customer(token: str, db):
    if not token:
        return None
    session = await db.portal_sessions.find_one({"token": token, "active": True}, {"_id": 0})
    if not session:
        return None
    return session


@router.post("/login")
async def portal_login(payload: Dict[str, Any], db=Depends(get_db)):
    email = (payload.get("email") or "").strip().lower()
    booking_code = (payload.get("booking_code") or "").strip()
    organization_id = (payload.get("organization_id") or "").strip()

    if not email or not booking_code:
        raise AppError(400, "INVALID", "E-posta ve rezervasyon kodu gereklidir")

    if not organization_id:
        raise AppError(400, "INVALID", "Organizasyon bilgisi gereklidir")

    booking = await db.bookings.find_one(
        {
            "organization_id": organization_id,
            "guest_email": {"$regex": _safe_email_regex(email), "$options": "i"},
            "confirmation_code": booking_code,
        },
        {"_id": 0},
    )
    if not booking:
        booking = await db.reservations.find_one(
            {
                "organization_id": organization_id,
                "guest_email": {"$regex": _safe_email_regex(email), "$options": "i"},
                "code": booking_code,
            },
            {"_id": 0},
        )
    if not booking:
        raise AppError(401, "NOT_FOUND", "Rezervasyon bulunamadi")

    token = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    await db.portal_sessions.insert_one({
        "token": token,
        "email": email,
        "booking_code": booking_code,
        "organization_id": organization_id,
        "customer_id": booking.get("customer_id"),
        "active": True,
        "created_at": now,
    })
    return {"token": token, "email": email, "booking_code": booking_code}


@router.post("/logout")
async def portal_logout(payload: Dict[str, Any], db=Depends(get_db)):
    token = payload.get("token", "")
    await db.portal_sessions.update_one({"token": token}, {"$set": {"active": False}})
    return {"ok": True}


@router.get("/my-bookings")
async def my_bookings(token: str = Query(...), db=Depends(get_db)):
    session = await _get_portal_customer(token, db)
    if not session:
        raise AppError(401, "UNAUTHORIZED", "Gecersiz oturum")

    email = session["email"]
    org_id = session.get("organization_id")

    if not org_id:
        raise AppError(401, "UNAUTHORIZED", "Gecersiz oturum - organizasyon bilgisi eksik")

    filt: Dict[str, Any] = {
        "organization_id": org_id,
        "guest_email": {"$regex": _safe_email_regex(email), "$options": "i"},
    }

    cursor = db.bookings.find(filt, {
        "_id": 0, "id": 1, "confirmation_code": 1, "hotel_name": 1,
        "check_in": 1, "check_out": 1, "status": 1, "total_price": 1,
        "currency": 1, "guest_name": 1, "created_at": 1,
    }).sort("created_at", -1)
    bookings = await cursor.to_list(length=50)

    res_cursor = db.reservations.find(
        {"organization_id": org_id, "guest_email": {"$regex": _safe_email_regex(email), "$options": "i"}},
        {"_id": 0, "id": 1, "code": 1, "hotel_name": 1, "check_in": 1, "check_out": 1, "status": 1, "total_price": 1, "currency": 1, "guest_name": 1, "created_at": 1},
    ).sort("created_at", -1)
    reservations = await res_cursor.to_list(length=50)

    return {"bookings": bookings, "reservations": reservations}


@router.get("/my-booking/{booking_code}")
async def my_booking_detail(booking_code: str, token: str = Query(...), db=Depends(get_db)):
    session = await _get_portal_customer(token, db)
    if not session:
        raise AppError(401, "UNAUTHORIZED", "Gecersiz oturum")

    email = session["email"]
    org_id = session.get("organization_id")

    if not org_id:
        raise AppError(401, "UNAUTHORIZED", "Gecersiz oturum - organizasyon bilgisi eksik")

    email_filt = {"$regex": _safe_email_regex(email), "$options": "i"}
    base_filt: Dict[str, Any] = {"organization_id": org_id, "guest_email": email_filt}

    booking = await db.bookings.find_one(
        {**base_filt, "confirmation_code": booking_code},
        {"_id": 0},
    )
    if not booking:
        booking = await db.reservations.find_one(
            {**base_filt, "code": booking_code},
            {"_id": 0},
        )
    if not booking:
        raise AppError(404, "NOT_FOUND", "Rezervasyon bulunamadi")
    return booking


@router.get("/my-documents")
async def my_documents(token: str = Query(...), db=Depends(get_db)):
    session = await _get_portal_customer(token, db)
    if not session:
        raise AppError(401, "UNAUTHORIZED", "Gecersiz oturum")

    org_id = session.get("organization_id")
    email = session["email"]

    if not org_id:
        raise AppError(401, "UNAUTHORIZED", "Gecersiz oturum - organizasyon bilgisi eksik")

    cursor = db.invoices.find(
        {"organization_id": org_id, "customer_email": {"$regex": _safe_email_regex(email), "$options": "i"}},
        {"_id": 0, "id": 1, "invoice_number": 1, "amount": 1, "currency": 1, "status": 1, "created_at": 1},
    ).sort("created_at", -1)
    invoices = await cursor.to_list(length=50)

    voucher_cursor = db.vouchers.find(
        {"organization_id": org_id, "guest_email": {"$regex": _safe_email_regex(email), "$options": "i"}},
        {"_id": 0, "id": 1, "code": 1, "hotel_name": 1, "check_in": 1, "status": 1, "created_at": 1},
    ).sort("created_at", -1)
    vouchers = await voucher_cursor.to_list(length=50)

    return {"invoices": invoices, "vouchers": vouchers}


@router.post("/support-request")
async def create_support_request(payload: Dict[str, Any], db=Depends(get_db)):
    token = payload.get("token", "")
    session = await _get_portal_customer(token, db)
    if not session:
        raise AppError(401, "UNAUTHORIZED", "Gecersiz oturum")

    org_id = session.get("organization_id")
    if not org_id:
        raise AppError(401, "UNAUTHORIZED", "Gecersiz oturum - organizasyon bilgisi eksik")

    now = datetime.now(timezone.utc).isoformat()
    ticket = {
        "id": str(uuid.uuid4()),
        "organization_id": org_id,
        "customer_email": session["email"],
        "booking_code": payload.get("booking_code", session.get("booking_code", "")),
        "subject": payload.get("subject", ""),
        "message": payload.get("message", ""),
        "category": payload.get("category", "general"),
        "status": "open",
        "source": "portal",
        "created_at": now,
        "updated_at": now,
    }
    await db.support_tickets.insert_one(ticket)
    return {"id": ticket["id"], "status": "open", "message": "Talebiniz alinmistir"}


@router.post("/cancel-request")
async def create_cancel_request(payload: Dict[str, Any], db=Depends(get_db)):
    token = payload.get("token", "")
    session = await _get_portal_customer(token, db)
    if not session:
        raise AppError(401, "UNAUTHORIZED", "Gecersiz oturum")

    org_id = session.get("organization_id")
    if not org_id:
        raise AppError(401, "UNAUTHORIZED", "Gecersiz oturum - organizasyon bilgisi eksik")

    now = datetime.now(timezone.utc).isoformat()
    request_doc = {
        "id": str(uuid.uuid4()),
        "organization_id": org_id,
        "customer_email": session["email"],
        "booking_code": payload.get("booking_code", ""),
        "reason": payload.get("reason", ""),
        "status": "pending",
        "created_at": now,
    }
    await db.cancel_requests.insert_one(request_doc)
    return {"id": request_doc["id"], "status": "pending", "message": "Iptal talebiniz alinmistir, en kisa surede donulecektir"}
