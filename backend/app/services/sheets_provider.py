"""Google Sheets Provider Layer.

Abstracts Google Sheets API with graceful fallback.
When GOOGLE_SERVICE_ACCOUNT_JSON is not set, returns structured
'not configured' responses instead of crashing.

Phase 2 stub: write_rows() for reservation write-back.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

_client_cache: Dict[str, Any] = {}


class SheetsProviderResult:
    """Structured result from provider operations."""
    def __init__(
        self,
        success: bool,
        data: Any = None,
        error: Optional[str] = None,
        configured: bool = True,
    ):
        self.success = success
        self.data = data
        self.error = error
        self.configured = configured

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "configured": self.configured,
        }


def is_configured() -> bool:
    """Check if Google Sheets integration is configured."""
    return bool(os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip())


def get_service_account_email() -> Optional[str]:
    """Extract service account email from JSON config."""
    raw = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip()
    if not raw:
        return None
    try:
        data = json.loads(raw)
        return data.get("client_email")
    except (json.JSONDecodeError, KeyError):
        return None


def _get_sheets_service():
    """Build and cache the Google Sheets API service."""
    if "service" in _client_cache:
        return _client_cache["service"]

    raw = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip()
    if not raw:
        raise RuntimeError("GOOGLE_SERVICE_ACCOUNT_JSON not configured")

    from google.oauth2 import service_account
    from googleapiclient.discovery import build

    creds_data = json.loads(raw)
    creds = service_account.Credentials.from_service_account_info(
        creds_data,
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
        ],
    )
    service = build("sheets", "v4", credentials=creds, cache_discovery=False)
    _client_cache["service"] = service
    return service


def get_config_status() -> Dict[str, Any]:
    """Return configuration status."""
    configured = is_configured()
    return {
        "configured": configured,
        "service_account_email": get_service_account_email() if configured else None,
        "message": None if configured else (
            "Google Sheets entegrasyonu yapilandirilmamis. "
            "GOOGLE_SERVICE_ACCOUNT_JSON env var gerekli."
        ),
    }


def read_sheet(
    sheet_id: str,
    tab: str = "Sheet1",
    range_a1: Optional[str] = None,
) -> SheetsProviderResult:
    """Read data from a Google Sheet.

    Returns SheetsProviderResult with data=(headers, rows).
    """
    if not is_configured():
        return SheetsProviderResult(
            success=False,
            configured=False,
            error="Google Sheets entegrasyonu yapilandirilmamis.",
        )

    try:
        service = _get_sheets_service()
        range_str = f"{tab}!{range_a1}" if range_a1 else tab
        result = service.spreadsheets().values().get(
            spreadsheetId=sheet_id,
            range=range_str,
        ).execute()

        values = result.get("values", [])
        if not values:
            return SheetsProviderResult(
                success=True,
                data={"headers": [], "rows": []},
            )

        headers = [str(h).strip() for h in values[0]]
        data_rows = []
        for row in values[1:]:
            padded = [str(cell).strip() if i < len(row) else "" for i, cell in enumerate(row)]
            while len(padded) < len(headers):
                padded.append("")
            if any(c for c in padded):
                data_rows.append(padded)

        return SheetsProviderResult(
            success=True,
            data={"headers": headers, "rows": data_rows},
        )

    except Exception as e:
        err = str(e)
        if "404" in err or "not found" in err.lower():
            return SheetsProviderResult(success=False, error=f"Sheet bulunamadi: {sheet_id}")
        if "403" in err or "permission" in err.lower():
            email = get_service_account_email() or "(bilinmiyor)"
            return SheetsProviderResult(
                success=False,
                error=f"Sheet erisimi yok. Lutfen sheet'i su email'e paylasin: {email}",
            )
        return SheetsProviderResult(success=False, error=f"Google Sheets API hatasi: {err}")


def get_sheet_metadata(sheet_id: str) -> SheetsProviderResult:
    """Get sheet metadata (title, worksheets list)."""
    if not is_configured():
        return SheetsProviderResult(
            success=False,
            configured=False,
            error="Google Sheets yapilandirilmamis.",
        )

    try:
        service = _get_sheets_service()
        meta = service.spreadsheets().get(
            spreadsheetId=sheet_id,
            fields="properties.title,sheets.properties",
        ).execute()

        title = meta.get("properties", {}).get("title", "")
        worksheets = [
            {
                "name": s.get("properties", {}).get("title", ""),
                "index": s.get("properties", {}).get("index", 0),
                "row_count": s.get("properties", {}).get("gridProperties", {}).get("rowCount", 0),
                "col_count": s.get("properties", {}).get("gridProperties", {}).get("columnCount", 0),
            }
            for s in meta.get("sheets", [])
        ]
        return SheetsProviderResult(
            success=True,
            data={"title": title, "worksheets": worksheets},
        )
    except Exception as e:
        return SheetsProviderResult(success=False, error=str(e))


def get_fingerprint(sheet_id: str, tab: str = "Sheet1") -> SheetsProviderResult:
    """Get a fingerprint (hash) of the sheet data for change detection."""
    result = read_sheet(sheet_id, tab)
    if not result.success:
        return result

    data = result.data or {}
    canonical = json.dumps(data, sort_keys=True, ensure_ascii=False)
    fp = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return SheetsProviderResult(success=True, data={"fingerprint": fp})


def append_rows(
    sheet_id: str,
    tab: str,
    rows: List[List[str]],
) -> SheetsProviderResult:
    """Append rows to a sheet (Phase 2 write-back)."""
    if not is_configured():
        return SheetsProviderResult(
            success=False,
            configured=False,
            error="Google Sheets yapilandirilmamis.",
        )

    try:
        service = _get_sheets_service()
        body = {"values": rows}
        service.spreadsheets().values().append(
            spreadsheetId=sheet_id,
            range=f"{tab}!A1",
            valueInputOption="USER_ENTERED",
            insertDataOption="INSERT_ROWS",
            body=body,
        ).execute()
        return SheetsProviderResult(success=True, data={"rows_appended": len(rows)})
    except Exception as e:
        return SheetsProviderResult(success=False, error=str(e))


def update_cells(
    sheet_id: str,
    tab: str,
    range_a1: str,
    values: List[List[str]],
) -> SheetsProviderResult:
    """Update specific cells (Phase 2 write-back)."""
    if not is_configured():
        return SheetsProviderResult(
            success=False,
            configured=False,
            error="Google Sheets yapilandirilmamis.",
        )

    try:
        service = _get_sheets_service()
        body = {"values": values}
        service.spreadsheets().values().update(
            spreadsheetId=sheet_id,
            range=f"{tab}!{range_a1}",
            valueInputOption="USER_ENTERED",
            body=body,
        ).execute()
        return SheetsProviderResult(success=True, data={"cells_updated": len(values)})
    except Exception as e:
        return SheetsProviderResult(success=False, error=str(e))
