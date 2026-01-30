from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel

from app.auth import get_current_user
from app.context_org import get_current_org
from app.services.suppliers.mock_supplier_service import search_mock_offers

router = APIRouter(prefix="/suppliers/mock", tags=["suppliers"])


class MockSearchRequest(BaseModel):
    check_in: str
    check_out: str
    guests: int
    city: str


@router.post("/search", status_code=status.HTTP_200_OK)
async def mock_supplier_search(
    payload: MockSearchRequest,
    user=Depends(get_current_user),  # noqa: ARG001 - auth + scoping
    org=Depends(get_current_org),  # noqa: ARG001 - org scoping only
) -> Dict[str, Any]:
    """Mock supplier search endpoint for Sprint 3 connector gate.

    Auth is enforced via get_current_user/get_current_org; the response is
    deterministic and does not depend on org for now.
    """

    # We pass the original payload for potential future branching, but the
    # current implementation always returns the same two offers.
    return await search_mock_offers(payload.model_dump())
