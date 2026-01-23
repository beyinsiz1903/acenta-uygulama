from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.auth import get_current_user, require_roles
from app.db import get_db
from app.utils import serialize_doc

router = APIRouter(prefix="/api/admin/b2b/marketplace", tags=["admin_b2b_marketplace"])


AdminDep = Depends(require_roles(["super_admin", "admin"]))


class ProductAuthorizationUpsertIn(BaseModel):
    partner_id: str = Field(..., min_length=1)
    product_id: str = Field(..., min_length=1)
    is_enabled: bool
    commission_rate: Optional[float] = None


@router.get("", dependencies=[AdminDep])
async def list_partner_product_authorizations(
    partner_id: str = Query(..., description="Partner id (partner_profiles._id)"),
    q: Optional[str] = Query(None, description="Optional free-text filter on product title"),
    type: Optional[str] = Query(None, description="Optional product type filter"),
    status: Optional[str] = Query(None, description="Optional product status filter (active/passive)"),
    db=Depends(get_db),
    user=Depends(get_current_user),
) -> Dict[str, Any]:
    """List products with partner-specific authorization info.

    Semantics (V1):
    - Missing authorization doc => is_enabled=False, commission_rate=None (güvenli varsayılan)
    """

    org_id = user["organization_id"]

    # Ensure partner exists and belongs to organization
    partner = await db.partner_profiles.find_one({"_id": partner_id, "organization_id": org_id})
    if not partner:
        # Also support ObjectId-based ids for safety
        try:
            oid = ObjectId(partner_id)
        except Exception:
            oid = None
        if oid is not None:
            partner = await db.partner_profiles.find_one({"_id": oid, "organization_id": org_id})
    if not partner:
        raise HTTPException(status_code=404, detail="PARTNER_NOT_FOUND")

    # Load products for this org
    prod_filter: Dict[str, Any] = {"organization_id": org_id}
    if type:
        prod_filter["type"] = type
    if status:
        prod_filter["status"] = status
    if q:
        prod_filter["title"] = {"$regex": q, "$options": "i"}

    cursor = db.products.find(prod_filter).sort("created_at", -1)
    products: List[Dict[str, Any]] = await cursor.to_list(length=500)

    if not products:
        return {"items": []}

    product_ids: List[ObjectId] = []
    for p in products:
        pid = p.get("_id")
        if isinstance(pid, ObjectId):
            product_ids.append(pid)
        else:
            try:
                product_ids.append(ObjectId(str(pid)))
            except Exception:
                # keep as-is string id
                pass

    # Load existing authorizations for this partner
    auth_filter: Dict[str, Any] = {"organization_id": org_id, "partner_id": str(partner.get("_id"))}
    if product_ids:
        auth_filter["product_id"] = {"$in": product_ids}

    auth_cursor = db.b2b_product_authorizations.find(auth_filter)
    auth_docs = await auth_cursor.to_list(length=None)

    auth_index: Dict[str, Dict[str, Any]] = {}
    for a in auth_docs:
        pid = a.get("product_id")
        key = str(pid)
        auth_index[key] = a

    items: List[Dict[str, Any]] = []
    for p in products:
        pid = p.get("_id")
        pid_str = str(pid)
        a = auth_index.get(pid_str)
        is_enabled = bool(a.get("is_enabled")) if a else False
        commission = a.get("commission_rate") if a else None

        item = {
            "product_id": pid_str,
            "title": p.get("title") or "Ürün",
            "type": p.get("type") or "hotel",
            "status": p.get("status") or "active",
            "is_enabled": is_enabled,
            "commission_rate": commission,
        }
        items.append(serialize_doc(item))

    return {"items": items}


@router.put("", dependencies=[AdminDep])
async def upsert_partner_product_authorization(
    payload: ProductAuthorizationUpsertIn,
    db=Depends(get_db),
    user=Depends(get_current_user),
) -> Dict[str, Any]:
    """Upsert authorization for a single (partner, product) pair.

    V1 semantics:
    - Missing doc treated as disabled; bu endpoint partner seçimindeki değişiklikleri yazar.
    """

    org_id = user["organization_id"]

    # Validate partner
    partner = await db.partner_profiles.find_one({"_id": payload.partner_id, "organization_id": org_id})
    if not partner:
        try:
            oid = ObjectId(payload.partner_id)
        except Exception:
            oid = None
        if oid is not None:
            partner = await db.partner_profiles.find_one({"_id": oid, "organization_id": org_id})
    if not partner:
        raise HTTPException(status_code=404, detail="PARTNER_NOT_FOUND")

    partner_id_str = str(partner.get("_id"))

    # Validate product
    try:
        product_oid: Any = ObjectId(payload.product_id)
    except Exception:
        product_oid = payload.product_id

    product = await db.products.find_one({"_id": product_oid, "organization_id": org_id})
    if not product:
        raise HTTPException(status_code=404, detail="PRODUCT_NOT_FOUND")

    now = datetime.now(timezone.utc).isoformat()

    update_doc: Dict[str, Any] = {
        "organization_id": org_id,
        "partner_id": partner_id_str,
        "product_id": product.get("_id"),
        "is_enabled": bool(payload.is_enabled),
        "commission_rate": float(payload.commission_rate) if payload.commission_rate is not None else None,
        "updated_at": now,
    }

    await db.b2b_product_authorizations.update_one(
        {
            "organization_id": org_id,
            "partner_id": partner_id_str,
            "product_id": product.get("_id"),
        },
        {"$set": update_doc, "$setOnInsert": {"created_at": now}},
        upsert=True,
    )

    return {"ok": True, "is_enabled": update_doc["is_enabled"], "commission_rate": update_doc["commission_rate"]}
