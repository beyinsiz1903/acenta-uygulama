"""Cancel Reason Codes Router."""
from __future__ import annotations

from fastapi import APIRouter

from app.constants.cancel_reasons import get_cancel_reasons_list

router = APIRouter(prefix="/api/reference", tags=["cancel-reasons"])


@router.get("/cancel-reasons")
async def list_cancel_reasons(lang: str = "tr"):
    """List all standard cancellation reason codes."""
    return get_cancel_reasons_list(lang)
