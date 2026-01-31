from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import HTTPException, Request, status


class TenantContext:
    """Lightweight accessor for tenant-related request state.

    This is intentionally minimal for v1 and does not change existing org
    resolution (get_current_org). It simply exposes optional tenant fields
    set by the tenant middleware.
    """

    def __init__(self, request: Request) -> None:
        self._request = request

    @property
    def tenant_id(self) -> Optional[str]:  # pragma: no cover - trivial accessors
        return getattr(self._request.state, "tenant_id", None)

    @property
    def tenant_key(self) -> Optional[str]:  # pragma: no cover - trivial accessors
        return getattr(self._request.state, "tenant_key", None)

    @property
    def organization_id(self) -> Optional[str]:  # pragma: no cover - trivial accessors
        return getattr(self._request.state, "tenant_org_id", None)


def enforce_tenant_org(filter_dict: Dict[str, Any], request: Request) -> Dict[str, Any]:
    """Inject organization_id from tenant context into a Mongo query filter.

    - If tenant is resolved and has an organization_id, ensure filter_dict
      always includes that organization_id.
    - If no tenant context is present, returns filter_dict unchanged to keep
      backward-compatible behavior for internal /api/* routes.
    """

    tenant_org_id = getattr(request.state, "tenant_org_id", None)
    if not tenant_org_id:
        return filter_dict

    # Never override an explicitly different organization_id filter
    existing = filter_dict.get("organization_id")
    if existing is not None and existing != tenant_org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CROSS_TENANT_FORBIDDEN",
        )

    filter_dict["organization_id"] = tenant_org_id
    return filter_dict


def forbid_cross_tenant_payload(payload: Dict[str, Any], request: Request) -> None:
    """Reject payloads that attempt to cross tenant boundaries.

    - If tenant context has an organization_id and payload provides a
      different organization_id, raise 403 CROSS_TENANT_FORBIDDEN.
    - If no tenant context, do nothing (backward compatible for internal
      /api/* routes).
    """

    tenant_org_id = getattr(request.state, "tenant_org_id", None)
    if not tenant_org_id:
        return

    body_org = payload.get("organization_id")
    if body_org is not None and body_org != tenant_org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CROSS_TENANT_FORBIDDEN",
        )
