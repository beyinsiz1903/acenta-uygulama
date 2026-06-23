"""Syroce PMS B2B — agency-side admin router.

Thin, admin-gated surface over the contract-locked B2B integration:
  - Channel A (REST) proxy: availability / rates / reservations.
  - Channel B (ARI) observability: consumer status + local ARI state.

Secrets are never echoed; only boolean readiness flags are reported. All write
paths are fail-closed (the client raises on ambiguity instead of guessing).
"""
from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, EmailStr, Field

from app.auth import require_roles
from app.db import get_db
from app.errors import AppError
from app.services.syroce_b2b.ari_consumer import STATE_COLLECTION, consumer_running
from app.services.syroce_b2b.client import SyroceB2BClient
from app.services.syroce_b2b.config import public_status
from app.services.syroce_b2b.errors import SyroceB2BError

logger = logging.getLogger("syroce_b2b.router")

router = APIRouter(prefix="/api/admin/syroce-b2b", tags=["syroce-b2b"])

AdminDep = Depends(require_roles(["super_admin", "admin", "operator"]))
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _to_app_error(exc: SyroceB2BError) -> AppError:
    status = exc.http_status if 400 <= exc.http_status < 600 else 502
    return AppError(
        status_code=status,
        code=f"syroce_b2b_{exc.code}",
        message=exc.detail,
        details=exc.payload or None,
    )


def _check_date(value: str, field: str) -> None:
    if not DATE_RE.match(value or ""):
        raise AppError(422, "invalid_date", f"{field} alanı YYYY-MM-DD formatında olmalı.")


class ReservationPayload(BaseModel):
    room_type: str
    check_in: str
    check_out: str
    guest_name: str = Field(..., min_length=2)
    guest_email: Optional[EmailStr] = None
    guest_phone: Optional[str] = None
    adults: int = Field(..., ge=1, le=20)
    children: int = Field(0, ge=0, le=20)
    special_requests: Optional[str] = None
    total_amount: Optional[float] = None  # 0/None -> PMS computes


# ── status / observability ───────────────────────────────────────

@router.get("/status")
async def status(_user: dict = AdminDep):
    return {**public_status(), "ari_consumer_running": consumer_running()}


@router.get("/ari")
async def ari_state(
    room_type: Optional[str] = None,
    event_type: Optional[str] = Query(None, pattern="^(availability|rate|restriction)$"),
    limit: int = Query(100, ge=1, le=500),
    _user: dict = AdminDep,
):
    db = await get_db()
    q: Dict[str, Any] = {}
    if room_type:
        q["room_type_code"] = room_type
    if event_type:
        q["event_type"] = event_type
    cursor = db[STATE_COLLECTION].find(q).sort("created_at", -1).limit(limit)
    items: List[Dict[str, Any]] = []
    async for d in cursor:
        d.pop("_id", None)
        items.append(d)
    return {"items": items, "count": len(items)}


# ── Channel A proxy ──────────────────────────────────────────────

@router.get("/availability")
async def availability(
    check_in: str = Query(...),
    check_out: str = Query(...),
    room_type: Optional[str] = None,
    _user: dict = AdminDep,
):
    _check_date(check_in, "check_in")
    _check_date(check_out, "check_out")
    if check_out <= check_in:
        raise AppError(422, "invalid_date_range", "check_out, check_in'den büyük olmalı.")
    try:
        return await SyroceB2BClient().get_availability(
            check_in=check_in, check_out=check_out, room_type=room_type
        )
    except SyroceB2BError as exc:
        raise _to_app_error(exc)


@router.get("/rates")
async def rates(
    start_date: str = Query(...),
    end_date: str = Query(...),
    room_type: Optional[str] = None,
    _user: dict = AdminDep,
):
    _check_date(start_date, "start_date")
    _check_date(end_date, "end_date")
    if end_date < start_date:
        raise AppError(422, "invalid_date_range", "end_date, start_date'ten büyük/eşit olmalı.")
    try:
        return await SyroceB2BClient().get_rates(
            start_date=start_date, end_date=end_date, room_type=room_type
        )
    except SyroceB2BError as exc:
        raise _to_app_error(exc)


@router.post("/reservations")
async def create_reservation(body: ReservationPayload, _user: dict = AdminDep):
    _check_date(body.check_in, "check_in")
    _check_date(body.check_out, "check_out")
    if body.check_out <= body.check_in:
        raise AppError(422, "invalid_date_range", "check_out, check_in'den büyük olmalı.")
    try:
        return await SyroceB2BClient().create_reservation(
            body.model_dump(exclude_none=True)
        )
    except SyroceB2BError as exc:
        raise _to_app_error(exc)


@router.get("/reservations")
async def list_reservations(
    status: Optional[str] = None,
    check_in_from: Optional[str] = None,
    check_in_to: Optional[str] = None,
    limit: int = Query(100, ge=1, le=500),
    _user: dict = AdminDep,
):
    try:
        return await SyroceB2BClient().list_reservations(
            status=status, check_in_from=check_in_from, check_in_to=check_in_to, limit=limit
        )
    except SyroceB2BError as exc:
        raise _to_app_error(exc)


@router.get("/reservations/{reservation_id}")
async def get_reservation(reservation_id: str, _user: dict = AdminDep):
    try:
        return await SyroceB2BClient().get_reservation(reservation_id)
    except SyroceB2BError as exc:
        raise _to_app_error(exc)


@router.put("/reservations/{reservation_id}/cancel")
async def cancel_reservation(reservation_id: str, _user: dict = AdminDep):
    try:
        return await SyroceB2BClient().cancel_reservation(reservation_id)
    except SyroceB2BError as exc:
        raise _to_app_error(exc)


__all__ = ["router"]
