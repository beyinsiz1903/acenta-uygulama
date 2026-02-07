"""O2 - Data Integrity Admin Endpoints.

GET /api/admin/system/integrity-report - Run orphan detection + integrity checks
"""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.auth import require_roles
from app.services import integrity_service

router = APIRouter(
    prefix="/api/admin/system",
    tags=["system_integrity"],
)


@router.get("/integrity-report")
async def get_integrity_report(
    user=Depends(require_roles(["super_admin"])),
):
    """Run data integrity checks and return a structured report."""
    orphans = await integrity_service.detect_orphans()
    audit_chains = await integrity_service.verify_all_audit_chains()
    ledger = await integrity_service.verify_ledger_integrity()

    return {
        "orphans": orphans,
        "audit_chains": {
            "tenants_checked": audit_chains.get("tenants_checked", 0),
            "broken_chains": audit_chains.get("broken_chains", 0),
        },
        "ledger": {
            "checked_accounts": ledger.get("checked_accounts", 0),
            "mismatches": ledger.get("mismatches", 0),
        },
    }
