from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import API_PREFIX, APP_NAME, APP_VERSION, CORS_ORIGINS
from app.db import close_mongo, connect_mongo, get_db
from app.errors import AppError
from app.exception_handlers import register_exception_handlers
from app.middleware.correlation_id import CorrelationIdMiddleware
from app.routers.admin import router as admin_router
from app.routers.admin_accounting import router as admin_accounting_router
from app.routers.admin_catalog import router as admin_catalog_router
from app.routers.admin_metrics import router as admin_metrics_router
from app.routers.admin_pricing import router as admin_pricing_router
from app.routers.admin_pricing_trace import router as admin_pricing_trace_router
from app.routers.admin_coupons import router as admin_coupons_router
from app.routers.admin_hotels import router as admin_hotels_router
from app.routers.auth import router as auth_router
from app.routers.auth_password_reset import router as auth_password_reset_router
from app.routers.b2b import router as b2b_router
from app.routers.b2b_bookings import router as b2b_bookings_router
from app.routers.b2b_bookings_list import router as b2b_bookings_list_router
from app.routers.b2b_hotels_search import router as b2b_hotels_search_router
from app.routers.b2b_quotes import router as b2b_quotes_router
from app.routers.b2b_portal import router as b2b_portal_router
from app.routers.b2b_announcements import router as b2b_announcements_router
from app.routers.finance import router as finance_router
from app.routers.bookings import router as bookings_router
from app.routers.booking_outcomes import router as booking_outcomes_router
from app.routers.inbox import router as inbox_router
from app.routers.reports import router as reports_router
from app.routers.inbox_v2 import router as inbox_v2_router
from app.routers.crm_customer_inbox import router as crm_customer_inbox_router
from app.routers.matches import router as matches_router
from app.routers.ops_b2b import router as ops_b2b_router
from app.routers.ops_booking_events import router as ops_booking_events_router
from app.routers.ops_cases import router as ops_cases_router
from app.routers.ops_click_to_pay import router as ops_click_to_pay_router
from app.routers.ops_finance import router as ops_finance_router
from app.routers.ops_tasks import router as ops_tasks_router
from app.routers.ops_incidents import router as ops_incidents_router
from app.routers.admin_supplier_health import router as admin_supplier_health_router
from app.routers.payments import router as payments_router
from app.routers.payments_stripe import router as payments_stripe_router
from app.routers.products import router as products_router
from app.routers.public_click_to_pay import router as public_click_to_pay_router
from app.routers.offers import router as offers_router
from app.routers.offers_booking import router as offers_booking_router
from app.routers.public_my_booking import router as public_my_booking_router
from app.routers.public_search import router as public_search_router
from app.routers.public_checkout import router as public_checkout_router
from app.routers.public_bookings import router as public_bookings_router
from app.routers.search import router as search_router
from app.routers.suppliers import router as suppliers_router, router_paximum as suppliers_paximum_router
from app.routers.vouchers import router as vouchers_router
from app.routers.inventory_shares import router as inventory_shares_router
from app.routers.settlements import network_settlements_router
from app.routers.commission_rules import router as commission_rules_router



from app.routers.partner_graph import router as partner_graph_router

from app.routers.b2b_network_bookings import router as b2b_network_bookings_router

from app.routers.web_booking import router as web_booking_router
from app.routers.web_catalog import router as web_catalog_router
from app.routers.crm_customers import router as crm_customers_router
from app.routers.crm_deals import router as crm_deals_router
from app.routers.crm_tasks import router as crm_tasks_router
from app.routers.crm_activities import router as crm_activities_router
from app.routers.crm_events import router as crm_events_router
from app.routers.reservations import router as reservations_router
from app.routers.pricing_quote import router as pricing_quote_router
from app.routers.pricing import router as pricing_router
from app.routers.pricing_rules import router as pricing_rules_router
from app.routers.marketplace import router as marketplace_router
from app.routers.marketplace_supplier_mapping import router as marketplace_supplier_mapping_router
from app.routers.b2b_marketplace_booking import router as b2b_marketplace_booking_router
from app.routers.admin_funnel import router as admin_funnel_router

from app.routers.theme import router as theme_router
from app.routers.admin_reporting import router as admin_reporting_router
from app.routers.admin_ical import router as admin_ical_router
from app.routers.admin_pricing_incidents import router as admin_pricing_incidents_router
from app.routers.admin_partners import router as admin_partners_router
from app.routers.admin_b2b_discounts import router as admin_b2b_discounts_router
from app.routers.admin_b2b_visibility import router as admin_b2b_visibility_router
from app.routers.admin_b2b_marketplace import router as admin_b2b_marketplace_router
from app.routers.admin_b2b_pricing import router as admin_b2b_pricing_router
from app.routers.admin_integrations import router as admin_integrations_router
from app.routers.admin_jobs import router as admin_jobs_router
from app.routers.admin_api_keys import router as admin_api_keys_router
from app.routers.metrics import router as metrics_router
from app.routers.partner_v1 import router as partner_v1_router
from app.routers.admin_agencies import router as admin_agencies_router
from app.routers.admin_agency_users import router as admin_agency_users_router
from app.routers.admin_statements import router as admin_statements_router
from app.routers.admin_whitelabel import router as admin_whitelabel_router
from app.routers.admin_settlements import router as admin_settlements_router
from app.routers.admin_parasut import router as admin_parasut_router
from app.routers.admin_b2b_agencies import router as admin_b2b_agencies_router
from app.routers.admin_b2b_funnel import router as admin_b2b_funnel_router
from app.routers.admin_b2b_announcements import router as admin_b2b_announcements_router
from app.routers.admin_tours import router as admin_tours_router
from app.routers.admin_cms_pages import router as admin_cms_pages_router
from app.routers.admin_campaigns import router as admin_campaigns_router
from app.routers.admin_links import router as admin_links_router
from app.routers.settings import router as settings_router
from app.routers.approval_tasks import router as approval_tasks_router
from app.routers.demo_scale_ui_proof import router as demo_scale_ui_proof_router
from app.routers.risk_snapshots import router as risk_snapshots_router
from app.routers.exports import router as exports_router, public_router as public_exports_router
from app.routers.action_policies import router as action_policies_router
from app.routers.saas_tenants import router as saas_tenants_router
from app.routers.tenant_features import router as tenant_features_router
from app.routers.admin_tenant_features import router as admin_tenant_features_router
from app.routers.admin_audit_logs import router as admin_audit_logs_router
from app.routers.admin_billing import router as admin_billing_router
from app.routers.admin_analytics import router as admin_analytics_router
from app.routers.billing_webhooks import router as billing_webhooks_router
from app.routers.b2b_events import router as b2b_events_router
from app.routers.dev_saas import router as dev_saas_router
from app.routers.admin_reports import router as admin_reports_router
from app.routers.match_alerts import router as match_alerts_router

# GTM + CRM deepening routers
from app.routers.gtm_demo_seed import router as gtm_demo_seed_router
from app.routers.activation_checklist import router as activation_checklist_router
from app.routers.upgrade_requests import router as upgrade_requests_router
from app.routers.tenant_health import router as tenant_health_router
from app.routers.crm_notes import router as crm_notes_router
from app.routers.crm_timeline import router as crm_timeline_router

from app.routers.seo import router as seo_router
from app.routers.public_campaigns import router as public_campaigns_router
from app.routers.public_tours import router as public_tours_router
from app.routers.public_cms_pages import router as public_cms_pages_router
from app.routers.public_partners import router as public_partners_router

# Enterprise Hardening (E1-E4) routers
from app.routers.enterprise_rbac import router as enterprise_rbac_router
from app.routers.enterprise_approvals import router as enterprise_approvals_router
from app.routers.enterprise_2fa import router as enterprise_2fa_router
from app.routers.enterprise_health import router as enterprise_health_router
from app.routers.enterprise_audit import router as enterprise_audit_router
from app.routers.enterprise_export import router as enterprise_export_router
from app.routers.enterprise_schedules import router as enterprise_schedules_router
from app.routers.enterprise_ip_whitelist import router as enterprise_ip_whitelist_router
from app.routers.enterprise_whitelabel import router as enterprise_whitelabel_router

from app.email_worker import email_dispatch_loop
from app.indexes import finance_indexes, inbox_indexes, pricing_indexes, public_indexes, voucher_indexes
from app.indexes import crm_indexes
from app.indexes import funnel_indexes
from app.indexes.jobs_indexes import ensure_jobs_indexes
from app.indexes.integration_hub_indexes import ensure_integration_hub_indexes
from app.indexes.api_keys_indexes import ensure_api_keys_indexes
from app.indexes.rate_limit_indexes import ensure_rate_limit_indexes
from app.indexes.tenant_indexes import ensure_tenant_indexes
from app.indexes.storefront_indexes import ensure_storefront_indexes
from app.indexes.pricing_indexes import ensure_pricing_indexes
from app.indexes.marketplace_indexes import ensure_marketplace_indexes
from app.integration_sync_worker import integration_sync_loop
from app.services.jobs import run_job_worker_loop


@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_mongo()
    db = await get_db()

    # Ensure indexes at startup for critical collections
    await finance_indexes.ensure_finance_indexes(db)
    await inbox_indexes.ensure_inbox_indexes(db)
    await pricing_indexes.ensure_pricing_indexes(db)
    await voucher_indexes.ensure_voucher_indexes(db)
    await public_indexes.ensure_public_indexes(db)
    await crm_indexes.ensure_crm_indexes(db)
    await funnel_indexes.ensure_funnel_indexes(db)
    await ensure_jobs_indexes(db)
    await ensure_integration_hub_indexes(db)
    await ensure_api_keys_indexes(db)
    await ensure_rate_limit_indexes(db)
    await ensure_tenant_indexes(db)
    await ensure_storefront_indexes(db)
    await ensure_pricing_indexes(db)
    await ensure_marketplace_indexes(db)
    from app.indexes.marketplace_indexes import ensure_offers_indexes
    await ensure_offers_indexes(db)
    # Supplier adapters are lazily initialized in AdapterRegistry._ensure_defaults_loaded()

    # GTM + CRM indexes
    try:
        await db.demo_seed_runs.create_index("tenant_id", unique=True)
        await db.rule_runs.create_index([("tenant_id", 1), ("rule_key", 1), ("date", 1)], unique=True)
        await db.crm_deals.create_index([("organization_id", 1), ("stage", 1)])
        await db.crm_deals.create_index([("organization_id", 1), ("owner_user_id", 1)])
        await db.crm_tasks.create_index([("organization_id", 1), ("owner_user_id", 1), ("status", 1)])
        await db.crm_tasks.create_index([("organization_id", 1), ("due_date", 1)])
        await db.crm_notes.create_index([("organization_id", 1), ("entity_type", 1), ("entity_id", 1)])
        await db.activation_checklist.create_index("tenant_id", unique=True)
        await db.upgrade_requests.create_index([("tenant_id", 1), ("status", 1)])
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning("GTM/CRM index creation warning: %s", e)

    # Start billing cron scheduler
    from app.billing.scheduler import start_scheduler, stop_scheduler
    start_scheduler()

    yield

    stop_scheduler()
    await close_mongo()


from app.middleware.tenant_middleware import TenantResolutionMiddleware

app = FastAPI(
    title=APP_NAME,
    version=APP_VERSION,
    lifespan=lifespan,
    openapi_url=f"{API_PREFIX}/openapi.json",
)

# Enterprise Hardening middleware (E3.1 + E3.3 + E2.2)
from app.middleware.structured_logging_middleware import StructuredLoggingMiddleware
from app.middleware.rate_limit_middleware import RateLimitMiddleware
from app.middleware.ip_whitelist_middleware import IPWhitelistMiddleware

# Correlation-Id middleware (request/response scoped) - should be early in the chain
app.add_middleware(CorrelationIdMiddleware)

# Structured logging (E3.1)
app.add_middleware(StructuredLoggingMiddleware)

# Rate limiting (E3.3)
app.add_middleware(RateLimitMiddleware)

# IP Whitelist (E2.2)
app.add_middleware(IPWhitelistMiddleware)

# Tenant resolution middleware (header/host/subdomain based)
app.add_middleware(TenantResolutionMiddleware)

from app.routers.storefront import router as storefront_router

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Structured exception handlers (AppError, validation, 404, 500, ...)
register_exception_handlers(app)

# Include routers
app.include_router(auth_router)
app.include_router(auth_password_reset_router)
app.include_router(admin_router)
app.include_router(admin_accounting_router)  # router already has /api prefix
app.include_router(admin_funnel_router)

app.include_router(admin_catalog_router)
app.include_router(admin_metrics_router)
app.include_router(admin_pricing_router)
app.include_router(admin_pricing_trace_router)
app.include_router(admin_coupons_router)  # router already has /api prefix
app.include_router(admin_hotels_router)
app.include_router(admin_reporting_router)
app.include_router(admin_ical_router)
app.include_router(admin_pricing_incidents_router)
app.include_router(admin_partners_router)
app.include_router(admin_b2b_discounts_router)
app.include_router(admin_b2b_visibility_router)
app.include_router(admin_b2b_marketplace_router)
app.include_router(admin_b2b_pricing_router)
app.include_router(admin_integrations_router)
app.include_router(admin_jobs_router)
app.include_router(admin_api_keys_router)
app.include_router(metrics_router)
app.include_router(partner_v1_router)
app.include_router(admin_agencies_router)
app.include_router(admin_agency_users_router)
app.include_router(admin_statements_router)
app.include_router(admin_whitelabel_router)
app.include_router(admin_settlements_router)
app.include_router(admin_parasut_router)
app.include_router(admin_b2b_agencies_router)
app.include_router(admin_b2b_funnel_router)
app.include_router(admin_b2b_announcements_router)
app.include_router(admin_tours_router)
app.include_router(admin_cms_pages_router)
app.include_router(admin_campaigns_router)
app.include_router(admin_links_router)
app.include_router(settings_router)
app.include_router(approval_tasks_router)
app.include_router(demo_scale_ui_proof_router)
app.include_router(risk_snapshots_router)
app.include_router(exports_router)
app.include_router(public_exports_router)
app.include_router(action_policies_router)
app.include_router(saas_tenants_router)
app.include_router(tenant_features_router)
app.include_router(admin_tenant_features_router)
app.include_router(admin_audit_logs_router)
app.include_router(admin_billing_router)
app.include_router(admin_analytics_router)
app.include_router(billing_webhooks_router)
app.include_router(b2b_events_router)
app.include_router(dev_saas_router)

app.include_router(theme_router)

app.include_router(b2b_router)
app.include_router(b2b_bookings_router)
app.include_router(b2b_bookings_list_router)
app.include_router(b2b_hotels_search_router)
from app.routers.b2b_exchange import router as b2b_exchange_router

app.include_router(b2b_quotes_router)
from app.routers.health import router as health_router

app.include_router(b2b_portal_router)
app.include_router(b2b_announcements_router)
app.include_router(finance_router, prefix=API_PREFIX)
app.include_router(bookings_router, prefix=API_PREFIX)
app.include_router(booking_outcomes_router, prefix=API_PREFIX)
app.include_router(inbox_router, prefix=API_PREFIX)
app.include_router(reports_router)
app.include_router(inbox_v2_router)
app.include_router(crm_customer_inbox_router)
app.include_router(matches_router)
app.include_router(match_alerts_router)
app.include_router(admin_reports_router)
app.include_router(ops_b2b_router)  # No prefix - router has its own
app.include_router(ops_booking_events_router, prefix=API_PREFIX)
app.include_router(ops_cases_router)  # No prefix - router has its own
app.include_router(ops_click_to_pay_router)  # No prefix - router has its own
app.include_router(ops_finance_router)
app.include_router(ops_tasks_router)  # No prefix - router has its own
app.include_router(ops_incidents_router)  # Unified Ops Incident Console
app.include_router(admin_supplier_health_router)  # Supplier health snapshot
app.include_router(payments_router, prefix=API_PREFIX)
app.include_router(payments_stripe_router, prefix=API_PREFIX)
app.include_router(products_router, prefix=API_PREFIX)
app.include_router(public_click_to_pay_router)  # No prefix - router has its own
app.include_router(offers_router)
app.include_router(offers_booking_router)
app.include_router(public_my_booking_router)    # No prefix - router has its own
app.include_router(public_search_router)        # No prefix - router has its own
app.include_router(public_checkout_router)      # No prefix - router has its own
app.include_router(public_bookings_router)      # No prefix - router has its own
app.include_router(commission_rules_router)

app.include_router(public_tours_router)         # No prefix - router has its own
app.include_router(network_settlements_router)

app.include_router(public_cms_pages_router)     # No prefix - router has its own
app.include_router(public_partners_router)      # No prefix - router has its own
app.include_router(partner_graph_router)
app.include_router(inventory_shares_router)


app.include_router(search_router, prefix=API_PREFIX)
app.include_router(suppliers_router, prefix=API_PREFIX)
app.include_router(storefront_router)

app.include_router(suppliers_paximum_router, prefix=API_PREFIX)
app.include_router(vouchers_router, prefix=API_PREFIX)
app.include_router(web_booking_router, prefix=API_PREFIX)
app.include_router(web_catalog_router, prefix=API_PREFIX)
app.include_router(crm_customers_router)
app.include_router(crm_deals_router)
app.include_router(crm_tasks_router)
app.include_router(crm_activities_router)
app.include_router(pricing_quote_router)
app.include_router(pricing_router, prefix=API_PREFIX)
app.include_router(pricing_rules_router, prefix=API_PREFIX)
app.include_router(marketplace_router, prefix=API_PREFIX)
app.include_router(marketplace_supplier_mapping_router, prefix=API_PREFIX)
app.include_router(b2b_marketplace_booking_router, prefix=API_PREFIX)
app.include_router(b2b_network_bookings_router)
app.include_router(health_router)
app.include_router(b2b_exchange_router)

app.include_router(crm_events_router)
app.include_router(reservations_router, prefix=API_PREFIX)
app.include_router(seo_router)
app.include_router(public_campaigns_router)

app.include_router(auth_router)

# Phase 5-8: Onboarding, WebPOS, Notifications, Advanced Reports
from app.routers.onboarding import router as onboarding_router
from app.routers.webpos import router as webpos_router
from app.routers.notifications import router as notifications_router
from app.routers.advanced_reports import router as advanced_reports_router

app.include_router(onboarding_router)
app.include_router(webpos_router)
app.include_router(notifications_router)
app.include_router(advanced_reports_router)

# GTM + CRM deepening
app.include_router(gtm_demo_seed_router)
app.include_router(activation_checklist_router)
app.include_router(upgrade_requests_router)
app.include_router(tenant_health_router)
app.include_router(crm_notes_router)
app.include_router(crm_timeline_router)


@app.get("/")
async def read_root() -> dict[str, str]:
    return {"message": f"{APP_NAME} is running", "version": APP_VERSION}


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}


if os.environ.get("ENABLE_EMAIL_WORKER") == "1":
    email_dispatch_loop()

if os.environ.get("ENABLE_INTEGRATION_SYNC_WORKER") == "1":
    integration_sync_loop()

if os.environ.get("ENABLE_JOB_WORKER") == "1":
    import asyncio

    asyncio.create_task(run_job_worker_loop("job-worker-1"))
