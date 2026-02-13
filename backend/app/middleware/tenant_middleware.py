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
    """Resolve tenant and inject RequestContext for all authenticated requests.

    For single-tenant setups, tenant is resolved from user's org automatically.
    """

    def __init__(self, app) -> None:  # type: ignore[override]
        super().__init__(app)
        self.base_domain = os.environ.get("BASE_DOMAIN", "")

    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        # Avoid repeated DB lookups if already set (e.g. in tests)
        if getattr(request.state, "tenant_resolved", False):
            return await call_next(request)

        path = request.url.path or ""

        # Pure infrastructure endpoints: no auth needed, skip entirely
        if (
            path.startswith("/docs")
            or path.startswith("/openapi.json")
            or path.startswith("/api/healthz")
            or path.startswith("/api/health/")
        ):
            return await call_next(request)

        db: AsyncIOMotorDatabase = await get_db()

        # ------------------------------------------------------------------
        # 1) Authenticate user via Authorization header (JWT)
        # ------------------------------------------------------------------
        auth_header = request.headers.get("authorization") or request.headers.get("Authorization")
        if not auth_header or not auth_header.lower().startswith("bearer "):
            # No auth header: let route-level auth dependencies handle it
            return await call_next(request)

        token = auth_header.split(" ", 1)[1].strip()
        try:
            payload = decode_token(token)
        except HTTPException:
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
        # 2) Tenant resolution (graceful, multi-fallback)
        # ------------------------------------------------------------------
        tenant_id_str = None

        # a) From X-Tenant-Id header
        tenant_id_header = (request.headers.get("X-Tenant-Id") or "").strip()
        if tenant_id_header:
            from bson import ObjectId
            try:
                tenant_lookup_id = ObjectId(tenant_id_header)
            except Exception:
                tenant_lookup_id = tenant_id_header
            tenant_doc: Optional[dict[str, Any]] = await db.tenants.find_one({"_id": tenant_lookup_id})
            if not tenant_doc:
                tenant_doc = await db.tenants.find_one({"_id": tenant_id_header})
            if tenant_doc:
                tenant_id_str = str(tenant_doc["_id"])

        # b) From user's tenant_id field
        if not tenant_id_str and user_doc.get("tenant_id"):
            tenant_id_str = str(user_doc["tenant_id"])

        # c) From organization lookup
        if not tenant_id_str:
            tenant_doc = await db.tenants.find_one({"organization_id": org_id})
            if tenant_doc:
                tenant_id_str = str(tenant_doc["_id"])

        # d) Fallback: use org_id as tenant_id for single-tenant setups
        if not tenant_id_str:
            tenant_id_str = str(org_id)

        # ------------------------------------------------------------------
        # 3) Membership & role resolution (graceful)
        # ------------------------------------------------------------------
        role = None
        if super_admin:
            role = "super_admin"
        else:
            try:
                mem_repo = MembershipRepository(db)
                # Try find_active_membership first, fall back to find_membership
                try:
                    membership = await mem_repo.find_active_membership(user_id=user_id, tenant_id=tenant_id_str)
                except (TypeError, AttributeError):
                    membership = await mem_repo.find_membership(tenant_id_str, user_id)
                role = membership.get("role") if membership else None
            except Exception:
                pass

        # ------------------------------------------------------------------
        # 4) Permissions expansion (graceful)
        # ------------------------------------------------------------------
        permissions: list[str] = []
        if super_admin:
            permissions = ["*"]
        elif role:
            try:
                roles_repo = RolesPermissionsRepository(db)
                role_doc = await roles_repo.get_by_role(role)
                if role_doc and isinstance(role_doc.get("permissions"), list):
                    permissions = [str(p) for p in role_doc["permissions"]]
            except Exception:
                pass

        # ------------------------------------------------------------------
        # 5) Inject RequestContext
        # ------------------------------------------------------------------
        ctx = RequestContext(
            org_id=str(org_id),
            tenant_id=tenant_id_str,
            user_id=user_id,
            role=role,
            permissions=permissions,
            subscription_status=None,
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
