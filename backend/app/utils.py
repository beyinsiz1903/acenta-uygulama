from __future__ import annotations

import csv
import io
import os
import secrets
import string
from datetime import datetime, timezone
from typing import Any, Iterable

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
        "created_at": created_at,
        "updated_at": updated_at,
    }
