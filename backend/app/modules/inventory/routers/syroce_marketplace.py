"""Syroce PMS Marketplace v1 — per-organization PROXY router.

Each request is scoped by `current_user.organization_id`. The actual Syroce
API key for that org is loaded from the encrypted `syroce_agencies` collection.
No platform-wide key is used here — that's only for admin operations.

Includes:
  - Local persistence of reservations in `agency_reservations` (org-scoped, idempotent).
  - Per-org rate-limit on /search.
  - CSV export on /reconciliation.
"""
from __future__ import annotations

import csv
import io
import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, EmailStr, Field
from pymongo.errors import DuplicateKeyError

from app.auth import require_roles
from app.db import get_db
from app.errors import AppError
from app.infrastructure.rate_limiter import check_rate_limit
from app.security.module_guard import require_org_module
from app.services.syroce.agent import SyroceAgentClient
from app.services.syroce.errors import SyroceError

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/syroce-marketplace",
    tags=["syroce-marketplace"],
    dependencies=[require_org_module("syroce_marketplace")],
)

UserDep = Depends(require_roles(["super_admin", "admin", "agent", "operator"]))

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
COLLECTION = "agency_reservations"


# ───────────────────── Helpers ─────────────────────

def _now() -> datetime:
    return datetime.now(timezone.utc)


def _org_id(user: dict) -> str:
    org = user.get("organization_id") or user.get("org_id") or user.get("tenant_id")
    if not org:
        raise AppError(status_code=400, code="missing_org", message="Organizasyon bilgisi bulunamadı.")
    return str(org)


def _to_app_error(exc: SyroceError) -> AppError:
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


async def _audit(db, org_id, user, action, target_id, meta=None):
    try:
        await db.audit_logs.insert_one({
            "id": str(uuid.uuid4()),
            "organization_id": org_id,
            "user_id": user.get("id") or user.get("sub"),
            "user_email": user.get("email"),
            "action": action,
            "module": "syroce_marketplace",
            "target_id": target_id,
            "metadata": meta or {},
            "created_at": _now(),
        })
    except Exception as e:
        logger.warning("syroce marketplace audit write failed: %s", e)


async def _ensure_indexes(db) -> None:
    try:
        await db[COLLECTION].create_index(
            [("organization_id", 1), ("external_reference", 1)],
            unique=True, name="uniq_org_external_reference",
        )
        await db[COLLECTION].create_index(
            [("organization_id", 1), ("created_at", -1)], name="org_created_at",
        )
        await db[COLLECTION].create_index(
            "syroce_reservation_id", unique=True, sparse=True, name="uniq_syroce_reservation_id",
        )
    except Exception as e:
        logger.debug("agency_reservations index ensure: %s", e)


def _serialize(doc: Dict[str, Any]) -> Dict[str, Any]:
    doc.pop("_id", None)
    return doc


async def _client(user: dict) -> SyroceAgentClient:
    """Get an org-scoped Syroce client. Maps SyroceError → AppError."""
    try:
        return await SyroceAgentClient.from_organization_id(_org_id(user))
    except SyroceError as exc:
        raise _to_app_error(exc)


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
    hotel_name: Optional[str] = None  # local snapshot only — total_amount sent NEVER


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
    client = await _client(user)
    try:
        return await client.list_hotels(city=city, country=country, q=q)
    except SyroceError as exc:
        raise _to_app_error(exc)


@router.post("/search")
async def search(
    payload: SearchPayload,
    user: dict = UserDep,
):
    _validate_date(payload.check_in, "check_in")
    _validate_date(payload.check_out, "check_out")
    if payload.check_out <= payload.check_in:
        raise AppError(422, "invalid_date_range", "check_out tarihi check_in tarihinden büyük olmalı.")

    org_id = _org_id(user)
    rl = await check_rate_limit(key=org_id, tier="syroce_search")
    if not rl.allowed:
        raise AppError(
            status_code=429,
            code="rate_limited",
            message=f"Çok hızlı arama yapıyorsunuz. Lütfen {max(1, rl.retry_after_ms // 1000)} saniye sonra tekrar deneyin.",
            details={"retry_after_ms": rl.retry_after_ms},
        )

    client = await _client(user)
    try:
        return await client.search_availability(payload.model_dump(exclude_none=True))
    except SyroceError as exc:
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
    client = await _client(user)
    try:
        return await client.get_rates(
            tenant_id=tenant_id, room_type=room_type, check_in=check_in, check_out=check_out,
        )
    except SyroceError as exc:
        raise _to_app_error(exc)


@router.post("/reservations")
async def create_reservation(body: CreateReservationPayload, user: dict = UserDep):
    _validate_date(body.check_in, "check_in")
    _validate_date(body.check_out, "check_out")
    if body.check_out <= body.check_in:
        raise AppError(422, "invalid_date_range", "check_out tarihi check_in tarihinden büyük olmalı.")

    db = await get_db()
    await _ensure_indexes(db)
    org_id = _org_id(user)

    external_ref = (body.external_reference or "").strip() or f"ACT-{uuid.uuid4().hex[:8].upper()}"

    # Idempotency: claim the (org, external_reference) slot BEFORE PMS call.
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
            return {"ok": True, "reservation": _serialize(existing), "idempotent": True}
        raise AppError(
            409, "duplicate_external_reference",
            f"Bu PNR ({external_ref}) için zaten bir işlem devam ediyor veya tamamlandı.",
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
    # NOTE: total_amount intentionally NOT sent — server-side price is authoritative.

    client = await _client(user)
    try:
        result = await client.create_reservation(pms_payload)
    except SyroceError as exc:
        try:
            await db[COLLECTION].delete_one(
                {"organization_id": org_id, "id": record_id, "status": "pending"}
            )
        except Exception:
            logger.exception("failed to clean up pending agency_reservation record")
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
            {"organization_id": org_id, "id": record_id}, {"$set": update}
        )
    except Exception as e:
        logger.error("agency_reservations local update failed after PMS success: %s", e)
        raise AppError(
            500, "local_persistence_failed",
            f"Rezervasyon PMS'te oluşturuldu (kod: {update.get('syroce_confirmation_code')}) "
            "ancak yerel kayıt güncellenemedi. Lütfen mutabakat sayfasından kontrol edin.",
            details={
                "syroce_confirmation_code": update.get("syroce_confirmation_code"),
                "syroce_reservation_id": update.get("syroce_reservation_id"),
                "external_reference": external_ref,
            },
        )

    final_doc = {**pending_doc, **update}
    await _audit(db, org_id, user, "marketplace_reservation_created", record_id, {
        "external_reference": external_ref,
        "syroce_reservation_id": update.get("syroce_reservation_id"),
        "syroce_confirmation_code": update.get("syroce_confirmation_code"),
    })
    return {"ok": True, "reservation": _serialize(final_doc), "raw": result}


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
    cursor = db[COLLECTION].find(q).sort("created_at", -1).skip((page - 1) * page_size).limit(page_size)
    items: List[Dict[str, Any]] = [_serialize(d) async for d in cursor]
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.get("/reservations/{reservation_id}")
async def get_reservation_detail(reservation_id: str, user: dict = UserDep):
    db = await get_db()
    org_id = _org_id(user)
    local = await db[COLLECTION].find_one({"organization_id": org_id, "id": reservation_id})
    if not local:
        raise AppError(404, "not_found", "Rezervasyon bulunamadı.")
    pms_id = local.get("syroce_reservation_id")
    pms_data: Dict[str, Any] = {}
    if pms_id:
        try:
            client = await _client(user)
            pms_data = await client.get_reservation(str(pms_id))
        except SyroceError as exc:
            logger.warning("PMS reservation fetch failed: %s", exc)
            pms_data = {"error": exc.detail}
    return {"local": _serialize(local), "pms": pms_data}


@router.delete("/reservations/{reservation_id}")
async def cancel_local_reservation(
    reservation_id: str,
    body: Optional[CancelPayload] = None,
    user: dict = UserDep,
):
    db = await get_db()
    org_id = _org_id(user)
    local = await db[COLLECTION].find_one({"organization_id": org_id, "id": reservation_id})
    if not local:
        raise AppError(404, "not_found", "Rezervasyon bulunamadı.")
    if local.get("status") == "cancelled":
        raise AppError(409, "already_cancelled", "Bu rezervasyon zaten iptal edilmiş.")
    pms_id = local.get("syroce_reservation_id")
    if not pms_id:
        raise AppError(409, "missing_pms_id", "Bu kayıt PMS'te tanımlı değil; iptal edilemez.")

    reason = (body.reason if body else "agency_request") or "agency_request"
    client = await _client(user)
    try:
        result = await client.cancel_reservation(str(pms_id), reason=reason)
    except SyroceError as exc:
        raise _to_app_error(exc)

    await db[COLLECTION].update_one(
        {"organization_id": org_id, "id": reservation_id},
        {"$set": {
            "status": "cancelled",
            "cancelled_at": _now(),
            "cancellation_reason": reason,
            "updated_at": _now(),
            "raw_cancel_response": result,
        }},
    )
    await _audit(db, org_id, user, "marketplace_reservation_cancelled", reservation_id, {
        "reason": reason, "syroce_reservation_id": pms_id,
    })
    return {"ok": True, "result": result}


@router.get("/reconciliation")
async def reconciliation(
    period_start: str = Query(...),
    period_end: str = Query(...),
    tenant_id: Optional[str] = None,
    format: str = Query("json", pattern="^(json|csv)$"),
    user: dict = UserDep,
):
    _validate_date(period_start, "period_start")
    _validate_date(period_end, "period_end")
    if period_end < period_start:
        raise AppError(422, "invalid_date_range", "period_end, period_start'tan büyük veya eşit olmalı.")

    client = await _client(user)
    try:
        data = await client.reconciliation(
            period_start=period_start, period_end=period_end, tenant_id=tenant_id,
        )
    except SyroceError as exc:
        raise _to_app_error(exc)

    if format == "csv":
        rows = data.get("rows") or data.get("hotels") or data.get("items") or []
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow([
            "Otel", "Tenant ID", "Rezervasyon", "Toplam Ciro", "Komisyon", "Net Ödenmesi",
        ])
        for r in rows:
            writer.writerow([
                r.get("hotel_name") or "",
                r.get("tenant_id") or "",
                r.get("reservations_count") or r.get("bookings_count") or 0,
                r.get("total_revenue") or r.get("gross_total") or 0,
                r.get("commission_total") or r.get("agency_commission") or 0,
                r.get("net_to_hotel") or r.get("net_total") or 0,
            ])
        buf.seek(0)
        filename = f"mutabakat_{period_start}_{period_end}.csv"
        return StreamingResponse(
            iter([buf.getvalue()]),
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    return data
