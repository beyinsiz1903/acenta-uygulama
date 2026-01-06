from __future__ import annotations

from fastapi import APIRouter, Depends

from app.auth import get_current_user, require_roles
from app.db import get_db
from app.errors import AppError
from app.schemas_b2b_quotes import QuoteCreateRequest, QuoteCreateResponse
from app.services.b2b_pricing import B2BPricingService

router = APIRouter(prefix="/api/b2b", tags=["b2b-quotes"])


def get_pricing_service(db=Depends(get_db)) -> B2BPricingService:
    return B2BPricingService(db)


@router.post("/quotes", response_model=QuoteCreateResponse, dependencies=[Depends(require_roles(["agency_agent", "agency_admin"]))])
async def create_b2b_quote(
    payload: QuoteCreateRequest,
    user=Depends(get_current_user),
    pricing: B2BPricingService = Depends(get_pricing_service),
):
    org_id = user.get("organization_id")
    agency_id = user.get("agency_id")
    if not agency_id:
        raise AppError(403, "forbidden", "User is not bound to an agency")

    quote = await pricing.create_quote(
        organization_id=org_id,
        agency_id=agency_id,
        channel_id=payload.channel_id,
        payload=payload,
        requested_by_email=user.get("email"),
    )
    return quote
