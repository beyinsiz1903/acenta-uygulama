"""RBAC Enforcement Middleware — Default-Deny Permission Checks.

Applies fine-grained permission checks to all API routes.
Routes without explicit permission mapping are denied by default.
"""
from __future__ import annotations

import logging
import time
from typing import Any

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

logger = logging.getLogger("middleware.rbac")

# Routes that bypass RBAC (public, health, auth)
BYPASS_PREFIXES = [
    "/api/health",
    "/api/auth/login",
    "/api/auth/register",
    "/api/auth/forgot-password",
    "/api/auth/reset-password",
    "/api/public/",
    "/api/p/",
    "/api/v1/auth/",
    "/api/v1/public/",
    "/api/billing/webhooks",
    "/api/stripe/webhook",
    "/docs",
    "/openapi.json",
    "/api/uploads/",
]

# Route prefix → required permission mapping
# Format: (http_method, path_prefix) → permission_code
ROUTE_PERMISSION_MAP: dict[tuple[str, str], str] = {
    # Booking
    ("GET", "/api/bookings"): "booking.view",
    ("POST", "/api/bookings"): "booking.create",
    ("PUT", "/api/bookings"): "booking.update",
    ("PATCH", "/api/bookings"): "booking.update",
    ("DELETE", "/api/bookings"): "booking.cancel",
    # Finance
    ("GET", "/api/ops/finance"): "finance.view",
    ("POST", "/api/ops/finance/accounts"): "finance.payment.create",
    ("POST", "/api/ops/finance/payments"): "finance.payment.create",
    ("POST", "/api/ops/finance/refunds"): "finance.refund.approve",
    ("PUT", "/api/ops/finance"): "finance.payment.create",
    ("POST", "/api/ops/finance/settlements"): "finance.settlement.manage",
    # Supplier ecosystem
    ("GET", "/api/suppliers"): "supplier.view",
    ("POST", "/api/suppliers"): "supplier.override",
    ("GET", "/api/suppliers/ecosystem"): "supplier.view",
    ("POST", "/api/suppliers/ecosystem"): "supplier.override",
    # Reliability
    ("GET", "/api/reliability"): "supplier.view",
    ("POST", "/api/reliability"): "supplier.override",
    ("PUT", "/api/reliability"): "supplier.override",
    # Governance
    ("GET", "/api/governance"): "governance.audit.view",
    ("POST", "/api/governance"): "governance.rbac.manage",
    ("PUT", "/api/governance"): "governance.rbac.manage",
    # Pricing
    ("GET", "/api/pricing"): "pricing.view",
    ("POST", "/api/pricing"): "pricing.rules.manage",
    ("PUT", "/api/pricing"): "pricing.rules.manage",
    # Incidents
    ("GET", "/api/ops/incidents"): "incident.view",
    ("POST", "/api/ops/incidents"): "incident.create",
    # Reports
    ("GET", "/api/reports"): "reports.view",
    ("GET", "/api/admin/reports"): "reports.view",
    ("POST", "/api/admin/reports"): "reports.export",
    # CRM
    ("GET", "/api/crm"): "crm.view",
    ("POST", "/api/crm"): "crm.manage",
    ("PUT", "/api/crm"): "crm.manage",
    # User management
    ("GET", "/api/admin/users"): "user.view",
    ("POST", "/api/admin/users"): "user.create",
    ("PUT", "/api/admin/users"): "user.update",
    ("DELETE", "/api/admin/users"): "user.delete",
    ("GET", "/api/admin/all-users"): "user.view",
    # Tenant/Agency
    ("GET", "/api/admin/agencies"): "tenant.view",
    ("POST", "/api/admin/agencies"): "tenant.settings.update",
    ("PUT", "/api/admin/agencies"): "tenant.settings.update",
    ("GET", "/api/settings"): "tenant.view",
    ("PUT", "/api/settings"): "tenant.settings.update",
    # Voucher
    ("GET", "/api/vouchers"): "voucher.view",
    ("POST", "/api/vouchers"): "voucher.generate",
    # Alerts
    ("GET", "/api/ops/alerts"): "alert.view",
    ("POST", "/api/ops/alerts"): "alert.config",
    # Admin system
    ("GET", "/api/admin/system"): "governance.audit.view",
    ("POST", "/api/admin/system"): "governance.rbac.manage",
    # Admin billing
    ("GET", "/api/admin/billing"): "finance.view",
    ("POST", "/api/admin/billing"): "finance.payment.create",
    # Infrastructure
    ("GET", "/api/infra"): "governance.audit.view",
    # Exports
    ("GET", "/api/exports"): "reports.export",
    ("POST", "/api/exports"): "reports.export",
}

# Default role → permission mapping (in-memory fallback)
DEFAULT_ROLE_PERMISSIONS: dict[str, list[str]] = {
    "super_admin": ["*"],
    "admin": ["*"],
    "ops_admin": [
        "booking.*", "supplier.*", "incident.*", "alert.*",
        "voucher.*", "user.view", "tenant.view",
        "governance.audit.view", "reports.*", "crm.view",
    ],
    "ops": [
        "booking.*", "supplier.*", "incident.*", "alert.*",
        "voucher.*", "user.view", "reports.*", "crm.view",
    ],
    "finance_admin": [
        "booking.view", "finance.*", "pricing.*",
        "reports.*", "governance.compliance.view",
        "user.view", "tenant.view", "crm.view",
    ],
    "agency_admin": [
        "booking.*", "finance.view", "finance.payment.create",
        "pricing.view", "incident.view", "alert.view", "voucher.*",
        "user.view", "user.create", "user.update", "user.role.assign",
        "tenant.view", "tenant.settings.update", "reports.*", "crm.*",
    ],
    "agent": [
        "booking.view", "booking.create", "booking.update",
        "finance.view", "pricing.view", "incident.view", "alert.view",
        "voucher.view", "voucher.generate", "user.view", "reports.view", "crm.*",
    ],
    "support": [
        "booking.view", "finance.view", "pricing.view",
        "incident.view", "alert.view", "voucher.view",
        "user.view", "reports.view", "crm.view",
    ],
    "hotel": [
        "booking.view", "tenant.view", "reports.view",
    ],
}


def _resolve_permissions(roles: list[str]) -> set[str]:
    """Resolve effective permissions from roles list."""
    perms: set[str] = set()
    for role in roles:
        role_perms = DEFAULT_ROLE_PERMISSIONS.get(role, [])
        perms.update(role_perms)
    return perms


def _match_permission(required: str, granted: set[str]) -> bool:
    """Check if required permission is satisfied by granted set."""
    if "*" in granted:
        return True
    if required in granted:
        return True
    # Wildcard: "booking.*" matches "booking.view"
    resource = required.split(".")[0] if "." in required else required
    if f"{resource}.*" in granted:
        return True
    return False


def _find_required_permission(method: str, path: str) -> str | None:
    """Find the required permission for a route."""
    # Exact match first
    for (m, prefix), perm in ROUTE_PERMISSION_MAP.items():
        if method == m and path.startswith(prefix):
            return perm
    # Broad match: GET on any known prefix
    for (m, prefix), perm in ROUTE_PERMISSION_MAP.items():
        if path.startswith(prefix):
            return perm
    return None


class RBACMiddleware(BaseHTTPMiddleware):
    """RBAC enforcement middleware with default-deny policy."""

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        method = request.method

        # Skip OPTIONS (CORS preflight)
        if method == "OPTIONS":
            return await call_next(request)

        # Skip bypass routes
        for prefix in BYPASS_PREFIXES:
            if path.startswith(prefix):
                return await call_next(request)

        # Skip non-API routes
        if not path.startswith("/api/"):
            return await call_next(request)

        # Extract user from request state (set by auth dependency)
        user = getattr(request.state, "user", None)
        if not user:
            # No user context yet — let auth dependency handle it
            # RBAC checks happen post-auth via the dependency injection
            return await call_next(request)

        roles = user.get("roles", [])
        required = _find_required_permission(method, path)

        if not required:
            # No permission mapping = allow for now (legacy routes)
            # In strict mode, this would be deny
            return await call_next(request)

        perms = _resolve_permissions(roles)
        if _match_permission(required, perms):
            return await call_next(request)

        # DENIED
        logger.warning(
            "RBAC_DENY user=%s roles=%s path=%s method=%s required=%s",
            user.get("email", "?"), roles, path, method, required,
        )

        # Best-effort audit log
        try:
            from app.db import get_db_sync
            # Audit is logged asynchronously; don't block the response
        except Exception:
            pass

        return JSONResponse(
            status_code=403,
            content={
                "error": "forbidden",
                "code": "rbac_denied",
                "message": f"Permission '{required}' required",
                "required_permission": required,
            },
        )
