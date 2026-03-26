"""Supplier Aggregator Router — Unified search across all connected suppliers.

Provides a single endpoint for searching products (hotels, tours, flights, etc.)
across multiple suppliers simultaneously.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Body
from typing import Any

from app.db import get_db
from app.auth import require_roles

router = APIRouter(prefix="/api/supplier-aggregator", tags=["supplier_aggregator"])


@router.post("/search")
async def unified_search(
    payload: dict = Body(...),
    current_user=Depends(require_roles(["admin", "super_admin", "agency_admin"])),
    db=Depends(get_db),
) -> dict[str, Any]:
    """Unified search across all connected suppliers.

    Body:
        product_type: "hotel" | "tour" | "flight" | "transfer" | "activity"
        suppliers: optional list of specific suppliers to search
        ... search params (checkin, checkout, destination, etc.)
    """
    from app.suppliers.supplier_aggregator import aggregated_search

    org_id = current_user.get("organization_id", current_user.get("org_id", ""))
    product_type = payload.pop("product_type", "hotel")
    suppliers = payload.pop("suppliers", None)

    return await aggregated_search(db, org_id, product_type, payload, suppliers)


@router.get("/capabilities")
async def get_capabilities(
    current_user=Depends(require_roles(["admin", "super_admin", "agency_admin"])),
    db=Depends(get_db),
) -> dict[str, Any]:
    """Get supplier capability matrix for the current agency."""
    from app.suppliers.supplier_aggregator import get_supplier_capabilities

    org_id = current_user.get("organization_id", current_user.get("org_id", ""))
    return await get_supplier_capabilities(db, org_id)


@router.get("/coverage")
async def get_product_coverage(
    current_user=Depends(require_roles(["admin", "super_admin", "agency_admin"])),
    db=Depends(get_db),
) -> dict[str, Any]:
    """Get product type coverage — which products have connected suppliers."""
    from app.suppliers.supplier_aggregator import get_supplier_capabilities

    org_id = current_user.get("organization_id", current_user.get("org_id", ""))
    caps = await get_supplier_capabilities(db, org_id)
    return {
        "product_coverage": caps.get("product_coverage", {}),
        "total_connected": caps.get("total_connected", 0),
    }
