from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.auth import require_roles
from app.db import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin/tenants", tags=["tenant-health"])


def _now() -> datetime:
    return datetime.now(timezone.utc)


@router.get("/health")
async def get_tenants_health(
    filter_type: Optional[str] = Query(None, description="Filter: trial_expiring, inactive, overdue"),
    db=Depends(get_db),
    user=Depends(require_roles(["super_admin"])),
):
    """Tenant health panel for super_admin. Returns per-tenant health metrics."""

    tenants = await db.tenants.find({}).to_list(length=500)
    now = _now()
    results = []

    for tenant in tenants:
        tenant_id = str(tenant.get("_id", ""))
        org_id = tenant.get("organization_id", "")

        # Last login (from users collection)
        last_user_login = None
        users = await db.users.find({"organization_id": org_id}).sort("last_login_at", -1).limit(1).to_list(1)
        if users and users[0].get("last_login_at"):
            last_user_login = users[0]["last_login_at"]

        # Last activity (from audit_logs)
        last_activity = None
        audit = await db.audit_logs.find({"organization_id": org_id}).sort("created_at", -1).limit(1).to_list(1)
        if audit:
            last_activity = audit[0].get("created_at")

        # Trial days left
        trial_days_left = None
        sub = await db.subscriptions.find_one({"tenant_id": tenant_id})
        if sub and sub.get("trial_end"):
            trial_end = sub["trial_end"]
            if isinstance(trial_end, str):
                try:
                    trial_end = datetime.fromisoformat(trial_end.replace("Z", "+00:00"))
                except Exception:
                    trial_end = None
            if trial_end:
                delta = (trial_end - now).days
                trial_days_left = max(0, delta)

        # Overdue payments count
        overdue_count = 0
        try:
            overdue_count = await db.reservations.count_documents({
                "organization_id": org_id,
                "status": "pending",
                "created_at": {"$lt": now - timedelta(days=7)},
            })
        except Exception:
            pass

        # Quota ratio (from capabilities)
        quota_ratio = None
        caps = await db.capabilities.find_one({"tenant_id": tenant_id})
        if caps:
            max_items = caps.get("max_products") or caps.get("max_rooms") or 100
            current_count = await db.products.count_documents({"organization_id": org_id})
            quota_ratio = round(current_count / max_items, 2) if max_items > 0 else 0

        entry = {
            "tenant_id": tenant_id,
            "tenant_name": tenant.get("name", ""),
            "organization_id": org_id,
            "status": tenant.get("status", "active"),
            "last_login_at": last_user_login,
            "last_activity_at": last_activity,
            "trial_days_left": trial_days_left,
            "overdue_payments_count": overdue_count,
            "quota_ratio": quota_ratio,
            "onboarding_completed": tenant.get("onboarding_completed", False),
            "created_at": tenant.get("created_at"),
        }

        # Apply filters
        if filter_type == "trial_expiring":
            if trial_days_left is not None and trial_days_left <= 7:
                results.append(entry)
        elif filter_type == "inactive":
            if last_activity is None or (now - last_activity).days > 7:
                results.append(entry)
        elif filter_type == "overdue":
            if overdue_count > 0:
                results.append(entry)
        else:
            results.append(entry)

    return {"items": results, "total": len(results)}
