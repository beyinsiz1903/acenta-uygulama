from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date, datetime, timezone
from typing import Any, Optional

from fastapi import HTTPException, Request
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.repositories.base_repository import with_org_filter, with_tenant_filter
from app.repositories.booking_repository import BookingRepository
from app.request_context import get_request_context
from app.services.booking_service import create_booking_draft


def _current_tenant_id() -> Optional[str]:
    ctx = get_request_context(required=False)
    return ctx.tenant_id if ctx else None


def _include_legacy_without_tenant() -> bool:
    ctx = get_request_context(required=False)
    if not ctx:
        return True
    if ctx.is_super_admin:
        return True
    return len(ctx.allowed_tenant_ids or []) <= 1


def _tenant_filter(base_filter: dict[str, Any]) -> dict[str, Any]:
    tenant_id = _current_tenant_id()
    if not tenant_id:
        return dict(base_filter)
    return with_tenant_filter(
        dict(base_filter),
        tenant_id,
        include_legacy_without_tenant=_include_legacy_without_tenant(),
    )


def _iso(value: Any) -> Optional[str]:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, str) and value:
        return value
    return None


def _currency(doc: dict[str, Any]) -> str:
    return str(doc.get("currency") or "TRY")


def _booking_status(doc: dict[str, Any]) -> str:
    return str(doc.get("status") or doc.get("state") or "draft")


def _booking_total(doc: dict[str, Any]) -> float:
    for field in ("gross_amount", "total_price", "amount", "net_amount"):
        value = doc.get(field)
        if value is not None:
            return round(float(value), 2)
    return 0.0


def _customer_name(doc: dict[str, Any]) -> Optional[str]:
    guest = doc.get("guest") or {}
    return (
        guest.get("full_name")
        or doc.get("guest_name")
        or doc.get("customer_name")
        or doc.get("customer_id")
    )


def _stay_value(doc: dict[str, Any], key: str) -> Optional[str]:
    stay = doc.get("stay") or {}
    return _iso(stay.get(key) or doc.get(key))


def _booking_summary(doc: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(doc.get("_id")),
        "status": _booking_status(doc),
        "total_price": _booking_total(doc),
        "currency": _currency(doc),
        "customer_name": _customer_name(doc),
        "hotel_name": doc.get("hotel_name"),
        "check_in": _stay_value(doc, "check_in"),
        "check_out": _stay_value(doc, "check_out"),
        "source": doc.get("source") or "backoffice",
        "created_at": _iso(doc.get("created_at")),
        "updated_at": _iso(doc.get("updated_at")),
    }


def _booking_detail(doc: dict[str, Any]) -> dict[str, Any]:
    base = _booking_summary(doc)
    base.update(
        {
            "tenant_id": doc.get("tenant_id"),
            "agency_id": doc.get("agency_id"),
            "hotel_id": doc.get("hotel_id"),
            "booking_ref": doc.get("booking_ref"),
            "offer_ref": doc.get("offer_ref"),
            "notes": doc.get("notes"),
        }
    )
    return base


def build_mobile_user(user: dict[str, Any]) -> dict[str, Any]:
    ctx = get_request_context(required=False)
    return {
        "id": str(user.get("id") or user.get("_id")),
        "email": user.get("email"),
        "name": user.get("name"),
        "roles": list(user.get("roles") or []),
        "organization_id": str(user.get("organization_id") or ""),
        "tenant_id": ctx.tenant_id if ctx else None,
        "current_session_id": user.get("current_session_id"),
        "allowed_tenant_ids": list((ctx.allowed_tenant_ids or []) if ctx else []),
    }


async def get_dashboard_summary(db: AsyncIOMotorDatabase, user: dict[str, Any]) -> dict[str, Any]:
    organization_id = str(user.get("organization_id") or "")
    if not organization_id:
        raise HTTPException(status_code=403, detail="Organization membership required")

    bookings = db.bookings
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    base_filter = with_org_filter({}, organization_id)
    today_filter = _tenant_filter({**base_filter, "created_at": {"$gte": today_start}})
    month_filter = _tenant_filter({**base_filter, "created_at": {"$gte": month_start}})

    bookings_today = await bookings.count_documents(today_filter)
    bookings_month = await bookings.count_documents(month_filter)
    month_docs = await bookings.find(month_filter, {"gross_amount": 1, "total_price": 1, "amount": 1, "currency": 1}).to_list(5000)

    revenue_month = round(sum(_booking_total(doc) for doc in month_docs), 2)
    currency = _currency(month_docs[0]) if month_docs else "TRY"

    return {
        "bookings_today": bookings_today,
        "bookings_month": bookings_month,
        "revenue_month": revenue_month,
        "currency": currency,
    }


async def list_bookings(
    db: AsyncIOMotorDatabase,
    user: dict[str, Any],
    *,
    limit: int = 20,
    status: Optional[str] = None,
) -> dict[str, Any]:
    organization_id = str(user.get("organization_id") or "")
    repo = BookingRepository(db)
    docs = await repo.list_bookings(
        organization_id,
        state=status,
        limit=limit,
        tenant_id=_current_tenant_id(),
        include_legacy_without_tenant=_include_legacy_without_tenant(),
    )
    total = await db.bookings.count_documents(
        _tenant_filter(with_org_filter({"state": status} if status else {}, organization_id))
    )
    return {"total": total, "items": [_booking_summary(doc) for doc in docs]}


async def get_booking(db: AsyncIOMotorDatabase, booking_id: str, user: dict[str, Any]) -> dict[str, Any]:
    organization_id = str(user.get("organization_id") or "")
    repo = BookingRepository(db)
    doc = await repo.get_by_id(
        organization_id,
        booking_id,
        tenant_id=_current_tenant_id(),
        include_legacy_without_tenant=_include_legacy_without_tenant(),
    )
    if not doc:
        raise HTTPException(status_code=404, detail="BOOKING_NOT_FOUND")
    return _booking_detail(doc)


def _build_mobile_booking_payload(payload: dict[str, Any], user: dict[str, Any]) -> dict[str, Any]:
    tenant_id = _current_tenant_id()
    guest_name = payload.get("guest_name") or payload.get("customer_name")
    booking_payload: dict[str, Any] = {
        "tenant_id": tenant_id,
        "agency_id": payload.get("agency_id") or user.get("agency_id"),
        "customer_id": payload.get("customer_id"),
        "customer_name": payload.get("customer_name") or guest_name,
        "guest_name": guest_name,
        "hotel_id": payload.get("hotel_id"),
        "hotel_name": payload.get("hotel_name"),
        "supplier_id": payload.get("supplier_id"),
        "offer_ref": payload.get("offer_ref"),
        "pricing": payload.get("pricing"),
        "amount": float(payload.get("amount") or 0),
        "currency": payload.get("currency") or "TRY",
        "booking_ref": payload.get("booking_ref"),
        "notes": payload.get("notes"),
        "occupancy": payload.get("occupancy") or {},
        "source": payload.get("source") or "mobile",
    }

    check_in = payload.get("check_in")
    check_out = payload.get("check_out")
    if check_in or check_out:
        booking_payload["stay"] = {
            "check_in": check_in,
            "check_out": check_out,
        }

    return booking_payload


async def create_booking(
    db: AsyncIOMotorDatabase,
    payload: dict[str, Any],
    user: dict[str, Any],
    request: Request,
) -> dict[str, Any]:
    organization_id = str(user.get("organization_id") or "")
    if not organization_id:
        raise HTTPException(status_code=403, detail="Organization membership required")

    actor = {
        "actor_type": "user",
        "actor_id": user.get("id"),
        "email": user.get("email"),
        "roles": user.get("roles", []),
    }

    booking_payload = _build_mobile_booking_payload(payload, user)
    booking_id = await create_booking_draft(db, organization_id, actor, booking_payload, request)
    repo = BookingRepository(db)
    doc = await repo.get_by_id(
        organization_id,
        booking_id,
        tenant_id=_current_tenant_id(),
        include_legacy_without_tenant=False,
    )
    if not doc:
        raise HTTPException(status_code=500, detail="BOOKING_PERSISTENCE_ERROR")
    return _booking_detail(doc)


async def get_reports_summary(db: AsyncIOMotorDatabase, user: dict[str, Any]) -> dict[str, Any]:
    organization_id = str(user.get("organization_id") or "")
    if not organization_id:
        raise HTTPException(status_code=403, detail="Organization membership required")

    since = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    since = since.replace(day=1)
    docs = await db.bookings.find(
        _tenant_filter(with_org_filter({"created_at": {"$gte": since}}, organization_id)),
        {
            "status": 1,
            "state": 1,
            "gross_amount": 1,
            "total_price": 1,
            "amount": 1,
            "currency": 1,
            "created_at": 1,
        },
    ).to_list(5000)

    status_counter: Counter[str] = Counter()
    daily: defaultdict[str, dict[str, Any]] = defaultdict(lambda: {"revenue": 0.0, "count": 0})
    total_revenue = 0.0

    for doc in docs:
        status_name = _booking_status(doc)
        status_counter[status_name] += 1
        total = _booking_total(doc)
        total_revenue += total
        day_key = (_iso(doc.get("created_at")) or "")[:10]
        if day_key:
            daily[day_key]["revenue"] += total
            daily[day_key]["count"] += 1

    currency = _currency(docs[0]) if docs else "TRY"
    status_breakdown = [
        {"status": status_name, "count": count}
        for status_name, count in status_counter.most_common()
    ]
    daily_sales = [
        {
            "day": day,
            "revenue": round(values["revenue"], 2),
            "count": int(values["count"]),
        }
        for day, values in sorted(daily.items())
    ]

    return {
        "total_bookings": len(docs),
        "total_revenue": round(total_revenue, 2),
        "currency": currency,
        "status_breakdown": status_breakdown,
        "daily_sales": daily_sales,
    }
