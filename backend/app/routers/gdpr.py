"""GDPR/KVKK Compliance Router.

Endpoints for:
- Data export (right to portability)
- Data deletion (right to erasure)
- Consent management
- GDPR request history
"""
from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from app.auth import get_current_user, require_roles
from app.db import get_db
from app.services.gdpr_service import (
    anonymize_user_data,
    delete_user_data,
    export_user_data,
    get_latest_consent,
    get_user_consents,
    record_consent,
)
from app.utils import serialize_doc

router = APIRouter(prefix="/api/gdpr", tags=["gdpr"])


class ConsentRequest(BaseModel):
    consent_type: str = Field(description="marketing|analytics|third_party|data_processing")
    granted: bool


class DataExportRequest(BaseModel):
    target_email: Optional[str] = None  # Admin can export for another user


class DataDeletionRequest(BaseModel):
    target_email: str
    confirm: bool = Field(description="Must be true to proceed")


class AnonymizeRequest(BaseModel):
    target_email: str
    confirm: bool = Field(description="Must be true to proceed")


# --- User endpoints ---

@router.post("/consent")
async def submit_consent(
    payload: ConsentRequest,
    request: Request,
    user=Depends(get_current_user),
):
    """Record a consent decision."""
    ip = request.headers.get("x-forwarded-for", request.client.host if request.client else "")
    ua = request.headers.get("user-agent", "")

    doc = await record_consent(
        user_email=user["email"],
        organization_id=user["organization_id"],
        consent_type=payload.consent_type,
        granted=payload.granted,
        ip_address=ip,
        user_agent=ua,
    )
    return {"status": "ok", "consent": doc}


@router.get("/consents")
async def list_consents(user=Depends(get_current_user)):
    """List all consent records for the current user."""
    return await get_user_consents(user["email"], user["organization_id"])


@router.get("/consents/{consent_type}")
async def get_consent_status(
    consent_type: str,
    user=Depends(get_current_user),
):
    """Get latest consent status for a specific type."""
    doc = await get_latest_consent(user["email"], user["organization_id"], consent_type)
    if not doc:
        return {"consent_type": consent_type, "granted": None, "message": "No consent recorded"}
    return doc


@router.post("/export-my-data")
async def export_my_data(user=Depends(get_current_user)):
    """Export all personal data (GDPR right to portability)."""
    return await export_user_data(user["email"], user["organization_id"])


@router.post("/delete-my-data")
async def request_deletion(
    payload: DataDeletionRequest,
    user=Depends(get_current_user),
):
    """Request deletion of personal data."""
    if not payload.confirm:
        raise HTTPException(status_code=400, detail="Confirm must be true")

    # Users can only delete their own data
    if payload.target_email != user["email"]:
        roles = set(user.get("roles") or [])
        if not roles.intersection({"super_admin"}):
            raise HTTPException(status_code=403, detail="Can only delete own data")

    result = await delete_user_data(
        user_email=payload.target_email,
        organization_id=user["organization_id"],
        requested_by=user["email"],
    )
    return result


# --- Admin endpoints ---

@router.post(
    "/admin/export",
    dependencies=[Depends(require_roles(["super_admin"]))],
)
async def admin_export_user_data(
    payload: DataExportRequest,
    user=Depends(get_current_user),
):
    """Admin: Export data for any user."""
    target = payload.target_email or user["email"]
    return await export_user_data(target, user["organization_id"])


@router.post(
    "/admin/anonymize",
    dependencies=[Depends(require_roles(["super_admin"]))],
)
async def admin_anonymize(
    payload: AnonymizeRequest,
    user=Depends(get_current_user),
):
    """Admin: Anonymize user data."""
    if not payload.confirm:
        raise HTTPException(status_code=400, detail="Confirm must be true")

    result = await anonymize_user_data(
        user_email=payload.target_email,
        organization_id=user["organization_id"],
        requested_by=user["email"],
    )
    return result


@router.get(
    "/admin/requests",
    dependencies=[Depends(require_roles(["super_admin"]))],
)
async def list_gdpr_requests(user=Depends(get_current_user)):
    """Admin: List all GDPR requests."""
    db = await get_db()
    docs = await db.gdpr_requests.find(
        {"organization_id": user["organization_id"]}
    ).sort("created_at", -1).to_list(200)
    return [serialize_doc(d) for d in docs]
