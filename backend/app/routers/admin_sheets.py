"""Portfolio Sync Engine — Admin Sheets API.

Multi-hotel Google Sheets sync management.
New endpoints under /api/admin/sheets/*

Backward compatible: existing /api/admin/import/* untouched.
"""
from __future__ import annotations

import io
import uuid
from typing import Any, Dict, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.auth import get_current_user, require_roles
from app.db import get_db
from app.errors import AppError
from app.services.audit_log_service import append_audit_log
from app.services.google_sheet_schema_service import (
    validate_inventory_headers,
)
from app.services.sheet_connection_service import (
    build_sheet_preflight,
    get_service_account_required_fields,
    validate_service_account_json,
)
from app.services.sheet_template_service import (
    build_sheet_templates_payload,
    render_template_csv,
)
from app.services.sheets_provider import (
    get_config_status,
    get_service_account_email,
    is_configured,
    read_sheet,
    set_db_config,
)
from app.services.hotel_portfolio_sync_service import (
    get_portfolio_health,
    get_stale_connections,
    run_hotel_sheet_sync,
)
from app.utils import now_utc, serialize_doc

router = APIRouter(prefix="/api/admin/sheets", tags=["admin_sheets"])
AdminDep = Depends(require_roles(["super_admin", "admin"]))


def _tenant_id(user: Dict[str, Any]) -> str:
    return user.get("tenant_id") or user["organization_id"]


def _configured_or_false_payload() -> Dict[str, Any]:
    templates = build_sheet_templates_payload()
    return {
        "configured": False,
        "message": "Google Sheets yapilandirilmamis.",
        "headers": [],
        "preview": [],
        "detected_mapping": {},
        "header_validation": {},
        "required_service_account_fields": get_service_account_required_fields(),
        "checklist": templates.get("checklist", []),
        "downloadable_templates": templates.get("downloadable_templates", []),
    }


async def _create_hotel_connection_record(
    body: "ConnectSheetRequest",
    user: Dict[str, Any],
    db,
) -> Dict[str, Any]:
    org_id = user["organization_id"]
    tenant_id = _tenant_id(user)

    existing = await db.hotel_portfolio_sources.find_one({
        "tenant_id": tenant_id,
        "hotel_id": body.hotel_id,
        "source_type": "google_sheets",
    })
    if existing:
        raise AppError(409, "connection_exists", "Bu otel icin zaten bir sheet baglantisi var.")

    hotel = await db.hotels.find_one({"_id": body.hotel_id, "organization_id": org_id})
    if not hotel:
        raise AppError(404, "hotel_not_found", "Otel bulunamadi.")

    detected_headers = []
    detected_mapping = {}
    sheet_title = ""
    worksheets = []
    header_validation: Dict[str, Any] = {}
    writeback_validation: Optional[Dict[str, Any]] = None
    writeback_bootstrap: Optional[Dict[str, Any]] = None
    validation_summary: Dict[str, Any] = {}
    validation_status = "pending_configuration"

    if is_configured(tenant_id):
        preflight = build_sheet_preflight(
            tenant_id=tenant_id,
            sheet_id=body.sheet_id,
            sheet_tab=body.sheet_tab,
            writeback_tab=body.writeback_tab,
            strict_headers=True,
            ensure_writeback=True,
        )
        sheet_title = preflight["sheet_title"]
        worksheets = preflight["worksheets"]
        detected_headers = preflight["detected_headers"]
        detected_mapping = preflight["detected_mapping"]
        header_validation = preflight["header_validation"]
        writeback_validation = preflight["writeback_validation"]
        writeback_bootstrap = preflight["writeback_bootstrap"]
        validation_summary = preflight["validation_summary"]
        validation_status = "validated"

    effective_mapping = body.mapping if body.mapping else detected_mapping

    doc = {
        "_id": str(uuid.uuid4()),
        "tenant_id": tenant_id,
        "organization_id": org_id,
        "hotel_id": body.hotel_id,
        "hotel_name": hotel.get("name", ""),
        "source_type": "google_sheets",
        "sheet_id": body.sheet_id,
        "sheet_tab": body.sheet_tab,
        "writeback_tab": body.writeback_tab,
        "sheet_title": sheet_title,
        "mapping": effective_mapping,
        "validation_status": validation_status,
        "validation_summary": validation_summary,
        "sync_enabled": body.sync_enabled,
        "sync_interval_minutes": body.sync_interval_minutes,
        "last_sync_at": None,
        "last_sync_status": None,
        "last_error": None,
        "last_fingerprint": None,
        "status": "active",
        "created_at": now_utc(),
        "updated_at": now_utc(),
        "created_by": user.get("email", ""),
    }
    await db.hotel_portfolio_sources.insert_one(doc)

    await append_audit_log(
        scope="portfolio_sync",
        tenant_id=tenant_id,
        actor_user_id=user.get("_id", ""),
        actor_email=user.get("email", ""),
        action="sheet_connected",
        after={"hotel_id": body.hotel_id, "sheet_id": body.sheet_id},
    )

    result = serialize_doc(doc)
    result["configured"] = is_configured(tenant_id)
    result["service_account_email"] = get_service_account_email(tenant_id)
    result["detected_headers"] = detected_headers
    result["detected_mapping"] = detected_mapping
    result["header_validation"] = header_validation
    result["validation_summary"] = validation_summary
    result["writeback_validation"] = writeback_validation
    result["writeback_bootstrap"] = writeback_bootstrap
    result["worksheets"] = worksheets
    return result


# ── Config Status ─────────────────────────────────────────

@router.get("/config", dependencies=[AdminDep])
async def get_sheets_config(user=Depends(get_current_user)):
    """Return Google Sheets integration configuration status."""
    payload = get_config_status(_tenant_id(user))
    payload["required_service_account_fields"] = get_service_account_required_fields()
    return payload


@router.get("/templates", dependencies=[AdminDep])
async def get_sheet_templates(user=Depends(get_current_user)):
    """Return the exact headers/checklist expected by Google Sheets sync."""
    templates = build_sheet_templates_payload()
    templates["configured"] = is_configured(_tenant_id(user))
    templates["service_account_email"] = get_service_account_email(_tenant_id(user))
    return templates


class ValidateSheetRequest(BaseModel):
    sheet_id: str
    sheet_tab: str = "Sheet1"
    writeback_tab: str = "Rezervasyonlar"


@router.post("/validate-sheet", dependencies=[AdminDep])
async def validate_sheet(
    body: ValidateSheetRequest,
    user=Depends(get_current_user),
):
    tenant_id = _tenant_id(user)
    if not is_configured(tenant_id):
        payload = _configured_or_false_payload()
        payload["sheet_id"] = body.sheet_id
        payload["sheet_tab"] = body.sheet_tab
        payload["writeback_tab"] = body.writeback_tab
        return payload

    result = build_sheet_preflight(
        tenant_id=tenant_id,
        sheet_id=body.sheet_id,
        sheet_tab=body.sheet_tab,
        writeback_tab=body.writeback_tab,
        strict_headers=False,
        ensure_writeback=False,
    )
    result["service_account_email"] = get_service_account_email(tenant_id)
    result["required_service_account_fields"] = get_service_account_required_fields()
    return result


@router.get("/download-template/{template_name}", dependencies=[AdminDep])
async def download_sheet_template(
    template_name: str,
    user=Depends(get_current_user),
):
    _ = user
    payload = render_template_csv(template_name)
    return StreamingResponse(
        io.BytesIO(payload["content"]),
        media_type=payload["media_type"],
        headers={"Content-Disposition": f"attachment; filename={payload['filename']}"},
    )


# ── Connect a Hotel Sheet ─────────────────────────────────

class ConnectSheetRequest(BaseModel):
    hotel_id: str
    sheet_id: str
    sheet_tab: str = "Sheet1"
    writeback_tab: str = "Rezervasyonlar"
    mapping: Dict[str, str] = Field(default_factory=dict)
    sync_enabled: bool = True
    sync_interval_minutes: int = 5


@router.post("/connect", dependencies=[AdminDep])
async def connect_hotel_sheet(
    body: ConnectSheetRequest,
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    """Connect a Google Sheet to a hotel for portfolio sync."""
    return await _create_hotel_connection_record(body, user, db)


@router.post("/connections", dependencies=[AdminDep])
async def create_hotel_connection(
    body: ConnectSheetRequest,
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    """REST-style alias for creating a Google Sheet connection."""
    return await _create_hotel_connection_record(body, user, db)


# ── List Connections ──────────────────────────────────────

@router.get("/connections", dependencies=[AdminDep])
async def list_sheet_connections(
    hotel_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    """List all hotel sheet connections."""
    tenant_id = _tenant_id(user)
    query: Dict[str, Any] = {"tenant_id": tenant_id}
    if hotel_id:
        query["hotel_id"] = hotel_id
    if status:
        query["status"] = status

    docs = await db.hotel_portfolio_sources.find(query).sort("created_at", -1).to_list(300)
    return [serialize_doc(d) for d in docs]


# ── Get Single Connection ─────────────────────────────────

@router.get("/connections/{hotel_id}", dependencies=[AdminDep])
async def get_hotel_connection(
    hotel_id: str,
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    """Get sheet connection for a specific hotel."""
    tenant_id = user.get("tenant_id") or user["organization_id"]
    conn = await db.hotel_portfolio_sources.find_one({
        "tenant_id": tenant_id,
        "hotel_id": hotel_id,
        "source_type": "google_sheets",
    })
    if not conn:
        return {"connected": False, "hotel_id": hotel_id}

    result = serialize_doc(conn)
    result["connected"] = True
    result["configured"] = is_configured(tenant_id)
    return result


# ── Update Connection ─────────────────────────────────────

class UpdateConnectionRequest(BaseModel):
    sync_enabled: Optional[bool] = None
    sync_interval_minutes: Optional[int] = None
    mapping: Optional[Dict[str, str]] = None
    sheet_tab: Optional[str] = None
    writeback_tab: Optional[str] = None
    status: Optional[str] = None


@router.patch("/connections/{hotel_id}", dependencies=[AdminDep])
async def update_hotel_connection(
    hotel_id: str,
    body: UpdateConnectionRequest,
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    """Update connection settings (enable/disable, mapping, interval)."""
    tenant_id = _tenant_id(user)
    conn = await db.hotel_portfolio_sources.find_one({
        "tenant_id": tenant_id,
        "hotel_id": hotel_id,
    })
    if not conn:
        raise AppError(404, "connection_not_found", "Sheet baglantisi bulunamadi.")

    update_fields: Dict[str, Any] = {"updated_at": now_utc()}
    if body.sync_enabled is not None:
        update_fields["sync_enabled"] = body.sync_enabled
    if body.sync_interval_minutes is not None:
        update_fields["sync_interval_minutes"] = body.sync_interval_minutes
    if body.mapping is not None:
        update_fields["mapping"] = body.mapping
    if body.sheet_tab is not None:
        update_fields["sheet_tab"] = body.sheet_tab
    if body.writeback_tab is not None:
        update_fields["writeback_tab"] = body.writeback_tab
    if body.status is not None:
        update_fields["status"] = body.status

    await db.hotel_portfolio_sources.update_one(
        {"_id": conn["_id"]},
        {"$set": update_fields},
    )

    # Audit
    await append_audit_log(
        scope="portfolio_sync",
        tenant_id=tenant_id,
        actor_user_id=user.get("_id", ""),
        actor_email=user.get("email", ""),
        action="sheet_connection_updated",
        before={"hotel_id": hotel_id},
        after=update_fields,
    )

    updated = await db.hotel_portfolio_sources.find_one({"_id": conn["_id"]})
    return serialize_doc(updated)


# ── Delete Connection ─────────────────────────────────────

@router.delete("/connections/{hotel_id}", dependencies=[AdminDep])
async def delete_hotel_connection(
    hotel_id: str,
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    """Delete/disconnect a hotel sheet connection."""
    tenant_id = _tenant_id(user)
    result = await db.hotel_portfolio_sources.delete_one({
        "tenant_id": tenant_id,
        "hotel_id": hotel_id,
    })
    if result.deleted_count == 0:
        raise AppError(404, "connection_not_found", "Sheet baglantisi bulunamadi.")

    # Also clean up fingerprints
    await db.sheet_row_fingerprints.delete_many({
        "tenant_id": tenant_id,
        "hotel_id": hotel_id,
    })

    # Audit
    await append_audit_log(
        scope="portfolio_sync",
        tenant_id=tenant_id,
        actor_user_id=user.get("_id", ""),
        actor_email=user.get("email", ""),
        action="sheet_disconnected",
        before={"hotel_id": hotel_id},
    )

    return {"deleted": True, "hotel_id": hotel_id}


# ── Sync Now ──────────────────────────────────────────────

@router.post("/sync/{hotel_id}", dependencies=[AdminDep])
async def sync_hotel_sheet(
    hotel_id: str,
    background_tasks: BackgroundTasks,
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    """Trigger manual sync for a specific hotel."""
    tenant_id = _tenant_id(user)
    conn = await db.hotel_portfolio_sources.find_one({
        "tenant_id": tenant_id,
        "hotel_id": hotel_id,
    })
    if not conn:
        raise AppError(404, "connection_not_found", "Sheet baglantisi bulunamadi.")

    if not is_configured(tenant_id):
        return {
            "status": "not_configured",
            "configured": False,
            "message": "Google Sheets yapilandirilmamis. Service Account JSON gerekli.",
        }

    result = await run_hotel_sheet_sync(db, conn, trigger="manual")

    # Audit
    await append_audit_log(
        scope="portfolio_sync",
        tenant_id=tenant_id,
        actor_user_id=user.get("_id", ""),
        actor_email=user.get("email", ""),
        action="sheet_sync_triggered",
        metadata={"hotel_id": hotel_id, "trigger": "manual", "status": result.get("status")},
    )

    return {
        "status": result.get("status", "unknown"),
        "run_id": result.get("_id"),
        "rows_read": result.get("rows_read", 0),
        "rows_changed": result.get("rows_changed", 0),
        "upserted": result.get("upserted", 0),
        "skipped": result.get("skipped", 0),
        "errors_count": result.get("errors_count", 0),
        "duration_ms": result.get("duration_ms", 0),
        "configured": True,
    }


# ── Sync All ──────────────────────────────────────────────

@router.post("/sync-all", dependencies=[AdminDep])
async def sync_all_sheets(
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    """Trigger sync for all enabled connections."""
    tenant_id = _tenant_id(user)
    if not is_configured(tenant_id):
        return {
            "status": "not_configured",
            "configured": False,
            "message": "Google Sheets yapilandirilmamis.",
        }

    connections = await db.hotel_portfolio_sources.find({
        "tenant_id": tenant_id,
        "sync_enabled": True,
    }).to_list(300)

    results = []
    for conn in connections:
        try:
            result = await run_hotel_sheet_sync(db, conn, trigger="manual_bulk")
            results.append({
                "hotel_id": conn["hotel_id"],
                "status": result.get("status"),
                "upserted": result.get("upserted", 0),
            })
        except Exception as e:
            results.append({
                "hotel_id": conn["hotel_id"],
                "status": "failed",
                "error": str(e),
            })

    return {
        "total": len(connections),
        "results": results,
        "configured": True,
    }


# ── Dashboard Status ──────────────────────────────────────

@router.get("/status", dependencies=[AdminDep])
async def get_portfolio_status(
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    """Portfolio sync dashboard summary."""
    tenant_id = _tenant_id(user)
    health = await get_portfolio_health(db, tenant_id)
    health["configured"] = is_configured(tenant_id)
    health["service_account_email"] = get_service_account_email(tenant_id)
    return health


# ── Sync Runs History ─────────────────────────────────────

@router.get("/runs", dependencies=[AdminDep])
async def list_sync_runs(
    hotel_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    """List recent sync runs."""
    tenant_id = user.get("tenant_id") or user["organization_id"]
    query: Dict[str, Any] = {"tenant_id": tenant_id}
    if hotel_id:
        query["hotel_id"] = hotel_id
    if status:
        query["status"] = status

    docs = await db.sheet_sync_runs.find(query).sort("started_at", -1).to_list(limit)
    return [serialize_doc(d) for d in docs]


# ── Stale Hotels ──────────────────────────────────────────

@router.get("/stale-hotels", dependencies=[AdminDep])
async def list_stale_hotels(
    stale_minutes: int = Query(30),
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    """List hotels with stale sheet data."""
    tenant_id = user.get("tenant_id") or user["organization_id"]
    stale = await get_stale_connections(db, tenant_id, stale_minutes)
    return [serialize_doc(s) for s in stale]


# ── Preview / Validate Mapping ────────────────────────────

class PreviewMappingRequest(BaseModel):
    sheet_id: str
    sheet_tab: str = "Sheet1"
    mapping: Dict[str, str] = Field(default_factory=dict)


@router.post("/preview-mapping", dependencies=[AdminDep])
async def preview_sheet_mapping(
    body: PreviewMappingRequest,
    user=Depends(get_current_user),
):
    """Read sheet and show mapped preview (first 20 rows)."""
    tenant_id = _tenant_id(user)
    if not is_configured(tenant_id):
        return _configured_or_false_payload()

    result = read_sheet(body.sheet_id, body.sheet_tab, tenant_id=tenant_id)
    if not result.success:
        raise AppError(400, "sheet_read_error", result.error or "Sheet okunamadi.")

    headers = result.data.get("headers", [])
    rows = result.data.get("rows", [])

    header_validation = validate_inventory_headers(headers)
    detected = header_validation["detected_mapping"]
    effective_mapping = body.mapping if body.mapping else detected

    from app.services.hotel_portfolio_sync_service import apply_mapping
    preview_rows = rows[:20]
    mapped = apply_mapping(headers, preview_rows, effective_mapping)

    return {
        "configured": True,
        "headers": headers,
        "detected_mapping": detected,
        "header_validation": header_validation,
        "effective_mapping": effective_mapping,
        "total_rows": len(rows),
        "preview": mapped[:20],
    }


# ── Hotels List (for connect wizard dropdown) ─────────────

@router.get("/available-hotels", dependencies=[AdminDep])
async def list_available_hotels(
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    """List hotels not yet connected to a sheet."""
    org_id = user["organization_id"]
    tenant_id = user.get("tenant_id") or org_id

    # Get connected hotel IDs
    connected_cursor = db.hotel_portfolio_sources.find(
        {"tenant_id": tenant_id},
        {"hotel_id": 1},
    )
    connected_ids = set()
    async for doc in connected_cursor:
        connected_ids.add(doc["hotel_id"])

    # Get all hotels
    hotels = await db.hotels.find(
        {"organization_id": org_id, "active": {"$ne": False}},
        {"_id": 1, "name": 1, "city": 1},
    ).to_list(1000)

    result = []
    for h in hotels:
        result.append({
            "_id": h["_id"],
            "name": h.get("name", ""),
            "city": h.get("city", ""),
            "connected": h["_id"] in connected_ids,
        })

    return result



# ── Write-Back Endpoints ─────────────────────────────────────

from app.services.sheet_writeback_service import (
    get_writeback_stats,
    process_pending_writebacks,
)


@router.get("/writeback/stats", dependencies=[AdminDep])
async def get_writeback_statistics(
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    """Get write-back queue statistics."""
    tenant_id = _tenant_id(user)
    stats = await get_writeback_stats(db, tenant_id)
    stats["configured"] = is_configured(tenant_id)
    return stats


@router.post("/writeback/process", dependencies=[AdminDep])
async def process_writeback_queue(
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    """Manually process pending write-back jobs."""
    tenant_id = _tenant_id(user)
    if not is_configured(tenant_id):
        return {
            "status": "not_configured",
            "configured": False,
            "message": "Google Sheets yapilandirilmamis.",
        }

    result = await process_pending_writebacks(db)
    return {
        "status": "processed",
        "configured": True,
        **result,
    }


@router.get("/writeback/queue", dependencies=[AdminDep])
async def list_writeback_queue(
    status: Optional[str] = Query(None),
    hotel_id: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    """List write-back queue items."""
    tenant_id = _tenant_id(user)
    query: Dict[str, Any] = {"tenant_id": tenant_id}
    if status:
        query["status"] = status
    if hotel_id:
        query["hotel_id"] = hotel_id

    docs = await db.sheet_writeback_queue.find(query).sort("created_at", -1).to_list(limit)
    return [serialize_doc(d) for d in docs]


@router.get("/changelog", dependencies=[AdminDep])
async def list_change_log(
    hotel_id: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    """List sheet change log entries."""
    tenant_id = _tenant_id(user)
    query: Dict[str, Any] = {"tenant_id": tenant_id}
    if hotel_id:
        query["hotel_id"] = hotel_id

    docs = await db.sheet_change_log.find(query).sort("created_at", -1).to_list(limit)
    return [serialize_doc(d) for d in docs]


# ══════════════════════════════════════════════════════════════
# SERVICE ACCOUNT MANAGEMENT
# ══════════════════════════════════════════════════════════════

class SaveServiceAccountRequest(BaseModel):
    service_account_json: str = Field(..., description="Google Service Account JSON")


@router.post("/service-account", dependencies=[AdminDep])
async def save_service_account(
    body: SaveServiceAccountRequest,
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    """Save Google Service Account JSON to database."""
    validated_payload = validate_service_account_json(body.service_account_json)
    raw = validated_payload["raw"]
    client_email = validated_payload["client_email"]
    project_id = validated_payload["project_id"]

    tenant_id = _tenant_id(user)

    # Save to DB
    await db.platform_config.update_one(
        {"tenant_id": tenant_id, "config_key": "google_service_account"},
        {
            "$set": {
                "config_value": raw,
                "client_email": client_email,
                "project_id": project_id,
                "updated_at": now_utc(),
                "updated_by": user.get("email", ""),
            },
            "$setOnInsert": {
                "_id": str(uuid.uuid4()),
                "tenant_id": tenant_id,
                "config_key": "google_service_account",
                "created_at": now_utc(),
            },
        },
        upsert=True,
    )

    # Update in-memory cache
    set_db_config(raw, tenant_id=tenant_id)

    # Audit log
    await append_audit_log(
        scope="sheets_config",
        tenant_id=tenant_id,
        actor_user_id=user.get("_id", ""),
        actor_email=user.get("email", ""),
        action="service_account_saved",
        after={"client_email": client_email, "project_id": project_id},
    )

    return {
        "status": "saved",
        "client_email": client_email,
        "project_id": project_id,
        "configured": True,
    }


@router.delete("/service-account", dependencies=[AdminDep])
async def delete_service_account(
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    """Remove Google Service Account configuration."""
    tenant_id = _tenant_id(user)
    await db.platform_config.delete_one({
        "tenant_id": tenant_id,
        "config_key": "google_service_account",
    })
    set_db_config("", tenant_id=tenant_id)

    await append_audit_log(
        scope="sheets_config",
        tenant_id=tenant_id,
        actor_user_id=user.get("_id", ""),
        actor_email=user.get("email", ""),
        action="service_account_deleted",
    )

    return {"status": "deleted", "configured": False}


# ══════════════════════════════════════════════════════════════
# AGENCY-SPECIFIC SHEET CONNECTIONS
# ══════════════════════════════════════════════════════════════

class ConnectAgencySheetRequest(BaseModel):
    hotel_id: str
    agency_id: str
    sheet_id: str
    sheet_tab: str = "Sheet1"
    writeback_tab: str = "Rezervasyonlar"
    mapping: Dict[str, str] = Field(default_factory=dict)
    sync_enabled: bool = True
    sync_interval_minutes: int = 5


@router.post("/connect-agency", dependencies=[AdminDep])
async def connect_agency_sheet(
    body: ConnectAgencySheetRequest,
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    """Connect a Google Sheet to a hotel×agency pair."""
    org_id = user["organization_id"]
    tenant_id = _tenant_id(user)

    # Validate hotel
    hotel = await db.hotels.find_one({"_id": body.hotel_id, "organization_id": org_id})
    if not hotel:
        raise AppError(404, "hotel_not_found", "Otel bulunamadi.")

    # Validate agency
    agency = await db.agencies.find_one({"_id": body.agency_id, "organization_id": org_id})
    if not agency:
        raise AppError(404, "agency_not_found", "Acenta bulunamadi.")

    # Check existing
    existing = await db.hotel_portfolio_sources.find_one({
        "tenant_id": tenant_id,
        "hotel_id": body.hotel_id,
        "agency_id": body.agency_id,
        "source_type": "google_sheets",
    })
    if existing:
        raise AppError(409, "connection_exists", "Bu otel-acenta ikilisi icin zaten bir sheet baglantisi var.")

    detected_headers = []
    detected_mapping = {}
    header_validation: Dict[str, Any] = {}
    writeback_bootstrap: Optional[Dict[str, Any]] = None
    validation_status = "pending_configuration"
    if is_configured(tenant_id):
        preflight = build_sheet_preflight(
            tenant_id=tenant_id,
            sheet_id=body.sheet_id,
            sheet_tab=body.sheet_tab,
            writeback_tab=body.writeback_tab,
            strict_headers=True,
            ensure_writeback=True,
        )
        sheet_title = preflight["sheet_title"]
        worksheets = preflight["worksheets"]
        detected_headers = preflight["detected_headers"]
        detected_mapping = preflight["detected_mapping"]
        header_validation = preflight["header_validation"]
        validation_summary = preflight["validation_summary"]
        writeback_validation = preflight["writeback_validation"]
        writeback_bootstrap = preflight["writeback_bootstrap"]
        validation_status = "validated"
    else:
        sheet_title = ""
        worksheets = []
        validation_summary = {}
        writeback_validation = None

    effective_mapping = body.mapping if body.mapping else detected_mapping

    doc = {
        "_id": str(uuid.uuid4()),
        "tenant_id": tenant_id,
        "organization_id": org_id,
        "hotel_id": body.hotel_id,
        "hotel_name": hotel.get("name", ""),
        "agency_id": body.agency_id,
        "agency_name": agency.get("name", ""),
        "source_type": "google_sheets",
        "sheet_id": body.sheet_id,
        "sheet_tab": body.sheet_tab,
        "writeback_tab": body.writeback_tab,
        "sheet_title": sheet_title,
        "mapping": effective_mapping,
        "validation_status": validation_status,
        "validation_summary": validation_summary,
        "sync_enabled": body.sync_enabled,
        "sync_interval_minutes": body.sync_interval_minutes,
        "last_sync_at": None,
        "last_sync_status": None,
        "last_error": None,
        "last_fingerprint": None,
        "status": "active",
        "created_at": now_utc(),
        "updated_at": now_utc(),
        "created_by": user.get("email", ""),
    }
    await db.hotel_portfolio_sources.insert_one(doc)

    await append_audit_log(
        scope="portfolio_sync",
        tenant_id=tenant_id,
        actor_user_id=user.get("_id", ""),
        actor_email=user.get("email", ""),
        action="agency_sheet_connected",
        after={
            "hotel_id": body.hotel_id,
            "agency_id": body.agency_id,
            "sheet_id": body.sheet_id,
        },
    )

    result = serialize_doc(doc)
    result["configured"] = is_configured(tenant_id)
    result["detected_headers"] = detected_headers
    result["detected_mapping"] = detected_mapping
    result["header_validation"] = header_validation
    result["validation_summary"] = validation_summary
    result["writeback_validation"] = writeback_validation
    result["writeback_bootstrap"] = writeback_bootstrap
    result["worksheets"] = worksheets
    return result


@router.get("/agency-connections", dependencies=[AdminDep])
async def list_agency_connections(
    hotel_id: Optional[str] = Query(None),
    agency_id: Optional[str] = Query(None),
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    """List agency-specific sheet connections."""
    tenant_id = _tenant_id(user)
    query: Dict[str, Any] = {
        "tenant_id": tenant_id,
        "agency_id": {"$exists": True, "$ne": None},
    }
    if hotel_id:
        query["hotel_id"] = hotel_id
    if agency_id:
        query["agency_id"] = agency_id

    docs = await db.hotel_portfolio_sources.find(query).sort("created_at", -1).to_list(500)
    return [serialize_doc(d) for d in docs]


@router.get("/agencies-for-hotel/{hotel_id}", dependencies=[AdminDep])
async def list_agencies_for_hotel(
    hotel_id: str,
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    """List agencies for hotel sheet connection wizard dropdown.

    First tries agency_hotel_links; if none, falls back to all active agencies.
    """
    org_id = user["organization_id"]
    tenant_id = _tenant_id(user)

    # Try hotel-specific links first
    links = await db.agency_hotel_links.find({
        "organization_id": org_id,
        "hotel_id": hotel_id,
        "active": True,
    }).to_list(500)

    agency_ids = [lnk["agency_id"] for lnk in links]

    if agency_ids:
        agencies = await db.agencies.find(
            {"_id": {"$in": agency_ids}},
        ).to_list(500)
    else:
        # Fallback: return all active agencies in the organization
        agencies = await db.agencies.find(
            {"organization_id": org_id, "active": {"$ne": False}},
        ).to_list(500)
        agency_ids = [a["_id"] for a in agencies]

    if not agencies:
        return []

    # Check which already have connections
    existing_conns = await db.hotel_portfolio_sources.find({
        "tenant_id": tenant_id,
        "hotel_id": hotel_id,
        "agency_id": {"$in": agency_ids},
    }).to_list(500)
    connected_agency_ids = {c["agency_id"] for c in existing_conns}

    return [
        {
            "_id": a["_id"],
            "name": a.get("name", ""),
            "contact_email": a.get("contact_email", ""),
            "connected": a["_id"] in connected_agency_ids,
        }
        for a in agencies
    ]

