from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from app.errors import AppError
from app.services.google_sheet_schema_service import (
    get_reservation_writeback_headers,
    headers_match_expected,
    validate_inventory_headers,
)
from app.services.sheets_provider import (
    ensure_tab_with_headers,
    get_sheet_metadata,
    read_sheet,
)

SERVICE_ACCOUNT_REQUIRED_FIELDS = [
    "type",
    "project_id",
    "private_key",
    "client_email",
    "token_uri",
]


def get_service_account_required_fields() -> List[str]:
    return list(SERVICE_ACCOUNT_REQUIRED_FIELDS)


def validate_service_account_json(raw_json: str) -> Dict[str, Any]:
    raw = raw_json.strip()
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise AppError(400, "invalid_json", "Gecersiz JSON formati.") from exc

    missing = [field for field in SERVICE_ACCOUNT_REQUIRED_FIELDS if not parsed.get(field)]
    if missing:
        raise AppError(400, "missing_fields", f"Eksik alanlar: {', '.join(missing)}")

    if parsed.get("type") != "service_account":
        raise AppError(400, "invalid_service_account_type", "JSON icindeki 'type' alani 'service_account' olmalidir.")

    private_key = str(parsed.get("private_key", ""))
    if "BEGIN PRIVATE KEY" not in private_key:
        raise AppError(400, "invalid_private_key", "private_key alani gecerli bir service account private key icermiyor.")

    client_email = str(parsed.get("client_email", "")).strip()
    if "gserviceaccount.com" not in client_email:
        raise AppError(400, "invalid_client_email", "client_email alani gecerli bir Google service account email olmali.")

    return {
        "raw": raw,
        "parsed": parsed,
        "client_email": client_email,
        "project_id": str(parsed.get("project_id", "")).strip(),
    }


def _raise_sheet_error(code: str, message: str) -> None:
    raise AppError(400, code, message)


def _inspect_writeback_tab(
    *,
    sheet_id: str,
    writeback_tab: str,
    available_tabs: List[str],
    tenant_id: str,
) -> Dict[str, Any]:
    expected_headers = get_reservation_writeback_headers()
    if writeback_tab not in available_tabs:
        return {
            "tab_name": writeback_tab,
            "exists": False,
            "valid": False,
            "headers_present": False,
            "existing_headers": [],
            "expected_headers": expected_headers,
            "action_required": "create_tab",
        }

    header_result = read_sheet(sheet_id, writeback_tab, "1:1", tenant_id=tenant_id)
    if not header_result.success:
        _raise_sheet_error(
            "writeback_tab_read_error",
            header_result.error or "Write-back sekmesi okunamadi.",
        )

    existing_headers = header_result.data.get("headers", [])
    if not existing_headers:
        return {
            "tab_name": writeback_tab,
            "exists": True,
            "valid": False,
            "headers_present": False,
            "existing_headers": [],
            "expected_headers": expected_headers,
            "action_required": "write_headers",
        }

    valid = headers_match_expected(existing_headers, expected_headers)
    return {
        "tab_name": writeback_tab,
        "exists": True,
        "valid": valid,
        "headers_present": True,
        "existing_headers": existing_headers,
        "expected_headers": expected_headers,
        "action_required": None if valid else "fix_headers",
    }


def build_sheet_preflight(
    *,
    tenant_id: str,
    sheet_id: str,
    sheet_tab: str,
    writeback_tab: Optional[str] = None,
    strict_headers: bool = False,
    ensure_writeback: bool = False,
) -> Dict[str, Any]:
    meta_result = get_sheet_metadata(sheet_id, tenant_id=tenant_id)
    if not meta_result.success:
        _raise_sheet_error(
            "sheet_metadata_error",
            meta_result.error or "Sheet metadata okunamadi.",
        )

    sheet_title = meta_result.data.get("title", "")
    worksheets = meta_result.data.get("worksheets", [])
    available_tabs = [worksheet.get("name", "") for worksheet in worksheets if worksheet.get("name")]
    if sheet_tab not in available_tabs:
        available = ", ".join(available_tabs) or "-"
        _raise_sheet_error(
            "sheet_tab_not_found",
            f"'{sheet_tab}' sekmesi bulunamadi. Mevcut sekmeler: {available}",
        )

    read_result = read_sheet(sheet_id, sheet_tab, "1:1", tenant_id=tenant_id)
    if not read_result.success:
        _raise_sheet_error(
            "sheet_read_error",
            read_result.error or "Sheet okunamadi.",
        )

    detected_headers = read_result.data.get("headers", [])
    header_validation = validate_inventory_headers(detected_headers)
    if strict_headers and header_validation["missing_required_labels"]:
        missing = ", ".join(header_validation["missing_required_labels"])
        _raise_sheet_error("missing_required_headers", f"Eksik zorunlu kolonlar: {missing}")

    writeback_validation = None
    writeback_bootstrap = None
    if writeback_tab:
        if ensure_writeback:
            ensure_result = ensure_tab_with_headers(
                sheet_id,
                writeback_tab,
                get_reservation_writeback_headers(),
                tenant_id=tenant_id,
            )
            if not ensure_result.success:
                _raise_sheet_error(
                    "writeback_tab_invalid",
                    ensure_result.error or "Write-back sekmesi hazirlanamadi.",
                )
            writeback_bootstrap = ensure_result.data
            writeback_validation = {
                "tab_name": writeback_tab,
                "exists": True,
                "valid": True,
                "headers_present": True,
                "existing_headers": get_reservation_writeback_headers(),
                "expected_headers": get_reservation_writeback_headers(),
                "action_required": None,
                **(writeback_bootstrap or {}),
            }
        else:
            writeback_validation = _inspect_writeback_tab(
                sheet_id=sheet_id,
                writeback_tab=writeback_tab,
                available_tabs=available_tabs,
                tenant_id=tenant_id,
            )

    valid = header_validation["valid"] and (
        writeback_validation["valid"] if writeback_validation is not None else True
    )

    return {
        "configured": True,
        "valid": valid,
        "sheet_id": sheet_id,
        "sheet_title": sheet_title,
        "sheet_tab": sheet_tab,
        "writeback_tab": writeback_tab,
        "worksheets": worksheets,
        "available_tabs": available_tabs,
        "detected_headers": detected_headers,
        "detected_mapping": header_validation["detected_mapping"],
        "header_validation": header_validation,
        "writeback_validation": writeback_validation,
        "writeback_bootstrap": writeback_bootstrap,
        "validation_summary": {
            "inventory_valid": header_validation["valid"],
            "writeback_valid": writeback_validation["valid"] if writeback_validation is not None else True,
            "missing_required_fields": header_validation["missing_required_fields"],
            "missing_required_labels": header_validation["missing_required_labels"],
            "recognized_headers": header_validation["recognized_headers"],
            "unrecognized_headers": header_validation["unrecognized_headers"],
        },
    }