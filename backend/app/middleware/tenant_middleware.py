from __future__ import annotations

import os
from typing import Any, Optional

from fastapi import HTTPException, Request
from motor.motor_asyncio import AsyncIOMotorDatabase
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.auth import decode_token, is_super_admin
from app.db import get_db
from app.errors import AppError
from app.request_context import RequestContext, set_request_context
from app.repositories.membership_repository import MembershipRepository
from app.repositories.roles_permissions_repository import RolesPermissionsRepository


def _error_response(status_code: int, code: str, message: str, details: Optional[dict[str, Any]] = None) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message, "details": details}},
    )

from app.services.subscription_service import SubscriptionService


class TenantResolutionMiddleware(BaseHTTPMiddleware):
    """Resolve tenant from header, host, or subdomain and attach to request.state.

    Resolution order:
      a) X-Tenant-Key header (exact match on tenants.tenant_key)
      b) Host header exact match against tenant_domains.domain
      c) Subdomain pattern: {subdomain}.{BASE_DOMAIN}

    Behavior:
      - If tenant cannot be resolved for /storefront/* routes, return 404
        TENANT_NOT_FOUND.
      - If tenant cannot be resolved for /api/* routes, allow existing
        behavior (no tenant required) for backward compatibility.
    """

    def __init__(self, app) -> None:  # type: ignore[override]
        super().__init__(app)
        self.base_domain = os.environ.get("BASE_DOMAIN", "")

    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        # Avoid repeated DB lookups if already set (e.g. in tests)
        if getattr(request.state, "tenant_resolved", False):
            return await call_next(request)

        path = request.url.path or ""

        # Whitelist: auth, health, resolve endpoint and B2B portal APIs
        # B2B portal (/api/b2b/*) organizasyon + acenta bazlı flow'dur,
        # tenant context'ine ihtiyaç duymaz; bu nedenle tenant middleware'ini bypass ederiz.
        if (
            path.startswith("/api/auth/")
            or path.startswith("/api/healthz")
            or path.startswith("/api/health/")
            or path.startswith("/api/saas/tenants/resolve")
            or path.startswith("/api/b2b/")
            or path.startswith("/api/admin/tenants")
            or path.startswith("/api/admin/audit-logs")
            or path.startswith("/api/admin/audit/")
            or path.startswith("/api/admin/rbac")
            or path.startswith("/api/admin/report-schedules")
            or path.startswith("/api/admin/ip-whitelist")
            or path.startswith("/api/admin/whitelabel")
            or path.startswith("/api/admin/tenant/")
            or path.startswith("/api/admin/billing")
            or path.startswith("/api/admin/analytics")
            or path.startswith("/api/admin/demo")
            or path.startswith("/api/webhook/")
            or path.startswith("/api/onboarding/")
            or path.startswith("/api/notifications")
            or path.startswith("/api/webpos/")
            or path.startswith("/api/reports/")
            or path.startswith("/api/activation/")
            or path.startswith("/api/upgrade-requests")
            or path.startswith("/api/approvals")
            or path.startswith("/api/efatura")
            or path.startswith("/api/sms")
            or path.startswith("/api/tickets")
            or path.startswith("/api/crm/")
            or path.startswith("/api/admin/system/")
            or path.startswith("/api/admin/import/")
            or path.startswith("/api/admin/sheets/")
            or path.startswith("/api/system/")
            or path.startswith("/docs")
            or path.startswith("/openapi.json")
        ):
            return await call_next(request)

        db: AsyncIOMotorDatabase = await get_db()

        # ------------------------------------------------------------------
        # 1) Authenticate user via Authorization header (JWT)
        # ------------------------------------------------------------------
        auth_header = request.headers.get("authorization") or request.headers.get("Authorization")
        if not auth_header or not auth_header.lower().startswith("bearer "):
            # Let existing auth dependencies handle 401 semantics
            return await call_next(request)

        token = auth_header.split(" ", 1)[1].strip()
        try:
            payload = decode_token(token)
        except HTTPException:
            # Normalize token errors to a deterministic 401 response instead of bubbling as 500/520
            return _error_response(401, "invalid_token", "Geçersiz token.", None)
        except Exception:
            return _error_response(401, "invalid_token", "Geçersiz token.", None)

        user_email = payload.get("sub")
        org_id = payload.get("org")
        if not user_email or not org_id:
            return _error_response(
                401,
                "invalid_token_payload",
                "Token payload missing required fields.",
                None,
            )

        user_doc = await db.users.find_one({"email": user_email, "organization_id": org_id})
        if not user_doc:
            return _error_response(
                401,
                "user_not_found",
                "User not found for token.",
                None,
            )

        user_id = str(user_doc.get("_id"))
        super_admin = is_super_admin(user_doc)

        # ------------------------------------------------------------------
        # 2) Tenant resolution via X-Tenant-Id header
        # ------------------------------------------------------------------
        tenant_id_header = (request.headers.get("X-Tenant-Id") or "").strip()
        if not tenant_id_header:
            # For SaaS APIs, tenant header is required (except for whitelisted routes).
            return _error_response(
                400,
                "tenant_header_missing",
                "X-Tenant-Id header is required for this endpoint.",
                None,
            )

        from bson import ObjectId

        tenant_lookup_id: Any = tenant_id_header
        try:
            # Try to interpret as ObjectId for Mongo-backed tenants
            tenant_lookup_id = ObjectId(tenant_id_header)
        except Exception:
            # Fallback to string _id; repositories must handle this shape.
            tenant_lookup_id = tenant_id_header

        tenant_doc: Optional[dict[str, Any]] = await db.tenants.find_one({"_id": tenant_lookup_id})
        if not tenant_doc:
            return _error_response(
                404,
                "tenant_not_found",
                "Tenant not found.",
                {"tenant_id": tenant_id_header},
            )

        status = tenant_doc.get("status", "active")
        is_active_flag = tenant_doc.get("is_active", True)
        active = (status == "active") and bool(is_active_flag)

        if not active:
            return _error_response(
                403,
                "tenant_inactive",
                "Tenant is inactive.",
                {"tenant_id": tenant_id_header, "status": status},
            )

        tenant_org_id = tenant_doc.get("organization_id") or tenant_doc.get("org_id")
        if tenant_org_id and str(tenant_org_id) != str(org_id):
            return _error_response(
                403,
                "cross_org_tenant_forbidden",
                "Tenant does not belong to the same organization as the user.",
                {"tenant_org_id": str(tenant_org_id), "user_org_id": str(org_id)},
            )

        tenant_id_str = str(tenant_doc.get("_id"))

        # ------------------------------------------------------------------
        # 3) Membership & role
        # ------------------------------------------------------------------
        membership_repo = MembershipRepository(db)
        membership = await membership_repo.find_active_membership(user_id=user_id, tenant_id=tenant_id_str)
        if not membership and not super_admin:
            raise AppError(
                status_code=403,
                code="tenant_access_forbidden",
                message="User does not have access to this tenant.",
                details={"tenant_id": tenant_id_str},
            )

        role = membership.get("role") if membership else None

        # ------------------------------------------------------------------
        # 4) Subscription guard (org-level)
        # ------------------------------------------------------------------
        sub_service = SubscriptionService(db)
        # We build a lightweight context for subscription checks
        sub_ctx = RequestContext(
            org_id=str(org_id),
            tenant_id=tenant_id_str,
            user_id=user_id,
            role=role,
            permissions=[],
            subscription_status=None,
            plan=None,
            is_super_admin=super_admin,
        )
        await sub_service.ensure_allowed(sub_ctx)
        subscription = await sub_service.get_active_for_org(str(org_id))
        subscription_status = subscription.get("status") if subscription else None

        # ------------------------------------------------------------------
        # 5) Permissions expansion
        # ------------------------------------------------------------------
        permissions: list[str] = []
        if role:
            roles_repo = RolesPermissionsRepository(db)
            role_doc = await roles_repo.get_by_role(role)
            if role_doc and isinstance(role_doc.get("permissions"), list):
                permissions = [str(p) for p in role_doc["permissions"]]

        # ------------------------------------------------------------------
        # 6) Inject context
        # ------------------------------------------------------------------
        ctx = RequestContext(
            org_id=str(org_id),
            tenant_id=tenant_id_str,
            user_id=user_id,
            role=role,
            permissions=permissions,
            subscription_status=subscription_status,
            plan=None,
            is_super_admin=super_admin,
        )
        set_request_context(ctx)
        request.state.ctx = ctx
        request.state.tenant_resolved = True
        request.state.tenant_id = tenant_id_str
        request.state.tenant_org_id = str(org_id)

        response = await call_next(request)
        return response
