from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.auth import get_current_user, require_roles
from app.db import get_db
from app.utils import now_utc, serialize_doc


router = APIRouter(prefix="/api/agency", tags=["agency-payment-settings"])


class OfflinePaymentSettingsIn(BaseModel):
  enabled: bool = Field(default=False)
  account_name: str = Field(default="")
  bank_name: Optional[str] = None
  iban: str = Field(default="")
  swift: Optional[str] = None
  currency: str = Field(default="TRY")
  default_due_days: int = Field(default=2, ge=0, le=365)
  note_template: Optional[str] = Field(default="Rezervasyon: {reference_code}")


class AgencyPaymentSettingsIn(BaseModel):
  offline: OfflinePaymentSettingsIn


async def _get_or_404_settings(db, org_id: Any, agency_id: Any) -> dict:
  doc = await db.agency_payment_settings.find_one(
    {"organization_id": org_id, "agency_id": agency_id}
  )
  if not doc:
    raise HTTPException(
      status_code=404,
      detail={
        "code": "AGENCY_SETTINGS_NOT_FOUND",
        "message": "Ödeme ayarları bulunamadı.",
      },
    )
  return doc


@router.get(
  "/payment-settings",
  dependencies=[Depends(require_roles(["agency_admin", "agency_agent"]))],
)
async def get_agency_payment_settings(user=Depends(get_current_user)):
  db = await get_db()
  org_id = user["organization_id"]
  agency_id = user.get("agency_id")
  if not agency_id:
    raise HTTPException(status_code=400, detail="USER_NOT_IN_AGENCY")

  doc = await db.agency_payment_settings.find_one(
    {"organization_id": org_id, "agency_id": agency_id}
  )
  if not doc:
    raise HTTPException(
      status_code=404,
      detail={
        "code": "AGENCY_SETTINGS_NOT_FOUND",
        "message": "Ödeme ayarları bulunamadı.",
      },
    )

  return serialize_doc(doc)


@router.put(
  "/payment-settings",
  dependencies=[Depends(require_roles(["agency_admin"]))],
)
async def upsert_agency_payment_settings(
  payload: AgencyPaymentSettingsIn, user=Depends(get_current_user)
):
  db = await get_db()
  org_id = user["organization_id"]
  agency_id = user.get("agency_id")
  if not agency_id:
    raise HTTPException(status_code=400, detail="USER_NOT_IN_AGENCY")

  body = payload.model_dump()

  # Normalize IBAN (remove spaces, upper-case)
  offline = body.get("offline") or {}
  raw_iban = (offline.get("iban") or "").replace(" ", "").strip()
  if raw_iban:
    offline["iban"] = raw_iban.upper()
  body["offline"] = offline

  # Upsert document
  now = now_utc()
  update_doc = {
    "organization_id": org_id,
    "agency_id": agency_id,
    **body,
    "updated_at": now,
  }

  await db.agency_payment_settings.update_one(
    {"organization_id": org_id, "agency_id": agency_id},
    {"$set": update_doc, "$setOnInsert": {"created_at": now}},
    upsert=True,
  )

  saved = await db.agency_payment_settings.find_one(
    {"organization_id": org_id, "agency_id": agency_id}
  )
  return serialize_doc(saved)
