from __future__ import annotations

from fastapi import APIRouter, Depends

from app.auth import get_current_user
from app.db import get_db
from app.schemas import InventoryUpsertIn
from app.services.inventory import upsert_inventory
from app.utils import serialize_doc

router = APIRouter(prefix="/api/inventory", tags=["inventory"])


@router.post("/upsert", dependencies=[Depends(get_current_user)])
async def upsert(payload: InventoryUpsertIn, user=Depends(get_current_user)):
    result = await upsert_inventory(user["organization_id"], user.get("email"), payload.model_dump())
    return result


@router.get("", dependencies=[Depends(get_current_user)])
async def list_inventory(product_id: str, start: str, end: str, user=Depends(get_current_user)):
    db = await get_db()
    docs = await db.inventory.find(
        {
            "organization_id": user["organization_id"],
            "product_id": product_id,
            "date": {"$gte": start, "$lte": end},
        }
    ).sort("date", 1).to_list(2000)
    return [serialize_doc(d) for d in docs]
