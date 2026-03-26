"""Finance domain — billing, payments, settlements, invoicing, accounting, ledger.

Owner: Finance Domain
Boundary: All financial lifecycle — billing, payments, settlements, invoicing,
          accounting, ledger, reconciliation, orders, and financial operations.

Phase 2, Dalga 3 additions:
  - routers/finance_ledger.py (ledger, settlement-runs, recon, exceptions)
  - routers/settlements.py (agency, hotel, network settlements)
  - routers/order_router.py (OMS)
"""
from fastapi import APIRouter

from app.config import API_PREFIX

# --- Core finance ---
from app.modules.finance.routers.finance import router as finance_router
from app.modules.finance.routers.admin_billing import router as admin_billing_router
from app.modules.finance.routers.admin_settlements import router as admin_settlements_router
from app.modules.finance.routers.admin_statements import router as admin_statements_router
from app.modules.finance.routers.admin_parasut import router as admin_parasut_router
from app.modules.finance.routers.admin_accounting import router as admin_accounting_router
from app.modules.finance.routers.billing_checkout import router as billing_checkout_router
from app.modules.finance.routers.billing_lifecycle import router as billing_lifecycle_router
from app.modules.finance.routers.billing_webhooks import router as billing_webhooks_router
from app.modules.finance.routers.payments import router as payments_router
from app.modules.finance.routers.payments_stripe import router as payments_stripe_router
from app.modules.finance.routers.efatura import router as efatura_router
from app.modules.finance.routers.invoice_engine import router as invoice_engine_router
from app.modules.finance.routers.reconciliation import router as reconciliation_router
from app.modules.finance.routers.multicurrency import router as multicurrency_router
from app.modules.finance.routers.accounting_sync import router as accounting_sync_router
from app.modules.finance.routers.accounting_providers import router as accounting_providers_router
from app.modules.finance.routers.commission_rules import router as commission_rules_router

# --- Ops finance ---
from app.modules.finance.routers.ops_finance import router as ops_finance_router
from app.modules.finance.routers.ops_finance_accounts import router as ops_finance_accounts_router
from app.modules.finance.routers.ops_finance_refunds import router as ops_finance_refunds_router
from app.modules.finance.routers.ops_finance_settlements import router as ops_finance_settlements_router
from app.modules.finance.routers.ops_finance_documents import router as ops_finance_documents_router
from app.modules.finance.routers.ops_finance_suppliers import router as ops_finance_suppliers_router
from app.modules.finance.routers.ops_click_to_pay import router as ops_click_to_pay_router
from app.modules.finance.routers.public_click_to_pay import router as public_click_to_pay_router

# --- Ledger & settlement runs (Phase 2, Dalga 3) ---
from app.modules.finance.routers.finance_ledger import (
    router as finance_ledger_router,
    settlement_router as finance_settlement_router,
    recon_router as finance_recon_router,
    exception_router as finance_exception_router,
)

# --- Agency/Hotel/Network settlements (Phase 2, Dalga 3) ---
from app.modules.finance.routers.settlements import (
    agency_router as agency_settlements_router,
    hotel_router as hotel_settlements_router,
    network_settlements_router,
)

# --- OMS (Phase 2, Dalga 3) ---
from app.modules.finance.routers.order_router import router as order_router

domain_router = APIRouter()

# Core finance
domain_router.include_router(finance_router, prefix=API_PREFIX)
domain_router.include_router(admin_billing_router)
domain_router.include_router(admin_settlements_router)
domain_router.include_router(admin_statements_router)
domain_router.include_router(admin_parasut_router)
domain_router.include_router(admin_accounting_router)
domain_router.include_router(billing_checkout_router)
domain_router.include_router(billing_lifecycle_router)
domain_router.include_router(billing_webhooks_router)
domain_router.include_router(payments_router, prefix=API_PREFIX)
domain_router.include_router(payments_stripe_router, prefix=API_PREFIX)
domain_router.include_router(efatura_router)
domain_router.include_router(invoice_engine_router)
domain_router.include_router(reconciliation_router)
domain_router.include_router(multicurrency_router)
domain_router.include_router(accounting_sync_router)
domain_router.include_router(accounting_providers_router)
domain_router.include_router(commission_rules_router)

# Ops finance
domain_router.include_router(ops_finance_router)
domain_router.include_router(ops_finance_accounts_router)
domain_router.include_router(ops_finance_refunds_router)
domain_router.include_router(ops_finance_settlements_router)
domain_router.include_router(ops_finance_documents_router)
domain_router.include_router(ops_finance_suppliers_router)
domain_router.include_router(ops_click_to_pay_router)
domain_router.include_router(public_click_to_pay_router)

# Ledger & settlement runs (prefix built-in: /api/finance/*)
domain_router.include_router(finance_ledger_router)
domain_router.include_router(finance_settlement_router)
domain_router.include_router(finance_recon_router)
domain_router.include_router(finance_exception_router)

# Agency/Hotel/Network settlements (prefix built-in: /api/agency, /api/hotel, /api/settlements)
domain_router.include_router(agency_settlements_router)
domain_router.include_router(hotel_settlements_router)
domain_router.include_router(network_settlements_router)

# OMS (prefix built-in: /api/orders)
domain_router.include_router(order_router)
