from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel

from app.auth import get_current_user
from app.constants.usage_metrics import UsageMetric
from app.db import get_db
from app.services.quota_enforcement_service import enforce_quota_or_raise
from app.services.usage_service import track_export_generated, track_report_generated
from app.utils import get_or_create_correlation_id, parse_date_range, to_csv

router = APIRouter(prefix="/api/reports", tags=["reports"])

class ReportGenerateBody(BaseModel):
    start: str | None = None
    end: str | None = None
    days: int | None = 30


def _report_scope_filter(user: dict[str, Any]) -> dict[str, Any]:
    flt: dict[str, Any] = {"organization_id": user["organization_id"]}
    roles = set(user.get("roles") or [])
    if user.get("agency_id") and roles.intersection({"agency_admin", "agency_agent"}) and not roles.intersection({"super_admin", "admin"}):
        flt["agency_id"] = user.get("agency_id")
    return flt


def _safe_iso(value: Any) -> str | None:
    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()
        except Exception:
            return None
    text = str(value or "").strip()
    return text or None


def _safe_day(value: Any) -> str:
    if hasattr(value, "strftime"):
        try:
            return value.strftime("%Y-%m-%d")
        except Exception:
            pass
    text = str(value or "").strip()
    return text[:10] if text else "-"


def _safe_float(*values: Any) -> float:
    for value in values:
        if value in (None, ""):
            continue
        try:
            return round(float(value), 2)
        except Exception:
            continue
    return 0.0


def _normalize_status(value: Any) -> str:
    raw = str(value or "draft").strip().lower()
    return {
        "booked": "confirmed",
        "guaranteed": "confirmed",
        "canceled": "cancelled",
        "paid": "completed",
        "quoted": "draft",
    }.get(raw, raw or "draft")


def _normalize_payment_status(doc: dict[str, Any], status: str) -> str:
    payment_status = str(doc.get("payment_status") or "").strip().lower()
    if payment_status:
        return payment_status
    if status in {"completed", "confirmed"}:
        return "paid"
    if status == "cancelled":
        return "void"
    return "pending"


def _normalize_report_row(doc: dict[str, Any], source: str, hotel_name_map: dict[str, str]) -> dict[str, Any]:
    status = _normalize_status(doc.get("status") or doc.get("state"))
    created_at = doc.get("created_at")
    amount = _safe_float(
        doc.get("gross_amount"),
        doc.get("total_price"),
        doc.get("amount"),
        (doc.get("amounts") or {}).get("sell"),
    )
    hotel_name = (
        doc.get("hotel_name")
        or doc.get("product_name")
        or hotel_name_map.get(str(doc.get("hotel_id")))
        or "Bilinmeyen otel"
    )
    guest_name = (
        (doc.get("guest") or {}).get("full_name")
        or doc.get("guest_name")
        or doc.get("customer_name")
        or "Misafir"
    )
    guest_email = (
        (doc.get("guest") or {}).get("email")
        or doc.get("guest_email")
        or doc.get("customer_email")
        or doc.get("email")
    )
    return {
        "id": str(doc.get("_id")),
        "source": source,
        "reference": doc.get("booking_ref") or doc.get("code") or str(doc.get("_id")),
        "hotel_name": hotel_name,
        "guest_name": guest_name,
        "guest_email": guest_email,
        "status": status,
        "payment_status": _normalize_payment_status(doc, status),
        "amount": amount,
        "currency": doc.get("currency") or "TRY",
        "created_at": _safe_iso(created_at),
        "day": _safe_day(created_at),
    }


async def _load_hotel_name_map(db, filters: dict[str, Any]) -> dict[str, str]:
    hotel_docs = await db.hotels.find(filters, {"_id": 1, "name": 1}).to_list(500)
    return {str(doc.get("_id")): doc.get("name") or "-" for doc in hotel_docs}


async def _load_report_rows(
    db,
    *,
    user: dict[str, Any],
    start_dt: datetime,
    end_dt: datetime,
) -> list[dict[str, Any]]:
    base_filters = _report_scope_filter(user)
    date_filter = {"created_at": {"$gte": start_dt, "$lt": end_dt}}
    query = {**base_filters, **date_filter}
    projection = {
        "_id": 1,
        "booking_ref": 1,
        "code": 1,
        "hotel_id": 1,
        "hotel_name": 1,
        "product_name": 1,
        "guest": 1,
        "guest_name": 1,
        "guest_email": 1,
        "customer_name": 1,
        "customer_email": 1,
        "status": 1,
        "state": 1,
        "payment_status": 1,
        "gross_amount": 1,
        "total_price": 1,
        "amount": 1,
        "amounts": 1,
        "currency": 1,
        "created_at": 1,
    }
    bookings = await db.bookings.find(query, projection).sort("created_at", -1).limit(1000).to_list(1000)
    reservations = await db.reservations.find(query, projection).sort("created_at", -1).limit(1000).to_list(1000)
    hotel_name_map = await _load_hotel_name_map(db, {"organization_id": user["organization_id"]})

    rows = [
        *[_normalize_report_row(doc, "agency_booking", hotel_name_map) for doc in bookings],
        *[_normalize_report_row(doc, "reservation", hotel_name_map) for doc in reservations],
    ]
    rows.sort(key=lambda row: row.get("created_at") or "", reverse=True)
    return rows


async def _resolve_report_tenant_id(db, user: dict[str, Any]) -> str | None:
    tenant_id = user.get("tenant_id")
    if tenant_id:
        return str(tenant_id)

    tenant = await db.tenants.find_one(
        {"organization_id": user.get("organization_id")},
        {"_id": 1},
        sort=[("created_at", 1)],
    )
    if tenant and tenant.get("_id") is not None:
        return str(tenant.get("_id"))
    return None


def _build_generated_report(rows: list[dict[str, Any]], *, start_dt: datetime, end_dt: datetime, days: int) -> dict[str, Any]:
    revenue_total = round(sum(row["amount"] for row in rows if row["status"] != "cancelled"), 2)
    total_bookings = len(rows)
    avg_booking_value = round(revenue_total / total_bookings, 2) if total_bookings else 0.0
    active_customers = {
        (row.get("guest_email") or row.get("guest_name") or "").strip().lower()
        for row in rows
        if (row.get("guest_email") or row.get("guest_name"))
    }

    status_counts: dict[str, int] = defaultdict(int)
    payment_health: dict[str, int] = defaultdict(int)
    source_counts: dict[str, int] = defaultdict(int)
    day_buckets: dict[str, dict[str, float]] = {}
    hotel_buckets: dict[str, dict[str, float]] = {}

    for row in rows:
        status_counts[row["status"]] += 1
        payment_health[row["payment_status"]] += 1
        source_counts[row["source"]] += 1

        day_bucket = day_buckets.setdefault(row["day"], {"revenue": 0.0, "count": 0})
        day_bucket["revenue"] += row["amount"]
        day_bucket["count"] += 1

        hotel_bucket = hotel_buckets.setdefault(row["hotel_name"], {"revenue": 0.0, "count": 0})
        hotel_bucket["revenue"] += row["amount"]
        hotel_bucket["count"] += 1

    daily_revenue = [
        {
            "day": day,
            "revenue": round(values["revenue"], 2),
            "count": int(values["count"]),
        }
        for day, values in sorted(day_buckets.items())
    ]
    top_hotels = sorted(
        [
            {
                "hotel_name": hotel_name,
                "booking_count": int(values["count"]),
                "revenue": round(values["revenue"], 2),
            }
            for hotel_name, values in hotel_buckets.items()
        ],
        key=lambda item: (item["booking_count"], item["revenue"]),
        reverse=True,
    )[:5]

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "period": {
            "start": start_dt.date().isoformat(),
            "end": (end_dt - timedelta(seconds=1)).date().isoformat(),
            "days": days,
        },
        "kpis": {
            "booking_count": total_bookings,
            "revenue_total": revenue_total,
            "avg_booking_value": avg_booking_value,
            "active_customer_count": len(active_customers),
            "confirmed_count": status_counts.get("confirmed", 0),
            "pending_count": status_counts.get("pending", 0) + status_counts.get("draft", 0),
            "cancelled_count": status_counts.get("cancelled", 0),
        },
        "status_breakdown": [
            {"status": status, "count": count}
            for status, count in sorted(status_counts.items(), key=lambda item: item[1], reverse=True)
        ],
        "daily_revenue": daily_revenue,
        "top_hotels": top_hotels,
        "payment_health": [
            {"status": status, "count": count}
            for status, count in sorted(payment_health.items(), key=lambda item: item[1], reverse=True)
        ],
        "source_breakdown": [
            {"source": source, "count": count}
            for source, count in sorted(source_counts.items(), key=lambda item: item[1], reverse=True)
        ],
        "recent_bookings": rows[:6],
    }


async def _generate_report_payload(
    request: Request,
    *,
    user: dict[str, Any],
    start: str | None,
    end: str | None,
    days: int | None,
) -> dict[str, Any]:
    start_dt, end_dt, actual_days = parse_date_range(start, end, days, default_days=30, max_days=180)
    db = await get_db()
    tenant_id = await _resolve_report_tenant_id(db, user)
    await enforce_quota_or_raise(
        organization_id=user.get("organization_id"),
        tenant_id=tenant_id,
        metric=UsageMetric.REPORT_GENERATED,
        action_label="Operasyon raporu oluşturma",
    )
    rows = await _load_report_rows(db, user=user, start_dt=start_dt, end_dt=end_dt)
    payload = _build_generated_report(rows, start_dt=start_dt, end_dt=end_dt, days=actual_days)

    correlation_id = get_or_create_correlation_id(request, None)
    await track_report_generated(
        organization_id=user.get("organization_id"),
        tenant_id=tenant_id,
        report_type="operations_overview",
        output_format="json",
        source="reports.generate",
        source_event_id=f"{correlation_id}:operations-overview:{payload['period']['start']}:{payload['period']['end']}",
        metadata={
            "booking_count": payload["kpis"]["booking_count"],
            "days": actual_days,
        },
    )
    return payload


@router.get("/reservations-summary", dependencies=[Depends(get_current_user)])
async def reservations_summary(user=Depends(get_current_user)):
    db = await get_db()
    pipeline = [
        {"$match": _report_scope_filter(user)},
        {"$group": {"_id": "$status", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
    ]
    rows = await db.reservations.aggregate(pipeline).to_list(100)
    return [{"status": r["_id"], "count": r["count"]} for r in rows]


@router.get("/sales-summary", dependencies=[Depends(get_current_user)])
async def sales_summary(days: int = 14, user=Depends(get_current_user)):
    db = await get_db()
    days = max(1, min(int(days or 14), 180))
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    pipeline = [
        {"$match": {**_report_scope_filter(user), "created_at": {"$gte": cutoff}}},
        {
            "$addFields": {
                "created_day": {"$substr": [{"$toString": "$created_at"}, 0, 10]}
            }
        },
        {
            "$group": {
                "_id": "$created_day",
                "revenue": {"$sum": "$total_price"},
                "count": {"$sum": 1},
            }
        },
        {"$sort": {"_id": 1}},
    ]
    rows = await db.reservations.aggregate(pipeline).to_list(400)
    return [{"day": r["_id"], "revenue": round(float(r.get("revenue") or 0), 2), "count": r["count"]} for r in rows]


@router.get("/generate", dependencies=[Depends(get_current_user)])
async def generate_report_get(
    request: Request,
    start: str | None = None,
    end: str | None = None,
    days: int | None = 30,
    user=Depends(get_current_user),
):
    return await _generate_report_payload(request, user=user, start=start, end=end, days=days)


@router.post("/generate", dependencies=[Depends(get_current_user)])
async def generate_report_post(
    body: ReportGenerateBody,
    request: Request,
    user=Depends(get_current_user),
):
    return await _generate_report_payload(request, user=user, start=body.start, end=body.end, days=body.days)


@router.get("/sales-summary.csv", dependencies=[Depends(get_current_user)])
async def sales_summary_csv(request: Request, days: int = 14, user=Depends(get_current_user)):
    await enforce_quota_or_raise(
        organization_id=user.get("organization_id"),
        tenant_id=user.get("tenant_id"),
        metric=UsageMetric.EXPORT_GENERATED,
        action_label="CSV export alma",
    )
    rows = await sales_summary(days=days, user=user)
    csv_str = to_csv(rows, ["day", "revenue", "count"])
    await track_export_generated(
        organization_id=user.get("organization_id"),
        tenant_id=user.get("tenant_id"),
        export_type="sales_summary",
        output_format="csv",
        source="reports.sales_summary",
        source_event_id=f"{get_or_create_correlation_id(request, None)}:sales-summary-csv:{days}",
        metadata={"row_count": len(rows), "days": days},
    )
    return Response(content=csv_str, media_type="text/csv")
