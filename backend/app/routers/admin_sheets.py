"""Portfolio Sync Engine — Admin Sheets API.

Multi-hotel Google Sheets sync management.
New endpoints under /api/admin/sheets/*

Backward compatible: existing /api/admin/import/* untouched.
"""
from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, Query
from pydantic import BaseModel, Field

from app.auth import get_current_user, require_roles
from app.db import get_db
from app.errors import AppError
from app.services.audit_log_service import append_audit_log
from app.services.sheets_provider import (
    get_config_status,
    get_service_account_email,
    get_sheet_metadata,
    is_configured,
    read_sheet,
    set_db_config,
)
from app.services.hotel_portfolio_sync_service import (
    auto_detect_mapping,
    get_portfolio_health,
    get_stale_connections,
    run_hotel_sheet_sync,
)
from app.utils import now_utc, serialize_doc

router = APIRouter(prefix="/api/admin/sheets", tags=["admin_sheets"])
AdminDep = Depends(require_roles(["super_admin", "admin"]))


# ── Config Status ─────────────────────────────────────────

@router.get("/config", dependencies=[AdminDep])
async def get_sheets_config(user=Depends(get_current_user)):
    """Return Google Sheets integration configuration status."""
    return get_config_status()


# ── Connect a Hotel Sheet ─────────────────────────────────

class ConnectSheetRequest(BaseModel):
    hotel_id: str
    sheet_id: str
    sheet_tab: str = "Sheet1"
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
    org_id = user["organization_id"]
    tenant_id = user.get("tenant_id") or org_id

    # Check if connection already exists
    existing = await db.hotel_portfolio_sources.find_one({
        "tenant_id": tenant_id,
        "hotel_id": body.hotel_id,
        "source_type": "google_sheets",
    })
    if existing:
        raise AppError(409, "connection_exists", "Bu otel icin zaten bir sheet baglantisi var.")

    # Validate hotel exists
    hotel = await db.hotels.find_one({"_id": body.hotel_id, "organization_id": org_id})
    if not hotel:
        raise AppError(404, "hotel_not_found", "Otel bulunamadi.")

    # Try to detect headers if configured
    detected_headers = []
    detected_mapping = {}
    sheet_title = ""
    worksheets = []

    if is_configured():
        # Get metadata
        meta_result = get_sheet_metadata(body.sheet_id)
        if meta_result.success:
            sheet_title = meta_result.data.get("title", "")
            worksheets = meta_result.data.get("worksheets", [])

        # Read headers for auto-detect
        read_result = read_sheet(body.sheet_id, body.sheet_tab, "1:1")
        if read_result.success:
            detected_headers = read_result.data.get("headers", [])
            if detected_headers and not body.mapping:
                detected_mapping = auto_detect_mapping(detected_headers)

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
        "sheet_title": sheet_title,
        "mapping": effective_mapping,
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

    # Audit log
    await append_audit_log(
        scope="portfolio_sync",
        tenant_id=tenant_id,
        actor_user_id=user.get("_id", ""),
        actor_email=user.get("email", ""),
        action="sheet_connected",
        after={"hotel_id": body.hotel_id, "sheet_id": body.sheet_id},
    )

    result = serialize_doc(doc)
    result["configured"] = is_configured()
    result["service_account_email"] = get_service_account_email()
    result["detected_headers"] = detected_headers
    result["detected_mapping"] = detected_mapping
    result["worksheets"] = worksheets
    return result


# ── List Connections ──────────────────────────────────────

@router.get("/connections", dependencies=[AdminDep])
async def list_sheet_connections(
    hotel_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    """List all hotel sheet connections."""
    tenant_id = user.get("tenant_id") or user["organization_id"]
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
    result["configured"] = is_configured()
    return result


# ── Update Connection ─────────────────────────────────────

class UpdateConnectionRequest(BaseModel):
    sync_enabled: Optional[bool] = None
    sync_interval_minutes: Optional[int] = None
    mapping: Optional[Dict[str, str]] = None
    sheet_tab: Optional[str] = None
    status: Optional[str] = None


@router.patch("/connections/{hotel_id}", dependencies=[AdminDep])
async def update_hotel_connection(
    hotel_id: str,
    body: UpdateConnectionRequest,
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    """Update connection settings (enable/disable, mapping, interval)."""
    tenant_id = user.get("tenant_id") or user["organization_id"]
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
    tenant_id = user.get("tenant_id") or user["organization_id"]
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
    tenant_id = user.get("tenant_id") or user["organization_id"]
    conn = await db.hotel_portfolio_sources.find_one({
        "tenant_id": tenant_id,
        "hotel_id": hotel_id,
    })
    if not conn:
        raise AppError(404, "connection_not_found", "Sheet baglantisi bulunamadi.")

    if not is_configured():
        return {
            "status": "not_configured",
            "configured": False,
            "message": "Google Sheets yapilandirilmamis. GOOGLE_SERVICE_ACCOUNT_JSON env var gerekli.",
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
    if not is_configured():
        return {
            "status": "not_configured",
            "configured": False,
            "message": "Google Sheets yapilandirilmamis.",
        }

    tenant_id = user.get("tenant_id") or user["organization_id"]
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
    tenant_id = user.get("tenant_id") or user["organization_id"]
    health = await get_portfolio_health(db, tenant_id)
    health["configured"] = is_configured()
    health["service_account_email"] = get_service_account_email()
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
    if not is_configured():
        return {
            "configured": False,
            "message": "Google Sheets yapilandirilmamis.",
            "headers": [],
            "preview": [],
            "detected_mapping": {},
        }

    result = read_sheet(body.sheet_id, body.sheet_tab)
    if not result.success:
        raise AppError(400, "sheet_read_error", result.error or "Sheet okunamadi.")

    headers = result.data.get("headers", [])
    rows = result.data.get("rows", [])

    detected = auto_detect_mapping(headers)
    effective_mapping = body.mapping if body.mapping else detected

    from app.services.hotel_portfolio_sync_service import apply_mapping
    preview_rows = rows[:20]
    mapped = apply_mapping(headers, preview_rows, effective_mapping)

    return {
        "configured": True,
        "headers": headers,
        "detected_mapping": detected,
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
    tenant_id = user.get("tenant_id") or user["organization_id"]
    stats = await get_writeback_stats(db, tenant_id)
    stats["configured"] = is_configured()
    return stats


@router.post("/writeback/process", dependencies=[AdminDep])
async def process_writeback_queue(
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    """Manually process pending write-back jobs."""
    if not is_configured():
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
    tenant_id = user.get("tenant_id") or user["organization_id"]
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
    tenant_id = user.get("tenant_id") or user["organization_id"]
    query: Dict[str, Any] = {"tenant_id": tenant_id}
    if hotel_id:
        query["hotel_id"] = hotel_id

    docs = await db.sheet_change_log.find(query).sort("created_at", -1).to_list(limit)
    return [serialize_doc(d) for d in docs]
