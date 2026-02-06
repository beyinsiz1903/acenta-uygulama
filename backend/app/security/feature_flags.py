from __future__ import annotations

from fastapi import Depends, Request

from app.errors import AppError
from app.security.b2b_context import B2BTenantContext, get_b2b_tenant_context
from app.services.feature_service import feature_service


def require_b2b_feature(feature_key: str):
  """Feature guard for B2B routes.

  Uses get_b2b_tenant_context which resolves tenant via X-Tenant-Id header
  and performs membership checks specific to B2B endpoints.
  """

  async def _guard(tenant_ctx: B2BTenantContext = Depends(get_b2b_tenant_context)) -> None:
    tenant_id = tenant_ctx.tenant_id
    has = await feature_service.has_feature(tenant_id, feature_key)
    if not has:
      raise AppError(
        403,
        "feature_not_enabled",
        "Bu özellik planınızda aktif değil.",
        {"feature": feature_key},
      )

  return _guard


def require_tenant_feature(feature_key: str):
  """Feature guard for non-B2B tenant-scoped routes.

  Uses request.state.tenant_id set by TenantResolutionMiddleware.
  This works for all routes that go through the tenant middleware
  (i.e., routes NOT whitelisted in the middleware).
  """

  async def _guard(request: Request) -> None:
    tenant_id = getattr(request.state, "tenant_id", None)
    if not tenant_id:
      raise AppError(
        400,
        "tenant_context_missing",
        "Tenant context bulunamadı.",
        {"feature": feature_key},
      )
    has = await feature_service.has_feature(tenant_id, feature_key)
    if not has:
      raise AppError(
        403,
        "feature_not_enabled",
        "Bu özellik planınızda aktif değil.",
        {"feature": feature_key},
      )

  return _guard
