"""TOTP 2FA service for Enterprise Security (E2.1).

Opt-in 2FA with recovery codes.
"""
from __future__ import annotations

import hashlib
import secrets
import uuid
from typing import Any, Dict, List, Optional, Tuple

import pyotp

from app.db import get_db
from app.utils import now_utc


def _generate_recovery_codes(count: int = 10) -> List[str]:
    """Generate single-use recovery codes."""
    return [secrets.token_hex(4).upper() for _ in range(count)]


def _hash_code(code: str) -> str:
    return hashlib.sha256(code.encode()).hexdigest()


async def enable_2fa(user_id: str, org_id: str) -> Dict[str, Any]:
    """Generate TOTP secret + recovery codes. Does NOT activate yet (needs verify)."""
    db = await get_db()
    secret = pyotp.random_base32()
    recovery_codes = _generate_recovery_codes(10)
    hashed_codes = [_hash_code(c) for c in recovery_codes]

    doc = {
        "_id": str(uuid.uuid4()),
        "user_id": user_id,
        "organization_id": org_id,
        "secret": secret,
        "enabled": False,
        "recovery_codes": hashed_codes,
        "created_at": now_utc(),
        "updated_at": now_utc(),
    }

    # Upsert - one 2FA config per user
    await db.user_2fa.update_one(
        {"user_id": user_id},
        {"$set": doc},
        upsert=True,
    )

    totp = pyotp.TOTP(secret)
    provisioning_uri = totp.provisioning_uri(
        name=user_id,
        issuer_name="Enterprise ERP",
    )

    return {
        "secret": secret,
        "provisioning_uri": provisioning_uri,
        "recovery_codes": recovery_codes,  # Plain text - show once
    }


async def verify_and_activate_2fa(user_id: str, otp_code: str) -> bool:
    """Verify OTP and activate 2FA. Returns True if activated."""
    db = await get_db()
    doc = await db.user_2fa.find_one({"user_id": user_id})
    if not doc or not doc.get("secret"):
        return False

    totp = pyotp.TOTP(doc["secret"])
    if not totp.verify(otp_code, valid_window=1):
        return False

    await db.user_2fa.update_one(
        {"user_id": user_id},
        {"$set": {"enabled": True, "updated_at": now_utc()}},
    )
    return True


async def disable_2fa(user_id: str, otp_code: str) -> bool:
    """Disable 2FA after verifying OTP."""
    db = await get_db()
    doc = await db.user_2fa.find_one({"user_id": user_id})
    if not doc or not doc.get("enabled"):
        return False

    totp = pyotp.TOTP(doc["secret"])
    if not totp.verify(otp_code, valid_window=1):
        return False

    await db.user_2fa.update_one(
        {"user_id": user_id},
        {"$set": {"enabled": False, "secret": None, "recovery_codes": [], "updated_at": now_utc()}},
    )
    return True


async def is_2fa_enabled(user_id: str) -> bool:
    """Check if user has 2FA enabled."""
    db = await get_db()
    doc = await db.user_2fa.find_one({"user_id": user_id})
    return bool(doc and doc.get("enabled"))


async def validate_otp_or_recovery(
    user_id: str, code: str
) -> Tuple[bool, str]:
    """Validate OTP or recovery code during login.
    Returns (success, method) where method is 'totp' or 'recovery'.
    """
    db = await get_db()
    doc = await db.user_2fa.find_one({"user_id": user_id})
    if not doc or not doc.get("enabled") or not doc.get("secret"):
        return False, "none"

    # Try TOTP first
    totp = pyotp.TOTP(doc["secret"])
    if totp.verify(code, valid_window=1):
        return True, "totp"

    # Try recovery code (single-use)
    hashed = _hash_code(code.upper().strip())
    recovery_codes = doc.get("recovery_codes") or []
    if hashed in recovery_codes:
        # Remove used recovery code
        recovery_codes.remove(hashed)
        await db.user_2fa.update_one(
            {"user_id": user_id},
            {"$set": {"recovery_codes": recovery_codes, "updated_at": now_utc()}},
        )
        return True, "recovery"

    return False, "none"
