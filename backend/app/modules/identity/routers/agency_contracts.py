"""Agency Contracts Router.

Manages:
- Agency-hotel pricing contracts (overrides)
- Agency-specific content overrides
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from app.auth import get_current_user, require_roles
from app.db import get_db
from app.services.agency_contracts_service import (
    delete_agency_hotel_contract,
    get_agency_hotel_contract,
    list_agency_content_overrides,
    list_agency_contracts,
    upsert_agency_content_override,
    upsert_agency_hotel_contract,
)
from app.services.audit import write_audit_log
from app.utils import serialize_doc

router = APIRouter(prefix="/api/admin/agency-contracts", tags=["agency-contracts"])


class PricingContractIn(BaseModel):
    agency_id: str
    hotel_id: str
    markup_percent: Optional[float] = None
    discount_percent: Optional[float] = None
    fixed_commission: Optional[float] = None
    currency: str = "TRY"
    room_type_overrides: Optional[dict] = None
    season_overrides: Optional[list] = None
    is_active: bool = True
    valid_from: Optional[str] = None
    valid_to: Optional[str] = None


class ContentOverrideIn(BaseModel):
    agency_id: str
    hotel_id: str
    display_name: Optional[str] = None
    description: Optional[str] = None
    images: Optional[list[str]] = None
    amenities: Optional[list[str]] = None
    star_rating: Optional[int] = None
    custom_tags: Optional[list[str]] = None
    is_active: bool = True


# --- Pricing Contracts ---

@router.get(
    "/pricing",
    dependencies=[Depends(require_roles(["super_admin"]))],
)
async def list_pricing_contracts(
    agency_id: Optional[str] = None,
    hotel_id: Optional[str] = None,
    user=Depends(get_current_user),
):
    """List all pricing contracts."""
    return await list_agency_contracts(
        organization_id=user["organization_id"],
        agency_id=agency_id,
        hotel_id=hotel_id,
    )


@router.post(
    "/pricing",
    dependencies=[Depends(require_roles(["super_admin"]))],
)
async def upsert_pricing_contract(
    payload: PricingContractIn,
    request: Request,
    user=Depends(get_current_user),
):
    """Create or update a pricing contract."""
    result = await upsert_agency_hotel_contract(
        organization_id=user["organization_id"],
        agency_id=payload.agency_id,
        hotel_id=payload.hotel_id,
        pricing=payload.model_dump(exclude_none=True),
        updated_by=user.get("email", ""),
    )

    await write_audit_log(
        await get_db(),
        organization_id=user["organization_id"],
        actor={"actor_type": "user", "email": user.get("email"), "roles": user.get("roles")},
        request=request,
        action="agency_contract.upsert",
        target_type="agency_hotel_contract",
        target_id=str(result.get("_id", "")),
        before=None,
        after=result,
    )

    return result


@router.get(
    "/pricing/{agency_id}/{hotel_id}",
    dependencies=[Depends(require_roles(["super_admin"]))],
)
async def get_pricing_contract(
    agency_id: str,
    hotel_id: str,
    user=Depends(get_current_user),
):
    """Get specific pricing contract."""
    doc = await get_agency_hotel_contract(
        organization_id=user["organization_id"],
        agency_id=agency_id,
        hotel_id=hotel_id,
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Contract not found")
    return serialize_doc(doc)


@router.delete(
    "/pricing/{contract_id}",
    dependencies=[Depends(require_roles(["super_admin"]))],
)
async def delete_contract(
    contract_id: str,
    request: Request,
    user=Depends(get_current_user),
):
    """Delete a pricing contract."""
    deleted = await delete_agency_hotel_contract(
        organization_id=user["organization_id"],
        contract_id=contract_id,
    )
    if not deleted:
        raise HTTPException(status_code=404, detail="Contract not found")

    await write_audit_log(
        await get_db(),
        organization_id=user["organization_id"],
        actor={"actor_type": "user", "email": user.get("email"), "roles": user.get("roles")},
        request=request,
        action="agency_contract.delete",
        target_type="agency_hotel_contract",
        target_id=contract_id,
        before=None,
        after=None,
    )

    return {"status": "deleted"}


# --- Content Overrides ---

@router.get(
    "/content",
    dependencies=[Depends(require_roles(["super_admin"]))],
)
async def list_content_overrides(
    agency_id: Optional[str] = None,
    hotel_id: Optional[str] = None,
    user=Depends(get_current_user),
):
    """List all content overrides."""
    return await list_agency_content_overrides(
        organization_id=user["organization_id"],
        agency_id=agency_id,
        hotel_id=hotel_id,
    )


@router.post(
    "/content",
    dependencies=[Depends(require_roles(["super_admin"]))],
)
async def upsert_content_override(
    payload: ContentOverrideIn,
    request: Request,
    user=Depends(get_current_user),
):
    """Create or update a content override."""
    result = await upsert_agency_content_override(
        organization_id=user["organization_id"],
        agency_id=payload.agency_id,
        hotel_id=payload.hotel_id,
        content=payload.model_dump(exclude_none=True),
        updated_by=user.get("email", ""),
    )

    await write_audit_log(
        await get_db(),
        organization_id=user["organization_id"],
        actor={"actor_type": "user", "email": user.get("email"), "roles": user.get("roles")},
        request=request,
        action="agency_content.upsert",
        target_type="agency_content_override",
        target_id=str(result.get("_id", "")),
        before=None,
        after=result,
    )

    return result
