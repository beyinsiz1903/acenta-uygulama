"""Syroce Marketplace v2 — Agency Contracts proxy router.

Each agency proposes commercial contracts to hotels (tenants) on the Syroce PMS.
Hotels approve/reject from their own panel. Search and reservations are then
gated by approved contracts on the PMS side.

This router proxies to the Syroce PMS `/api/marketplace/v1/contracts/*`
endpoints, scoped per organization via the encrypted X-API-Key.
"""
from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field, field_validator

from app.auth import require_roles
from app.errors import AppError
from app.security.module_guard import require_org_module
from app.services.syroce.agent import SyroceAgentClient
from app.services.syroce.errors import SyroceError

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/syroce-marketplace/contracts",
    tags=["syroce-marketplace-contracts"],
    dependencies=[require_org_module("syroce_marketplace")],
)

UserDep = Depends(require_roles(["super_admin", "admin", "agent", "operator"]))

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
ALLOWED_STATUSES = {"pending", "approved", "rejected", "terminated", "expired"}


def _validate_date(value: str, field: str) -> None:
    if not DATE_RE.match(value or ""):
        raise AppError(
            status_code=422,
            code="invalid_date",
            message=f"{field} alanı YYYY-MM-DD formatında olmalı.",
        )


# ───────────────────── Helpers ─────────────────────

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


async def _client(user: dict) -> SyroceAgentClient:
    try:
        return await SyroceAgentClient.from_organization_id(_org_id(user))
    except SyroceError as exc:
        raise _to_app_error(exc)


# ───────────────────── Pydantic models ─────────────────────

ALLOWED_PAYMENT_TERMS = {"prepaid", "on_arrival", "net_7", "net_15", "net_30"}
ALLOWED_CURRENCIES = {"TRY", "EUR", "USD"}


class CancellationPolicy(BaseModel):
    free_until_days_before: int = Field(0, ge=0, le=365)
    penalty_pct: float = Field(0.0, ge=0.0, le=100.0)
    no_show_penalty_pct: float = Field(100.0, ge=0.0, le=100.0)


class ProposeContractPayload(BaseModel):
    tenant_id: str = Field(..., min_length=1, description="Hedef otelin Syroce tenant ID'si")
    commission_pct: float = Field(..., ge=0.0, le=100.0)
    cancellation_policy: CancellationPolicy
    payment_terms: str
    valid_from: str = Field(..., description="YYYY-MM-DD")
    valid_to: str = Field(..., description="YYYY-MM-DD")
    currency: str = "TRY"
    allowed_room_types: List[str] = Field(default_factory=list)
    special_terms: Optional[str] = None

    @field_validator("payment_terms")
    @classmethod
    def _check_payment_terms(cls, v: str) -> str:
        if v not in ALLOWED_PAYMENT_TERMS:
            raise ValueError(f"payment_terms must be one of {sorted(ALLOWED_PAYMENT_TERMS)}")
        return v

    @field_validator("currency")
    @classmethod
    def _check_currency(cls, v: str) -> str:
        v = (v or "TRY").upper()
        if v not in ALLOWED_CURRENCIES:
            raise ValueError(f"currency must be one of {sorted(ALLOWED_CURRENCIES)}")
        return v


# ───────────────────── Routes ─────────────────────

@router.get("")
async def list_contracts(
    status: Optional[str] = Query(None, description="pending|approved|rejected|terminated|expired"),
    user: dict = UserDep,
):
    """List all contracts proposed by this agency."""
    if status and status not in ALLOWED_STATUSES:
        raise AppError(
            status_code=422,
            code="invalid_status",
            message=f"status alanı şunlardan biri olmalı: {sorted(ALLOWED_STATUSES)}",
        )
    client = await _client(user)
    try:
        raw = await client.list_contracts(status=status)
    except SyroceError as exc:
        raise _to_app_error(exc)
    # Normalize: PMS may return {items|contracts: [...]} or a raw array
    # (raw arrays are wrapped as {"data": [...]} by SyroceAgentClient).
    if isinstance(raw, dict):
        if "items" in raw or "contracts" in raw:
            return raw
        if isinstance(raw.get("data"), list):
            return {"items": raw["data"]}
    if isinstance(raw, list):
        return {"items": raw}
    return {"items": []}


@router.get("/{contract_id}")
async def get_contract_detail(contract_id: str, user: dict = UserDep):
    """Get details of a single contract."""
    client = await _client(user)
    try:
        return await client.get_contract(contract_id)
    except SyroceError as exc:
        raise _to_app_error(exc)


@router.post("/propose")
async def propose_contract(payload: ProposeContractPayload, user: dict = UserDep) -> Dict[str, Any]:
    """Propose a new contract to a target hotel."""
    _validate_date(payload.valid_from, "valid_from")
    _validate_date(payload.valid_to, "valid_to")
    if payload.valid_to <= payload.valid_from:
        raise AppError(
            status_code=422,
            code="invalid_date_range",
            message="valid_to tarihi valid_from tarihinden büyük olmalı.",
        )
    client = await _client(user)
    try:
        return await client.propose_contract(payload.model_dump(exclude_none=True))
    except SyroceError as exc:
        raise _to_app_error(exc)


@router.delete("/{contract_id}")
async def withdraw_contract(contract_id: str, user: dict = UserDep):
    """Withdraw a pending contract proposal."""
    client = await _client(user)
    try:
        return await client.withdraw_contract(contract_id)
    except SyroceError as exc:
        raise _to_app_error(exc)
