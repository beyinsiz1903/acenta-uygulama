"""Supplier Finance Router — Decomposed from ops_finance.py.

Handles: supplier accounts, balances, payable summary.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from bson import ObjectId

from app.db import get_db
from app.auth import require_roles
from app.services.supplier_finance import SupplierFinanceService

router = APIRouter(prefix="/api/ops/finance", tags=["ops_finance_suppliers"])


@router.get("/suppliers/{supplier_id}/accounts")
async def get_supplier_accounts(
    supplier_id: str,
    current_user=Depends(require_roles(["admin", "ops", "super_admin"])),
    db=Depends(get_db),
):
    org_id = current_user["organization_id"]
    svc = SupplierFinanceService(db)
    accounts = await svc.get_supplier_accounts(org_id, supplier_id)
    return {
        "supplier_id": supplier_id,
        "accounts": [
            {"account_id": acc["account_id"], "currency": acc["currency"], "code": acc["code"], "name": acc["name"], "status": acc["status"]}
            for acc in accounts
        ]
    }


@router.get("/suppliers/{supplier_id}/balances")
async def get_supplier_balances(
    supplier_id: str,
    currency: str = Query("EUR"),
    current_user=Depends(require_roles(["admin", "ops", "super_admin"])),
    db=Depends(get_db),
):
    org_id = current_user["organization_id"]
    svc = SupplierFinanceService(db)
    balance = await svc.get_supplier_balance(org_id, supplier_id, currency)
    return {"supplier_id": supplier_id, "currency": currency, "balance": balance}


@router.post("/suppliers/{supplier_id}/accounts/ensure")
async def ensure_supplier_account(
    supplier_id: str,
    currency: str = Query("EUR"),
    current_user=Depends(require_roles(["admin", "ops", "super_admin"])),
    db=Depends(get_db),
):
    org_id = current_user["organization_id"]
    svc = SupplierFinanceService(db)
    account_id = await svc.get_or_create_supplier_account(org_id, supplier_id, currency)
    account = await db.finance_accounts.find_one({"_id": ObjectId(account_id)})
    return {"account_id": account_id, "supplier_id": supplier_id, "currency": currency, "code": account["code"], "name": account["name"], "status": account["status"]}


@router.get("/suppliers/payable-summary")
async def get_supplier_payable_summary(
    currency: str = Query("EUR"),
    current_user=Depends(require_roles(["admin", "ops", "super_admin"])),
    db=Depends(get_db),
):
    org_id = current_user["organization_id"]
    svc = SupplierFinanceService(db)
    balances = await svc.get_all_supplier_balances(org_id, currency)
    return {"currency": currency, "total_payable": sum(b["balance"] for b in balances), "supplier_count": len(balances), "items": balances}
