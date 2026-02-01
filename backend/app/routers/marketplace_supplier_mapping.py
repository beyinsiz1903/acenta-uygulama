from __future__ import annotations

from typing import Any, Dict

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.auth import get_current_user
from app.db import get_db
from app.services.supplier_mapping_service import resolve_listing_supplier, apply_supplier_mapping
from app.utils import serialize_doc

router = APIRouter(prefix="/marketplace", tags=["marketplace-supplier-mapping"])


@router.post("/listings/{listing_id}/resolve-supplier")
async def resolve_supplier_for_listing(
    listing_id: str,
    request: Request,
    user=Depends(get_current_user),
) -> Dict[str, Any]:
    """Resolve supplier mapping for a marketplace listing.

    - Idempotent: if already resolved, returns current mapping.
    - V1: only supports mock_supplier_v1.
    """

    db = await get_db()
    org_id = user["organization_id"]

    try:
        oid = ObjectId(listing_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="LISTING_NOT_FOUND")

    listing = await db.marketplace_listings.find_one({"_id": oid, "organization_id": org_id})
    if not listing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="LISTING_NOT_FOUND")

    # If already resolved, return existing mapping
    mapping = (listing.get("supplier_mapping") or {})
    if mapping.get("status") == "resolved":
        return {
            "listing_id": listing_id,
            "status": "resolved",
            "supplier": mapping.get("supplier"),
            "supplier_offer_id": mapping.get("offer_id"),
        }

    # Otherwise resolve via adapter and persist mapping
    offer_ref = await resolve_listing_supplier(listing, organization_id=org_id)
    updated = await apply_supplier_mapping(db, listing, offer_ref)
    new_mapping = (updated.get("supplier_mapping") or {})

    return {
        "listing_id": listing_id,
        "status": new_mapping.get("status"),
        "supplier": offer_ref.supplier,
        "supplier_offer_id": offer_ref.supplier_offer_id,
    }
