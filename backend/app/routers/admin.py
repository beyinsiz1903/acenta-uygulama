from __future__ import annotations

import uuid
from datetime import timedelta
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Request

from app.auth import get_current_user, require_roles
from app.db import get_db
from app.services.audit import write_audit_log
from app.schemas import (
    AgencyHotelLinkCreateIn,
    AgencyHotelLinkPatchIn,
    HotelCreateIn,
    HotelForceSalesOverrideIn,
)
from app.utils import now_utc, serialize_doc, to_object_id

router = APIRouter(prefix="/api/admin", tags=["admin"])


def _new_id() -> str:
    return str(uuid.uuid4())


def _oid_or_404(id_str: str):
    """Convert string ID to ObjectId or raise 404"""
    try:
        return to_object_id(id_str)
    except Exception:
        raise HTTPException(status_code=404, detail="EMAIL_JOB_NOT_FOUND")


@router.post("/agencies", dependencies=[Depends(require_roles(["super_admin"]))])
async def create_agency(payload: dict, user=Depends(get_current_user)):
    """Create an agency.

    Minimal payload for Phase-1:
      {"name": str}

    We intentionally keep this payload flexible for MVP.
    """

    db = await get_db()
    name = (payload or {}).get("name")
    if not name:
        raise HTTPException(status_code=400, detail="name gerekli")

    doc = {
        "_id": _new_id(),
        "organization_id": user["organization_id"],
        "name": name,
        "created_at": now_utc(),
        "updated_at": now_utc(),
        "created_by": user.get("email"),
        "updated_by": user.get("email"),
        "is_active": True,
    }
    await db.agencies.insert_one(doc)
    saved = await db.agencies.find_one({"_id": doc["_id"]})
    return serialize_doc(saved)


@router.get("/agencies", dependencies=[Depends(require_roles(["super_admin"]))])
async def list_agencies(user=Depends(get_current_user)):
    db = await get_db()
    docs = await db.agencies.find({"organization_id": user["organization_id"]}).sort("created_at", -1).to_list(500)
    return [serialize_doc(d) for d in docs]


@router.post("/hotels", dependencies=[Depends(require_roles(["super_admin"]))])
async def create_hotel(payload: HotelCreateIn, user=Depends(get_current_user)):
    db = await get_db()
    doc = payload.model_dump()
    doc.update(
        {
            "_id": _new_id(),
            "organization_id": user["organization_id"],
            "created_at": now_utc(),
            "updated_at": now_utc(),
            "created_by": user.get("email"),
            "updated_by": user.get("email"),
        }
    )
    await db.hotels.insert_one(doc)
    saved = await db.hotels.find_one({"_id": doc["_id"]})
    return serialize_doc(saved)


@router.get("/hotels", dependencies=[Depends(require_roles(["super_admin"]))])
async def list_hotels(active: Optional[bool] = None, user=Depends(get_current_user)):
    db = await get_db()
    q = {"organization_id": user["organization_id"]}
    if active is not None:
        q["active"] = active
    docs = await db.hotels.find(q).sort("created_at", -1).to_list(500)
    return [serialize_doc(d) for d in docs]


@router.patch("/hotels/{hotel_id}/force-sales", dependencies=[Depends(require_roles(["super_admin"]))])
async def patch_hotel_force_sales(
    hotel_id: str,
    payload: HotelForceSalesOverrideIn,
    request: Request,
    user=Depends(get_current_user),
):
    """Toggle force_sales_open flag on a hotel.

    When force_sales_open is True, availability computation bypasses stop-sell and
    channel allocation rules and uses base inventory.
    """
    db = await get_db()
    existing = await db.hotels.find_one(
        {"organization_id": user["organization_id"], "_id": hotel_id}
    )
    if not existing:
        raise HTTPException(status_code=404, detail="Otel bulunamadı")

    now = now_utc()

    if payload.force_sales_open:
        expires_at = now + timedelta(hours=payload.ttl_hours or 6)
        update = {
            "force_sales_open": True,
            "force_sales_open_expires_at": expires_at,
            "force_sales_open_reason": (payload.reason or "").strip() or None,
            "force_sales_open_updated_by": user.get("email"),
            "force_sales_open_updated_at": now,
            "updated_at": now,
            "updated_by": user.get("email"),
        }
    else:
        update = {
            "force_sales_open": False,
            "force_sales_open_expires_at": None,
            "force_sales_open_reason": None,
            "force_sales_open_updated_by": user.get("email"),
            "force_sales_open_updated_at": now,
            "updated_at": now,
            "updated_by": user.get("email"),
        }

    await db.hotels.update_one({"_id": hotel_id}, {"$set": update})
    saved = await db.hotels.find_one({"_id": hotel_id})

    meta = {
        "force_sales_open": payload.force_sales_open,
        "ttl_hours": payload.ttl_hours if payload.force_sales_open else None,
        "expires_at": (expires_at.isoformat() if payload.force_sales_open else None)
        if payload.force_sales_open
        else None,
        "reason": (payload.reason or "").strip() or None,
    }

    await write_audit_log(
        db,
        organization_id=user["organization_id"],
        actor={"actor_type": "user", "email": user.get("email"), "roles": user.get("roles")},
        request=request,
        action="hotel.force_sales_override",
        target_type="hotel",
        target_id=hotel_id,
        before=existing,
        after=saved,
        meta=meta,
    )

    return serialize_doc(saved)


@router.post("/agency-hotel-links", dependencies=[Depends(require_roles(["super_admin"]))])
async def create_link(payload: AgencyHotelLinkCreateIn, request: Request, user=Depends(get_current_user)):
    db = await get_db()

    agency = await db.agencies.find_one({"organization_id": user["organization_id"], "_id": payload.agency_id})
    if not agency:
        raise HTTPException(status_code=404, detail="Acente bulunamadı")

    hotel = await db.hotels.find_one({"organization_id": user["organization_id"], "_id": payload.hotel_id})
    if not hotel:
        raise HTTPException(status_code=404, detail="Otel bulunamadı")

    doc = {
        "_id": _new_id(),
        "organization_id": user["organization_id"],
        "agency_id": payload.agency_id,
        "hotel_id": payload.hotel_id,
        "active": payload.active,
        # FAZ-6: Commission settings on link
        "commission_type": payload.commission_type,
        "commission_value": payload.commission_value,
        "created_at": now_utc(),
        "updated_at": now_utc(),
        "created_by": user.get("email"),
        "updated_by": user.get("email"),
    }

    try:
        await db.agency_hotel_links.insert_one(doc)
    except Exception:
        raise HTTPException(status_code=409, detail="Bu acenta-otel link'i zaten var")

    saved = await db.agency_hotel_links.find_one({"_id": doc["_id"]})

    await write_audit_log(
        db,
        organization_id=user["organization_id"],
        actor={"actor_type": "user", "email": user.get("email"), "roles": user.get("roles")},
        request=request,
        action="link.create",
        target_type="agency_hotel_link",
        target_id=doc["_id"],
        before=None,
        after=saved,
    )

    return serialize_doc(saved)


@router.get("/agency-hotel-links", dependencies=[Depends(require_roles(["super_admin"]))])
async def list_links(user=Depends(get_current_user)):
    db = await get_db()
    docs = await db.agency_hotel_links.find({"organization_id": user["organization_id"]}).sort("created_at", -1).to_list(1000)
    return [serialize_doc(d) for d in docs]


@router.patch("/agency-hotel-links/{link_id}", dependencies=[Depends(require_roles(["super_admin"]))])
async def patch_link(link_id: str, payload: AgencyHotelLinkPatchIn, request: Request, user=Depends(get_current_user)):
    db = await get_db()
    existing = await db.agency_hotel_links.find_one({"organization_id": user["organization_id"], "_id": link_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Link bulunamadı")

    update = {
        "updated_at": now_utc(),
        "updated_by": user.get("email"),
    }
    if payload.active is not None:
        update["active"] = payload.active

    if payload.commission_type is not None:
        update["commission_type"] = payload.commission_type
    if payload.commission_value is not None:
        update["commission_value"] = payload.commission_value

    await db.agency_hotel_links.update_one({"_id": link_id}, {"$set": update})
    saved = await db.agency_hotel_links.find_one({"_id": link_id})

    await write_audit_log(
        db,
        organization_id=user["organization_id"],
        actor={"actor_type": "user", "email": user.get("email"), "roles": user.get("roles")},
        request=request,
        action="link.update",
        target_type="agency_hotel_link",
        target_id=link_id,
        before=existing,
        after=saved,
    )

    return serialize_doc(saved)



@router.get("/email-outbox", dependencies=[Depends(require_roles(["super_admin"]))])
async def list_email_outbox(
    status: Optional[str] = None,
    event_type: Optional[str] = None,
    q: Optional[str] = None,
    limit: int = 50,
    cursor: Optional[str] = None,
    user=Depends(get_current_user),
):
    """List email outbox jobs for admin monitoring.

    This is a lightweight view: bodies are not returned.
    """
    db = await get_db()

    limit = max(1, min(limit, 200))

    query: dict[str, Any] = {"organization_id": user["organization_id"]}

    if status:
        query["status"] = status
    if event_type:
        query["event_type"] = event_type

    if q:
        # basic search on booking_id, to and subject
        query["$or"] = [
            {"booking_id": q},
            {"to": {"$elemMatch": {"$regex": q, "$options": "i"}}},
            {"subject": {"$regex": q, "$options": "i"}},
        ]

    sort = [("created_at", -1)]

    if cursor:
        # simple cursor based on created_at ISO string
        try:
            from datetime import datetime

            cursor_dt = datetime.fromisoformat(cursor)
            query["created_at"] = {"$lt": cursor_dt}
        except Exception:
            pass

    docs = await db.email_outbox.find(query).sort(sort).limit(limit).to_list(length=limit)

    items = []
    next_cursor_val = None
    for d in docs:
        items.append(
            {
                "id": str(d.get("_id")),
                "organization_id": d.get("organization_id"),
                "booking_id": d.get("booking_id"),
                "event_type": d.get("event_type"),
                "to": d.get("to") or [],
                "subject": d.get("subject"),
                "status": d.get("status"),
                "attempt_count": d.get("attempt_count", 0),
                "last_error": d.get("last_error"),
                "next_retry_at": d.get("next_retry_at"),
                "created_at": d.get("created_at"),
                "sent_at": d.get("sent_at"),
            }
        )
        next_cursor_val = d.get("created_at")

    return {"items": items, "next_cursor": next_cursor_val}


@router.post("/email-outbox/{job_id}/retry", dependencies=[Depends(require_roles(["super_admin"]))])
async def retry_email_outbox_job(job_id: str, user=Depends(get_current_user)):
    """Force retry of an email outbox job (set next_retry_at to now)."""
    db = await get_db()

    job_oid = _oid_or_404(job_id)
    job = await db.email_outbox.find_one({"_id": job_oid, "organization_id": user["organization_id"]})
    if not job:
        raise HTTPException(status_code=404, detail="EMAIL_JOB_NOT_FOUND")

    if job.get("status") == "sent":
        raise HTTPException(status_code=400, detail="EMAIL_ALREADY_SENT")

    await db.email_outbox.update_one(
        {"_id": job_oid},
        {"$set": {"status": "pending", "next_retry_at": now_utc(), "last_error": None}},
    )

    return {"ok": True}


# ============================================================================
# PILOT DASHBOARD & TRACKING
# ============================================================================

@router.get("/pilot/summary", dependencies=[Depends(require_roles(["super_admin"]))])
async def pilot_summary(days: int = 7, user=Depends(get_current_user)):
    """
    Pilot KPI summary for last N days.
    Returns behavioral metrics to measure pilot success.
    
    KPIs:
    - totalRequests: booking count (all statuses)
    - avgRequestsPerAgency: avg bookings per active agency
    - whatsappShareRate: % of confirmed bookings with whatsapp_clicked event
    - hotelPanelActionRate: % of bookings with hotel action (confirmed/cancelled from hotel)
    - avgApprovalMinutes: avg time from draft_created_at to hotel action
    - agenciesViewedSettlements: % agencies who viewed settlements page
    - hotelsViewedSettlements: % hotels who viewed settlements page  
    - flowCompletionRate: % of drafts that reached confirmed status
    """
    from datetime import datetime, timedelta
    
    db = await get_db()
    org_id = user["organization_id"]
    cutoff = now_utc() - timedelta(days=days)
    
    # 1) Total bookings (drafts + confirmed + cancelled) in period
    total_bookings = await db.bookings.count_documents({
        "organization_id": org_id,
        "created_at": {"$gte": cutoff}
    })
    
    # 2) Unique active agencies (those who created bookings)
    active_agencies_cursor = db.bookings.aggregate([
        {"$match": {"organization_id": org_id, "created_at": {"$gte": cutoff}}},
        {"$group": {"_id": "$agency_id"}},
        {"$count": "total"}
    ])
    active_agencies_result = await active_agencies_cursor.to_list(1)
    active_agencies_count = active_agencies_result[0]["total"] if active_agencies_result else 1
    avg_requests_per_agency = round(total_bookings / active_agencies_count, 2) if active_agencies_count > 0 else 0
    
    # 3) WhatsApp share rate: FIXED - use totalRequests as denominator (not just confirmed)
    # Rationale: if hotel doesn't approve, whatsapp action should still count
    confirmed_bookings = await db.bookings.count_documents({
        "organization_id": org_id,
        "status": "confirmed",
        "created_at": {"$gte": cutoff}
    })
    
    cancelled_bookings = await db.bookings.count_documents({
        "organization_id": org_id,
        "status": "cancelled",
        "created_at": {"$gte": cutoff}
    })
    
    # Count unique whatsapp clicks (by booking_id to avoid spam)
    whatsapp_clicks_cursor = db.booking_events.aggregate([
        {
            "$match": {
                "organization_id": org_id,
                "event_type": "booking.whatsapp_clicked",
                "created_at": {"$gte": cutoff}
            }
        },
        {"$group": {"_id": "$booking_id"}},
        {"$count": "total"}
    ])
    whatsapp_clicks_result = await whatsapp_clicks_cursor.to_list(1)
    whatsapp_clicked_count = whatsapp_clicks_result[0]["total"] if whatsapp_clicks_result else 0
    
    # Primary metric: whatsapp clicks / total requests (pilot behavior tracking)
    whatsapp_share_rate = round(whatsapp_clicked_count / total_bookings, 2) if total_bookings > 0 else 0
    
    # Secondary metric: whatsapp clicks / confirmed bookings (engagement after success)
    whatsapp_share_rate_confirmed = round(whatsapp_clicked_count / confirmed_bookings, 2) if confirmed_bookings > 0 else 0
    
    # 4) Hotel panel action rate: FIXED - include cancelled as action
    # Rationale: cancelled can be hotel rejection (until we have proper rejected status)
    hotel_action_count = confirmed_bookings + cancelled_bookings
    hotel_panel_action_rate = round(hotel_action_count / total_bookings, 2) if total_bookings > 0 else 0
    
    # 5) Average approval time: draft_created_at to confirmed_at
    # For simplicity, use created_at to updated_at for confirmed bookings
    approval_times_cursor = db.bookings.aggregate([
        {
            "$match": {
                "organization_id": org_id,
                "status": "confirmed",
                "created_at": {"$gte": cutoff}
            }
        },
        {
            "$project": {
                "approval_minutes": {
                    "$divide": [
                        {"$subtract": ["$updated_at", "$created_at"]},
                        60000  # Convert ms to minutes
                    ]
                }
            }
        },
        {
            "$group": {
                "_id": None,
                "avg_minutes": {"$avg": "$approval_minutes"}
            }
        }
    ])
    approval_times_result = await approval_times_cursor.to_list(1)
    avg_approval_minutes = round(approval_times_result[0]["avg_minutes"], 1) if approval_times_result else 0
    
    # 6) Settlements page views: track via audit logs (if available)
    # For pilot, simplified: check if any settlement API calls exist in audit
    agencies_viewed_settlements_cursor = db.audit_logs.aggregate([
        {
            "$match": {
                "organization_id": org_id,
                "action": {"$in": ["agency.settlements.viewed", "settlements.viewed"]},
                "created_at": {"$gte": cutoff}
            }
        },
        {"$group": {"_id": "$actor"}},
        {"$count": "total"}
    ])
    agencies_viewed_result = await agencies_viewed_settlements_cursor.to_list(1)
    agencies_viewed_count = agencies_viewed_result[0]["total"] if agencies_viewed_result else 0
    agencies_viewed_settlements = round(agencies_viewed_count / active_agencies_count, 2) if active_agencies_count > 0 else 0
    
    hotels_viewed_settlements_cursor = db.audit_logs.aggregate([
        {
            "$match": {
                "organization_id": org_id,
                "action": {"$in": ["hotel.settlements.viewed", "settlements.viewed"]},
                "created_at": {"$gte": cutoff}
            }
        },
        {"$group": {"_id": "$actor"}},
        {"$count": "total"}
    ])
    hotels_viewed_result = await hotels_viewed_settlements_cursor.to_list(1)
    hotels_viewed_count = hotels_viewed_result[0]["total"] if hotels_viewed_result else 0
    
    # Get unique hotels count
    active_hotels_cursor = db.bookings.aggregate([
        {"$match": {"organization_id": org_id, "created_at": {"$gte": cutoff}}},
        {"$group": {"_id": "$hotel_id"}},
        {"$count": "total"}
    ])
    active_hotels_result = await active_hotels_cursor.to_list(1)
    active_hotels_count = active_hotels_result[0]["total"] if active_hotels_result else 1
    hotels_viewed_settlements = round(hotels_viewed_count / active_hotels_count, 2) if active_hotels_count > 0 else 0
    
    # 7) Flow completion rate: confirmed / total
    flow_completion_rate = round(confirmed_bookings / total_bookings, 2) if total_bookings > 0 else 0
    
    # ====================================================================================
    # FAZ-2.1: BREAKDOWN AGGREGATIONS
    # ====================================================================================
    
    # 1) BY DAY: Daily total/confirmed/cancelled/whatsapp
    by_day_pipeline = [
        {"$match": {"organization_id": org_id, "created_at": {"$gte": cutoff}}},
        {
            "$group": {
                "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}},
                "total": {"$sum": 1},
                "confirmed": {"$sum": {"$cond": [{"$eq": ["$status", "confirmed"]}, 1, 0]}},
                "cancelled": {"$sum": {"$cond": [{"$eq": ["$status", "cancelled"]}, 1, 0]}}
            }
        },
        {"$sort": {"_id": 1}}
    ]
    by_day_result = await db.bookings.aggregate(by_day_pipeline).to_list(100)
    
    # Get whatsapp clicks by day
    whatsapp_by_day_pipeline = [
        {"$match": {"organization_id": org_id, "event_type": "booking.whatsapp_clicked", "created_at": {"$gte": cutoff}}},
        {
            "$group": {
                "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}},
                "whatsapp": {"$sum": 1}
            }
        }
    ]
    whatsapp_by_day_result = await db.booking_events.aggregate(whatsapp_by_day_pipeline).to_list(100)
    whatsapp_by_day_map = {r["_id"]: r["whatsapp"] for r in whatsapp_by_day_result}
    
    breakdown_by_day = [
        {
            "date": row["_id"],
            "total": row["total"],
            "confirmed": row["confirmed"],
            "cancelled": row["cancelled"],
            "whatsapp": whatsapp_by_day_map.get(row["_id"], 0)
        }
        for row in by_day_result
    ]
    
    # 2) BY HOTEL: Hotel-based performance
    by_hotel_pipeline = [
        {"$match": {"organization_id": org_id, "created_at": {"$gte": cutoff}}},
        {
            "$group": {
                "_id": "$hotel_id",
                "hotel_name": {"$first": "$hotel_name"},
                "total": {"$sum": 1},
                "confirmed": {"$sum": {"$cond": [{"$eq": ["$status", "confirmed"]}, 1, 0]}},
                "cancelled": {"$sum": {"$cond": [{"$eq": ["$status", "cancelled"]}, 1, 0]}},
                "approval_times": {
                    "$push": {
                        "$cond": [
                            {"$eq": ["$status", "confirmed"]},
                            {"$divide": [{"$subtract": ["$updated_at", "$created_at"]}, 60000]},
                            None
                        ]
                    }
                }
            }
        },
        {
            "$project": {
                "hotel_id": "$_id",
                "hotel_name": 1,
                "total": 1,
                "confirmed": 1,
                "cancelled": 1,
                "action_count": {"$add": ["$confirmed", "$cancelled"]},
                "action_rate": {"$divide": [{"$add": ["$confirmed", "$cancelled"]}, "$total"]},
                "approval_times": {
                    "$filter": {
                        "input": "$approval_times",
                        "cond": {"$ne": ["$$this", None]}
                    }
                }
            }
        },
        {
            "$project": {
                "hotel_id": 1,
                "hotel_name": 1,
                "total": 1,
                "confirmed": 1,
                "cancelled": 1,
                "action_count": 1,
                "action_rate": {"$round": ["$action_rate", 2]},
                "avg_approval_minutes": {
                    "$cond": [
                        {"$gt": [{"$size": "$approval_times"}, 0]},
                        {"$round": [{"$avg": "$approval_times"}, 1]},
                        0
                    ]
                }
            }
        }
    ]
    by_hotel_result = await db.bookings.aggregate(by_hotel_pipeline).to_list(100)
    
    breakdown_by_hotel = [
        {
            "hotel_id": str(row["hotel_id"]),
            "hotel_name": row.get("hotel_name", "Unknown"),
            "total": row["total"],
            "confirmed": row["confirmed"],
            "cancelled": row.get("cancelled", 0),
            "action_count": row.get("action_count", 0),
            "action_rate": row.get("action_rate", 0),
            "avg_approval_minutes": row.get("avg_approval_minutes", 0)
        }
        for row in by_hotel_result
    ]
    
    # 3) BY AGENCY: Agency-based conversion
    by_agency_pipeline = [
        {"$match": {"organization_id": org_id, "created_at": {"$gte": cutoff}}},
        {
            "$group": {
                "_id": "$agency_id",
                "total": {"$sum": 1},
                "confirmed": {"$sum": {"$cond": [{"$eq": ["$status", "confirmed"]}, 1, 0]}}
            }
        },
        {
            "$project": {
                "agency_id": "$_id",
                "total": 1,
                "confirmed": 1,
                "conversion_rate": {
                    "$round": [
                        {"$cond": [{"$gt": ["$total", 0]}, {"$divide": ["$confirmed", "$total"]}, 0]},
                        2
                    ]
                }
            }
        }
    ]
    by_agency_result = await db.bookings.aggregate(by_agency_pipeline).to_list(100)
    
    # Get agency names
    agency_ids = [str(r["agency_id"]) for r in by_agency_result]
    agencies_docs = await db.agencies.find({"_id": {"$in": agency_ids}}).to_list(100)
    agency_name_map = {str(a["_id"]): a.get("name", "Unknown") for a in agencies_docs}
    
    # Get whatsapp clicks by agency
    whatsapp_by_agency_pipeline = [
        {"$match": {"organization_id": org_id, "event_type": "booking.whatsapp_clicked", "created_at": {"$gte": cutoff}}},
        {"$group": {"_id": "$agency_id", "whatsapp_clicks": {"$sum": 1}}}
    ]
    whatsapp_by_agency_result = await db.booking_events.aggregate(whatsapp_by_agency_pipeline).to_list(100)
    whatsapp_by_agency_map = {str(r["_id"]): r["whatsapp_clicks"] for r in whatsapp_by_agency_result}
    
    breakdown_by_agency = [
        {
            "agency_id": str(row["agency_id"]),
            "agency_name": agency_name_map.get(str(row["agency_id"]), "Unknown"),
            "total": row["total"],
            "confirmed": row["confirmed"],
            "whatsapp_clicks": whatsapp_by_agency_map.get(str(row["agency_id"]), 0),
            "conversion_rate": row.get("conversion_rate", 0),
            "whatsapp_rate": round(
                whatsapp_by_agency_map.get(str(row["agency_id"]), 0) / row["total"], 2
            ) if row["total"] > 0 else 0
        }
        for row in by_agency_result
    ]
    
    return {
        "range": {
            "from": cutoff.isoformat(),
            "to": now_utc().isoformat(),
            "days": days
        },
        "kpis": {
            "totalRequests": total_bookings,
            "avgRequestsPerAgency": avg_requests_per_agency,
            "whatsappShareRate": whatsapp_share_rate,
            "hotelPanelActionRate": hotel_panel_action_rate,
            "avgApprovalMinutes": avg_approval_minutes,
            "agenciesViewedSettlements": agencies_viewed_settlements,
            "hotelsViewedSettlements": hotels_viewed_settlements,
            "flowCompletionRate": flow_completion_rate
        },
        "meta": {
            "activeAgenciesCount": active_agencies_count,
            "activeHotelsCount": active_hotels_count,
            "confirmedBookings": confirmed_bookings,
            "cancelledBookings": cancelled_bookings,
            "whatsappClickedCount": whatsapp_clicked_count,
            "whatsappShareRateConfirmed": whatsapp_share_rate_confirmed,
            "hotelConfirmedCount": confirmed_bookings,
            "hotelCancelledCount": cancelled_bookings,
            "hotelActionCount": hotel_action_count
        },
        "breakdown": {
            "by_day": breakdown_by_day,
            "by_hotel": breakdown_by_hotel,
            "by_agency": breakdown_by_agency
        }
    }

