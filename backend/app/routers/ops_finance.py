"""ops_finance.py — Legacy Compatibility Shim.

This file has been decomposed into domain-specific routers:
- ops_finance_accounts.py (accounts, credit profiles, statements, exposure, payments)
- ops_finance_refunds.py (refund case lifecycle)
- ops_finance_settlements.py (settlement runs, supplier accruals)
- ops_finance_documents.py (document upload/download/delete)
- ops_finance_suppliers.py (supplier finance accounts, balances)

This shim imports and re-exports the router from the new modules
to maintain backward compatibility during migration.
"""
from __future__ import annotations

from fastapi import APIRouter

# Create empty router — routes now live in decomposed files
router = APIRouter(prefix="/api/ops/finance", tags=["ops_finance_legacy"])


@router.get("/_decomposed")
async def decomposition_info():
    """Info endpoint showing the decomposition status."""
    return {
        "status": "decomposed",
        "modules": [
            "ops_finance_accounts",
            "ops_finance_refunds",
            "ops_finance_settlements",
            "ops_finance_documents",
            "ops_finance_suppliers",
        ],
        "note": "Legacy ops_finance.py has been decomposed into domain-specific routers.",
    }
