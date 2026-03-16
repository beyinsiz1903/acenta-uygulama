"""Finance Ledger Router — Phase 2A Visibility Layer.

All read-only endpoints for the Financial Ledger & Settlement system.
"""
from __future__ import annotations

from fastapi import APIRouter, Query
from typing import Optional

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

router = APIRouter(prefix="/api/finance/ledger", tags=["Finance Ledger"])
settlement_router = APIRouter(prefix="/api/finance/settlement-runs", tags=["Settlement Runs"])
recon_router = APIRouter(prefix="/api/finance/reconciliation", tags=["Reconciliation"])

ORG_ID = "default_org"


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


@settlement_router.get("/{run_id}")
async def api_settlement_run_detail(run_id: str):
    run = await get_settlement_run_by_id(ORG_ID, run_id)
    if not run:
        return {"error": "Settlement run not found"}, 404
    return run


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

    return {
        "ledger_summary": ledger_sum,
        "receivable_payable": recv_pay,
        "settlement_stats": settlement_stats,
        "reconciliation": recon,
    }


# ---------------------------------------------------------------------------
# Seed endpoint (dev only)
# ---------------------------------------------------------------------------

@router.post("/seed")
async def api_seed_finance_data():
    """Seed demo finance data for development/testing."""
    from app.services.finance_seed_service import seed_finance_data
    result = await seed_finance_data(ORG_ID)
    return result
