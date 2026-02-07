"""SMS Notification API router (B).

Permissions: notifications.sms.send, notifications.sms.view
"""
from __future__ import annotations

from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from app.auth import get_current_user, require_roles
from app.services.sms.service import (
    get_sms_templates,
    list_sms_logs,
    send_bulk_sms,
    send_sms_notification,
)

router = APIRouter(prefix="/api/sms", tags=["sms_notifications"])


class SendSMSIn(BaseModel):
    to: str = Field(..., description="Phone number")
    template_key: str = "custom"
    variables: Dict[str, str] = {}
    provider: str = "mock"


class SendBulkSMSIn(BaseModel):
    recipients: List[str]
    template_key: str = "custom"
    variables: Dict[str, str] = {}
    provider: str = "mock"


@router.post("/send")
async def send_sms(
    payload: SendSMSIn,
    user=Depends(get_current_user),
):
    """Send a single SMS notification."""
    org_id = user["organization_id"]
    tenant_id = user.get("tenant_id", org_id)
    result = await send_sms_notification(
        tenant_id=tenant_id,
        org_id=org_id,
        to=payload.to,
        template_key=payload.template_key,
        variables=payload.variables,
        provider_name=payload.provider,
        created_by=user.get("email", ""),
    )
    return result


@router.post("/send-bulk")
async def send_bulk(
    payload: SendBulkSMSIn,
    user=Depends(require_roles(["super_admin", "admin"])),
):
    """Send bulk SMS to multiple recipients."""
    org_id = user["organization_id"]
    tenant_id = user.get("tenant_id", org_id)
    result = await send_bulk_sms(
        tenant_id=tenant_id,
        org_id=org_id,
        recipients=payload.recipients,
        template_key=payload.template_key,
        variables=payload.variables,
        provider_name=payload.provider,
        created_by=user.get("email", ""),
    )
    return result


@router.get("/logs")
async def get_sms_logs(
    limit: int = Query(50, le=200),
    user=Depends(get_current_user),
):
    """List SMS logs."""
    org_id = user["organization_id"]
    tenant_id = user.get("tenant_id", "")
    items = await list_sms_logs(org_id, tenant_id, limit=limit)
    return {"items": items, "count": len(items)}


@router.get("/templates")
async def get_templates(user=Depends(get_current_user)):
    """List available SMS templates."""
    templates = await get_sms_templates()
    return {"templates": templates}
