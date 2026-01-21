from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

from fastapi import APIRouter, Depends

from app.auth import get_current_user, require_roles
from app.db import get_db
from app.utils import serialize_doc

router = APIRouter(prefix="/api/admin/tours", tags=["admin_tours"])

AdminDep = Depends(require_roles(["super_admin", "admin"]))


@router.get("", dependencies=[AdminDep])
async def list_tours(user=Depends(get_current_user), db=Depends(get_db)) -> List[Dict[str, Any]]:
  org_id = user["organization_id"]
  cursor = db.tours.find({"organization_id": org_id}).sort("created_at", -1)
  docs = await cursor.to_list(length=500)
  items: List[Dict[str, Any]] = []
  for doc in docs:
    items.append(
      {
        "id": str(doc.get("_id")),
        "name": doc.get("name") or "",
        "destination": doc.get("destination") or "",
        "base_price": float(doc.get("base_price") or 0.0),
        "currency": (doc.get("currency") or "EUR").upper(),
        "status": doc.get("status") or "active",
        "created_at": doc.get("created_at"),
      }
    )
  return items


@router.post("", dependencies=[AdminDep])
async def create_tour(payload: Dict[str, Any], user=Depends(get_current_user), db=Depends(get_db)) -> Dict[str, Any]:
  org_id = user["organization_id"]
  now = datetime.now(timezone.utc).isoformat()

  name = (payload.get("name") or "").strip()
  if not name:
    from app.errors import AppError

    raise AppError(400, "invalid_payload", "Tur adı zorunludur")

  destination = (payload.get("destination") or "").strip()
  base_price = float(payload.get("base_price") or 0.0)
  currency = (payload.get("currency") or "EUR").upper()
  status = (payload.get("status") or "active").strip() or "active"

  doc: Dict[str, Any] = {
    "organization_id": org_id,
    "name": name,
    "destination": destination,
    "base_price": base_price,
    "currency": currency,
    "status": status,
    "created_at": now,
  }

  res = await db.tours.insert_one(doc)
  doc["_id"] = res.inserted_id
  return serialize_doc(doc)
