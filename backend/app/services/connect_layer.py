from __future__ import annotations

from typing import Any, Optional

from fastapi import HTTPException

from app.services.mock_pms import MockPmsClient
from app.services.pms_client import PmsError, PmsClient


def get_pms_client() -> PmsClient:
    # FAZ-8: swap here to real adapter later
    return MockPmsClient()


def _raise_mapped(err: PmsError) -> None:
    # Standard error mapping
    if err.code in {"PMS_UNAVAILABLE", "TIMEOUT", "DOWN"}:
        raise HTTPException(status_code=503, detail="PMS_UNAVAILABLE")

    if err.code == "NO_INVENTORY":
        raise HTTPException(status_code=409, detail="NO_INVENTORY")

    if err.code == "PRICE_CHANGED":
        raise HTTPException(status_code=409, detail="PRICE_CHANGED")

    if err.code == "NOT_FOUND":
        raise HTTPException(status_code=404, detail="NOT_FOUND")

    # default
    raise HTTPException(status_code=err.http_status or 503, detail=err.code)


async def quote(*, organization_id: str, channel: str, payload: dict[str, Any]) -> dict[str, Any]:
    client = get_pms_client()
    try:
        return await client.quote(organization_id=organization_id, channel=channel, payload=payload)
    except PmsError as e:
        _raise_mapped(e)


async def create_booking(
    *,
    organization_id: str,
    channel: str,
    idempotency_key: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    client = get_pms_client()
    try:
        return await client.create_booking(
            organization_id=organization_id,
            channel=channel,
            idempotency_key=idempotency_key,
            payload=payload,
        )
    except PmsError as e:
        _raise_mapped(e)


async def cancel_booking(
    *,
    organization_id: str,
    channel: str,
    pms_booking_id: str,
    reason: Optional[str] = None,
) -> dict[str, Any]:
    client = get_pms_client()
    try:
        return await client.cancel_booking(
            organization_id=organization_id,
            channel=channel,
            pms_booking_id=pms_booking_id,
            reason=reason,
        )
    except PmsError as e:
        _raise_mapped(e)
