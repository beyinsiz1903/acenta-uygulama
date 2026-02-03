from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from contextvars import ContextVar

from app.errors import AppError


@dataclass
class RequestContext:
  """Per-request SaaS context injected by middleware.

  This is intentionally small and pure-data so that it can be passed around
  or stored in ContextVar without pulling in FastAPI/Request.
  """

  org_id: Optional[str]
  tenant_id: Optional[str]
  user_id: Optional[str]
  role: Optional[str]
  permissions: List[str]
  subscription_status: Optional[str] = None
  plan: Optional[str] = None
  is_super_admin: bool = False


_ctx_var: ContextVar[Optional[RequestContext]] = ContextVar("request_ctx", default=None)


def set_request_context(ctx: RequestContext) -> None:
  _ctx_var.set(ctx)


def get_request_context(required: bool = True) -> Optional[RequestContext]:
  ctx = _ctx_var.get()
  if required and ctx is None:
    raise AppError(status_code=500, code="REQUEST_CONTEXT_MISSING", message="Request context not initialized", details=None)
  return ctx


def _permission_matches(owned: str, required: str) -> bool:
  """Return True if a single owned permission covers required.

  - Exact match
  - Wildcard match: booking.* covers booking.create, booking.view, etc.
  """

  if owned == required:
    return True

  if owned.endswith(".*"):
    prefix = owned[:-2]
    return required.startswith(prefix + ".")

  return False


def has_permission(required: str, ctx: Optional[RequestContext] = None) -> bool:
  """Check if current context has the required permission.

  Super admins always pass.
  """

  if ctx is None:
    ctx = get_request_context(required=False)

  if ctx is None:
    return False

  if ctx.is_super_admin:
    return True

  for p in ctx.permissions:
    if _permission_matches(p, required):
      return True

  return False


def require_permission(required: str):
  """Decorator for service-layer methods that require a permission.

  This is intentionally framework-agnostic (does not depend on FastAPI
  dependencies). It expects RequestContext to be already set by middleware.
  """

  def decorator(func):  # type: ignore[no-untyped-def]
    async def wrapper(*args, **kwargs):  # type: ignore[no-untyped-def]
      ctx = get_request_context(required=True)
      if not has_permission(required, ctx):
        raise AppError(
          status_code=403,
          code="INSUFFICIENT_PERMISSIONS",
          message=f"Missing permission: {required}",
          details={"required": required, "role": ctx.role},
        )
      return await func(*args, **kwargs)

    return wrapper

  return decorator
