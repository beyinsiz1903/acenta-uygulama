from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends, Request

from app.auth import get_current_user
from app.db import get_db
from app.metrics import METRIC_BOOKINGS_CREATED, METRIC_USERS_CREATED
from app.request_context import get_request_context
from app.services.limits_service import LimitsService
from app.services.usage_service import UsageService
import os

router = APIRouter(prefix="/api/dev", tags=["dev_saas"], include_in_schema=False)


def _ensure_dev_mode() -> None:
    from app.errors import AppError

    flag = os.environ.get("DEV_MODE", "false").lower()
    enabled = flag in ("1", "true", "yes", "on")
    if not enabled:
        raise AppError(
            status_code=403,
            code="dev_mode_disabled",
            message="Developer endpoints are disabled.",
            details=None,
        )


@router.post("/users/create")
async def dev_create_user(request: Request, user: Dict[str, Any] = Depends(get_current_user)):
    """Dev-only user create that exercises max_users limit.

    This is NOT for production use. It simply inserts a dummy user for the
    caller's organization after enforcing max_users.
    """

    _ensure_dev_mode()
    db = await get_db()

    org_id = str(user["organization_id"])

    limits = LimitsService(db)
    await limits.enforce_max_users(org_id)

    # Insert a minimal dummy user for testing
    doc = {
        "email": f"dummy+{org_id}@example.com",
        "name": "Dummy User",
        "organization_id": org_id,
        "status": "active",
    }
    await db.users.insert_one(doc)

    usage = UsageService(db)
    await usage.log(METRIC_USERS_CREATED, org_id, tenant_id=None, value=1)

    return {"ok": True}


@router.post("/dummy-bookings/create")
async def dev_create_dummy_booking(request: Request, user: Dict[str, Any] = Depends(get_current_user)):
    """Dev-only dummy booking create to exercise booking limit.

    No real booking is created; we only enforce limits and log usage.
    """

    _ensure_dev_mode()

    ctx = get_request_context(required=True)

    db = await get_db()
    limits = LimitsService(db)
    await limits.enforce_booking_limit(ctx)

    usage = UsageService(db)
    await usage.log(METRIC_BOOKINGS_CREATED, ctx.org_id, tenant_id=ctx.tenant_id, value=1)

    return {"ok": True}
