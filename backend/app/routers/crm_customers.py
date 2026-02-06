from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.db import get_db
from app.auth import require_roles
from app.constants.features import FEATURE_CRM
from app.schemas_crm import (
    CustomerCreate,
    CustomerPatch,
    CustomerOut,
    CustomerDetailOut,
    DuplicateCustomerClusterOut,
    CustomerMergeRequest,
    CustomerMergeResultOut,
)
from app.services.crm_customers import (
    create_customer,
    list_customers,
    get_customer_detail_v2,
    patch_customer,
    find_duplicate_customers,
    perform_customer_merge,
)
from app.security.feature_flags import require_tenant_feature


router = APIRouter(prefix="/api/crm/customers", tags=["crm-customers"])

CrmFeatureDep = Depends(require_tenant_feature(FEATURE_CRM))


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

    # Fire-and-forget CRM event (customer created)
    from app.services.crm_events import log_crm_event

    await log_crm_event(
        db,
        org_id,
        entity_type="customer",
        entity_id=customer["id"],
        action="created",
        payload={"fields": list(body.model_fields_set)},
        actor={"id": user_id, "roles": current_user.get("roles") or []},
        source="api",
    )

    return customer


@router.get("/duplicates", response_model=List[DuplicateCustomerClusterOut])
async def http_list_duplicate_customers(
    db=Depends(get_db),
    current_user: dict = Depends(require_roles(["admin", "super_admin"])),
):
    org_id = current_user.get("organization_id")
    clusters = await find_duplicate_customers(db, org_id)
    return clusters


@router.get("/{customer_id}", response_model=CustomerDetailOut)
async def http_get_customer_detail(
    customer_id: str,
    db=Depends(get_db),
    current_user: dict = Depends(require_roles(["agency_agent", "super_admin"])),
):
    org_id = current_user.get("organization_id")
    data = await get_customer_detail_v2(db, org_id, customer_id)
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
    if not updated:
        raise HTTPException(status_code=404, detail="Customer not found")

    # Fire-and-forget CRM event (customer updated)
    from app.services.crm_events import log_crm_event

    await log_crm_event(
        db,
        org_id,
        entity_type="customer",
        entity_id=customer_id,
        action="updated",
        payload={"changed_fields": list(patch_dict.keys())},
        actor={"id": current_user.get("id"), "roles": current_user.get("roles") or []},
        source="api",
    )

    return updated


@router.post("/merge", response_model=CustomerMergeResultOut)
async def http_merge_customers(
    body: CustomerMergeRequest,
    db=Depends(get_db),
    current_user: dict = Depends(require_roles(["admin", "super_admin"])),
):
    org_id = current_user.get("organization_id")
    user_id = current_user.get("id") or "system"

    try:
        result = await perform_customer_merge(
            db,
            org_id,
            primary_id=body.primary_id,
            duplicate_ids=body.duplicate_ids,
            dry_run=body.dry_run,
            merged_by_user_id=user_id,
        )

        # Only log event for real merges (not dry-run)
        if not body.dry_run:
            from app.services.crm_events import log_crm_event

            await log_crm_event(
                db,
                org_id,
                entity_type="customer_merge",
                entity_id=body.primary_id,
                action="merged",
                payload={
                    "primary_id": result["primary_id"],
                    "merged_ids": result.get("merged_ids", []),
                    "skipped_ids": result.get("skipped_ids", []),
                    "rewired": result.get("rewired", {}),
                },
                actor={"id": user_id, "roles": current_user.get("roles") or []},
                source="api",
            )
    except ValueError as exc:
        msg = str(exc)
        if msg == "primary_id is required":
            raise HTTPException(status_code=400, detail="primary_id_required")
        if msg == "primary_customer_not_found":
            raise HTTPException(status_code=404, detail="primary_customer_not_found")
        if msg == "customer_merge_conflict":
            raise HTTPException(status_code=409, detail="customer_merge_conflict")
        raise HTTPException(status_code=400, detail="merge_failed")

    return result
