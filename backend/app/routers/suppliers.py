from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel

from app.auth import get_current_user
from app.context_org import get_current_org
from app.services.suppliers.mock_supplier_service import search_mock_offers

from fastapi import HTTPException

from app.errors import AppError
from app.services.supplier_search_service import search_paximum_offers


class PaximumSearchRequest(BaseModel):
    checkInDate: str
    checkOutDate: str
    destination: Dict[str, Any]
    rooms: list[Dict[str, Any]]
    nationality: str
    currency: str


router_paximum = APIRouter(prefix="/suppliers/paximum", tags=["suppliers"])


@router_paximum.post("/search", status_code=status.HTTP_200_OK)
async def paximum_supplier_search(
    payload: PaximumSearchRequest,
    user=Depends(get_current_user),  # noqa: ARG001 - auth + scoping
    org=Depends(get_current_org),  # noqa: ARG001 - org scoping only
) -> Dict[str, Any]:
    """Paximum supplier search endpoint for Sprint 3 XML gate.

    - Enforces TRY-only currency (request + response)
    - Delegates to supplier_search_service for upstream call + normalization
    - Relies on global AppError handler for error response shape
    """

    organization_id = str(org["id"])

    try:
        return await search_paximum_offers(organization_id, payload.model_dump())
    except AppError:
        # Let global exception handler map AppError to structured error_response
        raise

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
