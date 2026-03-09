from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.services.google_sheet_schema_service import get_reservation_writeback_headers
from app.utils import now_utc

SYSTEM_WRITEBACK_RECORD_TYPES = {
    "reservation_created",
    "reservation_cancelled",
    "booking_confirmed",
    "booking_cancelled",
    "booking_amended",
}

INCOMING_RESERVATION_RECORD_TYPES = {
    "incoming_reservation",
    "external_reservation",
    "sheet_reservation",
    "reservation_import",
    "incoming_booking",
}

STATUS_MAP = {
    "new": "pending",
    "pending": "pending",
    "awaiting_confirmation": "pending",
    "confirmed": "confirmed",
    "approved": "confirmed",
    "booked": "confirmed",
    "cancelled": "cancelled",
    "canceled": "cancelled",
    "rejected": "rejected",
}


def _safe_int(value: Any, default: int = 1) -> int:
    try:
        return max(int(float(str(value).replace(",", ".").strip() or default)), 1)
    except Exception:
        return default


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return round(float(str(value).replace(",", ".").strip() or default), 2)
    except Exception:
        return default


def _safe_iso(value: Any) -> str:
    raw = str(value or "").strip()
    if not raw:
        return now_utc().isoformat()
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc).isoformat()
    except Exception:
        return now_utc().isoformat()


def _normalize_status(value: Any) -> str:
    return STATUS_MAP.get(str(value or "pending").strip().casefold(), "pending")


def _normalize_row_payload(record: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "record_type": str(record.get("Kayit Tipi") or "").strip().casefold(),
        "record_id": str(record.get("Kayit ID") or "").strip(),
        "status": _normalize_status(record.get("Durum")),
        "guest_name": str(record.get("Misafir Ad Soyad") or "").strip(),
        "check_in": str(record.get("Giris Tarihi") or "").strip(),
        "check_out": str(record.get("Cikis Tarihi") or "").strip(),
        "pax": _safe_int(record.get("Kisi Sayisi"), 1),
        "room_type": str(record.get("Oda Tipi") or "Standard").strip() or "Standard",
        "total_price": _safe_float(record.get("Tutar"), 0.0),
        "currency": str(record.get("Para Birimi") or "TRY").strip() or "TRY",
        "channel": str(record.get("Kanal") or "google_sheets").strip() or "google_sheets",
        "operation_at": _safe_iso(record.get("Islem Tarihi")),
        "note": str(record.get("Acenta / Not") or "").strip(),
    }


def _row_fingerprint(payload: Dict[str, Any]) -> str:
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _stable_booking_id(source_key: str) -> str:
    digest = hashlib.sha1(source_key.encode("utf-8")).hexdigest()[:24]
    return f"sheet-booking-{digest}"


def _build_sheet_booking_doc(
    connection: Dict[str, Any],
    *,
    source_key: str,
    source_row: int,
    normalized: Dict[str, Any],
) -> Dict[str, Any]:
    created_at = normalized["operation_at"]
    check_in = normalized["check_in"]
    check_out = normalized["check_out"] or check_in
    nights = 1
    if check_in and check_out:
        try:
            start_dt = datetime.fromisoformat(check_in).date()
            end_dt = datetime.fromisoformat(check_out).date()
            nights = max((end_dt - start_dt).days, 1)
        except Exception:
            nights = 1

    total_price = normalized["total_price"]
    currency = normalized["currency"]
    agency_name = connection.get("agency_name") or normalized["note"]

    return {
        "organization_id": connection["organization_id"],
        "tenant_id": connection["hotel_id"],
        "hotel_id": connection["hotel_id"],
        "hotel_name": connection.get("hotel_name") or "-",
        "agency_id": connection.get("agency_id"),
        "agency_name": agency_name,
        "status": normalized["status"],
        "channel": normalized["channel"],
        "source": "google_sheets",
        "sheet_connection_id": connection["_id"],
        "sheet_source_key": source_key,
        "sheet_source_row": source_row,
        "sheet_source_record_id": normalized["record_id"],
        "sheet_record_type": normalized["record_type"],
        "stay": {
            "check_in": check_in,
            "check_out": check_out,
            "nights": nights,
        },
        "occupancy": {
            "adults": normalized["pax"],
            "children": 0,
        },
        "guest": {
            "full_name": normalized["guest_name"] or "Google Sheets Misafiri",
            "email": None,
            "phone": None,
        },
        "guest_name": normalized["guest_name"] or "Google Sheets Misafiri",
        "special_requests": normalized["note"] or None,
        "note_to_hotel": normalized["note"] or None,
        "booking_ref": normalized["record_id"] or source_key,
        "code": normalized["record_id"] or source_key,
        "rate_snapshot": {
            "room_type_name": normalized["room_type"],
            "board": "RO",
            "price": {
                "currency": currency,
                "total": total_price,
                "per_night": round(total_price / max(nights, 1), 2),
                "tax_included": True,
            },
        },
        "gross_amount": total_price,
        "commission_amount": 0.0,
        "net_amount": total_price,
        "currency": currency,
        "payment_status": "pending",
        "created_at": created_at,
        "updated_at": now_utc().isoformat(),
        "created_by": "google_sheets",
        "updated_by": "google_sheets",
    }


async def import_sheet_reservations(
    db,
    connection: Dict[str, Any],
    *,
    headers: List[str],
    rows: List[List[str]],
) -> Dict[str, Any]:
    expected_headers = get_reservation_writeback_headers()
    header_positions = {header: index for index, header in enumerate(headers)}
    missing_headers = [header for header in expected_headers if header not in header_positions]
    summary = {
        "processed": 0,
        "created": 0,
        "updated": 0,
        "cancelled": 0,
        "skipped": 0,
        "errors": [],
        "missing_headers": missing_headers,
    }

    if missing_headers:
        summary["errors"].append(
            {
                "message": f"Rezervasyon importu icin eksik basliklar: {', '.join(missing_headers)}",
            }
        )
        return summary

    for row_number, row in enumerate(rows, start=2):
        record = {
            header: str(row[position]).strip() if position < len(row) else ""
            for header, position in header_positions.items()
            if header in expected_headers
        }
        normalized = _normalize_row_payload(record)
        record_type = normalized["record_type"]
        if not record_type:
            summary["skipped"] += 1
            continue
        if record_type in SYSTEM_WRITEBACK_RECORD_TYPES or record_type not in INCOMING_RESERVATION_RECORD_TYPES:
            summary["skipped"] += 1
            continue
        if not normalized["check_in"]:
            summary["errors"].append({"row": row_number, "message": "Giris Tarihi zorunlu."})
            continue

        summary["processed"] += 1
        source_id = normalized["record_id"] or f"row-{row_number}"
        source_key = f"{connection['_id']}:{connection.get('writeback_tab', 'Rezervasyonlar')}:{source_id}"
        row_key = f"reservation_import|{source_key}"
        fingerprint = _row_fingerprint(normalized)

        existing_marker = await db.sheet_row_fingerprints.find_one(
            {
                "tenant_id": connection["tenant_id"],
                "hotel_id": connection["hotel_id"],
                "row_key": row_key,
            }
        )
        if existing_marker and existing_marker.get("fingerprint") == fingerprint:
            summary["skipped"] += 1
            continue

        await db.sheet_row_fingerprints.update_one(
            {
                "tenant_id": connection["tenant_id"],
                "hotel_id": connection["hotel_id"],
                "row_key": row_key,
            },
            {
                "$set": {
                    "fingerprint": fingerprint,
                    "updated_at": now_utc(),
                },
                "$setOnInsert": {
                    "_id": str(uuid.uuid4()),
                },
            },
            upsert=True,
        )

        booking_id = _stable_booking_id(source_key)
        booking_doc = _build_sheet_booking_doc(
            connection,
            source_key=source_key,
            source_row=row_number,
            normalized=normalized,
        )
        existing_booking = await db.bookings.find_one(
            {"organization_id": connection["organization_id"], "_id": booking_id}
        )

        if existing_booking:
            await db.bookings.update_one(
                {"_id": booking_id},
                {"$set": booking_doc},
            )
            if booking_doc["status"] == "cancelled":
                summary["cancelled"] += 1
            else:
                summary["updated"] += 1
            continue

        insert_doc = {"_id": booking_id, **booking_doc}
        await db.bookings.insert_one(insert_doc)
        summary["created"] += 1

    return summary