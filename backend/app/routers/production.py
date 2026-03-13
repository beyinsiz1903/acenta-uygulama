"""Voucher & Notification API Router — Production Activation Layer.

Endpoints:
- Voucher generation & download
- Email/Slack/Webhook notification dispatch
- Delivery log retrieval
"""
from __future__ import annotations

import os
from fastapi import APIRouter, Depends, Query
from fastapi.responses import FileResponse
from typing import Optional
from pydantic import BaseModel

from app.db import get_db
from app.auth import require_roles
from app.errors import AppError

router = APIRouter(prefix="/api/production", tags=["production_activation"])


# ============================================================================
# Voucher endpoints
# ============================================================================

class VoucherGenerateRequest(BaseModel):
    booking_id: str
    locale: str = "tr"
    brand: dict | None = None


@router.post("/vouchers/generate")
async def generate_voucher(
    payload: VoucherGenerateRequest,
    current_user=Depends(require_roles(["admin", "ops", "agent", "super_admin"])),
    db=Depends(get_db),
):
    from app.services.voucher_service import generate_voucher as gen_voucher
    result = await gen_voucher(
        db, current_user["organization_id"], payload.booking_id,
        brand=payload.brand, locale=payload.locale,
        actor=current_user.get("email", "system"),
    )
    if result.get("error"):
        raise AppError(400, "voucher_error", result["error"])
    return result


@router.get("/vouchers/{booking_id}/download")
async def download_voucher(
    booking_id: str,
    current_user=Depends(require_roles(["admin", "ops", "agent", "super_admin"])),
    db=Depends(get_db),
):
    from app.services.voucher_service import get_voucher_pdf_path
    path = await get_voucher_pdf_path(db, current_user["organization_id"], booking_id)
    if not path:
        raise AppError(404, "voucher_not_found", "Voucher not found. Generate first.")
    return FileResponse(
        path, media_type="application/pdf",
        filename=f"voucher_{booking_id}.pdf",
    )


@router.get("/vouchers")
async def list_vouchers(
    limit: int = Query(50, ge=1, le=200),
    current_user=Depends(require_roles(["admin", "ops", "super_admin"])),
    db=Depends(get_db),
):
    org_id = current_user["organization_id"]
    cursor = db.vouchers.find(
        {"organization_id": org_id, "status": "active"}, {"_id": 0}
    ).sort("generated_at", -1).limit(limit)
    items = await cursor.to_list(limit)
    return {"items": items, "total": len(items)}


# ============================================================================
# Notification delivery endpoints
# ============================================================================

class SendEmailRequest(BaseModel):
    to: str
    subject: str
    html: str
    reply_to: str | None = None


class SendSlackRequest(BaseModel):
    message: str
    webhook_url: str | None = None
    channel: str | None = None


class SendWebhookRequest(BaseModel):
    url: str
    payload: dict
    headers: dict | None = None


@router.post("/notifications/email")
async def send_notification_email(
    payload: SendEmailRequest,
    current_user=Depends(require_roles(["admin", "ops", "super_admin"])),
    db=Depends(get_db),
):
    from app.services.delivery_service import send_email
    return await send_email(
        db, current_user["organization_id"],
        payload.to, payload.subject, payload.html,
        reply_to=payload.reply_to,
    )


@router.post("/notifications/slack")
async def send_notification_slack(
    payload: SendSlackRequest,
    current_user=Depends(require_roles(["admin", "ops", "super_admin"])),
    db=Depends(get_db),
):
    from app.services.delivery_service import send_slack_alert
    return await send_slack_alert(
        db, current_user["organization_id"],
        payload.message, webhook_url=payload.webhook_url, channel=payload.channel,
    )


@router.post("/notifications/webhook")
async def send_notification_webhook(
    payload: SendWebhookRequest,
    current_user=Depends(require_roles(["admin", "ops", "super_admin"])),
    db=Depends(get_db),
):
    from app.services.delivery_service import send_webhook
    return await send_webhook(
        db, current_user["organization_id"],
        payload.url, payload.payload, headers=payload.headers,
    )


@router.get("/notifications/delivery-log")
async def get_notification_delivery_log(
    channel: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    current_user=Depends(require_roles(["admin", "ops", "super_admin"])),
    db=Depends(get_db),
):
    from app.services.delivery_service import get_delivery_log
    items = await get_delivery_log(
        db, current_user["organization_id"],
        channel=channel, status=status, limit=limit,
    )
    return {"items": items, "total": len(items)}


# ============================================================================
# Pipeline status endpoint
# ============================================================================

@router.get("/pipeline/status")
async def get_pipeline_status(
    current_user=Depends(require_roles(["admin", "ops", "super_admin"])),
    db=Depends(get_db),
):
    """Get production pipeline activation status."""
    import redis as redis_lib
    org_id = current_user["organization_id"]

    # Redis health
    redis_status = "unknown"
    try:
        redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
        r = redis_lib.from_url(redis_url, socket_timeout=2)
        r.ping()
        redis_status = "healthy"
    except Exception:
        redis_status = "unhealthy"

    # Supplier status
    supplier_count = await db.rel_supplier_status.count_documents({"organization_id": org_id})
    disabled_count = await db.rel_supplier_status.count_documents({"organization_id": org_id, "status": "disabled"})

    # Voucher count
    voucher_count = await db.vouchers.count_documents({"organization_id": org_id})

    # Notification delivery stats
    pipeline = [
        {"$match": {"organization_id": org_id}},
        {"$group": {"_id": "$status", "count": {"$sum": 1}}},
    ]
    delivery_stats = await db.notification_deliveries.aggregate(pipeline).to_list(10)
    delivery_by_status = {d["_id"]: d["count"] for d in delivery_stats}

    # Incident count
    open_incidents = await db.rel_incidents.count_documents({"organization_id": org_id, "status": "open"})

    return {
        "redis": redis_status,
        "suppliers": {
            "total": supplier_count,
            "disabled": disabled_count,
        },
        "vouchers_generated": voucher_count,
        "notifications": delivery_by_status,
        "open_incidents": open_incidents,
        "rbac_middleware": "active",
        "reliability_pipeline": "wired",
    }


# ============================================================================
# Production Readiness endpoints
# ============================================================================

@router.get("/readiness")
async def get_production_readiness(
    current_user=Depends(require_roles(["admin", "ops", "super_admin"])),
    db=Depends(get_db),
):
    """Get production readiness certification report."""
    from app.services.production_readiness import get_production_readiness as get_readiness
    return await get_readiness(db, current_user["organization_id"])


@router.get("/readiness/tasks")
async def get_production_tasks(
    current_user=Depends(require_roles(["admin", "ops", "super_admin"])),
):
    """Get top 30 production tasks."""
    from app.services.production_readiness import TOP_30_PRODUCTION_TASKS, GO_LIVE_RISK_MATRIX
    return {"tasks": TOP_30_PRODUCTION_TASKS, "risk_matrix": GO_LIVE_RISK_MATRIX}


@router.get("/readiness/secrets")
async def get_secret_inventory(
    current_user=Depends(require_roles(["admin", "super_admin"])),
):
    """Get secret management inventory and migration readiness."""
    from app.domain.governance.secret_migration import get_secret_inventory, get_migration_readiness
    return {
        "inventory": get_secret_inventory(),
        "migration": get_migration_readiness(),
    }


# ============================================================================
# Supplier integration preparation endpoints
# ============================================================================

@router.get("/suppliers/integrations")
async def get_supplier_integrations(
    current_user=Depends(require_roles(["admin", "ops", "super_admin"])),
):
    """Get real supplier integration configs and risk matrix."""
    from app.suppliers.real_integrations import (
        SUPPLIER_CONFIGS, SUPPLIER_RISK_MATRIX, ROLLOUT_ORDER,
    )
    configs = {}
    for code, cfg in SUPPLIER_CONFIGS.items():
        configs[code] = {
            "code": cfg.code, "name": cfg.name,
            "auth_method": cfg.auth_method,
            "rate_limit_rps": cfg.rate_limit_rps,
            "timeout_ms": cfg.timeout_ms,
            "sandbox_mode": cfg.sandbox_mode,
            "is_configured": bool(os.environ.get(cfg.env_key_name)),
        }
    return {
        "suppliers": configs,
        "risk_matrix": SUPPLIER_RISK_MATRIX,
        "rollout_order": ROLLOUT_ORDER,
    }
