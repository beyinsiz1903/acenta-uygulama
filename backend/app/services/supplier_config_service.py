"""Supplier Credential Configuration Service.

Manages sandbox/production credentials for each supplier.
Stores in MongoDB `supplier_credentials` collection.
Credentials are config-driven: when configured, sync uses real API; otherwise simulation.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from app.db import get_db

logger = logging.getLogger("supplier.config")


async def get_supplier_config(supplier: str) -> dict[str, Any] | None:
    """Get supplier configuration (credentials masked)."""
    db = await get_db()
    doc = await db.supplier_credentials.find_one(
        {"supplier": supplier}, {"_id": 0}
    )
    return doc


async def get_all_supplier_configs() -> dict[str, Any]:
    """Get all supplier configurations with masked credentials."""
    db = await get_db()
    configs = {}
    cursor = db.supplier_credentials.find({}, {"_id": 0})
    async for doc in cursor:
        supplier = doc["supplier"]
        configs[supplier] = {
            "supplier": supplier,
            "mode": doc.get("mode", "simulation"),
            "base_url": doc.get("base_url", ""),
            "configured": doc.get("configured", False),
            "last_validated": doc.get("last_validated"),
            "validation_status": doc.get("validation_status", "not_tested"),
            "has_credentials": bool(doc.get("credentials")),
            "updated_at": doc.get("updated_at"),
        }
    return configs


async def set_supplier_config(
    supplier: str,
    base_url: str,
    credentials: dict[str, str],
    mode: str = "sandbox",
) -> dict[str, Any]:
    """Set or update supplier credentials."""
    db = await get_db()
    now = datetime.now(timezone.utc).isoformat()

    doc = {
        "supplier": supplier,
        "base_url": base_url.rstrip("/"),
        "credentials": credentials,
        "mode": mode,
        "configured": True,
        "updated_at": now,
        "validation_status": "pending",
    }

    await db.supplier_credentials.update_one(
        {"supplier": supplier},
        {"$set": doc},
        upsert=True,
    )

    logger.info("Supplier config updated: %s (mode=%s)", supplier, mode)

    return {
        "supplier": supplier,
        "mode": mode,
        "base_url": base_url,
        "configured": True,
        "updated_at": now,
    }


async def remove_supplier_config(supplier: str) -> dict[str, Any]:
    """Remove supplier credentials (revert to simulation)."""
    db = await get_db()
    result = await db.supplier_credentials.delete_one({"supplier": supplier})
    return {
        "supplier": supplier,
        "removed": result.deleted_count > 0,
        "mode": "simulation",
    }


async def get_raw_credentials(supplier: str) -> dict[str, Any] | None:
    """Get raw credentials (internal use only, not exposed via API)."""
    db = await get_db()
    doc = await db.supplier_credentials.find_one(
        {"supplier": supplier}, {"_id": 0}
    )
    if not doc or not doc.get("configured"):
        return None
    return {
        "base_url": doc.get("base_url", ""),
        "credentials": doc.get("credentials", {}),
        "mode": doc.get("mode", "sandbox"),
    }


async def update_validation_status(
    supplier: str, status: str, details: dict[str, Any] | None = None
) -> None:
    """Update the validation status after a sandbox test."""
    db = await get_db()
    update = {
        "validation_status": status,
        "last_validated": datetime.now(timezone.utc).isoformat(),
    }
    if details:
        update["last_validation_details"] = details
    await db.supplier_credentials.update_one(
        {"supplier": supplier},
        {"$set": update},
    )


async def ensure_supplier_config_indexes() -> None:
    """Create indexes for supplier_credentials collection."""
    db = await get_db()
    await db.supplier_credentials.create_index("supplier", unique=True)
