"""Channel Manager — B2B distribution and partner access control.

Each distribution partner (sub-agency, reseller, affiliate) has:
  - supplier access control (which suppliers they can use)
  - product type permissions (hotel, flight, etc.)
  - pricing tier (affects markup/commission)
  - credit limit
  - approval workflow status

Data model stored in MongoDB: channel_partners collection.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger("suppliers.channel")


class PartnerStatus:
    PENDING = "pending"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    TERMINATED = "terminated"


class PartnerType:
    SUB_AGENCY = "sub_agency"
    RESELLER = "reseller"
    AFFILIATE = "affiliate"
    API_PARTNER = "api_partner"


async def create_partner(
    db,
    organization_id: str,
    partner_data: Dict[str, Any],
) -> Dict[str, Any]:
    """Register a new distribution partner."""
    from app.utils import now_utc
    import uuid

    partner_id = str(uuid.uuid4())
    now = now_utc()

    doc = {
        "_id": partner_id,
        "organization_id": organization_id,
        "partner_id": partner_id,
        "partner_type": partner_data.get("partner_type", PartnerType.SUB_AGENCY),
        "name": partner_data["name"],
        "contact_email": partner_data.get("contact_email", ""),
        "status": PartnerStatus.PENDING,
        # Access control
        "allowed_suppliers": partner_data.get("allowed_suppliers", []),  # empty = all
        "allowed_product_types": partner_data.get("allowed_product_types", []),  # empty = all
        # Pricing
        "pricing_tier": partner_data.get("pricing_tier", "standard"),
        "custom_markup_percentage": partner_data.get("custom_markup_percentage"),
        "commission_rate": partner_data.get("commission_rate", 8.0),
        # Credit
        "credit_limit": partner_data.get("credit_limit", 0),
        "credit_used": 0,
        "credit_currency": partner_data.get("credit_currency", "TRY"),
        # API access
        "api_key": None,
        "api_enabled": False,
        "rate_limit_rpm": partner_data.get("rate_limit_rpm", 60),
        # Metadata
        "created_at": now,
        "updated_at": now,
        "approved_at": None,
        "approved_by": None,
    }

    await db.channel_partners.insert_one(doc)

    # Emit event
    try:
        from app.infrastructure.event_bus import publish
        await publish(
            "partner.created",
            payload={"partner_id": partner_id, "name": doc["name"], "type": doc["partner_type"]},
            organization_id=organization_id,
            source="channel_manager",
        )
    except Exception:
        pass

    return {k: v for k, v in doc.items() if k != "_id"}


async def check_partner_access(
    db,
    organization_id: str,
    partner_id: str,
    supplier_code: str,
    product_type: str,
) -> Dict[str, Any]:
    """Verify if a partner has access to a supplier/product type.

    Returns: {"allowed": bool, "reason": str}
    """
    partner = await db.channel_partners.find_one(
        {"partner_id": partner_id, "organization_id": organization_id},
        {"_id": 0},
    )
    if not partner:
        return {"allowed": False, "reason": "partner_not_found"}

    if partner["status"] != PartnerStatus.ACTIVE:
        return {"allowed": False, "reason": f"partner_status_{partner['status']}"}

    # Check supplier access
    if partner["allowed_suppliers"] and supplier_code not in partner["allowed_suppliers"]:
        return {"allowed": False, "reason": "supplier_not_allowed"}

    # Check product type access
    if partner["allowed_product_types"] and product_type not in partner["allowed_product_types"]:
        return {"allowed": False, "reason": "product_type_not_allowed"}

    # Check credit limit
    if partner["credit_limit"] > 0 and partner["credit_used"] >= partner["credit_limit"]:
        return {"allowed": False, "reason": "credit_limit_exceeded"}

    return {"allowed": True, "reason": "ok", "pricing_tier": partner["pricing_tier"]}


async def list_partners(
    db,
    organization_id: str,
    *,
    status: Optional[str] = None,
    partner_type: Optional[str] = None,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """List all distribution partners for an organization."""
    query: Dict[str, Any] = {"organization_id": organization_id}
    if status:
        query["status"] = status
    if partner_type:
        query["partner_type"] = partner_type

    cursor = db.channel_partners.find(query, {"_id": 0}).sort("created_at", -1).limit(limit)
    return await cursor.to_list(length=limit)


async def approve_partner(
    db,
    organization_id: str,
    partner_id: str,
    approved_by: str,
) -> Dict[str, Any]:
    """Approve a pending partner."""
    from app.utils import now_utc
    import secrets

    now = now_utc()
    api_key = f"sk_partner_{secrets.token_hex(24)}"

    result = await db.channel_partners.update_one(
        {"partner_id": partner_id, "organization_id": organization_id, "status": PartnerStatus.PENDING},
        {
            "$set": {
                "status": PartnerStatus.ACTIVE,
                "approved_at": now,
                "approved_by": approved_by,
                "api_key": api_key,
                "api_enabled": True,
                "updated_at": now,
            }
        },
    )
    if result.modified_count == 0:
        return {"error": "partner_not_found_or_not_pending"}

    return {"partner_id": partner_id, "status": PartnerStatus.ACTIVE, "api_key": api_key}


async def update_partner_credit(
    db,
    organization_id: str,
    partner_id: str,
    amount: float,
) -> Dict[str, Any]:
    """Adjust partner credit usage (positive = charge, negative = credit back)."""
    from app.utils import now_utc
    result = await db.channel_partners.update_one(
        {"partner_id": partner_id, "organization_id": organization_id},
        {
            "$inc": {"credit_used": amount},
            "$set": {"updated_at": now_utc()},
        },
    )
    if result.modified_count == 0:
        return {"error": "partner_not_found"}
    return {"partner_id": partner_id, "credit_adjusted": amount}
