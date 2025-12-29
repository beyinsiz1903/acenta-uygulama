from __future__ import annotations

import csv
import io
import os
import secrets
import string
import hmac
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from typing import Any, Iterable, Tuple

from bson import ObjectId


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def date_to_utc_midnight(date_str: str) -> datetime:
    """Convert YYYY-MM-DD to timezone-aware UTC midnight datetime."""
    y, m, d = date_str.split("-")
    return datetime(int(y), int(m), int(d), tzinfo=timezone.utc)


def serialize_doc(doc: Any) -> Any:
    """Recursively convert MongoDB docs into JSON-serializable structures."""
    if doc is None:
        return None

    if isinstance(doc, ObjectId):
        return str(doc)

    if isinstance(doc, datetime):
        return doc.isoformat()

    if isinstance(doc, list):
        return [serialize_doc(x) for x in doc]

    if isinstance(doc, dict):
        out: dict[str, Any] = {}
        for k, v in doc.items():
            if k == "_id":
                out["id"] = serialize_doc(v)
            else:
                out[k] = serialize_doc(v)
        return out

    return doc


def to_object_id(id_str: str) -> ObjectId:
    return ObjectId(id_str)


def generate_code(prefix: str, length: int = 6) -> str:
    alphabet = string.digits
    return f"{prefix}-{''.join(secrets.choice(alphabet) for _ in range(length))}"


def generate_pnr() -> str:
    return generate_code("PNR", 8)


def generate_voucher_no() -> str:
    yyyymm = datetime.now(timezone.utc).strftime("%Y%m")
    return generate_code(f"VCH-{yyyymm}", 6)


def to_csv(rows: Iterable[dict[str, Any]], fieldnames: list[str]) -> str:
    buff = io.StringIO()
    writer = csv.DictWriter(buff, fieldnames=fieldnames)
    writer.writeheader()
    for r in rows:
        writer.writerow({k: r.get(k, "") for k in fieldnames})
    return buff.getvalue()


def safe_float(v: Any, default: float = 0.0) -> float:
    try:
        return float(v)
    except Exception:
        return default


def safe_int(v: Any, default: int = 0) -> int:
    try:
        return int(v)
    except Exception:
        return default


def date_range_yyyy_mm_dd(start: str, end: str) -> list[str]:
    """Inclusive start, exclusive end (accommodation nights)."""
    from datetime import date, timedelta

    s = date.fromisoformat(start)
    e = date.fromisoformat(end)
    out: list[str] = []
    cur = s
    while cur < e:
        out.append(cur.isoformat())
        cur += timedelta(days=1)
    return out


def require_env(name: str) -> str:
    v = os.environ.get(name)
    if not v:
        raise RuntimeError(f"Missing env var {name}")
    return v



BOOKING_STATUS_LABELS_TR = {
    "confirmed": "Onaylandı",
    "cancelled": "İptal Edildi",
    "completed": "Tamamlandı",
}

BOOKING_STATUS_LABELS_EN = {
    "confirmed": "Confirmed",
    "cancelled": "Cancelled",
    "completed": "Completed",
}


def build_booking_public_view(doc: dict[str, Any]) -> dict[str, Any]:
    """Normalize booking document for drawer/voucher/email use.

    Returns a serializable dict matching BookingPublicView schema.
    """
    if not doc:
        return {}

    booking_id = str(doc.get("_id") or "")
    stay = doc.get("stay") or {}
    occupancy = doc.get("occupancy") or {}
    guest = doc.get("guest") or {}
    rate = doc.get("rate_snapshot") or {}
    price = rate.get("price") or {}

    status_raw = (doc.get("status") or "").lower() or "confirmed"
    status_tr = BOOKING_STATUS_LABELS_TR.get(status_raw, status_raw)
    status_en = BOOKING_STATUS_LABELS_EN.get(status_raw, status_raw.capitalize())

    check_in = stay.get("check_in") or doc.get("check_in") or ""
    check_out = stay.get("check_out") or doc.get("check_out") or ""

    nights = stay.get("nights")
    if nights is None and check_in and check_out:
        try:
            from datetime import date

            d_in = date.fromisoformat(str(check_in)[:10])
            d_out = date.fromisoformat(str(check_out)[:10])
            nights = (d_out - d_in).days
        except Exception:
            nights = None

    room_type = rate.get("room_type_name") or rate.get("room_type_id")
    board_type = rate.get("board")

    total_amount = doc.get("gross_amount")
    if total_amount is None:
        total_amount = price.get("total")

    currency = doc.get("currency") or price.get("currency")

    destination = doc.get("hotel_city") or doc.get("city")

    # Serialize datetime objects to ISO format strings
    created_at = doc.get("created_at")
    if hasattr(created_at, "isoformat"):
        created_at = created_at.isoformat()

    updated_at = doc.get("updated_at")
    if hasattr(updated_at, "isoformat"):
        updated_at = updated_at.isoformat()

    confirmed_at = doc.get("confirmed_at")
    if hasattr(confirmed_at, "isoformat"):
        confirmed_at = confirmed_at.isoformat()

    return {
        "id": booking_id,
        "code": booking_id,
        "status": status_raw,
        "status_tr": status_tr,
        "status_en": status_en,
        "hotel_name": doc.get("hotel_name"),
        "destination": destination,
        "agency_name": doc.get("agency_name"),
        "guest_name": guest.get("full_name") or doc.get("guest_name"),
        "guest_email": guest.get("email"),
        "guest_phone": guest.get("phone"),
        "check_in_date": str(check_in) if check_in else None,
        "check_out_date": str(check_out) if check_out else None,
        "nights": nights,
        "room_type": room_type,
        "board_type": board_type,
        "adults": int(occupancy.get("adults") or 0) if occupancy else None,
        "children": int(occupancy.get("children") or 0) if occupancy else None,
        "total_amount": float(total_amount) if total_amount is not None else None,
        "currency": currency,
        "source": doc.get("source"),
        "payment_status": doc.get("payment_status"),
        "special_requests": doc.get("special_requests"),
        "confirmed_at": confirmed_at,
        "created_at": created_at,
        "updated_at": updated_at,
    }


# ========== FAZ-12.1: Date Range Helpers ==========

from datetime import timedelta
from typing import Optional, Tuple
from pydantic import BaseModel


class DateRangePeriod(BaseModel):
    """Date range period for API responses"""
    start: str  # YYYY-MM-DD
    end: str    # YYYY-MM-DD
    days: int


def parse_date_range(
    start: Optional[str],
    end: Optional[str],
    days: Optional[int],
    default_days: int = 30,
    max_days: int = 365,
) -> Tuple[datetime, datetime, int]:
    """
    Parse date range from query params with backward compatibility.
    
    Priority:
    1. If start or end is provided, use date range (end is inclusive)
    2. Otherwise, use days parameter
    
    Args:
        start: Start date (YYYY-MM-DD, inclusive)
        end: End date (YYYY-MM-DD, inclusive)
        days: Number of days back from now
        default_days: Default if nothing provided
        max_days: Maximum allowed days
        
    Returns:
        (cutoff_date, end_date, actual_days)
    """
    
    # Priority 1: Date range
    if start or end:
        try:
            # Parse start date
            if start:
                start_dt = datetime.strptime(start, "%Y-%m-%d")
                start_dt = start_dt.replace(tzinfo=timezone.utc)
            else:
                # If only end is given, default to 30 days before end
                end_dt_temp = datetime.strptime(end, "%Y-%m-%d") if end else now_utc()
                start_dt = end_dt_temp - timedelta(days=default_days)
                start_dt = start_dt.replace(tzinfo=timezone.utc)
            
            # Parse end date (inclusive, so add 1 day for exclusive upper bound)
            if end:
                end_dt = datetime.strptime(end, "%Y-%m-%d")
                end_dt = end_dt.replace(tzinfo=timezone.utc)
                # Make exclusive (end day included in results)
                end_dt = end_dt + timedelta(days=1)
            else:
                # If only start is given, default to now
                end_dt = now_utc()
            
            # Calculate actual days
            delta = end_dt - start_dt
            actual_days = max(1, delta.days)

            return start_dt, end_dt, actual_days
        except ValueError:
            # Invalid date format, fall back to days
            pass
    
    # Priority 2: Days parameter (backward compatible)
    days_val = days or default_days
    days_val = min(max(days_val, 1), max_days)
    
    end_dt = now_utc()
    start_dt = end_dt - timedelta(days=days_val)
    
    return start_dt, end_dt, days_val


def format_date_range(start: datetime, end: datetime) -> dict:
    """
    Format date range for API response.
    
    Returns:
        {
            "start": "YYYY-MM-DD",
            "end": "YYYY-MM-DD",
            "days": N
        }
    """
    # Adjust end back by 1 day since we made it exclusive
    end_inclusive = end - timedelta(days=1)
    
    delta = end - start
    days = max(1, delta.days)
    
    return {
        "start": start.strftime("%Y-%m-%d"),
        "end": end_inclusive.strftime("%Y-%m-%d"),
        "days": days,
    }

# ========== Voucher signing helpers (tour voucher security) ==========

DEFAULT_VOUCHER_TTL_MINUTES = 60


class VoucherTokenError(Exception):
    """Base class for voucher token errors."""


class VoucherTokenMissing(VoucherTokenError):
    pass


class VoucherTokenInvalid(VoucherTokenError):
    pass


class VoucherTokenExpired(VoucherTokenError):
    pass


@dataclass
class VoucherTokenPayload:
    voucher_id: str
    expires_at: datetime

    @property
    def exp_unix(self) -> int:
        return int(self.expires_at.timestamp())


def _voucher_env(name: str, default: str | None = None) -> str | None:
    v = os.environ.get(name)
    if v:
        return v
    return default


def get_voucher_secret() -> str:
    """Return HMAC secret for voucher signing.

    - In production, VOUCHER_SIGNING_SECRET should be set via env.
    - In development, we fall back to a static dev secret to avoid crashes.
    """

    secret = _voucher_env("VOUCHER_SIGNING_SECRET")
    if secret:
        return secret

    return "dev-voucher-secret"


def get_voucher_ttl_minutes() -> int:
    raw = _voucher_env("VOUCHER_TOKEN_TTL_MINUTES")
    if not raw:
        return DEFAULT_VOUCHER_TTL_MINUTES
    try:
        v = int(raw)
        return v if v > 0 else DEFAULT_VOUCHER_TTL_MINUTES
    except Exception:
        return DEFAULT_VOUCHER_TTL_MINUTES


def _compute_voucher_signature(secret: str, voucher_id: str, exp_unix: int) -> str:
    payload = f"{voucher_id}.{exp_unix}".encode("utf-8")
    key = secret.encode("utf-8")
    return hmac.new(key, payload, sha256).hexdigest()


def sign_voucher(voucher_id: str, expires_at: datetime | None = None) -> str:
    """Create a compact token for a voucher.

    Token format: "<exp_unix>.<hex_signature>" where
    signature = HMAC_SHA256(secret, f"{voucher_id}.{exp_unix}").
    """

    if expires_at is None:
        now = now_utc()
        ttl_min = get_voucher_ttl_minutes()
        from datetime import timedelta as _td

        expires_at = now + _td(minutes=max(ttl_min, 1))

    payload = VoucherTokenPayload(voucher_id=voucher_id, expires_at=expires_at)
    secret = get_voucher_secret()
    sig = _compute_voucher_signature(secret, payload.voucher_id, payload.exp_unix)
    return f"{payload.exp_unix}.{sig}"


def _parse_voucher_token(token: str) -> Tuple[int, str]:
    """Parse token into (exp_unix, signature_hex).

    Raises VoucherTokenInvalid if format is incorrect.
    """

    if not token:
        raise VoucherTokenMissing("Missing token")

    if token.count(".") != 1:
        raise VoucherTokenInvalid("Invalid token format")

    exp_str, sig = token.split(".", 1)
    try:
        exp_unix = int(exp_str)
    except Exception as e:  # pragma: no cover
        raise VoucherTokenInvalid("Invalid exp in token") from e

    if not sig or len(sig) < 16:
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
        from datetime import timezone as _tz

        now = now.replace(tzinfo=_tz.utc)

    exp_unix, sig = _parse_voucher_token(token)

    now_unix = int(now.timestamp())
    if exp_unix < now_unix:
        raise VoucherTokenExpired("Token expired")

    secret = get_voucher_secret()
    expected_sig = _compute_voucher_signature(secret, voucher_id, exp_unix)

    if not hmac.compare_digest(sig, expected_sig):
        raise VoucherTokenInvalid("Signature mismatch")

    # If we reach here, token is valid and not expired.


