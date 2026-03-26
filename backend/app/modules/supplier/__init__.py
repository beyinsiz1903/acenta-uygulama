"""Supplier domain — supplier adapters, aggregation, health, credentials, activation, ecosystem.

Owner: Supplier Domain
Boundary: All supplier lifecycle — onboarding, credentials, health, search aggregation,
          circuit breaker, adapter management, and ecosystem operations.

Routers consolidated here (Phase 2, Dalga 1):
  - suppliers.py              → Supplier CRUD, listing
  - paximum_router.py         → Paximum adapter endpoints
  - admin_supplier_health.py  → Admin health monitoring
  - ops_supplier_operations.py→ Ops supplier operations
  - supplier_activation.py    → Shadow/canary activation flow
  - supplier_credentials_router.py → Credential management
  - supplier_aggregator_router.py  → Multi-supplier search aggregation
  - suppliers/router.py       → Supplier ecosystem (search, availability, pricing)
"""
from fastapi import APIRouter

from app.config import API_PREFIX

# --- Core supplier CRUD & adapters ---
from app.modules.supplier.routers.suppliers import router as suppliers_router
from app.modules.supplier.routers.paximum_router import router as paximum_router

# --- Admin & ops ---
from app.modules.supplier.routers.admin_supplier_health import router as admin_supplier_health_router
from app.modules.supplier.routers.ops_supplier_operations import router as ops_supplier_operations_router

# --- Activation & credentials (Phase 2 consolidation) ---
from app.modules.supplier.routers.supplier_activation import router as supplier_activation_router
from app.modules.supplier.routers.supplier_credentials_router import router as supplier_credentials_router

# --- Aggregation & ecosystem (Phase 2 consolidation) ---
from app.modules.supplier.routers.supplier_aggregator_router import router as supplier_aggregator_router
from app.suppliers.router import router as supplier_ecosystem_router

domain_router = APIRouter()

# Core (prefix in router definition = /api/suppliers, /api/paximum)
domain_router.include_router(suppliers_router, prefix=API_PREFIX)
domain_router.include_router(paximum_router, prefix=API_PREFIX)

# Admin & ops (prefix built-in)
domain_router.include_router(admin_supplier_health_router)
domain_router.include_router(ops_supplier_operations_router)

# Activation & credentials (prefix built-in: /api/supplier-activation, /api/supplier-credentials)
domain_router.include_router(supplier_activation_router)
domain_router.include_router(supplier_credentials_router)

# Aggregation & ecosystem (prefix built-in: /api/supplier-aggregator, /api/suppliers/ecosystem)
domain_router.include_router(supplier_aggregator_router)
domain_router.include_router(supplier_ecosystem_router)
