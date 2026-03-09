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

from app.services.google_sheet_schema_service import headers_match_expected

logger = logging.getLogger(__name__)

_client_cache: Dict[str, Any] = {}
_db_config_cache: Dict[str, str] = {}


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


def _tenant_cache_key(tenant_id: Optional[str]) -> str:
    return str(tenant_id or "__default__")


def clear_db_configs() -> None:
    _db_config_cache.clear()
    if not os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip():
        _client_cache.clear()


def _get_raw_config(tenant_id: Optional[str] = None) -> str:
    env_val = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip()
    if env_val:
        return env_val
    if tenant_id is not None:
        return _db_config_cache.get(_tenant_cache_key(tenant_id), "")
    if len(_db_config_cache) == 1:
        return next(iter(_db_config_cache.values()))
    return ""


def get_service_account_json(tenant_id: Optional[str] = None) -> str:
    return _get_raw_config(tenant_id)


def set_db_config(service_account_json: str, tenant_id: Optional[str] = None) -> None:
    key = _tenant_cache_key(tenant_id)
    if service_account_json:
        _db_config_cache[key] = service_account_json
    else:
        _db_config_cache.pop(key, None)
    if not os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip():
        _client_cache.clear()


def is_configured(tenant_id: Optional[str] = None) -> bool:
    return bool(_get_raw_config(tenant_id))


def get_service_account_email(tenant_id: Optional[str] = None) -> Optional[str]:
    raw = _get_raw_config(tenant_id)
    if not raw:
        return None
    try:
        data = json.loads(raw)
        return data.get("client_email")
    except (json.JSONDecodeError, KeyError):
        return None


def _get_sheets_service(tenant_id: Optional[str] = None):
    raw = _get_raw_config(tenant_id)
    if not raw:
        raise RuntimeError("GOOGLE_SERVICE_ACCOUNT_JSON not configured")

    cache_key = f"service:{hashlib.sha256(raw.encode('utf-8')).hexdigest()}"
    if cache_key in _client_cache:
        return _client_cache[cache_key]

    from google.oauth2 import service_account
    from googleapiclient.discovery import build

    creds_data = json.loads(raw)
    creds = service_account.Credentials.from_service_account_info(
        creds_data,
        scopes=["https://www.googleapis.com/auth/spreadsheets"],
    )
    service = build("sheets", "v4", credentials=creds, cache_discovery=False)
    _client_cache[cache_key] = service
    return service


def get_config_status(tenant_id: Optional[str] = None) -> Dict[str, Any]:
    configured = is_configured(tenant_id)
    source = "env" if os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip() else ("db" if configured else "none")
    return {
        "configured": configured,
        "source": source,
        "service_account_email": get_service_account_email(tenant_id) if configured else None,
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
    tenant_id: Optional[str] = None,
    metering_context: Optional[Dict[str, Any]] = None,
) -> SheetsProviderResult:
    if not is_configured(tenant_id):
        return SheetsProviderResult(
            success=False,
            configured=False,
            error="Google Sheets entegrasyonu yapilandirilmamis.",
        )

    try:
        service = _get_sheets_service(tenant_id)
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
            return SheetsProviderResult(success=True, data={"headers": [], "rows": []})

        headers = [str(h).strip() for h in values[0]]
        data_rows = []
        for row in values[1:]:
            padded = [str(cell).strip() if i < len(row) else "" for i, cell in enumerate(row)]
            while len(padded) < len(headers):
                padded.append("")
            if any(c for c in padded):
                data_rows.append(padded)

        return SheetsProviderResult(success=True, data={"headers": headers, "rows": data_rows})
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
            email = get_service_account_email(tenant_id) or "(bilinmiyor)"
            return SheetsProviderResult(
                success=False,
                error=f"Sheet erisimi yok. Lutfen sheet'i su email'e paylasin: {email}",
            )
        return SheetsProviderResult(success=False, error=f"Google Sheets API hatasi: {err}")


def get_sheet_metadata(
    sheet_id: str,
    tenant_id: Optional[str] = None,
    metering_context: Optional[Dict[str, Any]] = None,
) -> SheetsProviderResult:
    if not is_configured(tenant_id):
        return SheetsProviderResult(
            success=False,
            configured=False,
            error="Google Sheets yapilandirilmamis.",
        )

    try:
        service = _get_sheets_service(tenant_id)
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
                "name": sheet.get("properties", {}).get("title", ""),
                "index": sheet.get("properties", {}).get("index", 0),
                "row_count": sheet.get("properties", {}).get("gridProperties", {}).get("rowCount", 0),
                "col_count": sheet.get("properties", {}).get("gridProperties", {}).get("columnCount", 0),
            }
            for sheet in meta.get("sheets", [])
        ]
        return SheetsProviderResult(success=True, data={"title": title, "worksheets": worksheets})
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
    tenant_id: Optional[str] = None,
    metering_context: Optional[Dict[str, Any]] = None,
) -> SheetsProviderResult:
    result = read_sheet(sheet_id, tab, tenant_id=tenant_id, metering_context=metering_context)
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
    tenant_id: Optional[str] = None,
    metering_context: Optional[Dict[str, Any]] = None,
) -> SheetsProviderResult:
    if not is_configured(tenant_id):
        return SheetsProviderResult(
            success=False,
            configured=False,
            error="Google Sheets yapilandirilmamis.",
        )

    try:
        service = _get_sheets_service(tenant_id)
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
    tenant_id: Optional[str] = None,
    metering_context: Optional[Dict[str, Any]] = None,
) -> SheetsProviderResult:
    if not is_configured(tenant_id):
        return SheetsProviderResult(
            success=False,
            configured=False,
            error="Google Sheets yapilandirilmamis.",
        )

    try:
        service = _get_sheets_service(tenant_id)
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


def _column_letter(index: int) -> str:
    result = ""
    current = index
    while current > 0:
        current, remainder = divmod(current - 1, 26)
        result = chr(65 + remainder) + result
    return result


def ensure_tab_with_headers(
    sheet_id: str,
    tab: str,
    headers: List[str],
    tenant_id: Optional[str] = None,
    metering_context: Optional[Dict[str, Any]] = None,
) -> SheetsProviderResult:
    if not is_configured(tenant_id):
        return SheetsProviderResult(
            success=False,
            configured=False,
            error="Google Sheets yapilandirilmamis.",
        )

    try:
        service = _get_sheets_service(tenant_id)
        meta = service.spreadsheets().get(
            spreadsheetId=sheet_id,
            fields="sheets.properties.title",
        ).execute()
        worksheet_names = {
            sheet.get("properties", {}).get("title", "")
            for sheet in meta.get("sheets", [])
        }
        tab_created = False

        if tab not in worksheet_names:
            service.spreadsheets().batchUpdate(
                spreadsheetId=sheet_id,
                body={"requests": [{"addSheet": {"properties": {"title": tab}}}]},
            ).execute()
            tab_created = True
        else:
            header_result = read_sheet(
                sheet_id,
                tab,
                "1:1",
                tenant_id=tenant_id,
                metering_context=metering_context,
            )
            existing_headers = header_result.data.get("headers", []) if header_result.success else []
            if existing_headers and not headers_match_expected(existing_headers, headers):
                return SheetsProviderResult(
                    success=False,
                    error=(
                        f"{tab} sekmesinin ilk satiri write-back şablonuyla uyusmuyor. "
                        "Bos bir sekme kullanin veya mevcut basliklari duzeltin."
                    ),
                )
            if existing_headers and headers_match_expected(existing_headers, headers):
                return SheetsProviderResult(
                    success=True,
                    data={"tab": tab, "tab_created": False, "headers_written": False},
                )

        last_column = _column_letter(len(headers))
        body = {"values": [headers]}
        service.spreadsheets().values().update(
            spreadsheetId=sheet_id,
            range=f"{tab}!A1:{last_column}1",
            valueInputOption="RAW",
            body=body,
        ).execute()
        return SheetsProviderResult(
            success=True,
            data={"tab": tab, "tab_created": tab_created, "headers_written": True},
        )
    except Exception as e:
        return SheetsProviderResult(success=False, error=str(e))
