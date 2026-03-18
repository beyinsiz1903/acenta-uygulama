"""Admin/System bypass rules for tenant isolation.

Defines which paths and operations are exempt from tenant scoping.
All exemptions are explicit and auditable.
"""
from __future__ import annotations

import logging
from typing import FrozenSet

logger = logging.getLogger("tenant.admin_bypass")

# Collections that are GLOBAL (not tenant-scoped)
# These collections intentionally contain cross-tenant data
GLOBAL_COLLECTIONS: FrozenSet[str] = frozenset({
    "organizations",
    "tenants",
    "memberships",
    "roles_permissions",
    "system_config",
    "system_health",
    "feature_flags",
    "plans",
    "platform_metrics",
    "migration_logs",
    "tenant_isolation_audits",
    "outbox_events",          # outbox is processed by system workers
    "booking_history",        # audit trail — read cross-tenant for admin views
})

# Collections that MUST be tenant-scoped (organization_id required)
TENANT_SCOPED_COLLECTIONS: FrozenSet[str] = frozenset({
    "bookings",
    "customers",
    "payments",
    "vouchers",
    "invoices",
    "hotels",
    "rateplans",
    "inventory",
    "crm_contacts",
    "crm_deals",
    "crm_activities",
    "crm_notes",
    "pricing_rules",
    "commission_rules",
    "settlements",
    "refund_cases",
    "notification_deliveries",
    "audit_log",
    "ops_cases",
    "ops_incidents",
    "agencies",
    "agency_hotel_links",
    "users",
    "email_outbox",
    "booking_events",
    "hotel_portfolio_sources",
    "search_analytics",
    "offers",
    "quotes",
    "reservations",
    "products",
    "orders",
})

# API paths that bypass tenant checks (health, docs, public endpoints)
TENANT_EXEMPT_PATHS: FrozenSet[str] = frozenset({
    "/docs",
    "/openapi.json",
    "/api/healthz",
    "/api/health",
    "/api/health/",
    "/api/auth/login",
    "/api/auth/register",
    "/api/auth/forgot-password",
    "/api/auth/reset-password",
})

# Path prefixes that bypass tenant checks
TENANT_EXEMPT_PREFIXES: tuple[str, ...] = (
    "/api/public/",
    "/api/storefront/",
    "/api/admin/booking-migration/",
    "/api/uploads/",
    "/docs",
)


def is_path_tenant_exempt(path: str) -> bool:
    """Check if a URL path is exempt from tenant isolation."""
    if path in TENANT_EXEMPT_PATHS:
        return True
    for prefix in TENANT_EXEMPT_PREFIXES:
        if path.startswith(prefix):
            return True
    return False


def is_collection_tenant_scoped(collection_name: str) -> bool:
    """Check if a collection requires tenant isolation."""
    return collection_name in TENANT_SCOPED_COLLECTIONS


def is_collection_global(collection_name: str) -> bool:
    """Check if a collection is intentionally global."""
    return collection_name in GLOBAL_COLLECTIONS
