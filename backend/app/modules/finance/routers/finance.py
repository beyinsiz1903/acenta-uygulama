from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends, status

from app.auth import get_current_user
from app.context_org import get_current_org
from app.db import get_db
from app.services.finance_views_service import get_exposure_summary

router = APIRouter(prefix="/finance", tags=["finance"])


@router.get("/exposure", status_code=status.HTTP_200_OK)
async def get_finance_exposure(
    db=Depends(get_db),
    user=Depends(get_current_user),  # noqa: ARG001 - reserved for future auth/roles
    org=Depends(get_current_org),
) -> Dict[str, Any]:
    organization_id = str(org["id"])
    summary = await get_exposure_summary(db, organization_id)
    return summary
