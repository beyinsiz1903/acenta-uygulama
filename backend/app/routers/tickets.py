"""QR Ticket + Check-in API router (C).

Permissions: tickets.create, tickets.checkin, tickets.view, tickets.cancel
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from app.auth import get_current_user, require_roles
from app.db import get_db
from app.services.audit_hash_chain import write_chained_audit_log
from app.services.ticket_service import (
    cancel_ticket,
    check_in_ticket,
    create_ticket,
    get_checkin_stats,
    get_ticket_by_code,
    list_tickets,
)

router = APIRouter(prefix="/api/tickets", tags=["tickets"])


class CreateTicketIn(BaseModel):
    reservation_id: str
    product_name: str
    customer_name: str
    customer_email: str = ""
    customer_phone: str = ""
    event_date: str = ""
    seat_info: str = ""
    notes: str = ""


class CheckInIn(BaseModel):
    ticket_code: str


@router.post("")
async def create_ticket_endpoint(
    payload: CreateTicketIn,
    request: Request,
    user=Depends(get_current_user),
):
    """Create a ticket for a reservation. Idempotent per reservation."""
    org_id = user["organization_id"]
    tenant_id = user.get("tenant_id", org_id)

    result = await create_ticket(
        tenant_id=tenant_id,
        org_id=org_id,
        reservation_id=payload.reservation_id,
        product_name=payload.product_name,
        customer_name=payload.customer_name,
        customer_email=payload.customer_email,
        customer_phone=payload.customer_phone,
        event_date=payload.event_date,
        seat_info=payload.seat_info,
        notes=payload.notes,
        created_by=user.get("email", ""),
    )

    try:
        db = await get_db()
        await write_chained_audit_log(
            db,
            organization_id=org_id,
            tenant_id=tenant_id,
            actor={"email": user.get("email"), "roles": user.get("roles")},
            action="TICKET_CREATED",
            target_type="ticket",
            target_id=result.get("ticket_code", ""),
        )
    except Exception:
        pass
    return result


@router.post("/check-in")
async def check_in(
    payload: CheckInIn,
    request: Request,
    user=Depends(get_current_user),
):
    """Check in a ticket by code. Returns error if already checked in."""
    tenant_id = user.get("tenant_id", user["organization_id"])
    result = await check_in_ticket(
        tenant_id=tenant_id,
        ticket_code=payload.ticket_code,
        checked_in_by=user.get("email", ""),
    )
    if "error" in result:
        status_map = {
            "not_found": 404,
            "already_checked_in": 409,
            "canceled": 410,
            "expired": 410,
        }
        code = result.get("code", "error")
        raise HTTPException(
            status_code=status_map.get(code, 400),
            detail=result["error"],
        )

    try:
        db = await get_db()
        await write_chained_audit_log(
            db,
            organization_id=user["organization_id"],
            tenant_id=tenant_id,
            actor={"email": user.get("email"), "roles": user.get("roles")},
            action="TICKET_CHECKED_IN",
            target_type="ticket",
            target_id=payload.ticket_code,
        )
    except Exception:
        pass
    return result


@router.get("/lookup/{ticket_code}")
async def lookup_ticket(
    ticket_code: str,
    user=Depends(get_current_user),
):
    """Look up a ticket by code."""
    tenant_id = user.get("tenant_id", user["organization_id"])
    ticket = await get_ticket_by_code(tenant_id, ticket_code)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket


@router.post("/{ticket_code}/cancel")
async def cancel_ticket_endpoint(
    ticket_code: str,
    user=Depends(require_roles(["super_admin", "admin"])),
):
    """Cancel an active ticket."""
    tenant_id = user.get("tenant_id", user["organization_id"])
    result = await cancel_ticket(tenant_id, ticket_code)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("")
async def get_tickets(
    status: Optional[str] = Query(None),
    reservation_id: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    user=Depends(get_current_user),
):
    """List tickets."""
    org_id = user["organization_id"]
    tenant_id = user.get("tenant_id", "")
    items = await list_tickets(
        org_id=org_id,
        tenant_id=tenant_id,
        status=status,
        reservation_id=reservation_id,
        limit=limit,
    )
    return {"items": items, "count": len(items)}


@router.get("/stats")
async def get_stats(user=Depends(get_current_user)):
    """Get check-in statistics."""
    org_id = user["organization_id"]
    tenant_id = user.get("tenant_id", "")
    stats = await get_checkin_stats(org_id, tenant_id)
    return stats
