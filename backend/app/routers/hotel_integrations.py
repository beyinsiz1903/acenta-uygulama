from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from app.auth import get_current_user, require_roles
from app.db import get_db
from app.services.audit import write_audit_log

router = APIRouter(prefix="/api/hotel/integrations", tags=["hotel-integrations"])


class IntegrationConfig(BaseModel):
  
    mode: Optional[str] = Field(default="pull", pattern="^(pull|push)$")
    channels: list[str] = Field(default_factory=list)


class IntegrationUpdate(BaseModel):
    provider: Optional[str] = Field(default=None)
    status: str = Field(pattern="^(not_configured|configured|connected|error|disabled)$")
    config: IntegrationConfig = Field(default_factory=IntegrationConfig)


ALLOWED_PROVIDERS = {"channex", "siteminder", "cloudbeds", "hotelrunner", "custom"}


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


async def _ensure_cm_integration(db, organization_id: str, hotel_id: str) -> dict[str, Any]:
    doc = await db.hotel_integrations.find_one(
        {
            "organization_id": organization_id,
            "hotel_id": hotel_id,
            "kind": "channel_manager",
        }
    )
    if doc:
        return doc

    now = _utc_now()
    doc = {
        "organization_id": organization_id,
        "hotel_id": hotel_id,
        "kind": "channel_manager",
        "provider": None,
        "status": "not_configured",
        "display_name": "Channel Manager",
        "external_account_id": None,
        "webhook_url": None,
        "last_sync_at": None,
        "last_error": None,
        "config": {},
        "secrets_ref": {"vault_key": None, "version": 0},
        "created_at": now,
        "updated_at": now,
    }
    await db.hotel_integrations.insert_one(doc)
    return doc


@router.get("", dependencies=[Depends(require_roles(["hotel_admin", "hotel_staff"]))])
async def get_hotel_integrations(user=Depends(get_current_user)):
    db = await get_db()
    hotel_id = user.get("hotel_id")
    if not hotel_id:
        raise HTTPException(status_code=403, detail="NOT_LINKED_TO_HOTEL")

    org_id = user["organization_id"]

    cm = await _ensure_cm_integration(db, org_id, str(hotel_id))

    item = {
        "id": str(cm.get("_id")),
        "kind": cm.get("kind"),
        "provider": cm.get("provider"),
        "status": cm.get("status"),
        "display_name": cm.get("display_name") or "Channel Manager",
        "last_sync_at": cm.get("last_sync_at"),
        "last_error": cm.get("last_error"),
        "config": cm.get("config") or {},
    }

    return {"items": [item]}


@router.put(
    "/channel-manager",
    dependencies=[Depends(require_roles(["hotel_admin"]))],
)
async def update_channel_manager(
    payload: IntegrationUpdate,
    request: Request,
    user=Depends(get_current_user),
):
    db = await get_db()
    hotel_id = user.get("hotel_id")
    if not hotel_id:
        raise HTTPException(status_code=403, detail="NOT_LINKED_TO_HOTEL")

    org_id = user["organization_id"]

    if payload.provider is not None and payload.provider not in ALLOWED_PROVIDERS:
        raise HTTPException(status_code=422, detail="INVALID_PROVIDER")

    now = _utc_now()

    existing = await _ensure_cm_integration(db, org_id, str(hotel_id))

    update_doc: dict[str, Any] = {
        "provider": payload.provider,
        "status": payload.status,
        "config": payload.config.model_dump(),
        "updated_at": now,
    }

    await db.hotel_integrations.update_one(
        {
            "organization_id": org_id,
            "hotel_id": str(hotel_id),
            "kind": "channel_manager",
        },
        {"$set": update_doc},
        upsert=True,
    )

    after = {**existing, **update_doc}

    await write_audit_log(
        db,
        organization_id=org_id,
        actor={
            "actor_type": "user",
            "email": user.get("email"),
            "roles": user.get("roles"),
        },
        request=request,
        action="integration.cm.update",
        target_type="hotel_integration",
        target_id=str(hotel_id),
        before=existing,
        after=after,
    )

    return {"ok": True}
