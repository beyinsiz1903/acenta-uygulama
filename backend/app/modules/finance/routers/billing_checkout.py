from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from app.auth import get_current_user
from app.db import get_db
from app.errors import AppError
from app.services.feature_service import feature_service
from app.services.stripe_checkout_service import stripe_checkout_service

router = APIRouter(tags=["billing_checkout"])


class CreateCheckoutBody(BaseModel):
    plan: str = Field(..., min_length=2)
    interval: str = Field(default="monthly", pattern="^(monthly|yearly)$")
    origin_url: str = Field(..., min_length=8)
    cancel_path: Optional[str] = "/pricing"


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


@router.post("/api/billing/create-checkout")
async def create_checkout_session(
    body: CreateCheckoutBody,
    request: Request,
    user=Depends(get_current_user),
) -> dict:
    tenant_id = await _resolve_tenant_id(user)
    current_plan = await feature_service.get_plan(tenant_id) if tenant_id else None
    return await stripe_checkout_service.create_checkout_session(
        request,
        tenant_id=tenant_id,
        organization_id=str(user.get("organization_id") or ""),
        user_id=str(user.get("id") or user.get("_id") or user.get("email") or ""),
        user_email=str(user.get("email") or ""),
        plan=body.plan,
        interval=body.interval,
        origin_url=body.origin_url,
        cancel_path=body.cancel_path,
        current_plan=current_plan,
    )


@router.get("/api/billing/checkout-status/{session_id}")
async def get_checkout_status(
    session_id: str,
    request: Request,
    user=Depends(get_current_user),
) -> dict:
    return await stripe_checkout_service.sync_checkout_status(request, session_id)


@router.post("/api/webhook/stripe")
async def stripe_checkout_webhook(request: Request) -> dict:
    payload = await request.body()
    signature = request.headers.get("Stripe-Signature")
    return await stripe_checkout_service.handle_webhook(request, payload, signature)
