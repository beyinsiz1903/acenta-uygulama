from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from app.auth import get_current_user
from app.db import get_db
from app.errors import AppError
from app.services.stripe_checkout_service import stripe_checkout_service

router = APIRouter(tags=["billing_lifecycle"])


class BillingPortalBody(BaseModel):
    origin_url: str = Field(..., min_length=8)
    return_path: Optional[str] = "/app/settings/billing"


class ChangePlanBody(BaseModel):
    plan: str = Field(..., min_length=2)
    interval: str = Field(default="monthly", pattern="^(monthly|yearly)$")
    origin_url: str = Field(..., min_length=8)
    cancel_path: Optional[str] = "/app/settings/billing"


async def _resolve_tenant_id(user: dict) -> str:
    tenant_id = str(user.get("tenant_id") or "")
    if tenant_id:
        return tenant_id

    organization_id = str(user.get("organization_id") or "")
    if not organization_id:
        raise AppError(404, "tenant_not_found", "Tenant bulunamadı.", {"reason": "organization_missing"})

    db = await get_db()
    tenant = await db.tenants.find_one({"organization_id": organization_id})
    if not tenant:
        raise AppError(404, "tenant_not_found", "Tenant bulunamadı.", {"organization_id": organization_id})
    return str(tenant.get("_id") or "")


@router.get("/api/billing/subscription")
async def get_billing_subscription(
    user=Depends(get_current_user),
) -> dict:
    tenant_id = await _resolve_tenant_id(user)
    overview = await stripe_checkout_service.get_billing_overview(
        tenant_id,
        user_email=str(user.get("email") or ""),
    )
    return {"tenant_id": tenant_id, **overview}


@router.post("/api/billing/customer-portal")
async def create_billing_portal_session(
    body: BillingPortalBody,
    user=Depends(get_current_user),
) -> dict:
    tenant_id = await _resolve_tenant_id(user)
    return await stripe_checkout_service.create_customer_portal_session(
        tenant_id,
        origin_url=body.origin_url,
        return_path=body.return_path,
        actor_user_id=str(user.get("id") or user.get("_id") or user.get("email") or ""),
        actor_email=str(user.get("email") or ""),
    )


@router.post("/api/billing/change-plan")
async def change_billing_plan(
    body: ChangePlanBody,
    user=Depends(get_current_user),
) -> dict:
    tenant_id = await _resolve_tenant_id(user)
    return await stripe_checkout_service.change_plan(
        tenant_id=tenant_id,
        organization_id=str(user.get("organization_id") or ""),
        user_id=str(user.get("id") or user.get("_id") or user.get("email") or ""),
        user_email=str(user.get("email") or ""),
        plan=body.plan,
        interval=body.interval,
        origin_url=body.origin_url,
        cancel_path=body.cancel_path,
    )


@router.post("/api/billing/cancel-subscription")
async def cancel_billing_subscription(
    user=Depends(get_current_user),
) -> dict:
    tenant_id = await _resolve_tenant_id(user)
    return await stripe_checkout_service.cancel_subscription_at_period_end(
        tenant_id,
        actor_user_id=str(user.get("id") or user.get("_id") or user.get("email") or ""),
        actor_email=str(user.get("email") or ""),
    )


@router.post("/api/billing/reactivate-subscription")
async def reactivate_billing_subscription(
    user=Depends(get_current_user),
) -> dict:
    tenant_id = await _resolve_tenant_id(user)
    return await stripe_checkout_service.reactivate_subscription(
        tenant_id,
        actor_user_id=str(user.get("id") or user.get("_id") or user.get("email") or ""),
        actor_email=str(user.get("email") or ""),
    )