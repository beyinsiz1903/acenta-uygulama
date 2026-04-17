"""Syroce PMS Marketplace v1 — proxy router + yerel rezervasyon kaydı.

Frontend bu router'a istek atar; router PMS Marketplace API'sine HTTP isteği yapar
ve gerektiğinde sonucu yerel `syroce_marketplace_bookings` koleksiyonuna kaydeder.
"""
from __future__ import annotations

import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, EmailStr, Field

from app.auth import require_roles
from app.db import get_db
from app.errors import AppError
from app.security.module_guard import require_org_module
from pymongo.errors import DuplicateKeyError

from app.services import syroce_marketplace as svc
from app.services.syroce_marketplace import SyroceMarketplaceError

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/syroce-marketplace",
    tags=["syroce-marketplace"],
    dependencies=[require_org_module("syroce_marketplace")],
)

UserDep = Depends(require_roles(["super_admin", "admin", "agent", "operator"]))

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
COLLECTION = "syroce_marketplace_bookings"


# ───────────────────── Helpers ─────────────────────

def _now() -> datetime:
    return datetime.now(timezone.utc)


def _org_id(user: dict) -> str:
    org = user.get("organization_id") or user.get("org_id") or user.get("tenant_id")
    if not org:
        raise AppError(status_code=400, code="missing_org", message="Organizasyon bilgisi bulunamadı.")
    return str(org)


def _to_app_error(exc: SyroceMarketplaceError) -> AppError:
    return AppError(
        status_code=exc.http_status if 400 <= exc.http_status < 600 else 502,
        code="syroce_marketplace_error",
        message=exc.detail,
        details=exc.payload or None,
    )


def _validate_date(value: str, field: str) -> None:
    if not DATE_RE.match(value or ""):
        raise AppError(
            status_code=422,
            code="invalid_date",
            message=f"{field} alanı YYYY-MM-DD formatında olmalı.",
        )


async def _audit(
    db,
    org_id: str,
    user: dict,
    action: str,
    target_id: str,
    meta: Optional[dict] = None,
) -> None:
    try:
        await db.audit_logs.insert_one(
            {
                "id": str(uuid.uuid4()),
                "organization_id": org_id,
                "user_id": user.get("id") or user.get("sub"),
                "user_email": user.get("email"),
                "action": action,
                "module": "syroce_marketplace",
                "target_id": target_id,
                "metadata": meta or {},
                "created_at": _now(),
            }
        )
    except Exception as e:
        logger.warning("syroce marketplace audit write failed: %s", e)


async def _ensure_indexes(db) -> None:
    """external_reference uniqueness per organization."""
    try:
        await db[COLLECTION].create_index(
            [("organization_id", 1), ("external_reference", 1)],
            unique=True,
            name="uniq_org_external_reference",
        )
        await db[COLLECTION].create_index(
            [("organization_id", 1), ("created_at", -1)],
            name="org_created_at",
        )
    except Exception as e:
        logger.debug("syroce marketplace index ensure: %s", e)


def _serialize_booking(doc: Dict[str, Any]) -> Dict[str, Any]:
    doc.pop("_id", None)
    return doc


# ───────────────────── Pydantic models ─────────────────────

class SearchPayload(BaseModel):
    check_in: str
    check_out: str
    adults: int = Field(..., ge=1, le=20)
    children: int = Field(0, ge=0, le=20)
    city: Optional[str] = None
    country: Optional[str] = None
    q: Optional[str] = None
    max_price: Optional[float] = None
    room_type: Optional[str] = None


class CreateReservationPayload(BaseModel):
    tenant_id: str
    room_type: str
    check_in: str
    check_out: str
    guest_name: str = Field(..., min_length=2)
    guest_email: EmailStr
    guest_phone: str = Field(..., min_length=5)
    adults: int = Field(..., ge=1, le=20)
    children: int = Field(0, ge=0, le=20)
    external_reference: Optional[str] = None
    special_requests: Optional[str] = None
    total_amount: Optional[float] = None
    hotel_name: Optional[str] = None  # UI'dan gelir, yerel kayıt için


class CancelPayload(BaseModel):
    reason: str = "agency_request"


# ───────────────────── Routes ─────────────────────

@router.get("/listings")
async def listings(
    city: Optional[str] = None,
    country: Optional[str] = None,
    q: Optional[str] = None,
    user: dict = UserDep,
):
    try:
        return await svc.list_hotels(city=city, country=country, q=q)
    except SyroceMarketplaceError as exc:
        raise _to_app_error(exc)


@router.post("/search")
async def search(
    payload: SearchPayload,
    user: dict = UserDep,
):
    _validate_date(payload.check_in, "check_in")
    _validate_date(payload.check_out, "check_out")
    if payload.check_out <= payload.check_in:
        raise AppError(
            status_code=422,
            code="invalid_date_range",
            message="check_out tarihi check_in tarihinden büyük olmalı.",
        )
    try:
        return await svc.search_availability(payload.model_dump(exclude_none=True))
    except SyroceMarketplaceError as exc:
        raise _to_app_error(exc)


@router.get("/rates")
async def rates(
    tenant_id: str = Query(...),
    room_type: str = Query(...),
    check_in: str = Query(...),
    check_out: str = Query(...),
    user: dict = UserDep,
):
    _validate_date(check_in, "check_in")
    _validate_date(check_out, "check_out")
    try:
        return await svc.get_rates(
            tenant_id=tenant_id,
            room_type=room_type,
            check_in=check_in,
            check_out=check_out,
        )
    except SyroceMarketplaceError as exc:
        raise _to_app_error(exc)


@router.post("/reservations")
async def create_reservation(
    body: CreateReservationPayload,
    user: dict = UserDep,
):
    _validate_date(body.check_in, "check_in")
    _validate_date(body.check_out, "check_out")
    if body.check_out <= body.check_in:
        raise AppError(
            status_code=422,
            code="invalid_date_range",
            message="check_out tarihi check_in tarihinden büyük olmalı.",
        )

    db = await get_db()
    await _ensure_indexes(db)
    org_id = _org_id(user)

    # Generate external_reference if missing
    external_ref = (body.external_reference or "").strip()
    if not external_ref:
        external_ref = f"ACT-{uuid.uuid4().hex[:8].upper()}"

    # ─── Idempotency: insert a "pending" record FIRST.
    # Compound unique index (organization_id, external_reference) ensures only
    # one concurrent caller can claim this reference. The other will get
    # DuplicateKeyError → 409 — without a duplicate PMS call.
    record_id = str(uuid.uuid4())
    pending_doc = {
        "id": record_id,
        "organization_id": org_id,
        "user_id": user.get("id") or user.get("sub"),
        "channel": "syroce_marketplace",
        "external_reference": external_ref,
        "syroce_tenant_id": body.tenant_id,
        "syroce_hotel_name": body.hotel_name or "",
        "room_type": body.room_type,
        "check_in": body.check_in,
        "check_out": body.check_out,
        "guest_name": body.guest_name,
        "guest_email": body.guest_email,
        "guest_phone": body.guest_phone,
        "adults": body.adults,
        "children": body.children,
        "special_requests": body.special_requests or "",
        "status": "pending",
        "created_at": _now(),
        "updated_at": _now(),
    }

    try:
        await db[COLLECTION].insert_one(pending_doc)
    except DuplicateKeyError:
        existing = await db[COLLECTION].find_one(
            {"organization_id": org_id, "external_reference": external_ref}
        )
        if existing and existing.get("status") in ("confirmed", "completed"):
            # True idempotency: return the prior successful record.
            return {
                "ok": True,
                "reservation": _serialize_booking(existing),
                "idempotent": True,
            }
        raise AppError(
            status_code=409,
            code="duplicate_external_reference",
            message=f"Bu PNR ({external_ref}) için zaten bir işlem devam ediyor veya tamamlandı.",
        )

    pms_payload: Dict[str, Any] = {
        "tenant_id": body.tenant_id,
        "room_type": body.room_type,
        "check_in": body.check_in,
        "check_out": body.check_out,
        "guest_name": body.guest_name,
        "guest_email": body.guest_email,
        "guest_phone": body.guest_phone,
        "adults": body.adults,
        "children": body.children,
        "external_reference": external_ref,
    }
    if body.special_requests:
        pms_payload["special_requests"] = body.special_requests
    if body.total_amount is not None:
        pms_payload["total_amount"] = body.total_amount

    try:
        result = await svc.create_reservation(pms_payload)
    except SyroceMarketplaceError as exc:
        # Mark record as failed so the same external_reference can be retried
        # (we delete so the user can fix and resubmit cleanly).
        try:
            await db[COLLECTION].delete_one(
                {"organization_id": org_id, "id": record_id, "status": "pending"}
            )
        except Exception:
            logger.exception("failed to clean up pending marketplace record")
        raise _to_app_error(exc)

    reservation = (result or {}).get("reservation") or {}

    update = {
        "syroce_reservation_id": reservation.get("id"),
        "syroce_confirmation_code": reservation.get("confirmation_code"),
        "syroce_tenant_id": reservation.get("tenant_id") or body.tenant_id,
        "syroce_hotel_name": reservation.get("hotel_name") or body.hotel_name or "",
        "room_type": reservation.get("room_type") or body.room_type,
        "room_number": reservation.get("room_number"),
        "total_amount": reservation.get("total_amount"),
        "commission_rate": reservation.get("agency_commission_rate"),
        "commission_amount": reservation.get("agency_commission_amount"),
        "net_to_hotel": reservation.get("net_to_hotel"),
        "status": reservation.get("status") or "confirmed",
        "raw_response": result,
        "updated_at": _now(),
    }

    try:
        await db[COLLECTION].update_one(
            {"organization_id": org_id, "id": record_id},
            {"$set": update},
        )
    except Exception as e:
        # Very rare: PMS booked but local update failed. Surface this so the
        # user/operator knows a reconciliation is required.
        logger.error("syroce marketplace local update failed after PMS success: %s", e)
        raise AppError(
            status_code=500,
            code="local_persistence_failed",
            message=(
                f"Rezervasyon PMS'te oluşturuldu (kod: {update.get('syroce_confirmation_code')}) "
                "ancak yerel kayıt güncellenemedi. Lütfen mutabakat sayfasından kontrol edin."
            ),
            details={
                "syroce_confirmation_code": update.get("syroce_confirmation_code"),
                "syroce_reservation_id": update.get("syroce_reservation_id"),
                "external_reference": external_ref,
            },
        )

    final_doc = {**pending_doc, **update}

    await _audit(
        db,
        org_id,
        user,
        "marketplace_reservation_created",
        record_id,
        {
            "external_reference": external_ref,
            "syroce_reservation_id": update.get("syroce_reservation_id"),
            "syroce_confirmation_code": update.get("syroce_confirmation_code"),
        },
    )

    return {"ok": True, "reservation": _serialize_booking(final_doc), "raw": result}


@router.get("/reservations")
async def list_reservations(
    status: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: dict = UserDep,
):
    db = await get_db()
    org_id = _org_id(user)
    q: Dict[str, Any] = {"organization_id": org_id}
    if status:
        q["status"] = status

    total = await db[COLLECTION].count_documents(q)
    cursor = (
        db[COLLECTION]
        .find(q)
        .sort("created_at", -1)
        .skip((page - 1) * page_size)
        .limit(page_size)
    )
    items: List[Dict[str, Any]] = []
    async for d in cursor:
        items.append(_serialize_booking(d))
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.get("/reservations/{reservation_id}")
async def get_reservation_detail(
    reservation_id: str,
    user: dict = UserDep,
):
    db = await get_db()
    org_id = _org_id(user)
    local = await db[COLLECTION].find_one(
        {"organization_id": org_id, "id": reservation_id}
    )
    if not local:
        raise AppError(
            status_code=404,
            code="not_found",
            message="Rezervasyon bulunamadı.",
        )

    pms_id = local.get("syroce_reservation_id")
    pms_data: Dict[str, Any] = {}
    if pms_id:
        try:
            pms_data = await svc.get_reservation(str(pms_id))
        except SyroceMarketplaceError as exc:
            logger.warning("PMS reservation fetch failed: %s", exc)
            pms_data = {"error": exc.detail}

    return {"local": _serialize_booking(local), "pms": pms_data}


@router.delete("/reservations/{reservation_id}")
async def cancel_local_reservation(
    reservation_id: str,
    body: Optional[CancelPayload] = None,
    user: dict = UserDep,
):
    db = await get_db()
    org_id = _org_id(user)
    local = await db[COLLECTION].find_one(
        {"organization_id": org_id, "id": reservation_id}
    )
    if not local:
        raise AppError(
            status_code=404,
            code="not_found",
            message="Rezervasyon bulunamadı.",
        )
    if local.get("status") == "cancelled":
        raise AppError(
            status_code=409,
            code="already_cancelled",
            message="Bu rezervasyon zaten iptal edilmiş.",
        )

    pms_id = local.get("syroce_reservation_id")
    if not pms_id:
        raise AppError(
            status_code=409,
            code="missing_pms_id",
            message="Bu kayıt PMS'te tanımlı değil; iptal edilemez.",
        )

    reason = (body.reason if body else "agency_request") or "agency_request"
    try:
        result = await svc.cancel_reservation(str(pms_id), reason=reason)
    except SyroceMarketplaceError as exc:
        raise _to_app_error(exc)

    await db[COLLECTION].update_one(
        {"organization_id": org_id, "id": reservation_id},
        {
            "$set": {
                "status": "cancelled",
                "cancelled_at": _now(),
                "cancel_reason": reason,
                "updated_at": _now(),
                "raw_cancel_response": result,
            }
        },
    )
    await _audit(
        db,
        org_id,
        user,
        "marketplace_reservation_cancelled",
        reservation_id,
        {"reason": reason, "syroce_reservation_id": pms_id},
    )
    return {"ok": True, "result": result}


@router.get("/reconciliation")
async def reconciliation(
    period_start: str = Query(...),
    period_end: str = Query(...),
    tenant_id: Optional[str] = None,
    user: dict = UserDep,
):
    _validate_date(period_start, "period_start")
    _validate_date(period_end, "period_end")
    if period_end < period_start:
        raise AppError(
            status_code=422,
            code="invalid_date_range",
            message="period_end, period_start'tan büyük veya eşit olmalı.",
        )
    try:
        return await svc.reconciliation_agency(
            period_start=period_start,
            period_end=period_end,
            tenant_id=tenant_id,
        )
    except SyroceMarketplaceError as exc:
        raise _to_app_error(exc)
