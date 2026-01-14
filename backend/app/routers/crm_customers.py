from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.db import get_db
from app.auth import require_roles
from app.schemas_crm import (
    CustomerCreate,
    CustomerPatch,
    CustomerOut,
    CustomerDetailOut,
    DuplicateCustomerClusterOut,
)
from app.services.crm_customers import (
    create_customer,
    list_customers,
    get_customer_detail,
    patch_customer,
    find_duplicate_customers,
)


router = APIRouter(prefix="/api/crm/customers", tags=["crm-customers"])


class ListResponse(BaseModel):
    items: List[CustomerOut]
    total: int
    page: int
    page_size: int


@router.get("", response_model=ListResponse)
async def http_list_customers(
    search: Optional[str] = None,
    type: Optional[str] = Query(default=None, alias="type"),
    tag: Optional[List[str]] = Query(default=None),
    page: int = 1,
    page_size: int = 25,
    db=Depends(get_db),
    current_user: dict = Depends(require_roles(["agency_agent", "super_admin"])),
):
    org_id = current_user.get("organization_id")
    items, total = await list_customers(
        db,
        org_id,
        search=search,
        cust_type=type,
        tags=tag,
        page=page,
        page_size=page_size,
    )
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.post("", response_model=CustomerOut)
async def http_create_customer(
    body: CustomerCreate,
    db=Depends(get_db),
    current_user: dict = Depends(require_roles(["agency_agent", "super_admin"])),
):
    org_id = current_user.get("organization_id")
    user_id = current_user.get("id")

    customer = await create_customer(db, org_id, user_id, body.model_dump())

    # CRM events will be wired in a later PR (F3.CRM.Events)
    # emit_crm_event(...)

    return customer


@router.get("/{customer_id}", response_model=CustomerDetailOut)
async def http_get_customer_detail(
    customer_id: str,
    db=Depends(get_db),
    current_user: dict = Depends(require_roles(["agency_agent", "super_admin"])),
):
    org_id = current_user.get("organization_id")
    data = await get_customer_detail(db, org_id, customer_id)
    if not data:
        raise HTTPException(status_code=404, detail="Customer not found")
    return data


@router.patch("/{customer_id}", response_model=CustomerOut)
async def http_patch_customer(
    customer_id: str,
    body: CustomerPatch,
    db=Depends(get_db),
    current_user: dict = Depends(require_roles(["agency_agent", "super_admin"])),
):
    org_id = current_user.get("organization_id")

    patch_dict = body.model_dump(exclude_unset=True)
    if not any(v is not None for v in patch_dict.values()):
        raise HTTPException(status_code=400, detail="No fields to update")

    updated = await patch_customer(db, org_id, customer_id, patch_dict)


@router.get("/duplicates", response_model=List[DuplicateCustomerClusterOut])
async def http_list_duplicate_customers(
    db=Depends(get_db),
    current_user: dict = Depends(require_roles(["admin", "super_admin"])),
):
    org_id = current_user.get("organization_id")
    clusters = await find_duplicate_customers(db, org_id)
    return clusters

    if not updated:
        raise HTTPException(status_code=404, detail="Customer not found")

    # CRM events will be wired in a later PR (F3.CRM.Events)
    # emit_crm_event(...)

    return updated
