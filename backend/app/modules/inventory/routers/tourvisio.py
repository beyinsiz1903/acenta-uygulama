"""TourVisio (San TSG) multi-product proxy router — per-tenant.

Each request loads the calling agency's TourVisio credentials from the
encrypted `supplier_credentials` collection (managed via the Supplier
Credentials UI / `/api/supplier-credentials/*`). Tokens are cached
process-wide but partitioned by tenant credential key, so tenants never
share auth state.

All endpoints under `/api/tourvisio/*`. Roles allowed:
super_admin / admin / agency_admin / operator.
"""
from __future__ import annotations

import logging
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.auth import require_roles
from app.db import get_db
from app.domain.suppliers.supplier_credentials_service import get_decrypted_credentials
from app.services.tourvisio import TourVisioClient, TourVisioError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/tourvisio", tags=["tourvisio"])

ROLES = ["super_admin", "admin", "agency_admin", "operator"]
UserDep = Depends(require_roles(ROLES))


def _org_id(user: dict) -> str:
    return user.get("organization_id") or user.get("org_id") or ""


async def _client_for(current_user: dict, db) -> TourVisioClient:
    """Build a per-tenant TourVisio client from this agency's stored credentials."""
    org_id = _org_id(current_user)
    if not org_id:
        raise HTTPException(status_code=400, detail="Aktif kullanıcı bir organizasyona bağlı değil.")
    creds = await get_decrypted_credentials(db, org_id, "tourvisio")
    if not creds or not creds.get("base_url"):
        raise HTTPException(
            status_code=400,
            detail=(
                "Bu acente için TourVisio credential'ları tanımlı değil. "
                "Tedarikçi Ayarları > TourVisio sayfasından base_url, agency, username, password girin."
            ),
        )
    try:
        return TourVisioClient(
            base_url=creds["base_url"],
            agency=creds.get("agency", ""),
            user=creds.get("username", ""),
            password=creds.get("password", ""),
        )
    except TourVisioError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)


def _raise(exc: TourVisioError) -> None:
    raise HTTPException(status_code=exc.status_code, detail=exc.message)


# ───────────────── Schemas ─────────────────


class GenericRequest(BaseModel):
    body: Dict[str, Any] = Field(default_factory=dict)


class ProxyRequest(BaseModel):
    path: str = Field(..., description="Endpoint path, e.g. /api/productservice/pricesearch")
    body: Dict[str, Any] = Field(default_factory=dict)


# ───────────────── Health & token ─────────────────


@router.get("/health")
async def tourvisio_health(current_user: dict = UserDep, db=Depends(get_db)) -> Dict[str, Any]:
    """Per-tenant credential status (does not call upstream)."""
    org_id = _org_id(current_user)
    if not org_id:
        return {"configured": False, "reason": "no_organization"}
    creds = await get_decrypted_credentials(db, org_id, "tourvisio")
    if not creds:
        return {"configured": False, "reason": "no_credentials", "organization_id": org_id}
    fields_ok = {
        "base_url": bool(creds.get("base_url")),
        "agency": bool(creds.get("agency")),
        "username": bool(creds.get("username")),
        "password": bool(creds.get("password")),
    }
    token_status = None
    if all(fields_ok.values()):
        try:
            cli = TourVisioClient(
                base_url=creds["base_url"],
                agency=creds["agency"],
                user=creds["username"],
                password=creds["password"],
            )
            token_status = cli.token_status()
        except TourVisioError:
            token_status = None
    return {
        "configured": all(fields_ok.values()),
        "organization_id": org_id,
        "fields": fields_ok,
        "token": token_status,
    }


@router.post("/auth/login")
async def tourvisio_login(current_user: dict = UserDep, db=Depends(get_db)) -> Dict[str, Any]:
    """Force a fresh Login for the calling agency and refresh its cached token."""
    cli = await _client_for(current_user, db)
    try:
        await cli.login()
    except TourVisioError as exc:
        _raise(exc)
    return {"ok": True, "token": cli.token_status()}


@router.post("/auth/clear")
async def tourvisio_logout(current_user: dict = UserDep, db=Depends(get_db)) -> Dict[str, Any]:
    cli = await _client_for(current_user, db)
    cli.clear_token()
    return {"ok": True, "token": cli.token_status()}


# ───────────────── Generic proxy ─────────────────


@router.post("/proxy")
async def tourvisio_proxy(
    payload: ProxyRequest, current_user: dict = UserDep, db=Depends(get_db)
) -> Dict[str, Any]:
    """Forward to any TourVisio endpoint. Returns the unwrapped `body`."""
    cli = await _client_for(current_user, db)
    try:
        return await cli.request(payload.path, payload.body)
    except TourVisioError as exc:
        _raise(exc)


# ───────────────── Lookups ─────────────────


@router.post("/lookup/payment-types")
async def lookup_payment_types(payload: GenericRequest, current_user: dict = UserDep, db=Depends(get_db)) -> Dict[str, Any]:
    cli = await _client_for(current_user, db)
    try:
        return await cli.get_payment_types(payload.body)
    except TourVisioError as exc:
        _raise(exc)


@router.post("/lookup/transportations")
async def lookup_transportations(payload: GenericRequest, current_user: dict = UserDep, db=Depends(get_db)) -> Dict[str, Any]:
    cli = await _client_for(current_user, db)
    try:
        return await cli.get_transportations(payload.body)
    except TourVisioError as exc:
        _raise(exc)


@router.post("/lookup/exchange-rates")
async def lookup_exchange_rates(payload: GenericRequest, current_user: dict = UserDep, db=Depends(get_db)) -> Dict[str, Any]:
    cli = await _client_for(current_user, db)
    try:
        return await cli.get_exchange_rates(payload.body)
    except TourVisioError as exc:
        _raise(exc)


# ───────────────── Search ─────────────────


@router.post("/search/arrival-autocomplete")
async def search_arrival_autocomplete(payload: GenericRequest, current_user: dict = UserDep, db=Depends(get_db)) -> Dict[str, Any]:
    cli = await _client_for(current_user, db)
    try:
        return await cli.autocomplete(payload.body)
    except TourVisioError as exc:
        _raise(exc)


@router.post("/search/departure-autocomplete")
async def search_departure_autocomplete(payload: GenericRequest, current_user: dict = UserDep, db=Depends(get_db)) -> Dict[str, Any]:
    cli = await _client_for(current_user, db)
    try:
        return await cli.departure_autocomplete(payload.body)
    except TourVisioError as exc:
        _raise(exc)


@router.post("/search/checkin-dates")
async def search_checkin_dates(payload: GenericRequest, current_user: dict = UserDep, db=Depends(get_db)) -> Dict[str, Any]:
    cli = await _client_for(current_user, db)
    try:
        return await cli.get_check_in_dates(payload.body)
    except TourVisioError as exc:
        _raise(exc)


@router.post("/search/pricesearch")
async def search_price_search(payload: GenericRequest, current_user: dict = UserDep, db=Depends(get_db)) -> Dict[str, Any]:
    cli = await _client_for(current_user, db)
    try:
        return await cli.price_search(payload.body)
    except TourVisioError as exc:
        _raise(exc)


@router.post("/search/product-info")
async def search_product_info(payload: GenericRequest, current_user: dict = UserDep, db=Depends(get_db)) -> Dict[str, Any]:
    cli = await _client_for(current_user, db)
    try:
        return await cli.get_product_info(payload.body)
    except TourVisioError as exc:
        _raise(exc)


@router.post("/search/offer-details")
async def search_offer_details(payload: GenericRequest, current_user: dict = UserDep, db=Depends(get_db)) -> Dict[str, Any]:
    cli = await _client_for(current_user, db)
    try:
        return await cli.get_offer_details(payload.body)
    except TourVisioError as exc:
        _raise(exc)


@router.post("/search/fare-rules")
async def search_fare_rules(payload: GenericRequest, current_user: dict = UserDep, db=Depends(get_db)) -> Dict[str, Any]:
    cli = await _client_for(current_user, db)
    try:
        return await cli.get_fare_rules(payload.body)
    except TourVisioError as exc:
        _raise(exc)


# ───────────────── Booking ─────────────────


@router.post("/booking/begin-transaction")
async def booking_begin(payload: GenericRequest, current_user: dict = UserDep, db=Depends(get_db)) -> Dict[str, Any]:
    cli = await _client_for(current_user, db)
    try:
        return await cli.begin_transaction(payload.body)
    except TourVisioError as exc:
        _raise(exc)


@router.post("/booking/set-reservation-info")
async def booking_set_info(payload: GenericRequest, current_user: dict = UserDep, db=Depends(get_db)) -> Dict[str, Any]:
    cli = await _client_for(current_user, db)
    try:
        return await cli.set_reservation_info(payload.body)
    except TourVisioError as exc:
        _raise(exc)


@router.post("/booking/commit-transaction")
async def booking_commit(payload: GenericRequest, current_user: dict = UserDep, db=Depends(get_db)) -> Dict[str, Any]:
    cli = await _client_for(current_user, db)
    try:
        return await cli.commit_transaction(payload.body)
    except TourVisioError as exc:
        _raise(exc)


@router.post("/booking/reservation-detail")
async def booking_detail(payload: GenericRequest, current_user: dict = UserDep, db=Depends(get_db)) -> Dict[str, Any]:
    cli = await _client_for(current_user, db)
    try:
        return await cli.get_reservation_detail(payload.body)
    except TourVisioError as exc:
        _raise(exc)


# ───────────────── Cancellation ─────────────────


@router.post("/cancellation/penalty")
async def cancellation_penalty(payload: GenericRequest, current_user: dict = UserDep, db=Depends(get_db)) -> Dict[str, Any]:
    cli = await _client_for(current_user, db)
    try:
        return await cli.get_cancellation_penalty(payload.body)
    except TourVisioError as exc:
        _raise(exc)


@router.post("/cancellation/cancel")
async def cancellation_cancel(payload: GenericRequest, current_user: dict = UserDep, db=Depends(get_db)) -> Dict[str, Any]:
    cli = await _client_for(current_user, db)
    try:
        return await cli.cancel_reservation(payload.body)
    except TourVisioError as exc:
        _raise(exc)
