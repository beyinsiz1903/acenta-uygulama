"""Pilot Agency Onboarding & Flow Validation API — MEGA PROMPT #35.

Endpoints:
  POST /api/pilot/setup              — Create pilot agency (wizard step 1)
  PUT  /api/pilot/setup/supplier     — Save supplier credential (step 2)
  PUT  /api/pilot/setup/accounting   — Save accounting credential (step 3)
  POST /api/pilot/test-connection    — Test connections (step 4)
  POST /api/pilot/test-search        — Test search (step 5)
  POST /api/pilot/test-booking       — Test booking (step 6)
  POST /api/pilot/test-invoice       — Test invoice (step 7)
  POST /api/pilot/test-accounting    — Test accounting sync (step 8)
  POST /api/pilot/test-reconciliation— Reconciliation check (step 9)
  GET  /api/pilot/agencies           — List pilot agencies
  GET  /api/pilot/metrics            — Pilot metrics dashboard
  GET  /api/pilot/incidents          — Pilot incidents
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.auth import require_roles
from app.services.pilot_flow_validator import (
    create_pilot_agency,
    get_pilot_agency,
    get_pilot_incidents,
    get_pilot_metrics_dashboard,
    list_pilot_agencies,
    run_batch_simulation,
    save_accounting_credential,
    save_supplier_credential,
    test_accounting_sync,
    test_booking,
    test_connections,
    test_invoice,
    test_reconciliation,
    test_search,
)

router = APIRouter(prefix="/api/pilot/onboarding", tags=["pilot-onboarding"])

_ADMIN_ROLES = ["super_admin", "admin"]


# ── Pydantic models ──────────────────────────────────────────────────

class AgencyCreatePayload(BaseModel):
    name: str
    contact_email: str = ""
    contact_phone: str = ""
    tax_id: str = ""
    mode: str = "sandbox"


class SupplierCredentialPayload(BaseModel):
    agency_name: str
    supplier_type: str
    api_key: str = ""
    api_secret: str = ""
    agency_code: str = ""


class AccountingCredentialPayload(BaseModel):
    agency_name: str
    provider_type: str
    company_code: str = ""
    username: str = ""
    password: str = ""


class AgencyNamePayload(BaseModel):
    agency_name: str


class SimulationPayload(BaseModel):
    count: int = 10
    supplier_type: str = "ratehawk"
    accounting_provider: str = "luca"


# ── Step 1: Create Agency ────────────────────────────────────────────

@router.post("/setup")
async def setup_agency(
    payload: AgencyCreatePayload,
    user: dict = Depends(require_roles(_ADMIN_ROLES)),
) -> dict[str, Any]:
    existing = await get_pilot_agency(payload.name)
    if existing:
        raise HTTPException(status_code=400, detail="Bu isimde bir pilot acenta zaten mevcut")
    return await create_pilot_agency(payload.model_dump())


# ── Step 2: Supplier Credential ──────────────────────────────────────

@router.put("/setup/supplier")
async def setup_supplier(
    payload: SupplierCredentialPayload,
    user: dict = Depends(require_roles(_ADMIN_ROLES)),
) -> dict[str, Any]:
    agency = await get_pilot_agency(payload.agency_name)
    if not agency:
        raise HTTPException(status_code=404, detail="Pilot acenta bulunamadi")
    return await save_supplier_credential(payload.agency_name, payload.model_dump())


# ── Step 3: Accounting Credential ────────────────────────────────────

@router.put("/setup/accounting")
async def setup_accounting(
    payload: AccountingCredentialPayload,
    user: dict = Depends(require_roles(_ADMIN_ROLES)),
) -> dict[str, Any]:
    agency = await get_pilot_agency(payload.agency_name)
    if not agency:
        raise HTTPException(status_code=404, detail="Pilot acenta bulunamadi")
    return await save_accounting_credential(payload.agency_name, payload.model_dump())


# ── Step 4: Connection Test ──────────────────────────────────────────

@router.post("/test-connection")
async def connection_test(
    payload: AgencyNamePayload,
    user: dict = Depends(require_roles(_ADMIN_ROLES)),
) -> dict[str, Any]:
    agency = await get_pilot_agency(payload.agency_name)
    if not agency:
        raise HTTPException(status_code=404, detail="Pilot acenta bulunamadi")
    return await test_connections(payload.agency_name)


# ── Step 5: Search Test ──────────────────────────────────────────────

@router.post("/test-search")
async def search_test(
    payload: AgencyNamePayload,
    user: dict = Depends(require_roles(_ADMIN_ROLES)),
) -> dict[str, Any]:
    agency = await get_pilot_agency(payload.agency_name)
    if not agency:
        raise HTTPException(status_code=404, detail="Pilot acenta bulunamadi")
    return await test_search(payload.agency_name)


# ── Step 6: Booking Test ─────────────────────────────────────────────

@router.post("/test-booking")
async def booking_test(
    payload: AgencyNamePayload,
    user: dict = Depends(require_roles(_ADMIN_ROLES)),
) -> dict[str, Any]:
    agency = await get_pilot_agency(payload.agency_name)
    if not agency:
        raise HTTPException(status_code=404, detail="Pilot acenta bulunamadi")
    return await test_booking(payload.agency_name)


# ── Step 7: Invoice Test ─────────────────────────────────────────────

@router.post("/test-invoice")
async def invoice_test(
    payload: AgencyNamePayload,
    user: dict = Depends(require_roles(_ADMIN_ROLES)),
) -> dict[str, Any]:
    agency = await get_pilot_agency(payload.agency_name)
    if not agency:
        raise HTTPException(status_code=404, detail="Pilot acenta bulunamadi")
    return await test_invoice(payload.agency_name)


# ── Step 8: Accounting Sync Test ─────────────────────────────────────

@router.post("/test-accounting")
async def accounting_test(
    payload: AgencyNamePayload,
    user: dict = Depends(require_roles(_ADMIN_ROLES)),
) -> dict[str, Any]:
    agency = await get_pilot_agency(payload.agency_name)
    if not agency:
        raise HTTPException(status_code=404, detail="Pilot acenta bulunamadi")
    return await test_accounting_sync(payload.agency_name)


# ── Step 9: Reconciliation Check ─────────────────────────────────────

@router.post("/test-reconciliation")
async def reconciliation_test(
    payload: AgencyNamePayload,
    user: dict = Depends(require_roles(_ADMIN_ROLES)),
) -> dict[str, Any]:
    agency = await get_pilot_agency(payload.agency_name)
    if not agency:
        raise HTTPException(status_code=404, detail="Pilot acenta bulunamadi")
    return await test_reconciliation(payload.agency_name)


# ── Batch Simulation ──────────────────────────────────────────────────

@router.post("/run-simulation")
async def simulation_run(
    payload: SimulationPayload,
    user: dict = Depends(require_roles(_ADMIN_ROLES)),
) -> dict[str, Any]:
    count = min(payload.count, 20)  # Cap at 20
    return await run_batch_simulation(count, payload.supplier_type, payload.accounting_provider)


# ── Read Endpoints ───────────────────────────────────────────────────

@router.get("/agencies")
async def agencies_list(
    user: dict = Depends(require_roles(_ADMIN_ROLES)),
) -> dict[str, Any]:
    return await list_pilot_agencies()


@router.get("/metrics")
async def metrics_dashboard(
    user: dict = Depends(require_roles(_ADMIN_ROLES)),
) -> dict[str, Any]:
    return await get_pilot_metrics_dashboard()


@router.get("/incidents")
async def incidents_list(
    user: dict = Depends(require_roles(_ADMIN_ROLES)),
) -> dict[str, Any]:
    return await get_pilot_incidents()
