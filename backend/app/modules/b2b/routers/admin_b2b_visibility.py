from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query

from app.auth import require_roles
from app.db import get_db
from app.errors import AppError
from app.utils import serialize_doc

router = APIRouter(prefix="/api/admin/b2b/visibility", tags=["admin_b2b_visibility"])

AdminDep = Depends(require_roles(["admin", "super_admin"]))


async def _get_agency(db, org_id: str, agency_id: str) -> Dict[str, Any]:
    """Fetch agency ensuring it belongs to current organization.

    Raises AppError(404) if not found.
    """

    from bson import ObjectId

    q: Dict[str, Any] = {"organization_id": org_id}

    # Allow both string and ObjectId ids
    try:
        oid = ObjectId(agency_id)
        q["_id"] = oid
    except Exception:
        q["_id"] = agency_id

    agency = await db.agencies.find_one(q)
    if not agency:
        raise AppError(404, "agency_not_found", "Agency not found", {"agency_id": agency_id})
    return agency


@router.get("/agencies/{agency_id}/products", dependencies=[AdminDep])
async def list_agency_product_visibility(
    agency_id: str,
    *,
    limit: int = Query(50, ge=1, le=200),
    q: Optional[str] = Query(None, description="Optional free-text filter on product name"),
    user=Depends(require_roles(["admin", "super_admin"])),
    db=Depends(get_db),
) -> Dict[str, Any]:
    """List products and whether they are blocked for the given agency.

    v1 semantics:
    - Uses products.b2b_visibility as a blacklist array of agency_ids
    - If agency id is present in the array, product is considered "blocked"
    """

    org_id = user["organization_id"]
    await _get_agency(db, org_id, agency_id)

    filt: Dict[str, Any] = {"organization_id": org_id, "status": "active"}
    if q:
        filt["name_search"] = {"$regex": q.strip().lower()}

    cursor = (
        db.products.find(
            filt,
            {"_id": 1, "name": 1, "type": 1, "status": 1, "b2b_visibility": 1},
        )
        .sort("created_at", -1)
        .limit(limit)
    )
    docs: List[Dict[str, Any]] = await cursor.to_list(length=limit)

    items: List[Dict[str, Any]] = []
    for doc in docs:
        pid = doc.get("_id")
        name = doc.get("name") or {}
        title = name.get("tr") or name.get("en") or "Ürün"
        vis = doc.get("b2b_visibility") or []
        blocked = False
        if isinstance(vis, list):
            blocked = str(agency_id) in {str(v) for v in vis}

        items.append(
            {
                "id": str(pid),
                "title": title,
                "type": doc.get("type") or "hotel",
                "status": doc.get("status") or "active",
                "blocked": blocked,
            }
        )

    return {"items": [serialize_doc(it) for it in items]}


class VisibilityUpdatePayload(dict):
    """Lightweight body model for visibility toggle.

    Using dict subclass to avoid importing full Pydantic stack here.
    """

    blocked: bool  # type: ignore[assignment]


@router.put("/agencies/{agency_id}/products/{product_id}", dependencies=[AdminDep])
async def update_agency_product_visibility(
    agency_id: str,
    product_id: str,
    payload: Dict[str, Any],
    user=Depends(require_roles(["admin", "super_admin"])),
    db=Depends(get_db),
) -> Dict[str, Any]:
    """Toggle whether a product is blocked for a specific agency.

    - blocked=True  -> add agency_id to products.b2b_visibility (blacklist)
    - blocked=False -> remove agency_id from products.b2b_visibility
    """

    org_id = user["organization_id"]
    await _get_agency(db, org_id, agency_id)

    from bson import ObjectId

    # Resolve product id
    try:
        pid = ObjectId(product_id)
    except Exception:
        pid = product_id

    product = await db.products.find_one({"_id": pid, "organization_id": org_id})
    if not product:
        raise AppError(404, "product_not_found", "Product not found", {"product_id": product_id})

    blocked = bool(payload.get("blocked"))

    if blocked:
        update = {"$addToSet": {"b2b_visibility": str(agency_id)}}
    else:
        update = {"$pull": {"b2b_visibility": str(agency_id)}}

    await db.products.update_one({"_id": pid, "organization_id": org_id}, update)

    return {"ok": True, "blocked": blocked}
