"""System domain — health, infrastructure, monitoring, cache, admin system ops, platform layers.

Owner: System Domain
Boundary: All system infrastructure — health checks, monitoring, cache,
          distributed locks, metrics, maintenance, notifications, platform layers,
          demo seeding, activation checklists, integrations management.

Phase 2, Dalga 5 additions: platform layers, admin misc, activity/config, demo seed.
"""
from fastapi import APIRouter

# --- Core system ---
from app.routers.health import router as health_router
from app.routers.health_dashboard import router as health_dashboard_router
from app.routers.cache_health_router import router as cache_health_router
from app.routers.cache_management import router as cache_management_router
from app.routers.infrastructure import router as infrastructure_router
from app.routers.distributed_locks import router as distributed_locks_router
from app.routers.metrics import router as metrics_router
from app.routers.notifications import router as notifications_router
from app.routers.sms_notifications import router as sms_notifications_router
from app.routers.reliability import router as reliability_router

# --- Admin system ---
from app.routers.admin_system_backups import router as admin_system_backups_router
from app.routers.admin_system_integrity import router as admin_system_integrity_router
from app.routers.admin_system_metrics import router as admin_system_metrics_router
from app.routers.admin_system_errors import router as admin_system_errors_router
from app.routers.admin_system_uptime import router as admin_system_uptime_router
from app.routers.admin_system_incidents import router as admin_system_incidents_router
from app.routers.admin_maintenance import router as admin_maintenance_router
from app.routers.admin_system_preflight import router as admin_system_preflight_router
from app.routers.admin_system_runbook import router as admin_system_runbook_router
from app.routers.admin_system_perf import router as admin_system_perf_router
from app.routers.system_product_mode import router as system_product_mode_router
from app.routers.admin_product_mode import router as admin_product_mode_router

# --- Platform layers (Phase 2, Dalga 5) ---
from app.routers.production import router as production_router
from app.routers.hardening import router as hardening_router
from app.routers.worker_infrastructure import router as worker_infra_router
from app.routers.stress_test_router import router as stress_test_router
from app.routers.pilot_launch_router import router as pilot_launch_router
from app.routers.intelligence_router import router as intelligence_router
from app.routers.scalability_router import router as scalability_router
from app.routers.operations_router import router as operations_router
from app.routers.market_launch_router import router as market_launch_router
from app.routers.growth_engine_router import router as growth_engine_router
from app.routers.pilot_onboarding_router import router as pilot_onboarding_router
from app.routers.gtm_demo_seed import router as gtm_demo_seed_router
from app.routers.activation_checklist import router as activation_checklist_router

# --- Admin misc (Phase 2, Dalga 5) ---
from app.routers.admin import router as admin_router
from app.routers.admin_demo_guide import router as admin_demo_guide_router
from app.routers.admin_import import router as admin_import_router
from app.routers.admin_integrations import router as admin_integrations_router
from app.routers.admin_jobs import router as admin_jobs_router
from app.routers.admin_links import router as admin_links_router
from app.routers.admin_metrics import router as admin_metrics_router
from app.routers.admin_demo_seed import router as admin_demo_seed_router
from app.routers.dev_saas import router as dev_saas_router
from app.routers.demo_scale_ui_proof import router as demo_scale_ui_proof_router
from app.routers.integrator_management import router as integrator_management_router
from app.routers.theme import router as theme_router
from app.routers.upgrade_requests import router as upgrade_requests_router

# --- Activity/Config (Phase 2, Dalga 5) ---
from app.routers.activity_timeline_router import router as activity_timeline_router
from app.routers.config_versions_router import router as config_versions_router

# --- Extensions (Phase 2, Dalga 5) ---
from app.routers.admin_campaigns import router as admin_campaigns_router
from app.routers.admin_cms_pages import router as admin_cms_pages_router
from app.routers.admin_coupons import router as admin_coupons_router
from app.routers.webpos import router as webpos_router
from app.routers.ai_assistant import router as ai_assistant_router

domain_router = APIRouter()

# Core system
domain_router.include_router(health_router)
domain_router.include_router(health_dashboard_router)
domain_router.include_router(cache_health_router)
domain_router.include_router(cache_management_router)
domain_router.include_router(infrastructure_router)
domain_router.include_router(distributed_locks_router)
domain_router.include_router(metrics_router)
domain_router.include_router(notifications_router)
domain_router.include_router(sms_notifications_router)
domain_router.include_router(reliability_router)

# Admin system
domain_router.include_router(admin_system_backups_router)
domain_router.include_router(admin_system_integrity_router)
domain_router.include_router(admin_system_metrics_router)
domain_router.include_router(admin_system_errors_router)
domain_router.include_router(admin_system_uptime_router)
domain_router.include_router(admin_system_incidents_router)
domain_router.include_router(admin_maintenance_router)
domain_router.include_router(admin_system_preflight_router)
domain_router.include_router(admin_system_runbook_router)
domain_router.include_router(admin_system_perf_router)
domain_router.include_router(system_product_mode_router)
domain_router.include_router(admin_product_mode_router)

# Platform layers
domain_router.include_router(production_router)
domain_router.include_router(hardening_router)
domain_router.include_router(worker_infra_router)
domain_router.include_router(stress_test_router)
domain_router.include_router(pilot_launch_router)
domain_router.include_router(intelligence_router)
domain_router.include_router(scalability_router)
domain_router.include_router(operations_router)
domain_router.include_router(market_launch_router)
domain_router.include_router(growth_engine_router)
domain_router.include_router(pilot_onboarding_router)
domain_router.include_router(gtm_demo_seed_router)
domain_router.include_router(activation_checklist_router)

# Admin misc
domain_router.include_router(admin_router)
domain_router.include_router(admin_demo_guide_router)
domain_router.include_router(admin_import_router)
domain_router.include_router(admin_integrations_router)
domain_router.include_router(admin_jobs_router)
domain_router.include_router(admin_links_router)
domain_router.include_router(admin_metrics_router)
domain_router.include_router(admin_demo_seed_router)
domain_router.include_router(dev_saas_router)
domain_router.include_router(demo_scale_ui_proof_router)
domain_router.include_router(integrator_management_router)
domain_router.include_router(theme_router)
domain_router.include_router(upgrade_requests_router)

# Activity/Config
domain_router.include_router(activity_timeline_router)
domain_router.include_router(config_versions_router)

# Extensions
domain_router.include_router(admin_campaigns_router)
domain_router.include_router(admin_cms_pages_router)
domain_router.include_router(admin_coupons_router)
domain_router.include_router(webpos_router)
domain_router.include_router(ai_assistant_router)
