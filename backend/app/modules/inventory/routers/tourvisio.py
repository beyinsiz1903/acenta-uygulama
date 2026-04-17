"""TourVisio (San TSG) multi-product proxy router.

Thin per-request proxy over `TourVisioClient`. Auth: super_admin / admin / operator.
All endpoints under `/api/tourvisio/*`.

Includes a generic `/proxy` endpoint that forwards arbitrary `{path, body}` —
useful while we evolve the typed surface. The typed wrappers below cover the
high-frequency endpoints (autocomplete, pricesearch, getproductinfo, booking
lifecycle, lookups, cancellation).
"""
from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.auth import require_roles
from app.services.tourvisio import TourVisioClient, TourVisioError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/tourvisio", tags=["tourvisio"])

UserDep = Depends(require_roles(["super_admin", "admin", "operator"]))


def _client() -> TourVisioClient:
    try:
        return TourVisioClient()
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
async def tourvisio_health(_user: dict = UserDep) -> Dict[str, Any]:
    """Confirms env vars are set; does not call the upstream API."""
    keys = ["TOURVISIO_BASE_URL", "TOURVISIO_AGENCY", "TOURVISIO_USER", "TOURVISIO_PASSWORD"]
    status = {k: bool(os.environ.get(k)) for k in keys}
    return {
        "configured": all(status.values()),
        **status,
        "token": TourVisioClient.cached_token_status(),
    }


@router.post("/auth/login")
async def tourvisio_login(_user: dict = UserDep) -> Dict[str, Any]:
    """Force a fresh Login and refresh the cached token."""
    TourVisioClient.clear_cached_token()
    cli = _client()
    try:
        await cli._get_token()  # noqa: SLF001 — intentional
    except TourVisioError as exc:
        _raise(exc)
    return {"ok": True, "token": TourVisioClient.cached_token_status()}


@router.post("/auth/clear")
async def tourvisio_logout(_user: dict = UserDep) -> Dict[str, Any]:
    TourVisioClient.clear_cached_token()
    return {"ok": True, "token": TourVisioClient.cached_token_status()}


# ───────────────── Generic proxy ─────────────────


@router.post("/proxy")
async def tourvisio_proxy(payload: ProxyRequest, _user: dict = UserDep) -> Dict[str, Any]:
    """Forward to any TourVisio endpoint. Returns the unwrapped `body`."""
    cli = _client()
    try:
        return await cli.request(payload.path, payload.body)
    except TourVisioError as exc:
        _raise(exc)


# ───────────────── Lookups ─────────────────


@router.post("/lookup/payment-types")
async def lookup_payment_types(payload: GenericRequest, _user: dict = UserDep) -> Dict[str, Any]:
    cli = _client()
    try:
        return await cli.get_payment_types(payload.body)
    except TourVisioError as exc:
        _raise(exc)


@router.post("/lookup/transportations")
async def lookup_transportations(payload: GenericRequest, _user: dict = UserDep) -> Dict[str, Any]:
    cli = _client()
    try:
        return await cli.get_transportations(payload.body)
    except TourVisioError as exc:
        _raise(exc)


@router.post("/lookup/exchange-rates")
async def lookup_exchange_rates(payload: GenericRequest, _user: dict = UserDep) -> Dict[str, Any]:
    cli = _client()
    try:
        return await cli.get_exchange_rates(payload.body)
    except TourVisioError as exc:
        _raise(exc)


# ───────────────── Search ─────────────────


@router.post("/search/arrival-autocomplete")
async def search_arrival_autocomplete(payload: GenericRequest, _user: dict = UserDep) -> Dict[str, Any]:
    cli = _client()
    try:
        return await cli.autocomplete(payload.body)
    except TourVisioError as exc:
        _raise(exc)


@router.post("/search/departure-autocomplete")
async def search_departure_autocomplete(payload: GenericRequest, _user: dict = UserDep) -> Dict[str, Any]:
    cli = _client()
    try:
        return await cli.departure_autocomplete(payload.body)
    except TourVisioError as exc:
        _raise(exc)


@router.post("/search/checkin-dates")
async def search_checkin_dates(payload: GenericRequest, _user: dict = UserDep) -> Dict[str, Any]:
    cli = _client()
    try:
        return await cli.get_check_in_dates(payload.body)
    except TourVisioError as exc:
        _raise(exc)


@router.post("/search/pricesearch")
async def search_price_search(payload: GenericRequest, _user: dict = UserDep) -> Dict[str, Any]:
    cli = _client()
    try:
        return await cli.price_search(payload.body)
    except TourVisioError as exc:
        _raise(exc)


@router.post("/search/product-info")
async def search_product_info(payload: GenericRequest, _user: dict = UserDep) -> Dict[str, Any]:
    cli = _client()
    try:
        return await cli.get_product_info(payload.body)
    except TourVisioError as exc:
        _raise(exc)


@router.post("/search/offer-details")
async def search_offer_details(payload: GenericRequest, _user: dict = UserDep) -> Dict[str, Any]:
    cli = _client()
    try:
        return await cli.get_offer_details(payload.body)
    except TourVisioError as exc:
        _raise(exc)


@router.post("/search/fare-rules")
async def search_fare_rules(payload: GenericRequest, _user: dict = UserDep) -> Dict[str, Any]:
    cli = _client()
    try:
        return await cli.get_fare_rules(payload.body)
    except TourVisioError as exc:
        _raise(exc)


# ───────────────── Booking ─────────────────


@router.post("/booking/begin-transaction")
async def booking_begin(payload: GenericRequest, _user: dict = UserDep) -> Dict[str, Any]:
    cli = _client()
    try:
        return await cli.begin_transaction(payload.body)
    except TourVisioError as exc:
        _raise(exc)


@router.post("/booking/set-reservation-info")
async def booking_set_info(payload: GenericRequest, _user: dict = UserDep) -> Dict[str, Any]:
    cli = _client()
    try:
        return await cli.set_reservation_info(payload.body)
    except TourVisioError as exc:
        _raise(exc)


@router.post("/booking/commit-transaction")
async def booking_commit(payload: GenericRequest, _user: dict = UserDep) -> Dict[str, Any]:
    cli = _client()
    try:
        return await cli.commit_transaction(payload.body)
    except TourVisioError as exc:
        _raise(exc)


@router.post("/booking/reservation-detail")
async def booking_detail(payload: GenericRequest, _user: dict = UserDep) -> Dict[str, Any]:
    cli = _client()
    try:
        return await cli.get_reservation_detail(payload.body)
    except TourVisioError as exc:
        _raise(exc)


# ───────────────── Cancellation ─────────────────


@router.post("/cancellation/penalty")
async def cancellation_penalty(payload: GenericRequest, _user: dict = UserDep) -> Dict[str, Any]:
    cli = _client()
    try:
        return await cli.get_cancellation_penalty(payload.body)
    except TourVisioError as exc:
        _raise(exc)


@router.post("/cancellation/cancel")
async def cancellation_cancel(payload: GenericRequest, _user: dict = UserDep) -> Dict[str, Any]:
    cli = _client()
    try:
        return await cli.cancel_reservation(payload.body)
    except TourVisioError as exc:
        _raise(exc)
