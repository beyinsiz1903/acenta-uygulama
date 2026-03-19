"""Webhook Subscription API — Organization-scoped CRUD + delivery history.

Endpoints:
  POST   /api/webhooks/subscriptions             — Create subscription
  GET    /api/webhooks/subscriptions             — List org subscriptions
  GET    /api/webhooks/subscriptions/{id}        — Get subscription (masked secret)
  PUT    /api/webhooks/subscriptions/{id}        — Update subscription
  DELETE /api/webhooks/subscriptions/{id}        — Deactivate subscription
  POST   /api/webhooks/subscriptions/{id}/rotate-secret — Rotate secret
  GET    /api/webhooks/subscriptions/{id}/deliveries   — Delivery history
  GET    /api/webhooks/events                    — List available events
  POST   /api/webhooks/deliveries/{id}/retry     — Manual retry
  GET    /api/webhooks/deliveries                — List deliveries for org
  GET    /api/webhooks/deliveries/failed         — Failed deliveries
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.auth import get_current_user
from app.db import get_db

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


# ── Schemas ──────────────────────────────────────────────────

class CreateSubscriptionRequest(BaseModel):
    target_url: str = Field(..., description="HTTPS endpoint URL")
    subscribed_events: list[str] = Field(..., description="Event types to subscribe to")
    description: str = Field("", description="Optional description")


class UpdateSubscriptionRequest(BaseModel):
    target_url: Optional[str] = None
    subscribed_events: Optional[list[str]] = None
    is_active: Optional[bool] = None
    description: Optional[str] = None


# ── Subscription CRUD ────────────────────────────────────────

@router.post("/subscriptions", summary="Create webhook subscription")
async def create_subscription(
    req: CreateSubscriptionRequest,
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    from app.services.webhook_service import create_subscription as svc_create

    org_id = user.get("organization_id")
    if not org_id:
        raise HTTPException(status_code=400, detail="Organization context required")

    sub, err = await svc_create(
        db,
        organization_id=org_id,
        target_url=req.target_url,
        subscribed_events=req.subscribed_events,
        description=req.description,
        created_by=user.get("email", ""),
    )
    if err:
        raise HTTPException(status_code=400, detail=err)

    return sub


@router.get("/subscriptions", summary="List webhook subscriptions")
async def list_subscriptions(
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    from app.services.webhook_service import list_subscriptions as svc_list

    org_id = user.get("organization_id")
    if not org_id:
        raise HTTPException(status_code=400, detail="Organization context required")

    subs = await svc_list(db, org_id)
    return {"subscriptions": subs, "count": len(subs)}


@router.get("/subscriptions/{subscription_id}", summary="Get webhook subscription")
async def get_subscription(
    subscription_id: str,
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    from app.services.webhook_service import get_subscription as svc_get

    org_id = user.get("organization_id")
    sub = await svc_get(db, subscription_id, org_id)
    if not sub:
        raise HTTPException(status_code=404, detail="Subscription not found")
    return sub


@router.put("/subscriptions/{subscription_id}", summary="Update webhook subscription")
async def update_subscription(
    subscription_id: str,
    req: UpdateSubscriptionRequest,
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    from app.services.webhook_service import update_subscription as svc_update

    org_id = user.get("organization_id")
    updates = req.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    sub, err = await svc_update(db, subscription_id, org_id, updates)
    if err:
        status = 404 if "not found" in err.lower() else 400
        raise HTTPException(status_code=status, detail=err)
    return sub


@router.delete("/subscriptions/{subscription_id}", summary="Deactivate webhook subscription")
async def delete_subscription(
    subscription_id: str,
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    from app.services.webhook_service import delete_subscription as svc_delete

    org_id = user.get("organization_id")
    deleted = await svc_delete(db, subscription_id, org_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Subscription not found")
    return {"status": "deactivated", "subscription_id": subscription_id}


@router.post(
    "/subscriptions/{subscription_id}/rotate-secret",
    summary="Rotate webhook secret",
)
async def rotate_secret(
    subscription_id: str,
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    from app.services.webhook_service import rotate_secret as svc_rotate

    org_id = user.get("organization_id")
    new_secret, err = await svc_rotate(db, subscription_id, org_id)
    if err:
        raise HTTPException(status_code=400, detail=err)
    return {"subscription_id": subscription_id, "new_secret": new_secret}


# ── Events ───────────────────────────────────────────────────

@router.get("/events", summary="List available webhook events")
async def list_events(user=Depends(get_current_user)):
    from app.services.webhook_service import ALLOWED_EVENTS
    return {"events": ALLOWED_EVENTS}


# ── Delivery History ─────────────────────────────────────────

@router.get(
    "/subscriptions/{subscription_id}/deliveries",
    summary="Delivery history for subscription",
)
async def subscription_deliveries(
    subscription_id: str,
    user=Depends(get_current_user),
    db=Depends(get_db),
    limit: int = Query(default=50, le=200),
    status: Optional[str] = Query(default=None),
):
    org_id = user.get("organization_id")

    # Verify subscription belongs to org
    sub = await db.webhook_subscriptions.find_one(
        {"subscription_id": subscription_id, "organization_id": org_id},
        {"_id": 1},
    )
    if not sub:
        raise HTTPException(status_code=404, detail="Subscription not found")

    query = {"subscription_id": subscription_id}
    if status:
        query["status"] = status

    cursor = db.webhook_deliveries.find(
        query, {"_id": 0}
    ).sort("created_at", -1).limit(limit)

    deliveries = await cursor.to_list(limit)
    return {"deliveries": deliveries, "count": len(deliveries)}


@router.get("/deliveries", summary="List deliveries for organization")
async def list_deliveries(
    user=Depends(get_current_user),
    db=Depends(get_db),
    limit: int = Query(default=50, le=200),
    status: Optional[str] = Query(default=None),
    event_type: Optional[str] = Query(default=None),
):
    org_id = user.get("organization_id")
    query: dict = {"organization_id": org_id}
    if status:
        query["status"] = status
    if event_type:
        query["event_type"] = event_type

    cursor = db.webhook_deliveries.find(
        query, {"_id": 0}
    ).sort("created_at", -1).limit(limit)

    deliveries = await cursor.to_list(limit)
    return {"deliveries": deliveries, "count": len(deliveries)}


@router.get("/deliveries/failed", summary="Failed deliveries for organization")
async def failed_deliveries(
    user=Depends(get_current_user),
    db=Depends(get_db),
    limit: int = Query(default=50, le=200),
):
    org_id = user.get("organization_id")
    cursor = db.webhook_deliveries.find(
        {"organization_id": org_id, "status": "failed"},
        {"_id": 0},
    ).sort("created_at", -1).limit(limit)

    deliveries = await cursor.to_list(limit)
    return {"deliveries": deliveries, "count": len(deliveries)}


@router.post("/deliveries/{delivery_id}/retry", summary="Retry a failed delivery")
async def retry_delivery(
    delivery_id: str,
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    org_id = user.get("organization_id")

    delivery = await db.webhook_deliveries.find_one(
        {"delivery_id": delivery_id, "organization_id": org_id},
        {"_id": 0},
    )
    if not delivery:
        raise HTTPException(status_code=404, detail="Delivery not found")

    if delivery["status"] not in ("failed",):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot retry delivery with status '{delivery['status']}'",
        )

    from app.tasks.webhook_tasks import replay_webhook_delivery
    replay_webhook_delivery.apply_async(
        kwargs={"delivery_id": delivery_id},
        queue="webhook_queue",
    )

    return {"status": "replay_queued", "delivery_id": delivery_id}
