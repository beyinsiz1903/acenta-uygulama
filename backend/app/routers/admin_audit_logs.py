from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.auth import require_roles
from app.services.audit_log_service import list_audit_logs

router = APIRouter(prefix="/api/admin/audit-logs", tags=["admin_audit_logs"])

AdminDep = Depends(require_roles(["super_admin", "admin"]))


@router.get("", dependencies=[AdminDep])
async def get_audit_logs(
  tenant_id: Optional[str] = Query(None),
  action: Optional[str] = Query(None),
  limit: int = Query(50, le=200),
  cursor: Optional[str] = Query(None),
) -> dict:
  """Admin: list audit logs with optional filters and cursor pagination."""
  items = await list_audit_logs(
    tenant_id=tenant_id,
    action=action,
    limit=limit,
    cursor=cursor,
  )
  next_cursor = items[-1]["id"] if items else None
  return {"items": items, "next_cursor": next_cursor}
