from __future__ import annotations

import functools
from typing import Any, Callable, Coroutine, Optional, TypeVar

from fastapi import Depends

from app.errors import AppError
from app.security.b2b_context import B2BTenantContext, get_b2b_tenant_context
from app.services.feature_service import feature_service

T = TypeVar("T")


def require_tenant_feature(feature_key: str) -> Callable[[Callable[..., Coroutine[Any, Any, T]]], Callable[..., Coroutine[Any, Any, T]]]:
  """Decorator for tenant-scoped feature enforcement.

  - Extracts tenant_id from B2BTenantContext (X-Tenant-Id + membership).
  - If feature is missing, raises AppError with code "feature_not_enabled".
  - Super-admin bypass is intentionally NOT applied here; this is purely
    tenant capability, not org-level toggle.
  """

  def decorator(func: Callable[..., Coroutine[Any, Any, T]]) -> Callable[..., Coroutine[Any, Any, T]]:
    @functools.wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> T:
      # Extract tenant_ctx from kwargs - it should be injected by FastAPI dependency
      tenant_ctx = kwargs.get('tenant_ctx')
      if tenant_ctx is None:
        # This should not happen in normal operation since the dependency should inject it
        raise AppError(
          500,
          "tenant_context_missing",
          "Tenant context is missing.",
          {"feature": feature_key},
        )
      
      tenant_id = tenant_ctx.tenant_id
      has = await feature_service.has_feature(tenant_id, feature_key)
      if not has:
        raise AppError(
          403,
          "feature_not_enabled",
          "Bu özellik planınızda aktif değil.",
          {"feature": feature_key},
        )
      return await func(*args, **kwargs)

    return wrapper

  return decorator
