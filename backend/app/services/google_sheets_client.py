"""Google Sheets API client with Service Account.

Graceful fallback when GOOGLE_SERVICE_ACCOUNT_JSON is not set.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

_client_cache: Dict[str, Any] = {}


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
            source=str(metering_context.get("source") or "integrations.google_sheets.legacy"),
            source_event_id=f"{source_event_id}:{operation}",
            metadata=payload,
        )
    )


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
        scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"],
    )
    service = build("sheets", "v4", credentials=creds, cache_discovery=False)
    _client_cache["service"] = service
    return service


def fetch_sheet_data(
    sheet_id: str,
    worksheet_name: str = "Sheet1",
    header_row: int = 1,
    metering_context: Optional[Dict[str, Any]] = None,
) -> Tuple[List[str], List[List[str]]]:
    """Fetch headers and data rows from a Google Sheet.

    Returns (headers, rows) where rows is list of list of strings.
    Raises RuntimeError if not configured or access denied.
    """
    if not is_configured():
        raise RuntimeError("Google Sheets entegrasyonu yap\u0131land\u0131r\u0131lmam\u0131\u015f.")

    service = _get_sheets_service()
    range_str = f"{worksheet_name}"
    try:
        result = service.spreadsheets().values().get(
            spreadsheetId=sheet_id,
            range=range_str,
        ).execute()
        _schedule_integration_call_metering(
            metering_context=metering_context,
            operation="fetch_sheet_data",
            metadata={"sheet_id": sheet_id, "worksheet": worksheet_name, "range": range_str, "status": "success"},
        )
    except Exception as e:
        err_str = str(e)
        _schedule_integration_call_metering(
            metering_context=metering_context,
            operation="fetch_sheet_data",
            metadata={"sheet_id": sheet_id, "worksheet": worksheet_name, "range": range_str, "status": "error", "error": err_str[:200]},
        )
        if "404" in err_str or "not found" in err_str.lower():
            raise RuntimeError(f"Sheet bulunamad\u0131: {sheet_id}")
        if "403" in err_str or "permission" in err_str.lower():
            email = get_service_account_email() or "(bilinmiyor)"
            raise RuntimeError(
                f"Sheet eri\u015fimi yok. L\u00fctfen sheet'i \u015fu email'e payla\u015f\u0131n: {email}"
            )
        raise RuntimeError(f"Google Sheets API hatas\u0131: {err_str}")

    values = result.get("values", [])
    if len(values) < 2:
        raise RuntimeError("Sheet'te en az 1 ba\u015fl\u0131k ve 1 veri sat\u0131r\u0131 olmal\u0131.")

    headers = [str(h).strip() for h in values[header_row - 1]]
    data_rows = []
    for row in values[header_row:]:
        # Pad row to match header length
        padded = [str(cell).strip() if i < len(row) else "" for i, cell in enumerate(row)]
        while len(padded) < len(headers):
            padded.append("")
        if any(c for c in padded):
            data_rows.append(padded)

    return headers, data_rows


def fetch_sheet_headers(
    sheet_id: str,
    worksheet_name: str = "Sheet1",
    header_row: int = 1,
    metering_context: Optional[Dict[str, Any]] = None,
) -> List[str]:
    """Fetch only the header row. Quick validation that access works."""
    if not is_configured():
        raise RuntimeError("Google Sheets entegrasyonu yap\u0131land\u0131r\u0131lmam\u0131\u015f.")

    service = _get_sheets_service()
    range_str = f"{worksheet_name}!{header_row}:{header_row}"
    try:
        result = service.spreadsheets().values().get(
            spreadsheetId=sheet_id,
            range=range_str,
        ).execute()
        _schedule_integration_call_metering(
            metering_context=metering_context,
            operation="fetch_sheet_headers",
            metadata={"sheet_id": sheet_id, "worksheet": worksheet_name, "range": range_str, "status": "success"},
        )
    except Exception as e:
        err_str = str(e)
        _schedule_integration_call_metering(
            metering_context=metering_context,
            operation="fetch_sheet_headers",
            metadata={"sheet_id": sheet_id, "worksheet": worksheet_name, "range": range_str, "status": "error", "error": err_str[:200]},
        )
        if "403" in err_str or "permission" in err_str.lower():
            email = get_service_account_email() or "(bilinmiyor)"
            raise RuntimeError(
                f"Sheet eri\u015fimi yok. L\u00fctfen \u015fu email'e payla\u015f\u0131n: {email}"
            )
        raise RuntimeError(f"Google Sheets API hatas\u0131: {err_str}")

    values = result.get("values", [])
    if not values:
        raise RuntimeError("Header sat\u0131r\u0131 bo\u015f.")

    return [str(h).strip() for h in values[0]]
