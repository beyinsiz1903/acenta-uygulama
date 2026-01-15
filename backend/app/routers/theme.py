from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, validator

from app.auth import get_current_user, require_roles
from app.db import get_db
from app.utils import now_utc

router = APIRouter(tags=["theme"])


class ThemeBrand(BaseModel):
  company_name: str = Field(..., max_length=200)
  logo_url: Optional[str] = None
  favicon_url: Optional[str] = None


class ThemeColors(BaseModel):
  primary: Optional[str] = None
  primary_foreground: Optional[str] = None
  background: Optional[str] = None
  foreground: Optional[str] = None
  muted: Optional[str] = None
  muted_foreground: Optional[str] = None
  border: Optional[str] = None

  @validator("primary", "primary_foreground", "background", "foreground", "muted", "muted_foreground", "border", pre=True)
  def _validate_hex(cls, v: Optional[str]) -> Optional[str]:  # type: ignore[override]
    if v is None or v == "":
      return None
    if isinstance(v, str) and len(v) == 7 and v.startswith("#"):
      try:
        int(v[1:], 16)
        return v
      except ValueError:
        pass
    raise ValueError("must be hex color like #RRGGBB or null")


class ThemeTypography(BaseModel):
  font_family: Optional[str] = Field(
    default="Inter, system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif",
    max_length=500,
  )


class ThemeAdminIn(BaseModel):
  name: Optional[str] = Field(default="Default Theme", max_length=200)
  brand: ThemeBrand
  colors: ThemeColors
  typography: ThemeTypography


class ThemeAdminOut(ThemeAdminIn):
  status: str
  updated_at: datetime
  updated_by_email: Optional[str]


class ThemePublicOut(BaseModel):
  brand: ThemeBrand
  colors: ThemeColors
  typography: ThemeTypography


DEFAULT_THEME = {
  "name": "Default Theme",
  "brand": {
    "company_name": "Syroce",
    "logo_url": None,
    "favicon_url": None,
  },
  "colors": {
    "primary": "#2563eb",
    "primary_foreground": "#ffffff",
    "background": "#ffffff",
    "foreground": "#0f172a",
    "muted": "#f1f5f9",
    "muted_foreground": "#475569",
    "border": "#e2e8f0",
  },
  "typography": {
    "font_family": "Inter, system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif",
  },
}


async def _get_active_theme_doc(db, organization_id: Optional[str] = None) -> Dict[str, Any]:
  q: Dict[str, Any] = {"status": "active"}
  if organization_id:
    q["organization_id"] = organization_id

  doc = await db.themes.find_one(q)
  if not doc:
    # Fallback: synthesized default theme (not persisted)
    return {
      "organization_id": organization_id,
      "status": "active",
      **DEFAULT_THEME,
      "updated_at": datetime.now(timezone.utc),
      "updated_by_email": None,
    }

  return doc


@router.get("/api/public/theme", response_model=ThemePublicOut)
async def get_public_theme(db=Depends(get_db)) -> ThemePublicOut:
  # Simple strategy: first active theme across orgs; good enough for P1
  doc = await _get_active_theme_doc(db, organization_id=None)
  return ThemePublicOut(
    brand=ThemeBrand(**doc.get("brand", DEFAULT_THEME["brand"])),
    colors=ThemeColors(**(doc.get("colors") or DEFAULT_THEME["colors"])),
    typography=ThemeTypography(**(doc.get("typography") or DEFAULT_THEME["typography"])),
  )


@router.get("/api/admin/theme", response_model=ThemeAdminOut)
async def get_admin_theme(
  db=Depends(get_db),
  user: dict[str, Any] = Depends(require_roles(["super_admin", "admin", "ops"])),
) -> ThemeAdminOut:
  org_id = user["organization_id"]
  doc = await _get_active_theme_doc(db, organization_id=org_id)
  return ThemeAdminOut(
    name=doc.get("name") or DEFAULT_THEME["name"],
    brand=ThemeBrand(**(doc.get("brand") or DEFAULT_THEME["brand"])),
    colors=ThemeColors(**(doc.get("colors") or DEFAULT_THEME["colors"])),
    typography=ThemeTypography(**(doc.get("typography") or DEFAULT_THEME["typography"])),
    status=doc.get("status", "active"),
    updated_at=doc.get("updated_at", now_utc()),
    updated_by_email=doc.get("updated_by_email"),
  )


@router.put("/api/admin/theme", response_model=ThemeAdminOut)
async def upsert_admin_theme(
  payload: ThemeAdminIn,
  db=Depends(get_db),
  user: dict[str, Any] = Depends(require_roles(["super_admin", "admin", "ops"])),
) -> ThemeAdminOut:
  org_id = user["organization_id"]
  email = user.get("email")
  now = now_utc()

  # Upsert active theme for this org
  update_doc = {
    "organization_id": org_id,
    "status": "active",
    "name": payload.name or DEFAULT_THEME["name"],
    "brand": payload.brand.dict(),
    "colors": payload.colors.dict(),
    "typography": payload.typography.dict(),
    "updated_at": now,
    "updated_by_email": email,
  }

  await db.themes.update_one(
    {"organization_id": org_id, "status": "active"},
    {"$set": update_doc, "$setOnInsert": {"created_at": now}},
    upsert=True,
  )

  return ThemeAdminOut(**update_doc)
