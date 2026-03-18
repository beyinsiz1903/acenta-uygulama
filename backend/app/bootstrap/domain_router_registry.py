"""Domain-based Router Registry — organized by bounded contexts.

BEFORE: 234 individual router imports + 234 include_router calls (spaghetti)
AFTER:  15 domain aggregate imports + remaining specialized routers

Domain Structure:
  1. AUTH       — authentication, 2FA, password reset
  2. IDENTITY   — users, agencies, RBAC, tenants, settings, whitelabel
  3. BOOKING    — unified state machine, booking commands
  4. B2B        — B2B network, marketplace, exchanges
  5. SUPPLIER   — supplier adapters, aggregation, health
  6. FINANCE    — billing, payments, settlements, invoicing, accounting
  7. CRM        — customers, deals, tasks, activities, leads
  8. OPERATIONS — ops cases, tasks, incidents
  9. ENTERPRISE — audit, approvals, governance
  10. SYSTEM    — health, infra, cache, monitoring, notifications
  11+ Remaining — inventory, public, admin misc, specialized routers
"""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.config import API_PREFIX
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

    # ADMIN: Orphan Order Migration
    from app.routers.admin_orphan_migration import router as orphan_migration_router
    app.include_router(orphan_migration_router)

    # ADMIN: Outbox Consumer Monitoring
    from app.routers.admin_outbox import router as outbox_admin_router
    app.include_router(outbox_admin_router, prefix="/api")

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # DOMAIN 1: BOOKING (Unified State Machine)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    from app.modules.booking.router import router as booking_commands_router
    from app.modules.booking.migration_router import router as booking_migration_router
    app.include_router(booking_commands_router, prefix="/api")
    app.include_router(booking_migration_router, prefix="/api")

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # DOMAIN 2: AUTH
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    from app.modules.auth import domain_router as auth_domain
    app.include_router(auth_domain)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # DOMAIN 3: IDENTITY (Users, Agencies, Tenants, RBAC)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    from app.modules.identity import domain_router as identity_domain
    app.include_router(identity_domain)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # DOMAIN 4: B2B (Network, Marketplace, Exchange)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    from app.modules.b2b import domain_router as b2b_domain
    app.include_router(b2b_domain)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # DOMAIN 5: SUPPLIER (Adapters, Aggregation, Health)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    from app.modules.supplier import domain_router as supplier_domain
    app.include_router(supplier_domain)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # DOMAIN 6: FINANCE (Billing, Payments, Settlements, Invoicing)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    from app.modules.finance import domain_router as finance_domain
    app.include_router(finance_domain)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # DOMAIN 7: CRM (Customers, Deals, Activities, Leads)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    from app.modules.crm import domain_router as crm_domain
    app.include_router(crm_domain)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # DOMAIN 8: OPERATIONS (Cases, Tasks, Incidents)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    from app.modules.operations import domain_router as operations_domain
    app.include_router(operations_domain)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # DOMAIN 9: ENTERPRISE (Audit, Approvals, Governance)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    from app.modules.enterprise import domain_router as enterprise_domain
    app.include_router(enterprise_domain)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # DOMAIN 10: SYSTEM (Health, Infra, Cache, Monitoring)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    from app.modules.system import domain_router as system_domain
    app.include_router(system_domain)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # REMAINING: Admin, Inventory, Public, Specialized
    # (to be consolidated in next phases)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    # --- Admin Core ---
    from app.routers.admin import router as admin_router
    from app.routers.admin_accounting import router as admin_accounting_router
    from app.routers.admin_analytics import router as admin_analytics_router
    from app.routers.admin_campaigns import router as admin_campaigns_router
    from app.routers.admin_catalog import router as admin_catalog_router
    from app.routers.admin_cms_pages import router as admin_cms_pages_router
    from app.routers.admin_coupons import router as admin_coupons_router
    from app.routers.admin_demo_guide import router as admin_demo_guide_router
    from app.routers.admin_funnel import router as admin_funnel_router
    from app.routers.admin_hotels import router as admin_hotels_router
    from app.routers.admin_ical import router as admin_ical_router
    from app.routers.admin_import import router as admin_import_router
    from app.routers.admin_insights import router as admin_insights_router
    from app.routers.admin_integrations import router as admin_integrations_router
    from app.routers.admin_jobs import router as admin_jobs_router
    from app.routers.admin_links import router as admin_links_router
    from app.routers.admin_metrics import router as admin_metrics_router
    from app.routers.admin_partners import router as admin_partners_router
    from app.routers.admin_pricing import router as admin_pricing_router
    from app.routers.admin_pricing_incidents import router as admin_pricing_incidents_router
    from app.routers.admin_pricing_trace import router as admin_pricing_trace_router
    from app.routers.admin_reporting import router as admin_reporting_router
    from app.routers.admin_reports import router as admin_reports_router
    from app.routers.admin_sheets import router as admin_sheets_router
    from app.routers.admin_tours import router as admin_tours_router
    app.include_router(admin_router)
    app.include_router(admin_accounting_router)
    app.include_router(admin_analytics_router)
    app.include_router(admin_campaigns_router)
    app.include_router(admin_catalog_router)
    app.include_router(admin_cms_pages_router)
    app.include_router(admin_coupons_router)
    app.include_router(admin_demo_guide_router)
    app.include_router(admin_funnel_router)
    app.include_router(admin_hotels_router)
    app.include_router(admin_ical_router)
    app.include_router(admin_import_router)
    app.include_router(admin_insights_router)
    app.include_router(admin_integrations_router)
    app.include_router(admin_jobs_router)
    app.include_router(admin_links_router)
    app.include_router(admin_metrics_router)
    app.include_router(admin_partners_router)
    app.include_router(admin_pricing_router)
    app.include_router(admin_pricing_incidents_router)
    app.include_router(admin_pricing_trace_router)
    app.include_router(admin_reporting_router)
    app.include_router(admin_reports_router)
    app.include_router(admin_sheets_router)
    app.include_router(admin_tours_router)

    # --- Booking Legacy (existing routers, to be migrated to modules/booking) ---
    from app.routers.bookings import router as bookings_router
    from app.routers.booking_outcomes import router as booking_outcomes_router
    app.include_router(bookings_router, prefix=API_PREFIX)
    app.include_router(booking_outcomes_router, prefix=API_PREFIX)

    # --- Inventory ---
    from app.routers.inventory_shares import router as inventory_shares_router
    from app.routers.inventory_snapshots_api import router as inventory_snapshots_api_router
    from app.routers.products import router as products_router
    from app.routers.hotel import router as agency_hotels_router
    from app.routers.hotel_integrations import router as hotel_integrations_router
    from app.routers.agency_availability import router as agency_availability_router
    from app.routers.agency_reservations import router as agency_reservations_router
    from app.routers.agency_pms import router as agency_pms_router
    from app.routers.agency_pms_accounting import router as agency_pms_accounting_router
    from app.routers.agency_sheets import router as agency_sheets_router
    from app.routers.agency_writeback import router as agency_writeback_router
    from app.routers.agency_booking import router as agency_booking_router
    from app.routers.rateplans import router as rateplans_router
    from app.routers.search import router as search_router
    from app.routers.reservations import router as reservations_router
    app.include_router(inventory_shares_router)
    app.include_router(inventory_snapshots_api_router)
    app.include_router(products_router, prefix=API_PREFIX)
    app.include_router(agency_hotels_router)
    app.include_router(hotel_integrations_router)
    app.include_router(agency_availability_router)
    app.include_router(agency_reservations_router)
    app.include_router(agency_pms_router)
    app.include_router(agency_pms_accounting_router)
    app.include_router(agency_sheets_router)
    app.include_router(agency_writeback_router)
    app.include_router(agency_booking_router)
    app.include_router(rateplans_router)
    app.include_router(search_router, prefix=API_PREFIX)
    app.include_router(reservations_router, prefix=API_PREFIX)

    # --- Public / Storefront ---
    from app.routers.public_bookings import router as public_bookings_router
    from app.routers.public_campaigns import router as public_campaigns_router
    from app.routers.public_checkout import router as public_checkout_router
    from app.routers.public_cms_pages import router as public_cms_pages_router
    from app.routers.public_my_booking import router as public_my_booking_router
    from app.routers.public_partners import router as public_partners_router
    from app.routers.public_search import router as public_search_router
    from app.routers.public_tours import router as public_tours_router
    from app.routers.storefront import router as storefront_router
    from app.routers.seo import router as seo_router
    from app.routers.tours_browse import router as tours_browse_router
    from app.routers.web_booking import router as web_booking_router
    from app.routers.web_catalog import router as web_catalog_router
    app.include_router(public_bookings_router)
    app.include_router(public_campaigns_router)
    app.include_router(public_checkout_router)
    app.include_router(public_cms_pages_router)
    app.include_router(public_my_booking_router)
    app.include_router(public_partners_router)
    app.include_router(public_search_router)
    app.include_router(public_tours_router)
    app.include_router(storefront_router)
    app.include_router(seo_router)
    app.include_router(tours_browse_router)
    app.include_router(web_booking_router, prefix=API_PREFIX)
    app.include_router(web_catalog_router, prefix=API_PREFIX)

    # --- Marketplace / Pricing ---
    from app.routers.marketplace import router as marketplace_router
    from app.routers.marketplace_supplier_mapping import router as marketplace_supplier_mapping_router
    from app.routers.pricing import router as pricing_router
    from app.routers.pricing_rules import router as pricing_rules_router
    from app.routers.pricing_quote import router as pricing_quote_router
    from app.routers.offers import router as offers_router
    from app.routers.offers_booking import router as offers_booking_router
    from app.routers.quotes import router as quotes_router
    from app.routers.vouchers import router as vouchers_router
    from app.routers.voucher import router as voucher_router
    from app.routers.cancel_reasons import router as cancel_reasons_router
    app.include_router(marketplace_router, prefix=API_PREFIX)
    app.include_router(marketplace_supplier_mapping_router, prefix=API_PREFIX)
    app.include_router(pricing_router, prefix=API_PREFIX)
    app.include_router(pricing_rules_router, prefix=API_PREFIX)
    app.include_router(pricing_quote_router)
    app.include_router(offers_router)
    app.include_router(offers_booking_router)
    app.include_router(quotes_router)
    app.include_router(vouchers_router, prefix=API_PREFIX)
    app.include_router(voucher_router)
    app.include_router(cancel_reasons_router)

    # --- Reports ---
    from app.routers.reports import router as reports_router
    from app.routers.advanced_reports import router as advanced_reports_router
    from app.routers.exports import router as exports_router
    from app.routers.exports import public_router as public_exports_router
    app.include_router(reports_router)
    app.include_router(advanced_reports_router)
    app.include_router(exports_router)
    app.include_router(public_exports_router)

    # --- Misc Specialized ---
    from app.routers.inbox import router as inbox_router
    from app.routers.inbox_v2 import router as inbox_v2_router
    from app.routers.tickets import router as tickets_router
    from app.routers.ai_assistant import router as ai_assistant_router
    from app.routers.dashboard_enhanced import router as dashboard_enhanced_router
    from app.routers.matches import router as matches_router
    from app.routers.match_alerts import router as match_alerts_router
    from app.routers.match_unblock import router as match_unblock_router
    from app.routers.risk_snapshots import router as risk_snapshots_router
    from app.routers.action_policies import router as action_policies_router
    from app.routers.approval_tasks import router as approval_tasks_router
    from app.routers.demo_scale_ui_proof import router as demo_scale_ui_proof_router
    from app.routers.dev_saas import router as dev_saas_router
    from app.routers.theme import router as theme_router
    from app.routers.upgrade_requests import router as upgrade_requests_router
    from app.routers.webpos import router as webpos_router
    from app.routers.integrator_management import router as integrator_management_router
    from app.routers.partner_graph import router as partner_graph_router
    from app.routers.partner_v1 import router as partner_v1_router
    app.include_router(inbox_router)
    app.include_router(inbox_v2_router)
    app.include_router(tickets_router)
    app.include_router(ai_assistant_router)
    app.include_router(dashboard_enhanced_router)
    app.include_router(matches_router)
    app.include_router(match_alerts_router)
    app.include_router(match_unblock_router)
    app.include_router(risk_snapshots_router)
    app.include_router(action_policies_router)
    app.include_router(approval_tasks_router)
    app.include_router(demo_scale_ui_proof_router)
    app.include_router(dev_saas_router)
    app.include_router(theme_router)
    app.include_router(upgrade_requests_router)
    app.include_router(webpos_router)
    app.include_router(integrator_management_router)
    app.include_router(partner_graph_router)
    app.include_router(partner_v1_router)

    # --- v1 Aliases ---
    from app.bootstrap.v1_registry import register_v1_routers
    register_v1_routers(app)

    # --- Specialized Platform Layers ---
    from app.routers.production import router as production_router
    from app.routers.hardening import router as hardening_router
    from app.routers.worker_infrastructure import router as worker_infra_router
    from app.routers.supplier_activation import router as supplier_activation_router
    from app.routers.stress_test_router import router as stress_test_router
    from app.routers.pilot_launch_router import router as pilot_launch_router
    from app.routers.supplier_credentials_router import router as supplier_credentials_router
    from app.routers.supplier_aggregator_router import router as supplier_aggregator_router
    from app.routers.unified_booking_router import router as unified_booking_router
    from app.routers.intelligence_router import router as intelligence_router
    from app.routers.revenue_router import router as revenue_router
    from app.routers.scalability_router import router as scalability_router
    from app.routers.operations_router import router as operations_router
    from app.routers.market_launch_router import router as market_launch_router
    from app.routers.growth_engine_router import router as growth_engine_router
    from app.routers.pilot_onboarding_router import router as pilot_onboarding_router
    from app.routers.pricing_engine_router import router as pricing_engine_router
    from app.routers.gtm_demo_seed import router as gtm_demo_seed_router
    from app.routers.activation_checklist import router as activation_checklist_router
    app.include_router(production_router)
    app.include_router(hardening_router)
    app.include_router(worker_infra_router)
    app.include_router(supplier_activation_router)
    app.include_router(stress_test_router)
    app.include_router(pilot_launch_router)
    app.include_router(supplier_credentials_router)
    app.include_router(supplier_aggregator_router)
    app.include_router(unified_booking_router)
    app.include_router(intelligence_router)
    app.include_router(revenue_router)
    app.include_router(scalability_router)
    app.include_router(operations_router)
    app.include_router(market_launch_router)
    app.include_router(growth_engine_router)
    app.include_router(pilot_onboarding_router)
    app.include_router(pricing_engine_router)
    app.include_router(gtm_demo_seed_router)
    app.include_router(activation_checklist_router)

    # --- Inventory Domain (refactored package) ---
    from app.routers.inventory import (
        sync_router as inv_sync_router,
        booking_router as inv_booking_router,
        diagnostics_router as inv_diagnostics_router,
        e2e_demo_router as inv_e2e_demo_router,
        onboarding_router as inv_onboarding_router,
    )
    app.include_router(inv_sync_router)
    app.include_router(inv_booking_router)
    app.include_router(inv_diagnostics_router)
    app.include_router(inv_e2e_demo_router)
    app.include_router(inv_onboarding_router)

    # --- Finance Ledger & Settlement (Phase 2A + 2B) ---
    from app.routers.finance_ledger import (
        router as finance_ledger_router,
        settlement_router as finance_settlement_router,
        recon_router as finance_recon_router,
        exception_router as finance_exception_router,
    )
    app.include_router(finance_ledger_router)
    app.include_router(finance_settlement_router)
    app.include_router(finance_recon_router)
    app.include_router(finance_exception_router)

    # --- Activity Timeline & Config Versions ---
    from app.routers.activity_timeline_router import router as activity_timeline_router
    from app.routers.config_versions_router import router as config_versions_router
    app.include_router(activity_timeline_router)
    app.include_router(config_versions_router)

    # --- OMS: Order Management System ---
    from app.routers.order_router import router as order_router
    app.include_router(order_router)

    # --- Agency Settlements (from settlements router) ---
    from app.routers.settlements import (
        agency_router as agency_settlements_router,
        hotel_router as hotel_settlements_router,
        network_settlements_router,
    )
    from app.suppliers.router import router as supplier_ecosystem_router
    app.include_router(supplier_ecosystem_router)
    app.include_router(agency_settlements_router)
    app.include_router(hotel_settlements_router)
    app.include_router(network_settlements_router)

    # --- Admin Demo Seed ---
    from app.routers.admin_demo_seed import router as admin_demo_seed_router
    app.include_router(admin_demo_seed_router)
