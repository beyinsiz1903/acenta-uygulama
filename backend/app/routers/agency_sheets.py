"""Agency-side Google Sheets connection management.

Each agency manages their own sheet connections. The agency_id is
auto-detected from the logged-in user's JWT, so no agency selector needed.

Endpoints:
  GET  /api/agency/sheets/connections       — list my connections
  GET  /api/agency/sheets/hotels            — hotels I can connect
  POST /api/agency/sheets/connect           — create connection (auto agency)
  DELETE /api/agency/sheets/connections/{id} — remove a connection
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.auth import get_current_user, require_roles
from app.db import get_db
from app.errors import AppError
from app.services.audit_log_service import append_audit_log
from app.services.sheets_provider import (
    get_service_account_email,
    is_configured,
    read_sheet,
)
from app.services.hotel_portfolio_sync_service import auto_detect_mapping
from app.utils import now_utc, serialize_doc

router = APIRouter(prefix="/api/agency/sheets", tags=["agency_sheets"])

AgencyDep = Depends(require_roles(["agency_admin", "agency_agent", "admin", "super_admin"]))


def _get_agency_id(user: dict) -> str:
    agency_id = user.get("agency_id")
    if not agency_id:
        raise AppError(403, "no_agency", "Bu islem icin bir acenteye bagli olmalisiniz.")
    return agency_id


# ── List My Hotels ────────────────────────────────────────

@router.get("/hotels", dependencies=[AgencyDep])
async def list_my_hotels(
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    """List hotels available to this agency for sheet connections."""
    agency_id = _get_agency_id(user)
    org_id = user["organization_id"]
    tenant_id = user.get("tenant_id") or org_id

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
    tenant_id = user.get("tenant_id") or user["organization_id"]

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
    tenant_id = user.get("tenant_id") or org_id

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

    # Try to detect headers
    detected_mapping = {}
    if is_configured():
        read_result = read_sheet(body.sheet_id, body.sheet_tab, "1:1")
        if read_result.success:
            headers = read_result.data.get("headers", [])
            if headers:
                detected_mapping = auto_detect_mapping(headers)

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
        "mapping": detected_mapping,
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
    result["configured"] = is_configured()
    result["service_account_email"] = get_service_account_email()
    return result


# ── Delete Connection ─────────────────────────────────────

@router.delete("/connections/{connection_id}", dependencies=[AgencyDep])
async def delete_connection(
    connection_id: str,
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    """Delete one of this agency's sheet connections."""
    agency_id = _get_agency_id(user)
    tenant_id = user.get("tenant_id") or user["organization_id"]

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
