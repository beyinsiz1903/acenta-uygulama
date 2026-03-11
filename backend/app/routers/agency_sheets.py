"""Agency-side Google Sheets connection management.

Each agency manages their own sheet connections. The agency_id is
auto-detected from the logged-in user's JWT, so no agency selector needed.

Endpoints:
  GET  /api/agency/sheets/connections       — list my connections
  GET  /api/agency/sheets/hotels            — hotels I can connect
  POST /api/agency/sheets/connect           — create connection (auto agency)
  DELETE /api/agency/sheets/connections/{id} — remove a connection
  PATCH /api/agency/sheets/connections/{id}/settings — update sync settings
  GET  /api/agency/sheets/sync-status       — auto-sync overview
  GET  /api/agency/sheets/sync-history      — sync run history
  POST /api/agency/sheets/credentials       — save agency Google credentials
  GET  /api/agency/sheets/credentials/status — check credential status
  DELETE /api/agency/sheets/credentials     — remove agency credentials
"""
from __future__ import annotations

import json
import uuid
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from app.auth import get_current_user, require_roles
from app.db import get_db
from app.errors import AppError
from app.services.audit_log_service import append_audit_log
from app.services.sheet_connection_service import (
    build_sheet_preflight,
)
from app.services.sheets_provider import (
    get_service_account_email,
    is_configured,
    set_db_config,
)
from app.services.hotel_portfolio_sync_service import run_hotel_sheet_sync
from app.utils import now_utc, serialize_doc

router = APIRouter(prefix="/api/agency/sheets", tags=["agency_sheets"])

AgencyDep = Depends(require_roles(["agency_admin", "agency_agent", "admin", "super_admin"]))


def _get_agency_id(user: dict) -> str:
    agency_id = user.get("agency_id")
    if not agency_id:
        raise AppError(403, "no_agency", "Bu islem icin bir acenteye bagli olmalisiniz.")
    return agency_id


def _tenant_id(user: dict) -> str:
    return user.get("tenant_id") or user["organization_id"]


# ── List My Hotels ────────────────────────────────────────

@router.get("/hotels", dependencies=[AgencyDep])
async def list_my_hotels(
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    """List hotels available to this agency for sheet connections."""
    agency_id = _get_agency_id(user)
    org_id = user["organization_id"]
    tenant_id = _tenant_id(user)

    # Get linked hotels
    links = await db.agency_hotel_links.find({
        "organization_id": org_id,
        "agency_id": agency_id,
        "active": True,
    }).to_list(500)

    hotel_ids = [lnk["hotel_id"] for lnk in links]

    # Fallback: if no links, get all active hotels in org
    if not hotel_ids:
        hotels = await db.hotels.find(
            {"organization_id": org_id, "active": {"$ne": False}},
            {"_id": 1, "name": 1, "city": 1},
        ).to_list(500)
    else:
        hotels = await db.hotels.find(
            {"_id": {"$in": hotel_ids}},
            {"_id": 1, "name": 1, "city": 1},
        ).to_list(500)

    # Check which already have connections
    existing = await db.hotel_portfolio_sources.find({
        "tenant_id": tenant_id,
        "agency_id": agency_id,
    }).to_list(500)
    connected_hotel_ids = {c["hotel_id"] for c in existing}

    return [
        {
            "_id": h["_id"],
            "name": h.get("name", ""),
            "city": h.get("city", ""),
            "connected": h["_id"] in connected_hotel_ids,
        }
        for h in hotels
    ]


# ── List My Connections ───────────────────────────────────

@router.get("/connections", dependencies=[AgencyDep])
async def list_my_connections(
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    """List this agency's sheet connections."""
    agency_id = _get_agency_id(user)
    tenant_id = _tenant_id(user)

    docs = await db.hotel_portfolio_sources.find({
        "tenant_id": tenant_id,
        "agency_id": agency_id,
        "source_type": "google_sheets",
    }).sort("created_at", -1).to_list(200)

    return [serialize_doc(d) for d in docs]


# ── Connect a Sheet ───────────────────────────────────────

class AgencyConnectSheetRequest(BaseModel):
    hotel_id: str
    sheet_id: str
    sheet_tab: str = "Sheet1"
    writeback_tab: str = "Rezervasyonlar"


@router.post("/connect", dependencies=[AgencyDep])
async def connect_sheet(
    body: AgencyConnectSheetRequest,
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    """Connect a Google Sheet to a hotel. Agency auto-detected from user."""
    agency_id = _get_agency_id(user)
    org_id = user["organization_id"]
    tenant_id = _tenant_id(user)

    # Validate hotel
    hotel = await db.hotels.find_one({"_id": body.hotel_id, "organization_id": org_id})
    if not hotel:
        raise AppError(404, "hotel_not_found", "Otel bulunamadi.")

    # Check existing
    existing = await db.hotel_portfolio_sources.find_one({
        "tenant_id": tenant_id,
        "hotel_id": body.hotel_id,
        "agency_id": agency_id,
        "source_type": "google_sheets",
    })
    if existing:
        raise AppError(409, "connection_exists", "Bu otel icin zaten bir sheet baglantiniz var.")

    # Get agency name
    agency = await db.agencies.find_one({"_id": agency_id})
    agency_name = agency.get("name", "") if agency else ""

    headers = []
    detected_mapping = {}
    header_validation = {}
    validation_summary = {}
    sheet_title = ""
    worksheets = []
    writeback_validation = None
    writeback_bootstrap = None
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
        headers = preflight["detected_headers"]
        detected_mapping = preflight["detected_mapping"]
        header_validation = preflight["header_validation"]
        validation_summary = preflight["validation_summary"]
        writeback_validation = preflight["writeback_validation"]
        writeback_bootstrap = preflight["writeback_bootstrap"]
        validation_status = "validated"

    doc = {
        "_id": str(uuid.uuid4()),
        "tenant_id": tenant_id,
        "organization_id": org_id,
        "hotel_id": body.hotel_id,
        "hotel_name": hotel.get("name", ""),
        "agency_id": agency_id,
        "agency_name": agency_name,
        "source_type": "google_sheets",
        "sheet_id": body.sheet_id,
        "sheet_tab": body.sheet_tab,
        "writeback_tab": body.writeback_tab,
        "sheet_title": sheet_title,
        "mapping": detected_mapping,
        "validation_status": validation_status,
        "validation_summary": validation_summary,
        "sync_enabled": True,
        "sync_interval_minutes": 5,
        "last_sync_at": None,
        "last_sync_status": None,
        "last_error": None,
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
            "agency_id": agency_id,
            "sheet_id": body.sheet_id,
        },
    )

    result = serialize_doc(doc)
    result["configured"] = is_configured(tenant_id)
    result["service_account_email"] = get_service_account_email(tenant_id)
    result["detected_headers"] = headers
    result["detected_mapping"] = detected_mapping
    result["header_validation"] = header_validation
    result["validation_summary"] = validation_summary
    result["writeback_validation"] = writeback_validation
    result["writeback_bootstrap"] = writeback_bootstrap
    result["worksheets"] = worksheets
    return result


# ── Sync Now ──────────────────────────────────────────────

@router.post("/sync/{connection_id}", dependencies=[AgencyDep])
async def sync_connection(
    connection_id: str,
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    """Trigger manual sync for one of this agency's connections."""
    agency_id = _get_agency_id(user)
    tenant_id = _tenant_id(user)

    conn = await db.hotel_portfolio_sources.find_one({
        "_id": connection_id,
        "tenant_id": tenant_id,
        "agency_id": agency_id,
    })
    if not conn:
        raise AppError(404, "not_found", "Baglanti bulunamadi.")

    if not is_configured(tenant_id):
        return {
            "status": "not_configured",
            "configured": False,
            "message": "Google Sheets yapilandirilmamis. Admin panelinden Service Account JSON'u girebilirsiniz.",
        }

    result = await run_hotel_sheet_sync(db, conn, trigger="manual")
    return {
        "status": result.get("status", "unknown"),
        "run_id": result.get("_id"),
        "rows_read": result.get("rows_read", 0),
        "rows_changed": result.get("rows_changed", 0),
        "upserted": result.get("upserted", 0),
        "errors_count": result.get("errors_count", 0),
        "duration_ms": result.get("duration_ms", 0),
        "configured": True,
    }


# ── Delete Connection ─────────────────────────────────────

@router.delete("/connections/{connection_id}", dependencies=[AgencyDep])
async def delete_connection(
    connection_id: str,
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    """Delete one of this agency's sheet connections."""
    agency_id = _get_agency_id(user)
    tenant_id = _tenant_id(user)

    result = await db.hotel_portfolio_sources.delete_one({
        "_id": connection_id,
        "tenant_id": tenant_id,
        "agency_id": agency_id,
    })
    if result.deleted_count == 0:
        raise AppError(404, "not_found", "Baglanti bulunamadi.")

    await append_audit_log(
        scope="portfolio_sync",
        tenant_id=tenant_id,
        actor_user_id=user.get("_id", ""),
        actor_email=user.get("email", ""),
        action="agency_sheet_disconnected",
        before={"connection_id": connection_id},
    )

    return {"deleted": True}


# ── Update Connection Settings ────────────────────────────

class UpdateConnectionSettingsRequest(BaseModel):
    sync_enabled: Optional[bool] = None
    sync_interval_minutes: Optional[int] = None


@router.patch("/connections/{connection_id}/settings", dependencies=[AgencyDep])
async def update_connection_settings(
    connection_id: str,
    body: UpdateConnectionSettingsRequest,
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    """Update sync settings for a connection."""
    agency_id = _get_agency_id(user)
    tenant_id = _tenant_id(user)

    conn = await db.hotel_portfolio_sources.find_one({
        "_id": connection_id,
        "tenant_id": tenant_id,
        "agency_id": agency_id,
    })
    if not conn:
        raise AppError(404, "not_found", "Baglanti bulunamadi.")

    update_fields: Dict[str, Any] = {"updated_at": now_utc()}
    if body.sync_enabled is not None:
        update_fields["sync_enabled"] = body.sync_enabled
    if body.sync_interval_minutes is not None:
        if body.sync_interval_minutes < 1 or body.sync_interval_minutes > 1440:
            raise AppError(400, "invalid_interval", "Sync araligi 1 ile 1440 dakika arasinda olmalidir.")
        update_fields["sync_interval_minutes"] = body.sync_interval_minutes

    await db.hotel_portfolio_sources.update_one(
        {"_id": connection_id},
        {"$set": update_fields},
    )

    updated = await db.hotel_portfolio_sources.find_one({"_id": connection_id})
    return serialize_doc(updated)


# ── Auto-Sync Status Overview ─────────────────────────────

@router.get("/sync-status", dependencies=[AgencyDep])
async def get_sync_status(
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    """Get auto-sync overview for this agency's connections."""
    agency_id = _get_agency_id(user)
    tenant_id = _tenant_id(user)

    conns = await db.hotel_portfolio_sources.find({
        "tenant_id": tenant_id,
        "agency_id": agency_id,
        "source_type": "google_sheets",
    }).to_list(200)

    connections_status = []
    for c in conns:
        connections_status.append({
            "connection_id": c["_id"],
            "hotel_id": c.get("hotel_id", ""),
            "hotel_name": c.get("hotel_name", ""),
            "sync_enabled": c.get("sync_enabled", False),
            "sync_interval_minutes": c.get("sync_interval_minutes", 5),
            "last_sync_at": c.get("last_sync_at"),
            "last_sync_status": c.get("last_sync_status"),
            "last_error": c.get("last_error"),
        })

    total = len(conns)
    enabled = sum(1 for c in conns if c.get("sync_enabled"))
    healthy = sum(1 for c in conns if c.get("last_sync_status") in ("success", "no_change"))
    failed = sum(1 for c in conns if c.get("last_sync_status") in ("error", "failed"))

    return {
        "total_connections": total,
        "sync_enabled_count": enabled,
        "healthy_count": healthy,
        "failed_count": failed,
        "scheduler_active": True,
        "connections": connections_status,
    }


# ── Sync History ──────────────────────────────────────────

@router.get("/sync-history", dependencies=[AgencyDep])
async def get_sync_history(
    connection_id: Optional[str] = Query(None),
    limit: int = Query(20, le=100),
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    """Get sync run history for this agency."""
    agency_id = _get_agency_id(user)
    tenant_id = _tenant_id(user)

    # Get agency's connection IDs
    conns = await db.hotel_portfolio_sources.find({
        "tenant_id": tenant_id,
        "agency_id": agency_id,
    }).to_list(200)
    conn_ids = [c["_id"] for c in conns]
    if not conn_ids:
        return {"items": [], "total": 0}

    query: Dict[str, Any] = {"connection_id": {"$in": conn_ids}}
    if connection_id and connection_id in conn_ids:
        query["connection_id"] = connection_id

    runs = await db.sheet_sync_runs.find(query).sort("started_at", -1).to_list(limit)

    # Build hotel name map
    hotel_ids = list({c.get("hotel_id", "") for c in conns})
    hotels = await db.hotels.find({"_id": {"$in": hotel_ids}}, {"_id": 1, "name": 1}).to_list(200)
    hotel_name_map = {h["_id"]: h.get("name", "") for h in hotels}
    conn_hotel_map = {c["_id"]: c.get("hotel_id", "") for c in conns}

    items = []
    for run in runs:
        hotel_id = run.get("hotel_id") or conn_hotel_map.get(run.get("connection_id", ""), "")
        items.append({
            "run_id": run["_id"],
            "connection_id": run.get("connection_id", ""),
            "hotel_id": hotel_id,
            "hotel_name": hotel_name_map.get(hotel_id, ""),
            "trigger": run.get("trigger", "unknown"),
            "status": run.get("status", "unknown"),
            "rows_read": run.get("rows_read", 0),
            "rows_changed": run.get("rows_changed", 0),
            "upserted": run.get("upserted", 0),
            "errors_count": run.get("errors_count", 0),
            "started_at": run.get("started_at"),
            "finished_at": run.get("finished_at"),
            "duration_ms": run.get("duration_ms", 0),
        })

    return {"items": items, "total": len(items)}


# ── Agency Google Sheets Credentials ──────────────────────

class SaveCredentialsRequest(BaseModel):
    service_account_json: str


@router.post("/credentials", dependencies=[AgencyDep])
async def save_agency_credentials(
    body: SaveCredentialsRequest,
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    """Save agency-specific Google Service Account credentials."""
    agency_id = _get_agency_id(user)
    tenant_id = _tenant_id(user)

    # Validate JSON
    try:
        creds_data = json.loads(body.service_account_json)
        if "client_email" not in creds_data or "private_key" not in creds_data:
            raise AppError(400, "invalid_credentials", "Gecersiz Service Account JSON. 'client_email' ve 'private_key' alanlari gerekli.")
    except json.JSONDecodeError:
        raise AppError(400, "invalid_json", "Gecersiz JSON formati.")

    # Save to platform_config with agency-specific key
    config_key = f"google_service_account_agency_{agency_id}"
    await db.platform_config.update_one(
        {"config_key": config_key, "tenant_id": tenant_id},
        {
            "$set": {
                "config_value": body.service_account_json,
                "agency_id": agency_id,
                "updated_at": now_utc(),
                "updated_by": user.get("email", ""),
            },
            "$setOnInsert": {
                "_id": str(uuid.uuid4()),
                "config_key": config_key,
                "tenant_id": tenant_id,
                "created_at": now_utc(),
            },
        },
        upsert=True,
    )

    # Update in-memory cache
    set_db_config(body.service_account_json, tenant_id=f"agency_{agency_id}")

    await append_audit_log(
        scope="portfolio_sync",
        tenant_id=tenant_id,
        actor_user_id=user.get("_id", ""),
        actor_email=user.get("email", ""),
        action="agency_credentials_saved",
        after={"agency_id": agency_id, "client_email": creds_data.get("client_email", "")},
    )

    return {
        "status": "saved",
        "client_email": creds_data.get("client_email", ""),
        "project_id": creds_data.get("project_id", ""),
    }


@router.get("/credentials/status", dependencies=[AgencyDep])
async def get_credentials_status(
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    """Check if this agency has its own Google credentials."""
    agency_id = _get_agency_id(user)
    tenant_id = _tenant_id(user)

    config_key = f"google_service_account_agency_{agency_id}"
    config = await db.platform_config.find_one(
        {"config_key": config_key, "tenant_id": tenant_id},
        {"_id": 0, "config_value": 1, "updated_at": 1, "updated_by": 1},
    )

    has_own_credentials = config is not None and bool(config.get("config_value"))
    own_email = None
    if has_own_credentials:
        try:
            data = json.loads(config["config_value"])
            own_email = data.get("client_email")
        except (json.JSONDecodeError, KeyError):
            pass

    # Check global credentials
    global_configured = is_configured(tenant_id)
    global_email = get_service_account_email(tenant_id) if global_configured else None

    return {
        "has_own_credentials": has_own_credentials,
        "own_service_account_email": own_email,
        "own_updated_at": config.get("updated_at") if config else None,
        "own_updated_by": config.get("updated_by") if config else None,
        "global_configured": global_configured,
        "global_service_account_email": global_email,
        "active_source": "agency" if has_own_credentials else ("global" if global_configured else "none"),
    }


@router.delete("/credentials", dependencies=[AgencyDep])
async def delete_agency_credentials(
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    """Remove agency-specific Google credentials (falls back to global)."""
    agency_id = _get_agency_id(user)
    tenant_id = _tenant_id(user)

    config_key = f"google_service_account_agency_{agency_id}"
    result = await db.platform_config.delete_one({
        "config_key": config_key,
        "tenant_id": tenant_id,
    })

    # Clear from in-memory cache
    set_db_config("", tenant_id=f"agency_{agency_id}")

    await append_audit_log(
        scope="portfolio_sync",
        tenant_id=tenant_id,
        actor_user_id=user.get("_id", ""),
        actor_email=user.get("email", ""),
        action="agency_credentials_deleted",
        after={"agency_id": agency_id},
    )

    return {
        "deleted": result.deleted_count > 0,
        "fallback": "global" if is_configured(tenant_id) else "none",
    }
