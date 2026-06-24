"""Syroce PMS B2B — agency-side admin router (Scenario B).

Admin-gated control surface over the contract-locked B2B integration:
  - Onboarding: create connect request + poll for the one-time API key.
  - Channel A (REST): availability / rates / reservations / folio.
  - Real-time: webhook subscription management + REST polling controls + local table.

Secrets (connect code, request token, API key, webhook secret) are never echoed;
only boolean readiness flags / prefixes are reported. All write paths are
fail-closed (the client raises on ambiguity instead of guessing).
"""
from __future__ import annotations

import logging
import re
import secrets as _secrets
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Header, Query
from pydantic import BaseModel, EmailStr, Field

from app.auth import require_roles
from app.db import get_db
from app.errors import AppError
from app.services.syroce_b2b import connection_store as store
from app.services.syroce_b2b import onboarding, polling
from app.services.syroce_b2b.client import SyroceB2BClient
from app.services.syroce_b2b.errors import SyroceB2BError
from app.services.syroce_b2b.idempotency import is_valid_key, resolve_key
from app.services.syroce_b2b.webhook_routes import INBOUND_WEBHOOK_PATH

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


async def _client() -> SyroceB2BClient:
    try:
        return await SyroceB2BClient.load()
    except SyroceB2BError as exc:
        raise _to_app_error(exc)


# ── payloads ──────────────────────────────────────────────────────

class ConnectRequestPayload(BaseModel):
    connect_code: str = Field(..., min_length=1)
    agency_name: str = Field(..., min_length=2)
    agency_platform_request_id: str = Field(..., min_length=4)
    contact_name: str = ""
    contact_email: str = ""
    contact_phone: str = ""
    note: str = ""
    external_agency_id: str = ""
    requested_scopes: List[str] = Field(default_factory=lambda: ["booking_engine", "webhooks"])


class ConnectPollPayload(BaseModel):
    connect_code: str = Field(..., min_length=1)


class RotateKeyPayload(BaseModel):
    api_key: str = Field(..., min_length=8)
    key_prefix: Optional[str] = None


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
    client_request_id: Optional[str] = None  # logical id for idempotency-key reuse


class FolioChargePayload(BaseModel):
    charge_type: str = Field(..., min_length=1)
    description: str = Field(..., min_length=1)
    amount: float
    quantity: int = Field(1, ge=1)


class WebhookRegisterPayload(BaseModel):
    events: List[str] = Field(..., min_length=1)
    url: Optional[str] = None  # default: this app's inbound receiver


class PollSettingsPayload(BaseModel):
    enabled: Optional[bool] = None
    horizon_days: Optional[int] = Field(None, ge=1, le=365)
    interval_seconds: Optional[int] = Field(None, ge=30, le=3600)
    room_types: Optional[List[str]] = None


# ── status ────────────────────────────────────────────────────────

@router.get("/status")
async def status(_user: dict = AdminDep):
    from app.services.syroce_b2b.config import get_b2b_config

    cfg = get_b2b_config()
    view = await store.public_view()
    return {
        **view,
        "base_url_configured": cfg.base_ready,
        "tenant_id_configured": bool(cfg.tenant_id),
        "polling_running": polling.polling_running(),
    }


# ── onboarding ────────────────────────────────────────────────────

@router.post("/connect")
async def connect_create(body: ConnectRequestPayload, _user: dict = AdminDep):
    try:
        return await onboarding.create_connect_request(
            connect_code=body.connect_code,
            agency_name=body.agency_name,
            agency_platform_request_id=body.agency_platform_request_id,
            contact_name=body.contact_name,
            contact_email=body.contact_email,
            contact_phone=body.contact_phone,
            note=body.note,
            external_agency_id=body.external_agency_id,
            requested_scopes=body.requested_scopes,
        )
    except SyroceB2BError as exc:
        raise _to_app_error(exc)


@router.post("/connect/poll")
async def connect_poll(body: ConnectPollPayload, _user: dict = AdminDep):
    try:
        return await onboarding.poll_connect_request(connect_code=body.connect_code)
    except SyroceB2BError as exc:
        raise _to_app_error(exc)


@router.post("/rotate-key")
async def rotate_key(body: RotateKeyPayload, _user: dict = AdminDep):
    """Apply a hotel-initiated key rotation (new key delivered out-of-band)."""
    await store.rotate_api_key(api_key=body.api_key, key_prefix=body.key_prefix)
    return {"ok": True, "message": "API key güncellendi."}


# ── Channel A: booking engine ─────────────────────────────────────

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
        return await (await _client()).get_availability(
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
        return await (await _client()).get_rates(
            start_date=start_date, end_date=end_date, room_type=room_type
        )
    except SyroceB2BError as exc:
        raise _to_app_error(exc)


@router.post("/reservations")
async def create_reservation(
    body: ReservationPayload,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    _user: dict = AdminDep,
):
    _check_date(body.check_in, "check_in")
    _check_date(body.check_out, "check_out")
    if body.check_out <= body.check_in:
        raise AppError(422, "invalid_date_range", "check_out, check_in'den büyük olmalı.")

    # A caller-supplied Idempotency-Key must be a valid UUID; reject (rather than
    # silently replace) so the caller's retry determinism is never broken.
    if idempotency_key is not None and not is_valid_key(idempotency_key):
        raise AppError(422, "invalid_idempotency_key", "Idempotency-Key geçerli bir UUID olmalı.")

    # Resolve a STABLE Idempotency-Key so logical retries never double-book:
    # a caller-supplied header wins; else a client_request_id maps to a persisted
    # key; else a fresh key is generated and echoed back for the caller to reuse.
    key = await resolve_key(provided_key=idempotency_key, client_request_id=body.client_request_id)
    payload = body.model_dump(exclude_none=True, exclude={"client_request_id"})
    try:
        result = await (await _client()).create_reservation(payload, idempotency_key=key)
    except SyroceB2BError as exc:
        raise _to_app_error(exc)
    if isinstance(result, dict):
        result.setdefault("idempotency_key", key)
    return result


@router.get("/reservations")
async def list_reservations(
    status: Optional[str] = None,
    check_in_from: Optional[str] = None,
    check_in_to: Optional[str] = None,
    limit: int = Query(100, ge=1, le=500),
    _user: dict = AdminDep,
):
    try:
        return await (await _client()).list_reservations(
            status=status, check_in_from=check_in_from, check_in_to=check_in_to, limit=limit
        )
    except SyroceB2BError as exc:
        raise _to_app_error(exc)


@router.get("/reservations/{reservation_id}")
async def get_reservation(reservation_id: str, _user: dict = AdminDep):
    try:
        return await (await _client()).get_reservation(reservation_id)
    except SyroceB2BError as exc:
        raise _to_app_error(exc)


@router.put("/reservations/{reservation_id}/cancel")
async def cancel_reservation(reservation_id: str, _user: dict = AdminDep):
    try:
        return await (await _client()).cancel_reservation(reservation_id)
    except SyroceB2BError as exc:
        raise _to_app_error(exc)


# ── Channel A: folio ──────────────────────────────────────────────

@router.get("/folio/{booking_id}")
async def get_folio(booking_id: str, _user: dict = AdminDep):
    try:
        return await (await _client()).get_folio(booking_id)
    except SyroceB2BError as exc:
        raise _to_app_error(exc)


@router.post("/folio/{booking_id}/charge")
async def add_folio_charge(booking_id: str, body: FolioChargePayload, _user: dict = AdminDep):
    try:
        return await (await _client()).add_folio_charge(booking_id, body.model_dump())
    except SyroceB2BError as exc:
        raise _to_app_error(exc)


@router.get("/folio/{booking_id}/invoice")
async def get_folio_invoice(booking_id: str, _user: dict = AdminDep):
    try:
        return await (await _client()).get_folio_invoice(booking_id)
    except SyroceB2BError as exc:
        raise _to_app_error(exc)


# ── webhook subscription management ───────────────────────────────

def _inbound_url(override: Optional[str]) -> str:
    if override:
        return override
    import os

    domain = (os.environ.get("REPLIT_DEV_DOMAIN") or "").strip()
    if not domain:
        domains = (os.environ.get("REPLIT_DOMAINS") or "").strip()
        domain = domains.split(",")[0].strip() if domains else ""
    if not domain:
        raise AppError(
            422,
            "webhook_url_required",
            "Webhook callback URL'i belirlenemedi; 'url' alanını gönderin.",
        )
    return f"https://{domain}{INBOUND_WEBHOOK_PATH}"


@router.post("/webhooks")
async def register_webhook(body: WebhookRegisterPayload, _user: dict = AdminDep):
    url = _inbound_url(body.url)
    secret = _secrets.token_urlsafe(32)  # used to verify inbound signatures
    try:
        result = await (await _client()).register_webhook(
            {"url": url, "events": body.events, "secret": secret}
        )
    except SyroceB2BError as exc:
        raise _to_app_error(exc)
    sub_id = None
    if isinstance(result, dict):
        sub_id = result.get("id") or result.get("subscription_id") or (result.get("webhook") or {}).get("id")
    await store.save_webhook(subscription_id=sub_id, secret=secret)
    return {"ok": True, "subscription_id": sub_id, "url": url, "events": body.events}


@router.get("/webhooks")
async def list_webhooks(_user: dict = AdminDep):
    try:
        return await (await _client()).list_webhooks()
    except SyroceB2BError as exc:
        raise _to_app_error(exc)


@router.delete("/webhooks/{subscription_id}")
async def delete_webhook(subscription_id: str, _user: dict = AdminDep):
    try:
        result = await (await _client()).delete_webhook(subscription_id)
    except SyroceB2BError as exc:
        raise _to_app_error(exc)
    await store.clear_webhook()
    return result if isinstance(result, dict) else {"ok": True}


@router.post("/webhooks/{subscription_id}/test")
async def test_webhook(subscription_id: str, _user: dict = AdminDep):
    try:
        return await (await _client()).test_webhook(subscription_id)
    except SyroceB2BError as exc:
        raise _to_app_error(exc)


# ── REST polling controls + local table ───────────────────────────

@router.put("/polling/settings")
async def update_polling(body: PollSettingsPayload, _user: dict = AdminDep):
    await store.set_poll_settings(
        enabled=body.enabled,
        horizon_days=body.horizon_days,
        interval_seconds=body.interval_seconds,
        room_types=body.room_types,
    )
    return {"ok": True, **(await store.get_poll_settings())}


@router.post("/polling/sync")
async def manual_sync(_user: dict = AdminDep):
    try:
        return await polling.sync_once()
    except SyroceB2BError as exc:
        raise _to_app_error(exc)


@router.get("/local-ari")
async def local_ari(
    room_type: Optional[str] = None,
    limit: int = Query(100, ge=1, le=500),
    _user: dict = AdminDep,
):
    db = await get_db()
    q: Dict[str, Any] = {}
    if room_type:
        q["room_type"] = room_type
    cursor = db[polling.LOCAL_COLLECTION].find(q).sort("synced_at", -1).limit(limit)
    items: List[Dict[str, Any]] = []
    async for d in cursor:
        d.pop("_id", None)
        items.append(d)
    return {"items": items, "count": len(items)}


__all__ = ["router"]
