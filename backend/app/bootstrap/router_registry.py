from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.bootstrap.v1_registry import register_v1_routers
from app.config import API_PREFIX
from app.exception_handlers import register_exception_handlers
from app.routers.action_policies import router as action_policies_router
from app.routers.activation_checklist import router as activation_checklist_router
from app.routers.admin import router as admin_router
from app.routers.admin_accounting import router as admin_accounting_router
from app.routers.admin_agencies import router as admin_agencies_router
from app.routers.admin_agency_users import all_users_router as admin_all_users_router
from app.routers.admin_agency_users import router as admin_agency_users_router
from app.routers.admin_analytics import router as admin_analytics_router
from app.routers.admin_api_keys import router as admin_api_keys_router
from app.routers.admin_audit_logs import router as admin_audit_logs_router
from app.routers.admin_b2b_agencies import router as admin_b2b_agencies_router
from app.routers.admin_b2b_announcements import router as admin_b2b_announcements_router
from app.routers.admin_b2b_discounts import router as admin_b2b_discounts_router
from app.routers.admin_b2b_funnel import router as admin_b2b_funnel_router
from app.routers.admin_b2b_marketplace import router as admin_b2b_marketplace_router
from app.routers.admin_b2b_pricing import router as admin_b2b_pricing_router
from app.routers.admin_b2b_visibility import router as admin_b2b_visibility_router
from app.routers.admin_billing import router as admin_billing_router
from app.routers.admin_campaigns import router as admin_campaigns_router
from app.routers.admin_catalog import router as admin_catalog_router
from app.routers.admin_cms_pages import router as admin_cms_pages_router
from app.routers.admin_coupons import router as admin_coupons_router
from app.routers.admin_demo_guide import router as admin_demo_guide_router
from app.routers.admin_funnel import router as admin_funnel_router
from app.routers.admin_hotels import router as admin_hotels_router
from app.routers.admin_ical import router as admin_ical_router
from app.routers.admin_import import router as admin_import_router
from app.routers.admin_integrations import router as admin_integrations_router
from app.routers.admin_jobs import router as admin_jobs_router
from app.routers.admin_links import router as admin_links_router
from app.routers.admin_metrics import router as admin_metrics_router
from app.routers.admin_maintenance import router as admin_maintenance_router
from app.routers.admin_parasut import router as admin_parasut_router
from app.routers.admin_partners import router as admin_partners_router
from app.routers.admin_product_mode import router as admin_product_mode_router
from app.routers.admin_pricing import router as admin_pricing_router
from app.routers.admin_pricing_incidents import router as admin_pricing_incidents_router
from app.routers.admin_pricing_trace import router as admin_pricing_trace_router
from app.routers.admin_reporting import router as admin_reporting_router
from app.routers.admin_reports import router as admin_reports_router
from app.routers.admin_settlements import router as admin_settlements_router
from app.routers.admin_sheets import router as admin_sheets_router
from app.routers.admin_statements import router as admin_statements_router
from app.routers.admin_supplier_health import router as admin_supplier_health_router
from app.routers.admin_system_backups import router as admin_system_backups_router
from app.routers.admin_system_errors import router as admin_system_errors_router
from app.routers.admin_system_incidents import router as admin_system_incidents_router
from app.routers.admin_system_integrity import router as admin_system_integrity_router
from app.routers.admin_system_metrics import router as admin_system_metrics_router
from app.routers.admin_system_perf import router as admin_system_perf_router
from app.routers.admin_system_preflight import router as admin_system_preflight_router
from app.routers.admin_system_runbook import router as admin_system_runbook_router
from app.routers.admin_system_uptime import router as admin_system_uptime_router
from app.routers.admin_tenant_features import router as admin_tenant_features_router
from app.routers.admin_tours import router as admin_tours_router
from app.routers.admin_whitelabel import router as admin_whitelabel_router
from app.routers.agency_availability import router as agency_availability_router
from app.routers.agency_profile import router as agency_profile_router
from app.routers.agency_sheets import router as agency_sheets_router
from app.routers.agency_writeback import router as agency_writeback_router
from app.routers.agency_contracts import router as agency_contracts_router
from app.routers.ai_assistant import router as ai_assistant_router
from app.routers.approval_tasks import router as approval_tasks_router
from app.routers.audit import router as audit_router
from app.routers.auth import router as auth_router
from app.routers.auth_password_reset import router as auth_password_reset_router
from app.routers.advanced_reports import router as advanced_reports_router
from app.routers.b2b import router as b2b_router
from app.routers.b2b_announcements import router as b2b_announcements_router
from app.routers.b2b_bookings import router as b2b_bookings_router
from app.routers.b2b_bookings_list import router as b2b_bookings_list_router
from app.routers.b2b_events import router as b2b_events_router
from app.routers.b2b_exchange import router as b2b_exchange_router
from app.routers.b2b_hotels_search import router as b2b_hotels_search_router
from app.routers.b2b_marketplace_booking import router as b2b_marketplace_booking_router
from app.routers.b2b_network_bookings import router as b2b_network_bookings_router
from app.routers.b2b_portal import router as b2b_portal_router
from app.routers.b2b_quotes import router as b2b_quotes_router
from app.routers.billing_webhooks import router as billing_webhooks_router
from app.routers.billing_checkout import router as billing_checkout_router
from app.routers.billing_lifecycle import router as billing_lifecycle_router
from app.routers.booking_outcomes import router as booking_outcomes_router
from app.routers.bookings import router as bookings_router
from app.routers.cache_management import router as cache_management_router
from app.routers.cancel_reasons import router as cancel_reasons_router
from app.routers.commission_rules import router as commission_rules_router
from app.routers.crm_activities import router as crm_activities_router
from app.routers.crm_customer_inbox import router as crm_customer_inbox_router
from app.routers.crm_customers import router as crm_customers_router
from app.routers.crm_deals import router as crm_deals_router
from app.routers.crm_events import router as crm_events_router
from app.routers.crm_notes import router as crm_notes_router
from app.routers.crm_tasks import router as crm_tasks_router
from app.routers.crm_timeline import router as crm_timeline_router
from app.routers.dashboard_enhanced import router as dashboard_enhanced_router
from app.routers.demo_scale_ui_proof import router as demo_scale_ui_proof_router
from app.routers.dev_saas import router as dev_saas_router
from app.routers.distributed_locks import router as distributed_locks_router
from app.routers.efatura import router as efatura_router
from app.routers.enterprise_2fa import router as enterprise_2fa_router
from app.routers.enterprise_approvals import router as enterprise_approvals_router
from app.routers.enterprise_audit import router as enterprise_audit_router
from app.routers.enterprise_export import router as enterprise_export_router
from app.routers.enterprise_health import router as enterprise_health_router
from app.routers.enterprise_ip_whitelist import router as enterprise_ip_whitelist_router
from app.routers.enterprise_rbac import router as enterprise_rbac_router
from app.routers.enterprise_schedules import router as enterprise_schedules_router
from app.routers.enterprise_whitelabel import router as enterprise_whitelabel_router
from app.routers.exports import public_router as public_exports_router
from app.routers.exports import router as exports_router
from app.routers.finance import router as finance_router
from app.routers.gdpr import router as gdpr_router
from app.routers.gtm_demo_seed import router as gtm_demo_seed_router
from app.routers.health import router as health_router
from app.routers.health_dashboard import router as health_dashboard_router
from app.routers.inbox_v2 import router as inbox_v2_router
from app.routers.inventory_shares import router as inventory_shares_router
from app.routers.inventory_snapshots_api import router as inventory_snapshots_api_router
from app.routers.marketplace import router as marketplace_router
from app.routers.marketplace_supplier_mapping import router as marketplace_supplier_mapping_router
from app.routers.match_alerts import router as match_alerts_router
from app.routers.matches import router as matches_router
from app.routers.metrics import router as metrics_router
from app.routers.multicurrency import router as multicurrency_router
from app.routers.notifications import router as notifications_router
from app.routers.offers import router as offers_router
from app.routers.offers_booking import router as offers_booking_router
from app.routers.onboarding import router as onboarding_router
from app.routers.ops_b2b import router as ops_b2b_router
from app.routers.ops_booking_events import router as ops_booking_events_router
from app.routers.ops_cases import router as ops_cases_router
from app.routers.ops_click_to_pay import router as ops_click_to_pay_router
from app.routers.ops_finance import router as ops_finance_router
from app.routers.ops_incidents import router as ops_incidents_router
from app.routers.ops_tasks import router as ops_tasks_router
from app.routers.partner_graph import router as partner_graph_router
from app.routers.partner_v1 import router as partner_v1_router
from app.routers.payments import router as payments_router
from app.routers.payments_stripe import router as payments_stripe_router
from app.routers.pricing import router as pricing_router
from app.routers.pricing_quote import router as pricing_quote_router
from app.routers.pricing_rules import router as pricing_rules_router
from app.routers.products import router as products_router
from app.routers.public_bookings import router as public_bookings_router
from app.routers.public_campaigns import router as public_campaigns_router
from app.routers.public_checkout import router as public_checkout_router
from app.routers.public_cms_pages import router as public_cms_pages_router
from app.routers.public_click_to_pay import router as public_click_to_pay_router
from app.routers.public_my_booking import router as public_my_booking_router
from app.routers.public_partners import router as public_partners_router
from app.routers.public_search import router as public_search_router
from app.routers.public_tours import router as public_tours_router
from app.routers.reports import router as reports_router
from app.routers.reservations import router as reservations_router
from app.routers.risk_snapshots import router as risk_snapshots_router
from app.routers.saas_tenants import router as saas_tenants_router
from app.routers.search import router as search_router
from app.routers.seo import router as seo_router
from app.routers.settlements import network_settlements_router
from app.routers.settings import router as settings_router
from app.routers.sms_notifications import router as sms_notifications_router
from app.routers.storefront import router as storefront_router
from app.routers.suppliers import router as suppliers_router
from app.routers.suppliers import router_paximum as suppliers_paximum_router
from app.routers.system_product_mode import router as system_product_mode_router
from app.routers.tenant_features import router as tenant_features_router
from app.routers.tenant_health import router as tenant_health_router
from app.routers.theme import router as theme_router
from app.routers.tickets import router as tickets_router
from app.routers.tours_browse import router as tours_browse_router
from app.routers.upgrade_requests import router as upgrade_requests_router
from app.routers.vouchers import router as vouchers_router
from app.routers.web_booking import router as web_booking_router
from app.routers.web_catalog import router as web_catalog_router
from app.routers.webpos import router as webpos_router


def register_routers(app: FastAPI) -> None:
    register_exception_handlers(app)

    uploads_dir = Path(__file__).resolve().parents[1] / "uploads" / "tours"
    uploads_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/api/uploads/tours", StaticFiles(directory=str(uploads_dir)), name="tour_uploads")

    app.include_router(auth_router)
    app.include_router(auth_password_reset_router)
    app.include_router(admin_router)
    app.include_router(admin_accounting_router)
    app.include_router(admin_funnel_router)
    app.include_router(admin_catalog_router)
    app.include_router(admin_metrics_router)
    app.include_router(admin_pricing_router)
    app.include_router(admin_pricing_trace_router)
    app.include_router(admin_coupons_router)
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
    app.include_router(admin_all_users_router)
    app.include_router(admin_statements_router)
    app.include_router(admin_whitelabel_router)
    app.include_router(admin_settlements_router)
    app.include_router(admin_parasut_router)
    app.include_router(admin_b2b_agencies_router)
    app.include_router(admin_b2b_funnel_router)
    app.include_router(admin_b2b_announcements_router)
    app.include_router(admin_tours_router)
    app.include_router(tours_browse_router)
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
    app.include_router(b2b_quotes_router)
    app.include_router(b2b_portal_router)
    app.include_router(b2b_announcements_router)
    app.include_router(finance_router, prefix=API_PREFIX)
    app.include_router(bookings_router, prefix=API_PREFIX)
    app.include_router(booking_outcomes_router, prefix=API_PREFIX)
    app.include_router(reports_router)
    app.include_router(inbox_v2_router)
    app.include_router(crm_customer_inbox_router)
    app.include_router(matches_router)
    app.include_router(match_alerts_router)
    app.include_router(admin_reports_router)
    app.include_router(ops_b2b_router)
    app.include_router(ops_booking_events_router, prefix=API_PREFIX)
    app.include_router(ops_cases_router)
    app.include_router(ops_click_to_pay_router)
    app.include_router(ops_finance_router)
    app.include_router(ops_tasks_router)
    app.include_router(ops_incidents_router)
    app.include_router(admin_supplier_health_router)
    app.include_router(payments_router, prefix=API_PREFIX)
    app.include_router(payments_stripe_router, prefix=API_PREFIX)
    app.include_router(products_router, prefix=API_PREFIX)
    app.include_router(public_click_to_pay_router)
    app.include_router(offers_router)
    app.include_router(offers_booking_router)
    app.include_router(public_my_booking_router)
    app.include_router(public_search_router)
    app.include_router(public_checkout_router)
    app.include_router(public_bookings_router)
    app.include_router(commission_rules_router)
    app.include_router(public_tours_router)
    app.include_router(network_settlements_router)
    app.include_router(public_cms_pages_router)
    app.include_router(public_partners_router)
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
    register_v1_routers(app)
    app.include_router(onboarding_router)
    app.include_router(billing_checkout_router)
    app.include_router(billing_lifecycle_router)
    app.include_router(webpos_router)
    app.include_router(notifications_router)
    app.include_router(advanced_reports_router)
    app.include_router(gtm_demo_seed_router)
    app.include_router(activation_checklist_router)
    app.include_router(upgrade_requests_router)
    app.include_router(tenant_health_router)
    app.include_router(crm_notes_router)
    app.include_router(crm_timeline_router)
    app.include_router(enterprise_rbac_router)
    app.include_router(enterprise_approvals_router)
    app.include_router(enterprise_2fa_router)
    app.include_router(enterprise_health_router)
    app.include_router(enterprise_audit_router)
    app.include_router(audit_router)
    app.include_router(enterprise_export_router)
    app.include_router(enterprise_schedules_router)
    app.include_router(enterprise_ip_whitelist_router)
    app.include_router(enterprise_whitelabel_router)
    app.include_router(efatura_router)
    app.include_router(sms_notifications_router)
    app.include_router(tickets_router)
    app.include_router(admin_system_backups_router)
    app.include_router(admin_system_integrity_router)
    app.include_router(admin_system_metrics_router)
    app.include_router(admin_system_errors_router)
    app.include_router(admin_system_uptime_router)
    app.include_router(admin_system_incidents_router)
    app.include_router(admin_maintenance_router)
    app.include_router(system_product_mode_router)
    app.include_router(admin_product_mode_router)
    app.include_router(admin_import_router)
    app.include_router(admin_sheets_router)
    app.include_router(agency_availability_router)
    app.include_router(agency_writeback_router)
    app.include_router(agency_sheets_router)
    app.include_router(agency_profile_router)
    app.include_router(admin_system_preflight_router)
    app.include_router(admin_system_runbook_router)
    app.include_router(admin_system_perf_router)
    app.include_router(admin_demo_guide_router)
    app.include_router(ai_assistant_router)
    app.include_router(dashboard_enhanced_router)
    app.include_router(gdpr_router)
    app.include_router(agency_contracts_router)
    app.include_router(multicurrency_router)
    app.include_router(cancel_reasons_router)
    app.include_router(cache_management_router)
    app.include_router(inventory_snapshots_api_router)
    app.include_router(distributed_locks_router)
    app.include_router(health_dashboard_router)
