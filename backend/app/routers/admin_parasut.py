from __future__ import annotations

from typing import Any, Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException

from app.auth import get_current_user, require_roles
from app.db import get_db
from app.schemas_parasut import (
    ParasutPushInvoiceV1Request,
    ParasutPushLogListResponse,
    ParasutPushStatusResponse,
)
from app.services.parasut_push_invoice_v1 import run_parasut_invoice_push
from app.utils import serialize_doc


router = APIRouter(prefix="/api/admin/finance/parasut", tags=["admin_parasut"])

AdminDep = Depends(require_roles(["super_admin", "admin"]))


@router.post("/push-invoice-v1", response_model=ParasutPushStatusResponse, dependencies=[AdminDep])
async def push_invoice_v1(
    payload: ParasutPushInvoiceV1Request,
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    """Trigger Paraşüt invoice push for a single booking.

    Uses current_user.organization_id; organization_id is NOT accepted from body.
    """

    org_id = user["organization_id"]
    booking_id = payload.booking_id

    # Defensive: ensure booking belongs to this org (404 if not).
    try:
        oid = ObjectId(booking_id)
    except Exception:
        raise HTTPException(status_code=422, detail="INVALID_BOOKING_ID")

    booking = await db.bookings.find_one({"_id": oid, "organization_id": org_id})
    if not booking:
        # Either booking does not exist or belongs to another org; do not leak info.
        raise HTTPException(status_code=404, detail="BOOKING_NOT_FOUND")

    result = await run_parasut_invoice_push(db, organization_id=org_id, booking_id=str(booking_id))

    # Normalise to ParasutPushStatusResponse
    return ParasutPushStatusResponse(
        status=result.get("status"),
        log_id=result.get("log_id", ""),
        parasut_contact_id=result.get("parasut_contact_id"),
        parasut_invoice_id=result.get("parasut_invoice_id"),
        reason=result.get("reason"),
    )


@router.get("/pushes", response_model=ParasutPushLogListResponse, dependencies=[AdminDep])
async def list_parasut_pushes(
    booking_id: Optional[str] = None,
    limit: int = 50,
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    """List recent Paraşüt push log entries for current organization.

    If booking_id is provided, filters by that booking only.
    """

    org_id = user["organization_id"]

    flt: dict[str, Any] = {"organization_id": org_id}
    if booking_id:
        flt["booking_id"] = booking_id

    cursor = (
        db.parasut_push_log.find(flt)
        .sort("created_at", -1)
        .limit(max(1, min(limit, 200)))
    )
    docs = [serialize_doc(d) for d in await cursor.to_list(length=limit)]

    return ParasutPushLogListResponse(items=docs)
