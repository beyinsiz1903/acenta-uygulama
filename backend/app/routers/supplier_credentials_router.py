"""Supplier Credentials Management Router.

Multi-tenant supplier credential CRUD + connection testing.
Agencies manage their own supplier connections (wwtatil, paximum, aviationstack).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Body
from typing import Any

from app.db import get_db
from app.auth import require_roles

router = APIRouter(prefix="/api/supplier-credentials", tags=["supplier_credentials"])


@router.get("/supported")
async def list_supported(
    current_user=Depends(require_roles(["admin", "super_admin", "agency_admin"])),
    db=Depends(get_db),
) -> dict[str, Any]:
    """List all supported supplier integrations."""
    from app.domain.suppliers.supplier_credentials_service import list_supported_suppliers
    return await list_supported_suppliers()


@router.get("/my")
async def get_my_credentials(
    current_user=Depends(require_roles(["admin", "super_admin", "agency_admin"])),
    db=Depends(get_db),
) -> dict[str, Any]:
    """Get all supplier credentials for the current agency."""
    from app.domain.suppliers.supplier_credentials_service import get_agency_credentials
    org_id = current_user.get("organization_id", current_user.get("org_id", ""))
    return await get_agency_credentials(db, org_id)


@router.post("/save")
async def save_credential(
    payload: dict = Body(...),
    current_user=Depends(require_roles(["admin", "super_admin", "agency_admin"])),
    db=Depends(get_db),
) -> dict[str, Any]:
    """Save supplier credentials for the current agency."""
    from app.domain.suppliers.supplier_credentials_service import save_credential as _save
    org_id = current_user.get("organization_id", current_user.get("org_id", ""))
    supplier = payload.get("supplier", "")
    fields = payload.get("fields", {})
    return await _save(db, org_id, supplier, fields)


@router.delete("/{supplier}")
async def delete_credential(
    supplier: str,
    current_user=Depends(require_roles(["admin", "super_admin", "agency_admin"])),
    db=Depends(get_db),
) -> dict[str, Any]:
    """Delete supplier credentials."""
    from app.domain.suppliers.supplier_credentials_service import delete_credential as _del
    org_id = current_user.get("organization_id", current_user.get("org_id", ""))
    return await _del(db, org_id, supplier)


@router.post("/test/{supplier}")
async def test_connection(
    supplier: str,
    current_user=Depends(require_roles(["admin", "super_admin", "agency_admin"])),
    db=Depends(get_db),
) -> dict[str, Any]:
    """Test supplier connection with saved credentials."""
    from app.domain.suppliers.supplier_credentials_service import test_connection as _test
    org_id = current_user.get("organization_id", current_user.get("org_id", ""))
    return await _test(db, org_id, supplier)


# ─── WWTatil-specific endpoints ────────────────────────────────────────────

@router.post("/wwtatil/tours")
async def wwtatil_get_tours(
    current_user=Depends(require_roles(["admin", "super_admin", "agency_admin"])),
    db=Depends(get_db),
) -> dict[str, Any]:
    """Get all tours from wwtatil using agency credentials."""
    from app.domain.suppliers.supplier_credentials_service import get_decrypted_credentials, get_cached_token
    from app.suppliers.adapters.wwtatil_adapter import WWTatilAdapter

    org_id = current_user.get("organization_id", current_user.get("org_id", ""))
    creds = await get_decrypted_credentials(db, org_id, "wwtatil")
    if not creds:
        return {"error": "No wwtatil credentials found. Please configure in Supplier Settings."}

    token = await get_cached_token(db, org_id, "wwtatil")
    if not token:
        auth = await WWTatilAdapter.authenticate(
            creds["base_url"], creds["application_secret_key"], creds["username"], creds["password"]
        )
        if not auth["success"]:
            return {"error": "Auth failed", "details": auth}
        token = auth["token"]

    adapter = WWTatilAdapter(creds["base_url"], token)
    agency_id = int(creds.get("agency_id", 0))
    return await adapter.get_all_tours(agency_id)


@router.post("/wwtatil/search")
async def wwtatil_search_tours(
    payload: dict = Body(...),
    current_user=Depends(require_roles(["admin", "super_admin", "agency_admin"])),
    db=Depends(get_db),
) -> dict[str, Any]:
    """Search tours from wwtatil."""
    from app.domain.suppliers.supplier_credentials_service import get_decrypted_credentials, get_cached_token
    from app.suppliers.adapters.wwtatil_adapter import WWTatilAdapter

    org_id = current_user.get("organization_id", current_user.get("org_id", ""))
    creds = await get_decrypted_credentials(db, org_id, "wwtatil")
    if not creds:
        return {"error": "No wwtatil credentials found."}

    token = await get_cached_token(db, org_id, "wwtatil")
    if not token:
        auth = await WWTatilAdapter.authenticate(
            creds["base_url"], creds["application_secret_key"], creds["username"], creds["password"]
        )
        if not auth["success"]:
            return {"error": "Auth failed", "details": auth}
        token = auth["token"]

    adapter = WWTatilAdapter(creds["base_url"], token)
    agency_id = int(creds.get("agency_id", 0))

    return await adapter.search_tours(
        agency_id=agency_id,
        start_date=payload.get("start_date", ""),
        end_date=payload.get("end_date", ""),
        adult_count=payload.get("adult_count", 2),
        child_count=payload.get("child_count", 0),
        tour_id=payload.get("tour_id"),
        tour_area_id=payload.get("tour_area_id"),
        tour_country_id=payload.get("tour_country_id"),
        detail=payload.get("detail", 0),
    )


@router.post("/wwtatil/basket/add")
async def wwtatil_add_basket(
    payload: dict = Body(...),
    current_user=Depends(require_roles(["admin", "super_admin", "agency_admin"])),
    db=Depends(get_db),
) -> dict[str, Any]:
    """Add item to wwtatil basket."""
    from app.domain.suppliers.supplier_credentials_service import get_decrypted_credentials, get_cached_token
    from app.suppliers.adapters.wwtatil_adapter import WWTatilAdapter

    org_id = current_user.get("organization_id", current_user.get("org_id", ""))
    creds = await get_decrypted_credentials(db, org_id, "wwtatil")
    if not creds:
        return {"error": "No wwtatil credentials found."}

    token = await get_cached_token(db, org_id, "wwtatil")
    if not token:
        auth = await WWTatilAdapter.authenticate(
            creds["base_url"], creds["application_secret_key"], creds["username"], creds["password"]
        )
        if not auth["success"]:
            return {"error": "Auth failed"}
        token = auth["token"]

    adapter = WWTatilAdapter(creds["base_url"], token)
    agency_id = int(creds.get("agency_id", 0))

    return await adapter.add_basket_item(
        agency_id=agency_id,
        reference_number=payload.get("reference_number", ""),
        product_id=payload.get("product_id", 0),
        product_type_id=payload.get("product_type_id", 0),
        product_period_id=payload.get("product_period_id", 0),
        price=payload.get("price", ""),
        currency_code=payload.get("currency_code", "TRY"),
        customers=payload.get("customers", []),
        billing_details=payload.get("billing_details", {}),
    )


@router.post("/wwtatil/booking/create")
async def wwtatil_create_booking(
    payload: dict = Body(...),
    current_user=Depends(require_roles(["admin", "super_admin", "agency_admin"])),
    db=Depends(get_db),
) -> dict[str, Any]:
    """Create booking from wwtatil basket."""
    from app.domain.suppliers.supplier_credentials_service import get_decrypted_credentials, get_cached_token
    from app.suppliers.adapters.wwtatil_adapter import WWTatilAdapter

    org_id = current_user.get("organization_id", current_user.get("org_id", ""))
    creds = await get_decrypted_credentials(db, org_id, "wwtatil")
    if not creds:
        return {"error": "No wwtatil credentials found."}

    token = await get_cached_token(db, org_id, "wwtatil")
    if not token:
        auth = await WWTatilAdapter.authenticate(
            creds["base_url"], creds["application_secret_key"], creds["username"], creds["password"]
        )
        if not auth["success"]:
            return {"error": "Auth failed"}
        token = auth["token"]

    adapter = WWTatilAdapter(creds["base_url"], token)
    agency_id = int(creds.get("agency_id", 0))

    return await adapter.create_booking(
        agency_id=agency_id,
        basket_id=payload.get("basket_id", 0),
        tracking_number=payload.get("tracking_number", ""),
        price=payload.get("price", ""),
    )
