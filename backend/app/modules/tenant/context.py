"""Tenant context extraction — FastAPI dependency for tenant-scoped operations.

Every endpoint that touches tenant data MUST use one of:
  - require_tenant_context(): strict — raises 403 if no tenant
  - get_tenant_context():     lenient — returns None if no tenant (for public endpoints)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from fastapi import HTTPException, Request

from app.request_context import RequestContext, get_request_context


@dataclass(frozen=True)
class TenantContext:
    """Immutable tenant context for the current request."""

    org_id: str
    tenant_id: str
    user_id: str
    is_super_admin: bool = False

    @property
    def org_filter(self) -> dict:
        """Standard MongoDB filter for organization-scoped queries."""
        return {"organization_id": self.org_id}

    def scoped_filter(self, extra: dict | None = None) -> dict:
        """Build a MongoDB filter scoped to this tenant's organization."""
        base = {"organization_id": self.org_id}
        if extra:
            base.update(extra)
        return base


def _extract_from_request(request: Request) -> Optional[TenantContext]:
    """Extract TenantContext from request state (set by TenantResolutionMiddleware)."""
    ctx: Optional[RequestContext] = getattr(request.state, "ctx", None)
    if ctx is None:
        ctx = get_request_context(required=False)

    if ctx is None or not ctx.org_id:
        return None

    return TenantContext(
        org_id=ctx.org_id,
        tenant_id=ctx.tenant_id or "",
        user_id=ctx.user_id or "",
        is_super_admin=ctx.is_super_admin,
    )


async def require_tenant_context(request: Request) -> TenantContext:
    """FastAPI dependency: STRICT tenant context. Raises 403 if missing.

    Usage:
        @router.get("/bookings")
        async def list_bookings(tc: TenantContext = Depends(require_tenant_context)):
            ...
    """
    tc = _extract_from_request(request)
    if tc is None or not tc.org_id:
        raise HTTPException(
            status_code=403,
            detail="Tenant bağlamı gerekli. Lütfen giriş yapın.",
        )
    return tc


async def get_tenant_context(request: Request) -> Optional[TenantContext]:
    """FastAPI dependency: LENIENT tenant context. Returns None if missing.

    For public endpoints or optional tenant scoping.
    """
    return _extract_from_request(request)
