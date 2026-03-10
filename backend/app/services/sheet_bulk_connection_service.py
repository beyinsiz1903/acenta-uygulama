from __future__ import annotations

import csv
import io
from typing import Any, Dict, List, Literal, Tuple


BulkConnectionScope = Literal["hotel", "agency"]


HOTEL_TEMPLATE_HEADERS = [
    "hotel_id",
    "sheet_id",
    "sheet_tab",
    "writeback_tab",
    "sync_enabled",
    "sync_interval_minutes",
]

AGENCY_TEMPLATE_HEADERS = [
    "hotel_id",
    "agency_id",
    "sheet_id",
    "sheet_tab",
    "writeback_tab",
    "sync_enabled",
    "sync_interval_minutes",
]


HEADER_ALIASES: Dict[str, List[str]] = {
    "hotel_id": ["hotel_id", "otel_id", "hotelid", "otelid"],
    "agency_id": ["agency_id", "acenta_id", "agencyid", "acentaid"],
    "sheet_id": ["sheet_id", "sheetid", "google_sheet_id", "googlesheetid"],
    "sheet_tab": ["sheet_tab", "sheettab", "tab", "sayfa", "sekme"],
    "writeback_tab": [
        "writeback_tab",
        "writebacktab",
        "rezervasyon_tab",
        "rezervasyonlar_tab",
        "rezervasyon_sekmesi",
    ],
    "sync_enabled": ["sync_enabled", "syncenabled", "otomatik_sync", "auto_sync"],
    "sync_interval_minutes": [
        "sync_interval_minutes",
        "syncintervalminutes",
        "sync_interval",
        "dakika",
        "interval",
    ],
}


def _normalize_key(value: str) -> str:
    return (
        str(value or "")
        .strip()
        .lower()
        .replace("ı", "i")
        .replace("İ", "i")
        .replace("ğ", "g")
        .replace("ü", "u")
        .replace("ş", "s")
        .replace("ö", "o")
        .replace("ç", "c")
        .replace(" ", "_")
        .replace("-", "_")
    )


def get_scope_headers(scope: BulkConnectionScope) -> List[str]:
    return list(HOTEL_TEMPLATE_HEADERS if scope == "hotel" else AGENCY_TEMPLATE_HEADERS)


def render_bulk_connection_template(scope: BulkConnectionScope) -> Dict[str, Any]:
    headers = get_scope_headers(scope)
    sample_row = [
        "hotel_123",
        "sheet_abc123",
        "Sheet1",
        "Rezervasyonlar",
        "true",
        "5",
    ]
    if scope == "agency":
        sample_row.insert(1, "agency_456")

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(headers)
    writer.writerow(sample_row)
    content = buffer.getvalue().encode("utf-8")
    filename = f"syroce_bulk_{scope}_sheet_connections_template.csv"
    return {
        "filename": filename,
        "media_type": "text/csv; charset=utf-8",
        "content": content,
        "headers": headers,
    }



def parse_bulk_text(raw_text: str) -> Tuple[List[str], List[List[str]]]:
    cleaned_lines = [line for line in (raw_text or "").replace("\r\n", "\n").split("\n") if line.strip()]
    if len(cleaned_lines) < 2:
        raise ValueError("En az 1 başlık ve 1 veri satırı gerekli.")

    joined = "\n".join(cleaned_lines)
    delimiter = "\t"
    try:
        dialect = csv.Sniffer().sniff(joined[:2048], delimiters="\t,;")
        delimiter = dialect.delimiter
    except Exception:
        delimiter = "\t" if "\t" in cleaned_lines[0] else ","

    reader = csv.reader(io.StringIO(joined), delimiter=delimiter)
    rows = [[str(cell).strip() for cell in row] for row in reader]
    if len(rows) < 2:
        raise ValueError("En az 1 başlık ve 1 veri satırı gerekli.")

    headers = rows[0]
    data_rows = [row for row in rows[1:] if any(str(cell).strip() for cell in row)]
    return headers, data_rows


def map_bulk_headers(headers: List[str]) -> Dict[int, str]:
    mapping: Dict[int, str] = {}
    alias_to_canonical: Dict[str, str] = {}
    for canonical, aliases in HEADER_ALIASES.items():
        for alias in aliases:
            alias_to_canonical[_normalize_key(alias)] = canonical

    for idx, header in enumerate(headers):
        normalized = _normalize_key(header)
        canonical = alias_to_canonical.get(normalized)
        if canonical:
            mapping[idx] = canonical
    return mapping


def _to_bool(value: Any, default: bool = True) -> bool:
    if value in (None, ""):
        return default
    normalized = _normalize_key(str(value))
    if normalized in {"1", "true", "evet", "yes", "aktif", "on"}:
        return True
    if normalized in {"0", "false", "hayir", "hayır", "no", "pasif", "off"}:
        return False
    return default


def _to_int(value: Any, default: int = 5) -> int:
    if value in (None, ""):
        return default
    try:
        return int(float(str(value).strip().replace(",", ".")))
    except (TypeError, ValueError):
        return default


def normalize_bulk_rows(
    headers: List[str],
    rows: List[List[str]],
    scope: BulkConnectionScope,
) -> List[Dict[str, Any]]:
    index_mapping = map_bulk_headers(headers)
    result: List[Dict[str, Any]] = []
    for row_number, row in enumerate(rows, start=2):
        raw: Dict[str, Any] = {"row_number": row_number}
        for idx, field in index_mapping.items():
            raw[field] = row[idx].strip() if idx < len(row) else ""

        normalized = {
            "row_number": row_number,
            "hotel_id": str(raw.get("hotel_id", "")).strip(),
            "sheet_id": str(raw.get("sheet_id", "")).strip(),
            "sheet_tab": str(raw.get("sheet_tab", "")).strip() or "Sheet1",
            "writeback_tab": str(raw.get("writeback_tab", "")).strip() or "Rezervasyonlar",
            "sync_enabled": _to_bool(raw.get("sync_enabled"), True),
            "sync_interval_minutes": _to_int(raw.get("sync_interval_minutes"), 5),
        }
        if scope == "agency":
            normalized["agency_id"] = str(raw.get("agency_id", "")).strip()
        result.append(normalized)
    return result


async def validate_bulk_connection_rows(
    db,
    *,
    organization_id: str,
    tenant_id: str,
    scope: BulkConnectionScope,
    rows: List[Dict[str, Any]],
) -> Dict[str, Any]:
    hotel_ids = sorted({row.get("hotel_id", "") for row in rows if row.get("hotel_id")})
    agency_ids = sorted({row.get("agency_id", "") for row in rows if row.get("agency_id")})

    hotels = await db.hotels.find(
        {"organization_id": organization_id, "_id": {"$in": hotel_ids}},
        {"_id": 1, "name": 1, "city": 1},
    ).to_list(max(1, len(hotel_ids) or 1))
    hotel_map = {str(hotel.get("_id") or ""): hotel for hotel in hotels}

    agency_map: Dict[str, Dict[str, Any]] = {}
    if scope == "agency" and agency_ids:
        agencies = await db.agencies.find(
            {"organization_id": organization_id, "_id": {"$in": agency_ids}},
            {"_id": 1, "name": 1, "contact_email": 1},
        ).to_list(max(1, len(agency_ids)))
        agency_map = {str(agency.get("_id") or ""): agency for agency in agencies}

    existing_connections = await db.hotel_portfolio_sources.find(
        {
            "tenant_id": tenant_id,
            "hotel_id": {"$in": hotel_ids or [""]},
            "source_type": "google_sheets",
        },
        {"hotel_id": 1, "agency_id": 1},
    ).to_list(5000)
    existing_hotel_ids = {str(doc.get("hotel_id") or "") for doc in existing_connections}
    existing_agency_pairs = {
        (str(doc.get("hotel_id") or ""), str(doc.get("agency_id") or ""))
        for doc in existing_connections
        if doc.get("agency_id")
    }

    valid_rows: List[Dict[str, Any]] = []
    invalid_rows: List[Dict[str, Any]] = []
    seen_keys: set[tuple[str, str]] = set()

    for row in rows:
        row_errors: List[Dict[str, str]] = []
        hotel_id = str(row.get("hotel_id") or "").strip()
        agency_id = str(row.get("agency_id") or "").strip()
        row_key = (hotel_id, agency_id if scope == "agency" else "")

        if not hotel_id:
            row_errors.append({"field": "hotel_id", "message": "hotel_id zorunlu."})
        if not row.get("sheet_id"):
            row_errors.append({"field": "sheet_id", "message": "sheet_id zorunlu."})
        if scope == "agency" and not agency_id:
            row_errors.append({"field": "agency_id", "message": "agency_id zorunlu."})

        if row.get("sync_interval_minutes", 0) <= 0:
            row_errors.append({
                "field": "sync_interval_minutes",
                "message": "sync_interval_minutes 1 veya daha büyük olmalı.",
            })

        hotel = hotel_map.get(hotel_id)
        if hotel_id and hotel is None:
            row_errors.append({"field": "hotel_id", "message": f"Otel bulunamadı: {hotel_id}"})

        agency = None
        if scope == "agency" and agency_id:
            agency = agency_map.get(agency_id)
            if agency is None:
                row_errors.append({"field": "agency_id", "message": f"Acenta bulunamadı: {agency_id}"})

        if row_key in seen_keys:
            duplicate_field = "hotel_id" if scope == "hotel" else "hotel_id+agency_id"
            row_errors.append({"field": duplicate_field, "message": "Dosyada tekrar eden bağlantı satırı var."})
        else:
            seen_keys.add(row_key)

        if scope == "hotel" and hotel_id and hotel_id in existing_hotel_ids:
            row_errors.append({"field": "hotel_id", "message": "Bu otel için zaten bir sheet bağlantısı var."})

        if scope == "agency" and hotel_id and agency_id and (hotel_id, agency_id) in existing_agency_pairs:
            row_errors.append({
                "field": "hotel_id+agency_id",
                "message": "Bu otel-acenta ikilisi için zaten bir sheet bağlantısı var.",
            })

        normalized = {
            **row,
            "hotel_name": hotel.get("name", "") if hotel else "",
            "hotel_city": hotel.get("city", "") if hotel else "",
        }
        if scope == "agency":
            normalized["agency_name"] = agency.get("name", "") if agency else ""

        if row_errors:
            invalid_rows.append({
                "row_number": row.get("row_number"),
                "data": normalized,
                "errors": row_errors,
            })
            continue

        valid_rows.append(normalized)

    return {
        "scope": scope,
        "summary": {
            "total_rows": len(rows),
            "valid_rows": len(valid_rows),
            "invalid_rows": len(invalid_rows),
        },
        "required_fields": get_scope_headers(scope),
        "valid_rows": valid_rows,
        "invalid_rows": invalid_rows,
    }
