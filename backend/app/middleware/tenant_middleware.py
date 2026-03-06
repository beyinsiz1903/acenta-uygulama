from __future__ import annotations

import os
from typing import Any, Optional

from fastapi import HTTPException, Request
from motor.motor_asyncio import AsyncIOMotorDatabase
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.auth import decode_token, is_super_admin
from app.db import get_db
from app.request_context import RequestContext, set_request_context
from app.repositories.membership_repository import MembershipRepository
from app.repositories.roles_permissions_repository import RolesPermissionsRepository
from app.repositories.tenant_repository import TenantRepository


def _error_response(status_code: int, code: str, message: str, details: Optional[dict[str, Any]] = None) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message, "details": details}},
    )



class TenantResolutionMiddleware(BaseHTTPMiddleware):
    """Resolve tenant and inject RequestContext for all authenticated requests.

    For single-tenant setups, tenant is resolved from user's org automatically.
    """

    def __init__(self, app) -> None:  # type: ignore[override]
        super().__init__(app)
        self.base_domain = os.environ.get("BASE_DOMAIN", "")

    @staticmethod
    def _normalize_tenant_id(raw: str) -> str:
        return raw.strip()

    async def _resolve_effective_tenant(
        self,
        *,
        db: AsyncIOMotorDatabase,
        user_doc: dict[str, Any],
        org_id: str,
        user_id: str,
        super_admin: bool,
        tenant_id_header: str,
    ) -> tuple[str, str, list[str], Optional[dict[str, Any]]]:
        tenant_repo = TenantRepository(db)
        mem_repo = MembershipRepository(db)

        requested_tenant = self._normalize_tenant_id(tenant_id_header) if tenant_id_header else ""
        active_memberships = await mem_repo.list_active_memberships(user_id)
        allowed_tenant_ids = [str(m.get("tenant_id")) for m in active_memberships if m.get("tenant_id")]
        membership_map = {str(m.get("tenant_id")): m for m in active_memberships if m.get("tenant_id")}

        if requested_tenant:
            tenant_doc = await tenant_repo.get_by_id(requested_tenant)
            if not tenant_doc:
                raise HTTPException(status_code=404, detail="Tenant bulunamadı")

            tenant_id_str = str(tenant_doc.get("_id"))
            if super_admin:
                return tenant_id_str, "header_super_admin_override", allowed_tenant_ids, membership_map.get(tenant_id_str)

            membership = membership_map.get(tenant_id_str)
            if not membership:
                raise HTTPException(status_code=403, detail="Bu tenant için aktif üyelik bulunamadı")
            return tenant_id_str, "header_membership", allowed_tenant_ids, membership

        if super_admin:
            if user_doc.get("tenant_id"):
                return str(user_doc["tenant_id"]), "user_doc", allowed_tenant_ids, membership_map.get(str(user_doc["tenant_id"]))
            tenant_doc = await tenant_repo.get_first_for_org(org_id)
            if tenant_doc:
                return str(tenant_doc.get("_id")), "org_fallback", allowed_tenant_ids, membership_map.get(str(tenant_doc.get("_id")))
            return str(org_id), "org_id_fallback", allowed_tenant_ids, None

        if len(allowed_tenant_ids) == 1:
            tenant_id_str = allowed_tenant_ids[0]
            return tenant_id_str, "single_membership", allowed_tenant_ids, membership_map.get(tenant_id_str)

        if user_doc.get("tenant_id") and str(user_doc["tenant_id"]) in allowed_tenant_ids:
            tenant_id_str = str(user_doc["tenant_id"])
            return tenant_id_str, "user_doc_membership", allowed_tenant_ids, membership_map.get(tenant_id_str)

        if set(user_doc.get("roles") or []).intersection({"admin"}):
            org_tenants = await tenant_repo.list_for_org(org_id)
            if len(org_tenants) == 1:
                tenant_id_str = str(org_tenants[0].get("_id"))
                return tenant_id_str, "admin_org_fallback", allowed_tenant_ids, membership_map.get(tenant_id_str)
            if len(org_tenants) == 0:
                return str(org_id), "admin_org_id_fallback", allowed_tenant_ids, None

        raise HTTPException(status_code=403, detail="Tenant bağlamı çözülemedi")

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
        # 2) Tenant resolution (membership-bound, controlled super-admin override)
        # ------------------------------------------------------------------
        tenant_id_header = (request.headers.get("X-Tenant-Id") or "").strip()
        try:
            tenant_id_str, tenant_source, allowed_tenant_ids, membership = await self._resolve_effective_tenant(
                db=db,
                user_doc=user_doc,
                org_id=str(org_id),
                user_id=user_id,
                super_admin=super_admin,
                tenant_id_header=tenant_id_header,
            )
        except HTTPException as exc:
            return _error_response(exc.status_code, "tenant_resolution_failed", str(exc.detail), None)

        # ------------------------------------------------------------------
        # 3) Membership & role resolution (graceful)
        # ------------------------------------------------------------------
        role = None
        if super_admin:
            role = "super_admin"
        else:
            role = (membership or {}).get("role")
            if role is None:
                roles = list(user_doc.get("roles") or [])
                role = roles[0] if roles else None

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
            tenant_source=tenant_source,
            allowed_tenant_ids=allowed_tenant_ids,
            subscription_status=None,
            plan=None,
            is_super_admin=super_admin,
        )
        set_request_context(ctx)
        request.state.ctx = ctx
        request.state.tenant_resolved = True
        request.state.tenant_id = tenant_id_str
        request.state.tenant_org_id = str(org_id)
        request.state.allowed_tenant_ids = allowed_tenant_ids

        response = await call_next(request)
        return response
