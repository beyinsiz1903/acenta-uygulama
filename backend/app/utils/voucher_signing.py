from __future__ import annotations

import hmac
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from typing import Tuple

from app.utils import now_utc


class VoucherTokenError(Exception):
    """Base class for voucher token errors."""


class VoucherTokenMissing(VoucherTokenError):
    pass


class VoucherTokenInvalid(VoucherTokenError):
    pass


class VoucherTokenExpired(VoucherTokenError):
    pass


DEFAULT_TTL_MINUTES = 60


def _env(name: str, default: str | None = None) -> str | None:
    v = os.environ.get(name)
    if v:
        return v
    return default


def get_voucher_secret() -> str:
    """Return HMAC secret for voucher signing.

    - In production, VOUCHER_SIGNING_SECRET should be set via env.
    - For development, we fall back to a static dev secret to avoid crashes.
    """

    secret = _env("VOUCHER_SIGNING_SECRET")
    if secret:
        return secret

    # Dev fallback – intentionally constant but non-empty.
    # If stricter behavior is desired, set VOUCHER_SIGNING_SECRET in env.
    return "dev-voucher-secret"


def get_voucher_ttl_minutes() -> int:
    raw = _env("VOUCHER_TOKEN_TTL_MINUTES")
    if not raw:
        return DEFAULT_TTL_MINUTES
    try:
        v = int(raw)
        return v if v > 0 else DEFAULT_TTL_MINUTES
    except Exception:
        return DEFAULT_TTL_MINUTES


@dataclass
class VoucherTokenPayload:
    voucher_id: str
    expires_at: datetime

    @property
    def exp_unix(self) -> int:
        return int(self.expires_at.timestamp())


def _compute_signature(secret: str, voucher_id: str, exp_unix: int) -> str:
    payload = f"{voucher_id}.{exp_unix}".encode("utf-8")
    key = secret.encode("utf-8")
    return hmac.new(key, payload, sha256).hexdigest()


def sign_voucher(voucher_id: str, expires_at: datetime | None = None) -> str:
    """Create a compact token for a voucher.

    Token format: "<exp_unix>.<hex_signature>"
    where signature = HMAC_SHA256(secret, f"{voucher_id}.{exp_unix}").
    """

    if expires_at is None:
        now = now_utc()
        ttl_min = get_voucher_ttl_minutes()
        expires_at = now + timedelta(minutes=max(ttl_min, 1))

    payload = VoucherTokenPayload(voucher_id=voucher_id, expires_at=expires_at)
    secret = get_voucher_secret()
    sig = _compute_signature(secret, payload.voucher_id, payload.exp_unix)
    return f"{payload.exp_unix}.{sig}"


def _parse_token(token: str) -> Tuple[int, str]:
    """Parse token into (exp_unix, signature_hex).

    Raises VoucherTokenInvalid if format is incorrect.
    """

    if not token:
        raise VoucherTokenMissing("Missing token")

    # Strict: exactly one dot
    if token.count(".") != 1:
        raise VoucherTokenInvalid("Invalid token format")

    exp_str, sig = token.split(".", 1)
    try:
        exp_unix = int(exp_str)
    except Exception as e:  # pragma: no cover - defensive
        raise VoucherTokenInvalid("Invalid exp in token") from e

    if not sig or len(sig) < 16:  # very small sanity check
        raise VoucherTokenInvalid("Invalid signature in token")

    return exp_unix, sig


def verify_voucher_token(voucher_id: str, token: str, now: datetime | None = None) -> None:
    """Verify voucher token for a given voucher_id.

    - Raises VoucherTokenMissing if token is empty
    - Raises VoucherTokenInvalid if format/signature is invalid
    - Raises VoucherTokenExpired if exp is in the past
    """

    if now is None:
        now = now_utc()
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    exp_unix, sig = _parse_token(token)

    # Expiry check
    now_unix = int(now.timestamp())
    if exp_unix < now_unix:
        raise VoucherTokenExpired("Token expired")

    secret = get_voucher_secret()
    expected_sig = _compute_signature(secret, voucher_id, exp_unix)

    if not hmac.compare_digest(sig, expected_sig):
        raise VoucherTokenInvalid("Signature mismatch")

    # If we reach here, token is valid and not expired.
