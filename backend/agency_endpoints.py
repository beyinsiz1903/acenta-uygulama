"""
Agency Booking Request Endpoints
=================================
Production-ready acenta talep sistemi.

Özellikler:
- Idempotency (duplicate request protection)
- Soft availability check (request time)
- Hard availability check (approve time)
- Status machine with audit trail
- Auto-expire after 30 minutes
- Commission calculation

Endpoints:
1. POST /api/agency/booking-requests - Create request (idempotent)
2. GET /api/agency/booking-requests/{id} - Get request detail
3. POST /api/agency/booking-requests/{id}/cancel - Cancel by agency
4. GET /api/hotel/booking-requests - List hotel requests
5. POST /api/hotel/booking-requests/{id}/approve - Approve (creates booking)
6. POST /api/hotel/booking-requests/{id}/reject - Reject with reason
"""

from fastapi import APIRouter, HTTPException, Depends, Header, Request
from typing import Optional, List
from datetime import datetime, timedelta, timezone
from motor.motor_asyncio import AsyncIOMotorDatabase

from agency_models import (
    CreateAgencyBookingRequestIn,
    RejectBookingRequestIn,
    AgencyBookingRequest,
    RestrictionsSnapshot,
    AvailabilitySnapshot,
    AuditEvent,
    now_utc,
    iso,
    new_uuid,
    FINAL_STATUSES,
    PENDING_STATUSES,
    is_final_status,
    is_pending_status
)

# Import from main server (will be available after integration)
# from server import db, get_current_user, User, UserRole

DEFAULT_REQUEST_TTL_MINUTES = 30

# Router
agency_router = APIRouter(prefix="/api", tags=["Agency Booking Requests"])

# ============= HELPER FUNCTIONS =============

async def expire_if_needed(db: AsyncIOMotorDatabase, req_doc: dict) -> dict:
    """
    Lazy expire: Eğer request pending durumda ve süresi dolmuşsa expired'a çek.
    """
    if req_doc.get("status") in PENDING_STATUSES:
        exp_str = req_doc.get("expires_at")
        if exp_str:
            exp_dt = datetime.fromisoformat(exp_str.replace("Z", "+00:00"))
            if now_utc() > exp_dt:
                # Expire it
                await db.agency_booking_requests.update_one(
                    {
                        "request_id": req_doc["request_id"],
                        "status": {"$in": list(PENDING_STATUSES)}
                    },
                    {
                        "$set": {
                            "status": "expired",
                            "status_updated_at": iso(now_utc()),
                            "resolved_at": iso(now_utc()),
                            "resolved_by_user_id": "system"
                        },
                        "$push": {
                            "audit_events": {
                                "event": "expired",
                                "actor_id": "system",
                                "actor_type": "system",
                                "timestamp": iso(now_utc()),
                                "metadata": {}
                            }
                        }
                    }
                )
                req_doc["status"] = "expired"
    return req_doc


async def compute_soft_availability_and_restrictions(
    db: AsyncIOMotorDatabase,
    hotel_id: str,
    room_type_id: str,
    check_in: str,
    check_out: str
) -> tuple[int, dict]:
    """
    TODO: Bu fonksiyonu mevcut availability + restrictions helper'larına bağla.
    
    Şimdilik placeholder döndürüyor. Gerçek implementasyonda:
    - /api/pms/rooms/availability endpoint'inin backend fonksiyonunu çağır
    - rate_periods'tan min_stay/stop_sell/cta/ctd oku
    
    Returns:
        (available_rooms: int, restrictions: dict)
    """
    # PLACEHOLDER - Replace with real logic
    available = 5
    restrictions = {
        "stop_sell": False,
        "min_stay": 1,
        "max_stay": None,
        "cta": False,
        "ctd": False
    }
    
    # TODO: Real implementation:
    # available = await check_availability_soft(db, hotel_id, room_type_id, check_in, check_out)
    # restrictions = await get_restrictions(db, hotel_id, room_type_id, check_in, check_out)
    
    return available, restrictions


async def compute_price_snapshot(
    db: AsyncIOMotorDatabase,
    hotel_id: str,
    room_type_id: str,
    rate_plan_id: str,
    check_in: str,
    check_out: str
) -> tuple[float, float, str, int]:
    """
    TODO: Bu fonksiyonu mevcut rate_periods + rate_plans helper'larına bağla.
    
    Returns:
        (price_per_night, total_price, currency, nights)
    """
    # PLACEHOLDER - Replace with real logic
    ci = datetime.fromisoformat(check_in)
    co = datetime.fromisoformat(check_out)
    nights = (co - ci).days
    
    price_per_night = 1500.0
    currency = "TRY"
    total_price = price_per_night * max(nights, 1)
    
    # TODO: Real implementation:
    # price_per_night, currency = await get_rate_from_periods(db, hotel_id, room_type_id, rate_plan_id, check_in, check_out)
    # total_price = price_per_night * nights
    
    return price_per_night, total_price, currency, nights


async def get_commission_pct_for_link(
    db: AsyncIOMotorDatabase,
    agency_id: str,
    hotel_id: str
) -> float:
    """
    TODO: Bu fonksiyonu agency_hotel_links collection'ından oku.
    
    Şimdilik sabit 15% döndürüyor.
    """
    # PLACEHOLDER
    return 15.0
    
    # TODO: Real implementation:
    # link = await db.agency_hotel_links.find_one({"agency_id": agency_id, "hotel_id": hotel_id})
    # return link.get("commission_pct_default", 15.0) if link else 15.0


# ============= ENDPOINTS =============

@agency_router.post("/agency/booking-requests", response_model=AgencyBookingRequest)
async def create_agency_booking_request(
    payload: CreateAgencyBookingRequestIn,
    request: Request,
    Idempotency_Key: Optional[str] = Header(None, alias="Idempotency-Key"),
    # current_user: User = Depends(get_current_user)  # Uncomment after integration
):
    """
    Acenta booking request oluştur (idempotent).
    
    **Idempotency:**
    - Client her request için unique Idempotency-Key göndermeli
    - Aynı key ile 2. request gelirse existing döner (duplicate protection)
    
    **Business Logic:**
    - Soft availability check (stok düşmez)
    - Restrictions check (stop_sell, min_stay)
    - Pricing snapshot (commission hesapla)
    - 30 dakika sonra auto-expire
    
    **Required Header:**
    - `Idempotency-Key: <uuid>` (client generates)
    """
    from server import db  # Import here to avoid circular dependency
    
    # TODO: Auth check - Uncomment after integration
    # if current_user.role not in ["AGENCY_ADMIN", "AGENCY_AGENT"]:
    #     raise HTTPException(403, "Agency role required")
    # agency_id = current_user.agency_id or current_user.tenant_id
    # user_id = current_user.id
    
    # PLACEHOLDER - Replace with real auth
    agency_id = "AGENCY_ID_PLACEHOLDER"
    user_id = "AGENCY_USER_ID_PLACEHOLDER"
    
    if not Idempotency_Key:
        raise HTTPException(400, "Missing Idempotency-Key header")
    
    # 1) Idempotency check
    existing = await db.agency_booking_requests.find_one({"idempotency_key": Idempotency_Key})
    if existing:
        existing.pop("_id", None)
        existing = await expire_if_needed(db, existing)
        
        if is_final_status(existing["status"]):
            # Already finalized - return 409 or existing (your choice)
            raise HTTPException(409, f"Request already finalized with status: {existing['status']}")
        
        # Pending - return existing
        return AgencyBookingRequest(**existing)
    
    # 2) Soft availability + restrictions check
    available, restrictions = await compute_soft_availability_and_restrictions(
        db, payload.hotel_id, payload.room_type_id, payload.check_in, payload.check_out
    )
    
    if available < 1:
        raise HTTPException(400, "No availability for selected dates")
    
    if restrictions.get("stop_sell"):
        raise HTTPException(400, "Stop sell is active for this room type")
    
    # 3) Min stay check
    ci = datetime.fromisoformat(payload.check_in)
    co = datetime.fromisoformat(payload.check_out)
    nights = (co - ci).days
    
    min_stay = int(restrictions.get("min_stay") or 1)
    if nights < min_stay:
        raise HTTPException(400, f"Minimum stay is {min_stay} nights")
    
    # 4) Pricing snapshot
    price_per_night, total_price, currency, nights = await compute_price_snapshot(
        db, payload.hotel_id, payload.room_type_id, payload.rate_plan_id,
        payload.check_in, payload.check_out
    )
    
    # 5) Commission calculation
    commission_pct = await get_commission_pct_for_link(db, agency_id, payload.hotel_id)
    commission_amount = round(total_price * (commission_pct / 100.0), 2)
    net_to_hotel = round(total_price - commission_amount, 2)
    
    # 6) Create request document
    created_at = now_utc()
    expires_at = created_at + timedelta(minutes=DEFAULT_REQUEST_TTL_MINUTES)
    
    req_doc = {
        "request_id": new_uuid(),
        "idempotency_key": Idempotency_Key,
        
        "agency_id": agency_id,
        "hotel_id": payload.hotel_id,
        "room_type_id": payload.room_type_id,
        "rate_plan_id": payload.rate_plan_id,
        
        "check_in": payload.check_in,
        "check_out": payload.check_out,
        "nights": nights,
        "adults": payload.adults,
        "children": payload.children,
        
        "customer_name": payload.customer_name,
        "customer_phone": payload.customer_phone,
        "customer_email": payload.customer_email,
        
        "price_per_night": float(price_per_night),
        "total_price": float(total_price),
        "currency": currency,
        "commission_pct": float(commission_pct),
        "commission_amount": float(commission_amount),
        "net_to_hotel": float(net_to_hotel),
        
        "status": "submitted",
        "status_updated_at": iso(created_at),
        
        "restrictions_snapshot": restrictions,
        "availability_at_request": {
            "available_rooms": int(available),
            "checked_at": iso(created_at)
        },
        
        "created_at": iso(created_at),
        "created_by_user_id": user_id,
        "expires_at": iso(expires_at),
        
        "resolved_at": None,
        "resolved_by_user_id": None,
        "resolution_notes": None,
        "booking_id": None,
        
        "audit_events": [
            {
                "event": "created",
                "actor_id": user_id,
                "actor_type": "agency",
                "timestamp": iso(created_at),
                "metadata": {}
            }
        ],
        
        "source": payload.source,
        "user_agent": request.headers.get("user-agent"),
        "ip_address": request.client.host if request.client else None,
    }
    
    # 7) Insert (handle duplicate race condition)
    try:
        await db.agency_booking_requests.insert_one(req_doc)
    except Exception as e:
        # Possible duplicate key on idempotency_key
        existing2 = await db.agency_booking_requests.find_one({"idempotency_key": Idempotency_Key})
        if existing2:
            existing2.pop("_id", None)
            existing2 = await expire_if_needed(db, existing2)
            if is_final_status(existing2["status"]):
                raise HTTPException(409, f"Request already finalized")
            return AgencyBookingRequest(**existing2)
        raise HTTPException(500, f"Database error: {str(e)}")
    
    # 8) Notify hotel (TODO: WhatsApp/email)
    # await notify_hotel_new_request(req_doc)
    
    req_doc.pop("_id", None)
    return AgencyBookingRequest(**req_doc)


@agency_router.get("/agency/booking-requests/{request_id}", response_model=AgencyBookingRequest)
async def get_agency_booking_request(
    request_id: str,
    # current_user: User = Depends(get_current_user)
):
    """
    Acenta kendi request'ini görüntüle.
    """
    from server import db
    
    # TODO: Auth
    # agency_id = current_user.agency_id or current_user.tenant_id
    agency_id = "AGENCY_ID_PLACEHOLDER"
    
    doc = await db.agency_booking_requests.find_one({"request_id": request_id})
    if not doc:
        raise HTTPException(404, "Request not found")
    
    doc.pop("_id", None)
    
    # Auth check
    if doc["agency_id"] != agency_id:
        raise HTTPException(403, "Not your agency's request")
    
    doc = await expire_if_needed(db, doc)
    return AgencyBookingRequest(**doc)


@agency_router.post("/agency/booking-requests/{request_id}/cancel")
async def cancel_agency_booking_request(
    request_id: str,
    # current_user: User = Depends(get_current_user)
):
    """
    Acenta kendi request'ini iptal et (pending ise).
    """
    from server import db
    
    # TODO: Auth
    # agency_id = current_user.agency_id or current_user.tenant_id
    # user_id = current_user.id
    agency_id = "AGENCY_ID_PLACEHOLDER"
    user_id = "AGENCY_USER_ID_PLACEHOLDER"
    
    req_doc = await db.agency_booking_requests.find_one({"request_id": request_id})
    if not req_doc:
        raise HTTPException(404, "Request not found")
    
    req_doc.pop("_id", None)
    
    if req_doc["agency_id"] != agency_id:
        raise HTTPException(403, "Not your agency's request")
    
    req_doc = await expire_if_needed(db, req_doc)
    
    if is_final_status(req_doc["status"]):
        return {
            "status": "already_final",
            "request_id": request_id,
            "current_status": req_doc["status"]
        }
    
    # Cancel
    await db.agency_booking_requests.update_one(
        {"request_id": request_id, "status": {"$in": list(PENDING_STATUSES)}},
        {
            "$set": {
                "status": "cancelled",
                "status_updated_at": iso(now_utc()),
                "resolved_at": iso(now_utc()),
                "resolved_by_user_id": user_id,
                "resolution_notes": "Cancelled by agency"
            },
            "$push": {
                "audit_events": {
                    "event": "cancelled",
                    "actor_id": user_id,
                    "actor_type": "agency",
                    "timestamp": iso(now_utc()),
                    "metadata": {}
                }
            }
        }
    )
    
    return {"status": "cancelled", "request_id": request_id}


@agency_router.get("/hotel/booking-requests")
async def list_hotel_booking_requests(
    status: Optional[str] = None,
    limit: int = 50,
    # current_user: User = Depends(get_current_user)
):
    """
    Otel: gelen talepleri listele.
    
    İlk görüntülemede status: submitted → hotel_review'a geçer.
    """
    from server import db
    
    # TODO: Auth
    # if current_user.role not in ["ADMIN", "SUPERVISOR", "FRONT_DESK"]:
    #     raise HTTPException(403, "Hotel role required")
    # hotel_id = current_user.tenant_id
    # user_id = current_user.id
    hotel_id = "HOTEL_ID_PLACEHOLDER"
    user_id = "HOTEL_USER_ID_PLACEHOLDER"
    
    query = {"hotel_id": hotel_id}
    if status:
        query["status"] = status
    
    cursor = db.agency_booking_requests.find(query, {"_id": 0}).sort("created_at", -1).limit(min(limit, 100))
    results = []
    
    async for doc in cursor:
        doc = await expire_if_needed(db, doc)
        
        # Auto-transition: submitted → hotel_review (first view)
        if doc.get("status") == "submitted":
            await db.agency_booking_requests.update_one(
                {"request_id": doc["request_id"], "status": "submitted"},
                {
                    "$set": {
                        "status": "hotel_review",
                        "status_updated_at": iso(now_utc())
                    },
                    "$push": {
                        "audit_events": {
                            "event": "hotel_viewed",
                            "actor_id": user_id,
                            "actor_type": "hotel",
                            "timestamp": iso(now_utc()),
                            "metadata": {}
                        }
                    }
                }
            )
            doc["status"] = "hotel_review"
        
        results.append(doc)
    
    return {"items": results, "count": len(results)}


@agency_router.post("/hotel/booking-requests/{request_id}/approve")
async def approve_booking_request(
    request_id: str,
    # current_user: User = Depends(get_current_user)
):
    """
    Otel: talebi onayla → booking oluştur.
    
    **Critical Logic:**
    - Hard availability check (son kontrol)
    - Booking create (commission fields set)
    - Idempotent (2. approve → aynı booking döner)
    """
    from server import db
    
    # TODO: Auth
    # if current_user.role not in ["ADMIN", "SUPERVISOR", "FRONT_DESK"]:
    #     raise HTTPException(403, "Hotel role required")
    # hotel_id = current_user.tenant_id
    # hotel_user_id = current_user.id
    hotel_id = "HOTEL_ID_PLACEHOLDER"
    hotel_user_id = "HOTEL_USER_ID_PLACEHOLDER"
    
    req_doc = await db.agency_booking_requests.find_one({"request_id": request_id})
    if not req_doc:
        raise HTTPException(404, "Request not found")
    
    req_doc.pop("_id", None)
    
    if req_doc["hotel_id"] != hotel_id:
        raise HTTPException(403, "Not your hotel's request")
    
    req_doc = await expire_if_needed(db, req_doc)
    
    # Idempotent approve
    if req_doc["status"] == "approved" and req_doc.get("booking_id"):
        booking = await db.bookings.find_one({"id": req_doc["booking_id"]}, {"_id": 0})
        return {
            "status": "already_approved",
            "request_id": request_id,
            "booking_id": req_doc["booking_id"],
            "booking": booking
        }
    
    if not is_pending_status(req_doc["status"]):
        raise HTTPException(400, f"Cannot approve from status: {req_doc['status']}")
    
    # HARD availability check (final check before booking creation)
    available, _restrictions = await compute_soft_availability_and_restrictions(
        db, req_doc["hotel_id"], req_doc["room_type_id"],
        req_doc["check_in"], req_doc["check_out"]
    )
    
    if available < 1:
        # Auto-reject (no availability at approval time)
        await db.agency_booking_requests.update_one(
            {"request_id": request_id, "status": {"$in": list(PENDING_STATUSES)}},
            {
                "$set": {
                    "status": "rejected",
                    "status_updated_at": iso(now_utc()),
                    "resolved_at": iso(now_utc()),
                    "resolved_by_user_id": "system",
                    "resolution_notes": "No availability at approval time"
                },
                "$push": {
                    "audit_events": {
                        "event": "rejected",
                        "actor_id": "system",
                        "actor_type": "system",
                        "timestamp": iso(now_utc()),
                        "metadata": {"reason": "no_availability"}
                    }
                }
            }
        )
        raise HTTPException(409, "No availability - request auto-rejected")
    
    # Create booking (senin mevcut booking modelinle uyumlu)
    booking_id = new_uuid()
    booking_doc = {
        "id": booking_id,
        "tenant_id": req_doc["hotel_id"],
        
        "room_id": None,  # Will be assigned later
        "room_type": req_doc["room_type_id"],  # Your system uses room_type string
        
        "check_in": req_doc["check_in"],
        "check_out": req_doc["check_out"],
        "adults": req_doc["adults"],
        "children": req_doc["children"],
        
        "guest_name": req_doc["customer_name"],
        "guest_phone": req_doc["customer_phone"],
        "guest_email": req_doc.get("customer_email"),
        
        # Source & commission (senin mevcut fields)
        "source_channel": "agency",
        "agency_id": req_doc["agency_id"],
        "commission_pct": req_doc["commission_pct"],
        "commission_amount": req_doc["commission_amount"],
        
        # Status
        "status": "confirmed",  # Direct to confirmed
        "booking_date": iso(now_utc()),
        "created_at": iso(now_utc()),
        "created_by": hotel_user_id,
        
        # Pricing
        "total_price": req_doc["total_price"],
        "currency": req_doc["currency"],
        
        # Payment model (senin mevcut enum)
        "payment_model": "agency",  # AGENCY pays hotel later
        
        # Link to request
        "agency_request_id": request_id
    }
    
    # Insert booking
    await db.bookings.insert_one(booking_doc)
    
    # Update request to approved
    await db.agency_booking_requests.update_one(
        {"request_id": request_id, "status": {"$in": list(PENDING_STATUSES)}},
        {
            "$set": {
                "status": "approved",
                "status_updated_at": iso(now_utc()),
                "booking_id": booking_id,
                "resolved_at": iso(now_utc()),
                "resolved_by_user_id": hotel_user_id
            },
            "$push": {
                "audit_events": {
                    "event": "approved",
                    "actor_id": hotel_user_id,
                    "actor_type": "hotel",
                    "timestamp": iso(now_utc()),
                    "metadata": {
                        "booking_id": booking_id,
                        "final_availability": int(available - 1)
                    }
                }
            }
        }
    )
    
    # TODO: Notify agency (WhatsApp/email)
    # await notify_agency_approved(req_doc, booking_doc)
    
    booking_doc.pop("_id", None)
    return {
        "status": "approved",
        "request_id": request_id,
        "booking_id": booking_id,
        "booking": booking_doc
    }


@agency_router.post("/hotel/booking-requests/{request_id}/reject")
async def reject_booking_request(
    request_id: str,
    payload: RejectBookingRequestIn,
    # current_user: User = Depends(get_current_user)
):
    """
    Otel: talebi reddet (reason zorunlu).
    """
    from server import db
    
    # TODO: Auth
    # if current_user.role not in ["ADMIN", "SUPERVISOR", "FRONT_DESK"]:
    #     raise HTTPException(403, "Hotel role required")
    # hotel_id = current_user.tenant_id
    # hotel_user_id = current_user.id
    hotel_id = "HOTEL_ID_PLACEHOLDER"
    hotel_user_id = "HOTEL_USER_ID_PLACEHOLDER"
    
    req_doc = await db.agency_booking_requests.find_one({"request_id": request_id})
    if not req_doc:
        raise HTTPException(404, "Request not found")
    
    req_doc.pop("_id", None)
    
    if req_doc["hotel_id"] != hotel_id:
        raise HTTPException(403, "Not your hotel's request")
    
    req_doc = await expire_if_needed(db, req_doc)
    
    if is_final_status(req_doc["status"]):
        return {
            "status": "already_final",
            "request_id": request_id,
            "current_status": req_doc["status"]
        }
    
    if not is_pending_status(req_doc["status"]):
        raise HTTPException(400, f"Cannot reject from status: {req_doc['status']}")
    
    # Reject
    await db.agency_booking_requests.update_one(
        {"request_id": request_id, "status": {"$in": list(PENDING_STATUSES)}},
        {
            "$set": {
                "status": "rejected",
                "status_updated_at": iso(now_utc()),
                "resolved_at": iso(now_utc()),
                "resolved_by_user_id": hotel_user_id,
                "resolution_notes": payload.reason
            },
            "$push": {
                "audit_events": {
                    "event": "rejected",
                    "actor_id": hotel_user_id,
                    "actor_type": "hotel",
                    "timestamp": iso(now_utc()),
                    "metadata": {"reason": payload.reason}
                }
            }
        }
    )
    
    # TODO: Notify agency (WhatsApp/email)
    # await notify_agency_rejected(req_doc)
    
    return {"status": "rejected", "request_id": request_id, "reason": payload.reason}
