"""O1 - Backup & Restore Admin Endpoints.

GET  /api/admin/system/backups      - List backups
POST /api/admin/system/backups/run  - Trigger manual backup
DELETE /api/admin/system/backups/{id} - Delete backup
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.auth import get_current_user, require_roles
from app.db import get_db
from app.services.audit_hash_chain import write_chained_audit_log
from app.services import backup_service

router = APIRouter(
    prefix="/api/admin/system/backups",
    tags=["system_backups"],
)


@router.get("")
async def list_backups(
    skip: int = 0,
    limit: int = 50,
    user=Depends(require_roles(["super_admin"])),
):
    """List all system backups."""
    items = await backup_service.list_backups(skip=skip, limit=limit)
    return {"items": items, "total": len(items)}


@router.post("/run")
async def run_backup(
    user=Depends(require_roles(["super_admin"])),
):
    """Trigger a manual backup."""
    result = await backup_service.run_full_backup(backup_type="manual")

    # Audit log
    db = await get_db()
    await write_chained_audit_log(
        db,
        organization_id=user.get("organization_id", ""),
        tenant_id=user.get("tenant_id", ""),
        actor={"actor_type": "user", "actor_id": str(user.get("_id", "")), "email": user.get("email", "")},
        action="system.backup.run",
        target_type="system_backup",
        target_id=result.get("backup_id", ""),
        after={"status": result.get("status"), "filename": result.get("filename")},
    )

    return result


@router.delete("/{backup_id}")
async def delete_backup(
    backup_id: str,
    user=Depends(require_roles(["super_admin"])),
):
    """Delete a backup."""
    deleted = await backup_service.delete_backup(backup_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Backup not found")

    # Audit log
    db = await get_db()
    await write_chained_audit_log(
        db,
        organization_id=user.get("organization_id", ""),
        tenant_id=user.get("tenant_id", ""),
        actor={"actor_type": "user", "actor_id": str(user.get("_id", "")), "email": user.get("email", "")},
        action="system.backup.delete",
        target_type="system_backup",
        target_id=backup_id,
    )

    return {"deleted": True, "backup_id": backup_id}
