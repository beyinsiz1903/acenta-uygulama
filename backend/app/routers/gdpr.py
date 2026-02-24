"""GDPR/KVKK Full Compliance Router.

Endpoints for:
- Data export (right to portability) - comprehensive
- Data deletion (right to erasure)
- Consent management (KVKK consent types)
- Data anonymization
- GDPR/KVKK request history
- Data retention policy
- Data processing log (Veri İşleme Kaydı - KVKK Madde 16)
- Consent types reference
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from app.auth import get_current_user, require_roles
from app.db import get_db
from app.services.gdpr_service import (
    KVKK_CONSENT_TYPES,
    anonymize_user_data,
    delete_user_data,
    export_user_data,
    get_data_processing_log,
    get_latest_consent,
    get_retention_policy,
    get_user_consents,
    record_consent,
)
from app.utils import serialize_doc

router = APIRouter(prefix="/api/gdpr", tags=["gdpr"])


class ConsentRequest(BaseModel):
    consent_type: str = Field(description="acik_riza|marketing|analytics|third_party|data_processing|profiling|international_transfer|cookie_essential|cookie_analytics|cookie_marketing")
    granted: bool
    legal_basis: Optional[str] = None
    version: str = "1.0"


class DataExportRequest(BaseModel):
    target_email: Optional[str] = None


class DataDeletionRequest(BaseModel):
    target_email: str
    confirm: bool = Field(description="Must be true to proceed")


class AnonymizeRequest(BaseModel):
    target_email: str
    confirm: bool = Field(description="Must be true to proceed")


# --- Reference endpoints ---

@router.get("/consent-types")
async def list_consent_types():
    """List all KVKK consent types."""
    return {
        "consent_types": [
            {"key": k, "label": v} for k, v in KVKK_CONSENT_TYPES.items()
        ]
    }


@router.get("/retention-policy")
async def get_retention():
    """Get data retention policy (KVKK Madde 7)."""
    return await get_retention_policy()


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
        legal_basis=payload.legal_basis or "",
        version=payload.version,
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
    """Export all personal data (KVKK Madde 11 - Veri taşınabilirliği)."""
    return await export_user_data(user["email"], user["organization_id"])


@router.post("/delete-my-data")
async def request_deletion(
    payload: DataDeletionRequest,
    user=Depends(get_current_user),
):
    """Request deletion of personal data (KVKK Madde 7)."""
    if not payload.confirm:
        raise HTTPException(status_code=400, detail="Onay gereklidir (confirm: true)")

    if payload.target_email != user["email"]:
        roles = set(user.get("roles") or [])
        if not roles.intersection({"super_admin"}):
            raise HTTPException(status_code=403, detail="Sadece kendi verilerinizi silebilirsiniz")

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
    """Admin: Anonymize user data (KVKK anonim hale getirme)."""
    if not payload.confirm:
        raise HTTPException(status_code=400, detail="Onay gereklidir (confirm: true)")

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
    """Admin: List all GDPR/KVKK requests."""
    db = await get_db()
    docs = await db.gdpr_requests.find(
        {"organization_id": user["organization_id"]}
    ).sort("created_at", -1).to_list(200)
    return [serialize_doc(d) for d in docs]


@router.get(
    "/admin/processing-log",
    dependencies=[Depends(require_roles(["super_admin"]))],
)
async def list_processing_log(
    limit: int = 200,
    user=Depends(get_current_user),
):
    """Admin: KVKK Madde 16 - Veri İşleme Envanteri."""
    return await get_data_processing_log(user["organization_id"], limit)
