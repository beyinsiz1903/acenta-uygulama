"""Agency-specific pricing and content overrides.

Provides:
- Agency-hotel pricing contracts (pricing overrides)
- Agency-specific content (images, descriptions)
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from app.db import get_db
from app.utils import now_utc

logger = logging.getLogger("agency_contracts")


# ----- Pricing Overrides -----

async def upsert_agency_hotel_contract(
    organization_id: str,
    agency_id: str,
    hotel_id: str,
    pricing: dict[str, Any],
    updated_by: str = "",
) -> dict[str, Any]:
    """Create or update an agency-hotel pricing contract.

    pricing dict can include:
    - markup_percent: float (e.g., 10.0 for 10%)
    - discount_percent: float (e.g., 5.0 for 5% off)
    - fixed_commission: float
    - currency: str
    - room_type_overrides: dict[str, dict] (per room type pricing)
    - season_overrides: list[dict] (seasonal pricing)
    """
    db = await get_db()
    now = now_utc()

    existing = await db.agency_hotel_contracts.find_one({
        "organization_id": organization_id,
        "agency_id": agency_id,
        "hotel_id": hotel_id,
    })

    doc = {
        "organization_id": organization_id,
        "agency_id": agency_id,
        "hotel_id": hotel_id,
        "markup_percent": pricing.get("markup_percent"),
        "discount_percent": pricing.get("discount_percent"),
        "fixed_commission": pricing.get("fixed_commission"),
        "currency": pricing.get("currency", "TRY"),
        "room_type_overrides": pricing.get("room_type_overrides", {}),
        "season_overrides": pricing.get("season_overrides", []),
        "is_active": pricing.get("is_active", True),
        "valid_from": pricing.get("valid_from"),
        "valid_to": pricing.get("valid_to"),
        "updated_at": now,
        "updated_by": updated_by,
    }

    if existing:
        await db.agency_hotel_contracts.update_one(
            {"_id": existing["_id"]},
            {"$set": doc},
        )
        doc["_id"] = existing["_id"]
    else:
        doc["_id"] = str(uuid.uuid4())
        doc["created_at"] = now
        await db.agency_hotel_contracts.insert_one(doc)

    return doc


async def get_agency_hotel_contract(
    organization_id: str,
    agency_id: str,
    hotel_id: str,
) -> Optional[dict[str, Any]]:
    """Get pricing contract for a specific agency-hotel pair."""
    db = await get_db()
    return await db.agency_hotel_contracts.find_one({
        "organization_id": organization_id,
        "agency_id": agency_id,
        "hotel_id": hotel_id,
        "is_active": True,
    })


async def list_agency_contracts(
    organization_id: str,
    agency_id: Optional[str] = None,
    hotel_id: Optional[str] = None,
) -> list[dict[str, Any]]:
    """List pricing contracts with optional filters."""
    db = await get_db()
    query: dict[str, Any] = {"organization_id": organization_id}
    if agency_id:
        query["agency_id"] = agency_id
    if hotel_id:
        query["hotel_id"] = hotel_id

    docs = await db.agency_hotel_contracts.find(query).sort("updated_at", -1).to_list(1000)
    return [{k: v for k, v in d.items()} for d in docs]


async def delete_agency_hotel_contract(
    organization_id: str,
    contract_id: str,
) -> bool:
    result = await (await get_db()).agency_hotel_contracts.delete_one({
        "_id": contract_id,
        "organization_id": organization_id,
    })
    return result.deleted_count > 0


def apply_agency_pricing(
    base_price: float,
    contract: dict[str, Any],
    room_type: str = "",
) -> float:
    """Apply agency-specific pricing to a base price."""
    if not contract:
        return base_price

    # Check room type overrides first
    room_overrides = contract.get("room_type_overrides", {})
    if room_type and room_type in room_overrides:
        override = room_overrides[room_type]
        if "fixed_price" in override:
            return float(override["fixed_price"])
        if "discount_percent" in override:
            return round(base_price * (1 - float(override["discount_percent"]) / 100), 2)

    # Apply markup
    markup = contract.get("markup_percent")
    if markup:
        base_price = round(base_price * (1 + float(markup) / 100), 2)

    # Apply discount
    discount = contract.get("discount_percent")
    if discount:
        base_price = round(base_price * (1 - float(discount) / 100), 2)

    return base_price


# ----- Content Overrides -----

async def upsert_agency_content_override(
    organization_id: str,
    agency_id: str,
    hotel_id: str,
    content: dict[str, Any],
    updated_by: str = "",
) -> dict[str, Any]:
    """Create or update agency-specific content for a hotel.

    content dict can include:
    - display_name: str (custom hotel name)
    - description: str (custom description)
    - images: list[str] (custom image URLs)
    - amenities: list[str] (custom amenity list)
    - star_rating: int (override star rating display)
    - custom_tags: list[str]
    """
    db = await get_db()
    now = now_utc()

    existing = await db.agency_content_overrides.find_one({
        "organization_id": organization_id,
        "agency_id": agency_id,
        "hotel_id": hotel_id,
    })

    doc = {
        "organization_id": organization_id,
        "agency_id": agency_id,
        "hotel_id": hotel_id,
        "display_name": content.get("display_name"),
        "description": content.get("description"),
        "images": content.get("images", []),
        "amenities": content.get("amenities"),
        "star_rating": content.get("star_rating"),
        "custom_tags": content.get("custom_tags", []),
        "is_active": content.get("is_active", True),
        "updated_at": now,
        "updated_by": updated_by,
    }

    if existing:
        await db.agency_content_overrides.update_one(
            {"_id": existing["_id"]},
            {"$set": doc},
        )
        doc["_id"] = existing["_id"]
    else:
        doc["_id"] = str(uuid.uuid4())
        doc["created_at"] = now
        await db.agency_content_overrides.insert_one(doc)

    return doc


async def get_agency_content_override(
    organization_id: str,
    agency_id: str,
    hotel_id: str,
) -> Optional[dict[str, Any]]:
    """Get content override for a specific agency-hotel pair."""
    db = await get_db()
    return await db.agency_content_overrides.find_one({
        "organization_id": organization_id,
        "agency_id": agency_id,
        "hotel_id": hotel_id,
        "is_active": True,
    })


async def list_agency_content_overrides(
    organization_id: str,
    agency_id: Optional[str] = None,
    hotel_id: Optional[str] = None,
) -> list[dict[str, Any]]:
    db = await get_db()
    query: dict[str, Any] = {"organization_id": organization_id}
    if agency_id:
        query["agency_id"] = agency_id
    if hotel_id:
        query["hotel_id"] = hotel_id

    docs = await db.agency_content_overrides.find(query).sort("updated_at", -1).to_list(1000)
    return [{k: v for k, v in d.items()} for d in docs]


def merge_hotel_content(
    base_hotel: dict[str, Any],
    override: Optional[dict[str, Any]],
) -> dict[str, Any]:
    """Merge base hotel data with agency-specific overrides."""
    if not override:
        return base_hotel

    merged = dict(base_hotel)
    if override.get("display_name"):
        merged["name"] = override["display_name"]
    if override.get("description"):
        merged["description"] = override["description"]
    if override.get("images"):
        merged["images"] = override["images"]
    if override.get("amenities"):
        merged["amenities"] = override["amenities"]
    if override.get("star_rating") is not None:
        merged["star_rating"] = override["star_rating"]
    if override.get("custom_tags"):
        merged["custom_tags"] = override["custom_tags"]

    merged["has_agency_override"] = True
    return merged


async def ensure_agency_contract_indexes() -> None:
    db = await get_db()
    try:
        await db.agency_hotel_contracts.create_index(
            [("organization_id", 1), ("agency_id", 1), ("hotel_id", 1)],
            unique=True, name="idx_org_agency_hotel",
        )
        await db.agency_hotel_contracts.create_index(
            [("organization_id", 1), ("agency_id", 1)],
            name="idx_org_agency",
        )
        await db.agency_content_overrides.create_index(
            [("organization_id", 1), ("agency_id", 1), ("hotel_id", 1)],
            unique=True, name="idx_content_org_agency_hotel",
        )
        await db.agency_content_overrides.create_index(
            [("organization_id", 1), ("agency_id", 1)],
            name="idx_content_org_agency",
        )
    except Exception as e:
        logger.warning("Agency contract index creation warning: %s", e)
