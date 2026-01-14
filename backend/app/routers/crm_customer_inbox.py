from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.auth import require_roles
from app.db import get_db
from app.schemas_inbox import PaginatedThreadsOut
from app.services.inbox_v2 import list_threads


router = APIRouter(prefix="/api/crm/customers", tags=["crm-customer-inbox"])


@router.get("/{customer_id}/inbox-threads", response_model=PaginatedThreadsOut)
async def http_list_customer_inbox_threads(
    customer_id: str,
    page: int = 1,
    page_size: int = 50,
    db=Depends(get_db),
    current_user: dict = Depends(require_roles(["admin", "super_admin", "ops"])),
):
    """List inbox threads for a given CRM customer.

    - Org scoped
    - Returns PaginatedThreadsOut
    - If customer has no threads, returns empty list (200)
    """

    org_id = current_user.get("organization_id")

    items, total = await list_threads(
        db,
        org_id,
        status=None,
        channel=None,
        customer_id=customer_id,
        q=None,
        page=page,
        page_size=page_size,
    )

    # list_threads already clamps pagination, but we want to echo clamped values
    # back in the response shape; easiest is to trust list_threads' internal clamp
    # and just pass through the requested page/page_size here.
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": min(max(page_size, 1), 200),
    }
