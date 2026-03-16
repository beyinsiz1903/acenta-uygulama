"""Finance Ledger Router — Phase 2A Visibility + Phase 2B Workflow & Ops.

Read-only endpoints for visibility plus workflow actions for settlement runs
and exception management.
"""
from __future__ import annotations

from fastapi import APIRouter, Query
from typing import Optional
from pydantic import BaseModel

from app.services.finance_ledger_service import (
    get_ledger_entries,
    get_ledger_entry_by_id,
    get_ledger_summary,
    get_receivable_payable,
    get_recent_postings,
    get_agency_balances,
    get_supplier_payables,
)
from app.services.settlement_run_service import (
    get_settlement_runs,
    get_settlement_run_by_id,
    get_settlement_run_stats,
)
from app.services.reconciliation_summary_service import (
    get_reconciliation_summary,
    get_reconciliation_snapshots,
    get_margin_revenue_summary,
)
from app.services.settlement_workflow_service import (
    create_settlement_draft,
    transition_settlement,
    add_entries_to_draft,
    remove_entry_from_draft,
    get_unassigned_entries,
)
from app.services.finance_exception_service import (
    get_exceptions,
    get_exception_stats,
    resolve_exception,
    dismiss_exception,
)

router = APIRouter(prefix="/api/finance/ledger", tags=["Finance Ledger"])
settlement_router = APIRouter(prefix="/api/finance/settlement-runs", tags=["Settlement Runs"])
recon_router = APIRouter(prefix="/api/finance/reconciliation", tags=["Reconciliation"])
exception_router = APIRouter(prefix="/api/finance/exceptions", tags=["Finance Exceptions"])

ORG_ID = "default_org"


# ── Pydantic models for request bodies ──

class CreateDraftRequest(BaseModel):
    run_type: str
    entity_id: str
    entity_name: str
    period_start: str
    period_end: str
    currency: str = "EUR"
    notes: Optional[str] = None

class TransitionRequest(BaseModel):
    actor: str = "admin"
    reason: Optional[str] = None

class AddEntriesRequest(BaseModel):
    entry_ids: list[str]

class ResolveExceptionRequest(BaseModel):
    resolution: str
    resolved_by: str = "admin"
    notes: Optional[str] = None

class DismissExceptionRequest(BaseModel):
    reason: str = ""


# ---------------------------------------------------------------------------
# Ledger Endpoints
# ---------------------------------------------------------------------------

@router.get("/summary")
async def api_ledger_summary():
    return await get_ledger_summary(ORG_ID)


@router.get("/receivable-payable")
async def api_receivable_payable():
    return await get_receivable_payable(ORG_ID)


@router.get("/recent-postings")
async def api_recent_postings(limit: int = Query(20, ge=1, le=100)):
    return await get_recent_postings(ORG_ID, limit=limit)


@router.get("/agency-balances")
async def api_agency_balances(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    status: Optional[str] = None,
):
    return await get_agency_balances(ORG_ID, skip=skip, limit=limit, status=status)


@router.get("/supplier-payables")
async def api_supplier_payables(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    status: Optional[str] = None,
):
    return await get_supplier_payables(ORG_ID, skip=skip, limit=limit, status=status)


@router.get("/entries")
async def api_ledger_entries(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    account_type: Optional[str] = None,
    entity_type: Optional[str] = None,
    financial_status: Optional[str] = None,
):
    return await get_ledger_entries(
        ORG_ID,
        skip=skip,
        limit=limit,
        account_type=account_type,
        entity_type=entity_type,
        financial_status=financial_status,
    )


@router.get("/entries/{entry_id}")
async def api_ledger_entry_detail(entry_id: str):
    entry = await get_ledger_entry_by_id(ORG_ID, entry_id)
    if not entry:
        return {"error": "Entry not found"}, 404
    return entry


# ---------------------------------------------------------------------------
# Settlement Run Endpoints
# ---------------------------------------------------------------------------

@settlement_router.get("")
async def api_settlement_runs(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    status: Optional[str] = None,
    run_type: Optional[str] = None,
):
    return await get_settlement_runs(
        ORG_ID, skip=skip, limit=limit, status=status, run_type=run_type
    )


@settlement_router.get("/stats")
async def api_settlement_run_stats():
    return await get_settlement_run_stats(ORG_ID)


@settlement_router.get("/unassigned-entries")
async def api_unassigned_entries(
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    limit: int = Query(100, ge=1, le=500),
):
    return await get_unassigned_entries(ORG_ID, entity_type=entity_type, entity_id=entity_id, limit=limit)


@settlement_router.get("/{run_id}")
async def api_settlement_run_detail(run_id: str):
    run = await get_settlement_run_by_id(ORG_ID, run_id)
    if not run:
        return {"error": "Settlement run not found"}, 404
    return run


# ---------------------------------------------------------------------------
# Settlement Workflow Endpoints (Phase 2B)
# ---------------------------------------------------------------------------

@settlement_router.post("")
async def api_create_settlement_draft(body: CreateDraftRequest):
    result = await create_settlement_draft(
        org_id=ORG_ID,
        run_type=body.run_type,
        entity_id=body.entity_id,
        entity_name=body.entity_name,
        period_start=body.period_start,
        period_end=body.period_end,
        currency=body.currency,
        notes=body.notes,
    )
    return result


@settlement_router.patch("/{run_id}/submit")
async def api_submit_settlement(run_id: str, body: TransitionRequest):
    result = await transition_settlement(ORG_ID, run_id, "pending_approval", body.actor, body.reason)
    if "error" in result:
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=result.get("status_code", 400), content={"error": result["error"]})
    return result


@settlement_router.patch("/{run_id}/approve")
async def api_approve_settlement(run_id: str, body: TransitionRequest):
    result = await transition_settlement(ORG_ID, run_id, "approved", body.actor, body.reason)
    if "error" in result:
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=result.get("status_code", 400), content={"error": result["error"]})
    return result


@settlement_router.patch("/{run_id}/reject")
async def api_reject_settlement(run_id: str, body: TransitionRequest):
    result = await transition_settlement(ORG_ID, run_id, "rejected", body.actor, body.reason)
    if "error" in result:
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=result.get("status_code", 400), content={"error": result["error"]})
    return result


@settlement_router.patch("/{run_id}/mark-paid")
async def api_mark_paid_settlement(run_id: str, body: TransitionRequest):
    result = await transition_settlement(ORG_ID, run_id, "paid", body.actor, body.reason)
    if "error" in result:
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=result.get("status_code", 400), content={"error": result["error"]})
    return result


@settlement_router.post("/{run_id}/add-entries")
async def api_add_entries_to_draft(run_id: str, body: AddEntriesRequest):
    result = await add_entries_to_draft(ORG_ID, run_id, body.entry_ids)
    if "error" in result:
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=result.get("status_code", 400), content={"error": result["error"]})
    return result


@settlement_router.delete("/{run_id}/remove-entry/{entry_id}")
async def api_remove_entry_from_draft(run_id: str, entry_id: str):
    result = await remove_entry_from_draft(ORG_ID, run_id, entry_id)
    if "error" in result:
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=result.get("status_code", 400), content={"error": result["error"]})
    return result


# ---------------------------------------------------------------------------
# Reconciliation Endpoints
# ---------------------------------------------------------------------------

@recon_router.get("/summary")
async def api_reconciliation_summary():
    return await get_reconciliation_summary(ORG_ID)


@recon_router.get("/snapshots")
async def api_reconciliation_snapshots(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
):
    return await get_reconciliation_snapshots(ORG_ID, skip=skip, limit=limit, status=status)


@recon_router.get("/margin-revenue")
async def api_margin_revenue_summary():
    return await get_margin_revenue_summary(ORG_ID)


# ---------------------------------------------------------------------------
# Finance Overview (aggregated dashboard data)
# ---------------------------------------------------------------------------

@router.get("/overview")
async def api_finance_overview():
    """Combined endpoint for the Finance Overview dashboard KPIs."""
    ledger_sum = await get_ledger_summary(ORG_ID)
    recv_pay = await get_receivable_payable(ORG_ID)
    settlement_stats = await get_settlement_run_stats(ORG_ID)
    recon = await get_reconciliation_summary(ORG_ID)
    exc_stats = await get_exception_stats(ORG_ID)

    return {
        "ledger_summary": ledger_sum,
        "receivable_payable": recv_pay,
        "settlement_stats": settlement_stats,
        "reconciliation": recon,
        "exception_stats": exc_stats,
    }


# ---------------------------------------------------------------------------
# Exception Queue Endpoints (Phase 2B)
# ---------------------------------------------------------------------------

@exception_router.get("")
async def api_exceptions(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    status: Optional[str] = None,
    severity: Optional[str] = None,
    exception_type: Optional[str] = None,
):
    return await get_exceptions(
        ORG_ID, skip=skip, limit=limit, status=status,
        severity=severity, exception_type=exception_type,
    )


@exception_router.get("/stats")
async def api_exception_stats():
    return await get_exception_stats(ORG_ID)


@exception_router.patch("/{exception_id}/resolve")
async def api_resolve_exception(exception_id: str, body: ResolveExceptionRequest):
    result = await resolve_exception(
        ORG_ID, exception_id, body.resolution, body.resolved_by, body.notes,
    )
    if "error" in result:
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=result.get("status_code", 400), content={"error": result["error"]})
    return result


@exception_router.patch("/{exception_id}/dismiss")
async def api_dismiss_exception(exception_id: str, body: DismissExceptionRequest):
    result = await dismiss_exception(ORG_ID, exception_id, body.reason)
    if "error" in result:
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=result.get("status_code", 400), content={"error": result["error"]})
    return result


# ---------------------------------------------------------------------------
# Seed endpoint (dev only)
# ---------------------------------------------------------------------------

@router.post("/seed")
async def api_seed_finance_data():
    """Seed demo finance data for development/testing."""
    from app.services.finance_seed_service import seed_finance_data
    result = await seed_finance_data(ORG_ID)
    return result
