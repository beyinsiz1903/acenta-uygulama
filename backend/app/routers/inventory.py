from __future__ import annotations

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException

from app.auth import get_current_user
from app.constants.features import FEATURE_INVENTORY
from app.db import get_db
from app.schemas import InventoryBulkUpsertIn, InventoryUpsertIn
from app.security.feature_flags import require_tenant_feature
from app.services.inventory import bulk_upsert_inventory, upsert_inventory
from app.utils import serialize_doc, to_object_id

router = APIRouter(prefix="/api/inventory", tags=["inventory"])

InventoryFeatureDep = Depends(require_tenant_feature(FEATURE_INVENTORY))


def _oid_or_400(id_str: str) -> ObjectId:
    try:
        return to_object_id(id_str)
    except Exception:
        raise HTTPException(status_code=400, detail="Geçersiz id")


@router.post("/upsert", dependencies=[Depends(get_current_user)])
async def upsert(payload: InventoryUpsertIn, user=Depends(get_current_user)):
    try:
        doc = payload.model_dump()
        doc["source"] = doc.get("source") or "local"
        result = await upsert_inventory(user["organization_id"], user.get("email"), doc)
    except ValueError:
        raise HTTPException(status_code=400, detail="Geçersiz veri")
    return result


@router.post("/bulk_upsert", dependencies=[Depends(get_current_user)])
async def bulk_upsert(payload: InventoryBulkUpsertIn, user=Depends(get_current_user)):
    try:
        doc = payload.model_dump()
        doc["source"] = doc.get("source") or "local"
        result = await bulk_upsert_inventory(user["organization_id"], user.get("email"), doc)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return result


@router.get("", dependencies=[Depends(get_current_user)])
async def list_inventory(product_id: str, start: str, end: str, user=Depends(get_current_user)):
    db = await get_db()
    docs = await db.inventory.find(
        {
            "organization_id": user["organization_id"],
            "product_id": _oid_or_400(product_id),
            "date": {"$gte": start, "$lte": end},
        }
    ).sort("date", 1).to_list(2000)
    return [serialize_doc(d) for d in docs]
