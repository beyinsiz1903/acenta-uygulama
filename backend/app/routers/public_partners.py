from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr, Field

from app.db import get_db


router = APIRouter(prefix="/api/public/partners", tags=["public_partners"])


class PartnerApplyIn(BaseModel):
  name: str = Field(..., min_length=1, max_length=200)
  email: EmailStr
  message: str = Field("", max_length=2000)
  org: str = Field(..., min_length=1, max_length=64, description="Organization id (tenant)")


@router.post("/apply")
async def partner_apply(payload: PartnerApplyIn, db=Depends(get_db)) -> JSONResponse:
  """Public endpoint for partner application.

  Creates a partner_profiles document with status=pending. Admins can
  review and update via /api/admin/partners.
  """

  now = datetime.now(timezone.utc).isoformat()

  doc: Dict[str, Any] = {
    "organization_id": payload.org,
    "name": payload.name.strip(),
    "contact_email": payload.email,
    "status": "pending",
    "api_key_name": None,
    "default_markup_percent": 0.0,
    "notes": (payload.message or "").strip() or None,
    "source": "public_form",
    "created_at": now,
    "updated_at": now,
  }

  await db.partner_profiles.insert_one(doc)

  return JSONResponse(status_code=200, content={"ok": True})
