"""Domain-based Router Registry — organized by bounded contexts.

Phase 2 complete: ALL routers consolidated into domain modules.

Domain Structure (16 domains):
  0.  TENANT     — multi-tenant isolation (security boundary)
  1.  BOOKING    — unified state machine, booking lifecycle
  2.  AUTH       — authentication, 2FA, password reset
  3.  IDENTITY   — users, agencies, RBAC, tenants, settings
  4.  B2B        — B2B network, marketplace, exchanges, partners
  5.  SUPPLIER   — supplier adapters, aggregation, health, credentials
  6.  FINANCE    — billing, payments, settlements, invoicing, ledger, OMS
  7.  CRM        — customers, deals, tasks, activities, leads, inbox
  8.  OPERATIONS — ops cases, tasks, incidents, tickets
  9.  ENTERPRISE — audit, approvals, governance, risk, policies
  10. SYSTEM     — health, infra, cache, monitoring, platform layers, extensions
  11. INVENTORY  — hotel/room management, availability, PMS, sheets, search
  12. PRICING    — pricing engine, rules, quotes, offers, marketplace
  13. PUBLIC     — storefront, public search, checkout, SEO
  14. REPORTING  — reports, analytics, dashboard, exports
  15. WEBHOOKS   — organization-scoped webhooks + admin

Legacy routers remaining in registry: 2 (orphan migration, outbox admin)
"""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.exception_handlers import register_exception_handlers


def register_routers(app: FastAPI) -> None:
    register_exception_handlers(app)

    # Static files
    uploads_dir = Path(__file__).resolve().parents[1] / "uploads" / "tours"
    uploads_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/api/uploads/tours", StaticFiles(directory=str(uploads_dir)), name="tour_uploads")

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # DOMAIN 0: TENANT ISOLATION (Security Boundary)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    from app.modules.tenant.router import router as tenant_isolation_router
    app.include_router(tenant_isolation_router)

    # Legacy admin: Orphan Migration + Outbox (kept here — cross-domain utilities)
    from app.routers.admin_orphan_migration import router as orphan_migration_router
    app.include_router(orphan_migration_router)

    from app.routers.admin_outbox import router as outbox_admin_router
    app.include_router(outbox_admin_router, prefix="/api")

    # Webhook System (Organization-scoped + Admin)
    from app.routers.webhooks import router as webhooks_router
    app.include_router(webhooks_router, prefix="/api")

    from app.routers.admin_webhooks import router as admin_webhooks_router
    app.include_router(admin_webhooks_router, prefix="/api")

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # DOMAIN 1: BOOKING
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    from app.modules.booking import domain_router as booking_domain
    app.include_router(booking_domain)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # DOMAIN 2: AUTH
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    from app.modules.auth import domain_router as auth_domain
    app.include_router(auth_domain)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # DOMAIN 3: IDENTITY
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    from app.modules.identity import domain_router as identity_domain
    app.include_router(identity_domain)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # DOMAIN 4: B2B
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    from app.modules.b2b import domain_router as b2b_domain
    app.include_router(b2b_domain)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # DOMAIN 5: SUPPLIER
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    from app.modules.supplier import domain_router as supplier_domain
    app.include_router(supplier_domain)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # DOMAIN 6: FINANCE
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    from app.modules.finance import domain_router as finance_domain
    app.include_router(finance_domain)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # DOMAIN 7: CRM
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    from app.modules.crm import domain_router as crm_domain
    app.include_router(crm_domain)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # DOMAIN 8: OPERATIONS
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    from app.modules.operations import domain_router as operations_domain
    app.include_router(operations_domain)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # DOMAIN 9: ENTERPRISE
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    from app.modules.enterprise import domain_router as enterprise_domain
    app.include_router(enterprise_domain)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # DOMAIN 10: SYSTEM
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    from app.modules.system import domain_router as system_domain
    app.include_router(system_domain)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # DOMAIN 11: INVENTORY
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    from app.modules.inventory import domain_router as inventory_domain
    app.include_router(inventory_domain)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # DOMAIN 12: PRICING
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    from app.modules.pricing import domain_router as pricing_domain
    app.include_router(pricing_domain)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # DOMAIN 13: PUBLIC
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    from app.modules.public import domain_router as public_domain
    app.include_router(public_domain)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # DOMAIN 14: REPORTING
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    from app.modules.reporting import domain_router as reporting_domain
    app.include_router(reporting_domain)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # CUSTOMER PORTAL (registered directly to avoid circular imports in public domain)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    from app.modules.operations.routers.customer_portal import router as customer_portal_router
    app.include_router(customer_portal_router)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # V1 ALIASES (backward compatibility)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    from app.bootstrap.v1_registry import register_v1_routers
    register_v1_routers(app)
