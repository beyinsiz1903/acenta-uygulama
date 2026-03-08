"""Google Sheets Provider Layer.

Abstracts Google Sheets API with graceful fallback.
When GOOGLE_SERVICE_ACCOUNT_JSON is not set, returns structured
'not configured' responses instead of crashing.

Phase 2 stub: write_rows() for reservation write-back.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_client_cache: Dict[str, Any] = {}
_db_config_cache: Dict[str, Any] = {}


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


def _get_raw_config() -> str:
    """Get service account JSON from env or DB cache."""
    # Priority: env var > DB cached value
    env_val = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip()
    if env_val:
        return env_val
    return _db_config_cache.get("service_account_json", "")


def set_db_config(service_account_json: str) -> None:
    """Set the DB-cached service account config (called after DB read)."""
    _db_config_cache["service_account_json"] = service_account_json
    # Invalidate cached service
    _client_cache.pop("service", None)


def is_configured() -> bool:
    """Check if Google Sheets integration is configured."""
    return bool(_get_raw_config())


def get_service_account_email() -> Optional[str]:
    """Extract service account email from JSON config."""
    raw = _get_raw_config()
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

    raw = _get_raw_config()
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
    source = "env" if os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip() else ("db" if configured else "none")
    return {
        "configured": configured,
        "source": source,
        "service_account_email": get_service_account_email() if configured else None,
        "message": None if configured else (
            "Google Sheets entegrasyonu yapilandirilmamis. "
            "Admin panelinden Service Account JSON'u girebilirsiniz."
        ),
    }


def _schedule_integration_call_metering(
    *,
    metering_context: Optional[Dict[str, Any]],
    operation: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    if not metering_context:
        return

    source_event_id = str(metering_context.get("source_event_id") or "").strip()
    organization_id = metering_context.get("organization_id")
    tenant_id = metering_context.get("tenant_id")
    if not source_event_id or (organization_id is None and tenant_id is None):
        return

    payload = {
        **(metering_context.get("metadata") or {}),
        **(metadata or {}),
    }

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return

    from app.services.usage_service import track_integration_call

    loop.create_task(
        track_integration_call(
            organization_id=str(organization_id) if organization_id is not None else None,
            tenant_id=str(tenant_id) if tenant_id is not None else None,
            integration_key="google_sheets",
            operation=operation,
            source=str(metering_context.get("source") or "integrations.google_sheets"),
            source_event_id=f"{source_event_id}:{operation}",
            metadata=payload,
        )
    )


def read_sheet(
    sheet_id: str,
    tab: str = "Sheet1",
    range_a1: Optional[str] = None,
    metering_context: Optional[Dict[str, Any]] = None,
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
        call_metadata = {"sheet_id": sheet_id, "tab": tab, "range": range_str}
        result = service.spreadsheets().values().get(
            spreadsheetId=sheet_id,
            range=range_str,
        ).execute()
        _schedule_integration_call_metering(
            metering_context=metering_context,
            operation="read_sheet",
            metadata={**call_metadata, "status": "success"},
        )

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
        _schedule_integration_call_metering(
            metering_context=metering_context,
            operation="read_sheet",
            metadata={
                "sheet_id": sheet_id,
                "tab": tab,
                "range": f"{tab}!{range_a1}" if range_a1 else tab,
                "status": "error",
                "error": err[:200],
            },
        )
        if "404" in err or "not found" in err.lower():
            return SheetsProviderResult(success=False, error=f"Sheet bulunamadi: {sheet_id}")
        if "403" in err or "permission" in err.lower():
            email = get_service_account_email() or "(bilinmiyor)"
            return SheetsProviderResult(
                success=False,
                error=f"Sheet erisimi yok. Lutfen sheet'i su email'e paylasin: {email}",
            )
        return SheetsProviderResult(success=False, error=f"Google Sheets API hatasi: {err}")


def get_sheet_metadata(sheet_id: str, metering_context: Optional[Dict[str, Any]] = None) -> SheetsProviderResult:
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
        _schedule_integration_call_metering(
            metering_context=metering_context,
            operation="get_sheet_metadata",
            metadata={"sheet_id": sheet_id, "status": "success"},
        )

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
        _schedule_integration_call_metering(
            metering_context=metering_context,
            operation="get_sheet_metadata",
            metadata={"sheet_id": sheet_id, "status": "error", "error": str(e)[:200]},
        )
        return SheetsProviderResult(success=False, error=str(e))


def get_fingerprint(
    sheet_id: str,
    tab: str = "Sheet1",
    metering_context: Optional[Dict[str, Any]] = None,
) -> SheetsProviderResult:
    """Get a fingerprint (hash) of the sheet data for change detection."""
    result = read_sheet(sheet_id, tab, metering_context=metering_context)
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
    metering_context: Optional[Dict[str, Any]] = None,
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
        _schedule_integration_call_metering(
            metering_context=metering_context,
            operation="append_rows",
            metadata={"sheet_id": sheet_id, "tab": tab, "row_count": len(rows), "status": "success"},
        )
        return SheetsProviderResult(success=True, data={"rows_appended": len(rows)})
    except Exception as e:
        _schedule_integration_call_metering(
            metering_context=metering_context,
            operation="append_rows",
            metadata={"sheet_id": sheet_id, "tab": tab, "row_count": len(rows), "status": "error", "error": str(e)[:200]},
        )
        return SheetsProviderResult(success=False, error=str(e))


def update_cells(
    sheet_id: str,
    tab: str,
    range_a1: str,
    values: List[List[str]],
    metering_context: Optional[Dict[str, Any]] = None,
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
        _schedule_integration_call_metering(
            metering_context=metering_context,
            operation="update_cells",
            metadata={"sheet_id": sheet_id, "tab": tab, "range": range_a1, "row_count": len(values), "status": "success"},
        )
        return SheetsProviderResult(success=True, data={"cells_updated": len(values)})
    except Exception as e:
        _schedule_integration_call_metering(
            metering_context=metering_context,
            operation="update_cells",
            metadata={"sheet_id": sheet_id, "tab": tab, "range": range_a1, "row_count": len(values), "status": "error", "error": str(e)[:200]},
        )
        return SheetsProviderResult(success=False, error=str(e))
