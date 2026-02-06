from __future__ import annotations

import functools
from typing import Any, Callable, Coroutine, Optional, TypeVar

from fastapi import Depends

from app.errors import AppError
from app.security.b2b_context import B2BTenantContext, get_b2b_tenant_context
from app.services.feature_service import feature_service
from app.constants.features import FEATURE_B2B

T = TypeVar("T")


def require_tenant_feature(feature_key: str):
  """Dependency for tenant-scoped feature enforcement.

  - Extracts tenant_id from B2BTenantContext (X-Tenant-Id + membership).
  - If feature is missing, raises AppError with code "feature_not_enabled".
  - Super-admin bypass is intentionally NOT applied here; this is purely
    tenant capability, not org-level toggle.
  
  Usage:
    @router.get("/some-endpoint")
    async def my_endpoint(
        tenant_ctx: B2BTenantContext = Depends(get_b2b_tenant_context),
        _: None = Depends(require_tenant_feature("b2b")),
    ):
        # endpoint logic here
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
    return None
  
  return _guard
