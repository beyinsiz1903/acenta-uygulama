from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse

from app.auth import require_roles
from app.services.audit_log_service import list_audit_logs

router = APIRouter(prefix="/api/admin/audit-logs", tags=["admin_audit_logs"])

AdminDep = Depends(require_roles(["super_admin", "admin"]))


def _serialize_item(item: dict) -> dict:
  """Convert datetime fields to ISO strings."""
  out = dict(item)
  for k, v in out.items():
    if isinstance(v, datetime):
      out[k] = v.isoformat()
  return out


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
  serialized = [_serialize_item(i) for i in items]
  next_cursor = serialized[-1]["id"] if serialized else None
  return {"items": serialized, "next_cursor": next_cursor}
