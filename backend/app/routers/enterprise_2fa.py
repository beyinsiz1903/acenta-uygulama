"""Enterprise 2FA router (E2.1).

Opt-in TOTP with recovery codes.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.auth import get_current_user
from app.services.totp_service import (
    disable_2fa,
    enable_2fa,
    is_2fa_enabled,
    verify_and_activate_2fa,
)

router = APIRouter(prefix="/api/auth/2fa", tags=["enterprise_2fa"])


class Enable2FAResponse(BaseModel):
    secret: str
    provisioning_uri: str
    recovery_codes: list[str]


class Verify2FARequest(BaseModel):
    otp_code: str


class Disable2FARequest(BaseModel):
    otp_code: str


@router.post("/enable")
async def enable_2fa_endpoint(user=Depends(get_current_user)):
    """Generate TOTP secret and recovery codes. Must verify to activate."""
    user_id = user.get("id") or user.get("email")
    org_id = user.get("organization_id", "")

    # Check if already enabled
    if await is_2fa_enabled(user_id):
        raise HTTPException(status_code=409, detail="2FA is already enabled")

    result = await enable_2fa(user_id, org_id)
    return result


@router.post("/verify")
async def verify_2fa_endpoint(
    payload: Verify2FARequest,
    user=Depends(get_current_user),
):
    """Verify OTP to activate 2FA."""
    user_id = user.get("id") or user.get("email")

    success = await verify_and_activate_2fa(user_id, payload.otp_code)
    if not success:
        raise HTTPException(status_code=401, detail="Invalid OTP code")

    return {"message": "2FA activated successfully", "enabled": True}


@router.post("/disable")
async def disable_2fa_endpoint(
    payload: Disable2FARequest,
    user=Depends(get_current_user),
):
    """Disable 2FA (requires valid OTP)."""
    user_id = user.get("id") or user.get("email")

    success = await disable_2fa(user_id, payload.otp_code)
    if not success:
        raise HTTPException(status_code=401, detail="Invalid OTP code or 2FA not enabled")

    return {"message": "2FA disabled successfully", "enabled": False}


@router.get("/status")
async def get_2fa_status(user=Depends(get_current_user)):
    """Check if 2FA is enabled for current user."""
    user_id = user.get("id") or user.get("email")
    enabled = await is_2fa_enabled(user_id)
    return {"enabled": enabled}
