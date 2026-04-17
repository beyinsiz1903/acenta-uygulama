"""Identity domain — users, agencies, RBAC, API keys, whitelabel, GDPR."""
from fastapi import APIRouter

from app.modules.identity.routers.admin_agencies import router as admin_agencies_router
from app.modules.identity.routers.admin_syroce_agencies import router as admin_syroce_agencies_router
from app.modules.identity.routers.admin_agency_users import router as admin_agency_users_router
from app.modules.identity.routers.admin_agency_users import all_users_router as admin_all_users_router
from app.modules.identity.routers.admin_api_keys import router as admin_api_keys_router
from app.modules.identity.routers.admin_audit_logs import router as admin_audit_logs_router
from app.modules.identity.routers.admin_whitelabel import router as admin_whitelabel_router
from app.modules.identity.routers.enterprise_rbac import router as enterprise_rbac_router
from app.modules.identity.routers.enterprise_ip_whitelist import router as enterprise_ip_whitelist_router
from app.modules.identity.routers.enterprise_whitelabel import router as enterprise_whitelabel_router
from app.modules.identity.routers.enterprise_export import router as enterprise_export_router
from app.modules.identity.routers.gdpr import router as gdpr_router
from app.modules.identity.routers.saas_tenants import router as saas_tenants_router
from app.modules.identity.routers.tenant_features import router as tenant_features_router
from app.modules.identity.routers.admin_tenant_features import router as admin_tenant_features_router
from app.modules.identity.routers.tenant_health import router as tenant_health_router
from app.modules.identity.routers.settings import router as settings_router
from app.modules.identity.routers.agency_profile import router as agency_profile_router
from app.modules.identity.routers.agency_contracts import router as agency_contracts_router
from app.modules.identity.routers.onboarding import router as onboarding_router
from app.modules.identity.routers.org_modules import router as org_modules_router

domain_router = APIRouter()
domain_router.include_router(org_modules_router)
domain_router.include_router(admin_agencies_router)
domain_router.include_router(admin_syroce_agencies_router)
domain_router.include_router(admin_agency_users_router)
domain_router.include_router(admin_all_users_router)
domain_router.include_router(admin_api_keys_router)
domain_router.include_router(admin_audit_logs_router)
domain_router.include_router(admin_whitelabel_router)
domain_router.include_router(enterprise_rbac_router)
domain_router.include_router(enterprise_ip_whitelist_router)
domain_router.include_router(enterprise_whitelabel_router)
domain_router.include_router(enterprise_export_router)
domain_router.include_router(gdpr_router)
domain_router.include_router(saas_tenants_router)
domain_router.include_router(tenant_features_router)
domain_router.include_router(admin_tenant_features_router)
domain_router.include_router(tenant_health_router)
domain_router.include_router(settings_router)
domain_router.include_router(agency_profile_router)
domain_router.include_router(agency_contracts_router)
domain_router.include_router(onboarding_router)
