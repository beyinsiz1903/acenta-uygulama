from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from fastapi import status

from app.errors import AppError
from app.utils import now_utc
# For v1 we do not call real supplier APIs; mapping is deterministic from external_ref.


@dataclass
class SupplierOfferRef:
    supplier: str
    supplier_offer_id: str
    raw: Dict[str, Any]


async def resolve_listing_supplier(listing: Dict[str, Any], organization_id: str) -> SupplierOfferRef:
    """Resolve supplier offer for a marketplace listing.

    V1: only supports mock_supplier_v1 using resolve_mock_offer.
    """
    supplier_info = (listing.get("supplier") or {})
    name = (supplier_info.get("name") or "").strip()
    external_ref = (supplier_info.get("external_ref") or "").strip()

    if not name:
        raise AppError(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            code="SUPPLIER_NOT_SUPPORTED",
            message="supplier.name is required for supplier mapping",
            details={"reason": "missing_name"},
        )

    if name != "mock_supplier_v1":
        raise AppError(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            code="SUPPLIER_NOT_SUPPORTED",
            message=f"Supplier '{name}' is not supported in v1.",
            details={"supplier": name},
        )

    if not external_ref:
        raise AppError(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            code="LISTING_SUPPLIER_REF_REQUIRED",
            message="supplier.external_ref is required for supplier mapping",
            details={"supplier": name},
        )

    try:
        # Mock resolution: deterministic mapping from external_ref
        offer_id = f"MOCK-{external_ref}"
        raw = {"external_ref": external_ref}
        return SupplierOfferRef(supplier=name, supplier_offer_id=offer_id, raw=raw)
    except AppError:
        raise
    except Exception as exc:  # Unexpected adapter errors
        raise AppError(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="SUPPLIER_RESOLVE_FAILED",
            message="Supplier resolve failed due to unexpected error.",
            details={"supplier": name, "reason": str(exc)},
        ) from exc


async def apply_supplier_mapping(db, listing: Dict[str, Any], mapping: SupplierOfferRef) -> Dict[str, Any]:
    """Persist supplier_mapping on listing in a race-safe way.

    Only sets mapping if current status != "resolved".
    """
    listing_id = listing.get("_id")
    if not listing_id:
        return listing

    now = now_utc()
    update_doc = {
        "supplier_mapping": {
            "status": "resolved",
            "resolved_at": now,
            "offer_id": mapping.supplier_offer_id,
            "raw": mapping.raw,
        },
        "updated_at": now,
    }

    await db.marketplace_listings.update_one(
        {"_id": listing_id, "supplier_mapping.status": {"$ne": "resolved"}},
        {"$set": update_doc},
    )

    # Reload latest listing
    updated = await db.marketplace_listings.find_one({"_id": listing_id})
    return updated or listing
