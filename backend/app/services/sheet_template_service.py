from __future__ import annotations

import csv
import io
from typing import Any, Dict, List

from app.errors import AppError
from app.services.google_sheet_schema_service import (
    INVENTORY_OPTIONAL_FIELDS,
    INVENTORY_REQUIRED_FIELDS,
    INVENTORY_FIELD_LABELS,
    get_reservation_writeback_headers,
    get_sheet_templates_payload,
)


def _inventory_headers() -> List[str]:
    ordered_fields = [*INVENTORY_REQUIRED_FIELDS, *INVENTORY_OPTIONAL_FIELDS]
    return [INVENTORY_FIELD_LABELS[field] for field in ordered_fields]


def get_downloadable_templates() -> List[Dict[str, str]]:
    return [
        {
            "name": "inventory-sync",
            "label": "Envanter Sync CSV",
            "filename": "syroce_inventory_sync_template.csv",
        },
        {
            "name": "reservation-writeback",
            "label": "Rezervasyon Write-back CSV",
            "filename": "syroce_reservation_writeback_template.csv",
        },
    ]


def build_sheet_templates_payload() -> Dict[str, Any]:
    payload = get_sheet_templates_payload()
    payload["downloadable_templates"] = get_downloadable_templates()
    return payload


def render_template_csv(template_name: str) -> Dict[str, Any]:
    template_key = (template_name or "").strip().casefold()
    buffer = io.StringIO()
    writer = csv.writer(buffer)

    if template_key == "inventory-sync":
        headers = _inventory_headers()
        writer.writerow(headers)
        writer.writerow([
            "2026-06-12",
            "Deluxe",
            "18500",
            "6",
            "Hayir",
            "Syroce Demo Hotel",
            "Istanbul",
            "Turkiye",
            "Erken rezervasyon icin acik",
            "5",
            "+90 212 555 00 00",
            "sales@syroce.test",
            "Besiktas / Istanbul",
            "https://example.com/hotel.jpg",
        ])
        filename = "syroce_inventory_sync_template.csv"
    elif template_key == "reservation-writeback":
        template_payload = get_sheet_templates_payload()["reservation_writeback"]
        headers = get_reservation_writeback_headers()
        writer.writerow(headers)
        sample_row = template_payload.get("sample_row", {})
        writer.writerow([sample_row.get(header, "") for header in headers])
        filename = "syroce_reservation_writeback_template.csv"
    else:
        raise AppError(404, "template_not_found", "Istenen sheet sablonu bulunamadi.")

    return {
        "filename": filename,
        "content": buffer.getvalue().encode("utf-8-sig"),
        "media_type": "text/csv; charset=utf-8",
    }