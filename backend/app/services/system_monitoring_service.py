"""O3 - Monitoring & Metrics Service.

Provides system metrics, slow request logging, and exception aggregation.
"""
from __future__ import annotations

import shutil
import uuid
from datetime import datetime, timedelta
from typing import Any, Optional

from app.db import get_db
from app.utils import now_utc


async def get_system_metrics() -> dict[str, Any]:
    """Aggregate system-wide metrics."""
    db = await get_db()
    now = now_utc()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    five_min_ago = now - timedelta(minutes=5)

    # Active tenants
    try:
        active_tenants = len(await db.organizations.distinct("_id"))
    except Exception:
        active_tenants = 0

    # Total users
    try:
        total_users = await db.users.count_documents({})
    except Exception:
        total_users = 0

    # Invoices today
    try:
        invoices_today = await db.efatura_invoices.count_documents(
            {"created_at": {"$gte": today_start}}
        )
    except Exception:
        invoices_today = 0

    # SMS sent today
    try:
        sms_sent_today = await db.sms_logs.count_documents(
            {"created_at": {"$gte": today_start}}
        )
    except Exception:
        sms_sent_today = 0

    # Tickets checked in today
    try:
        tickets_checked_in_today = await db.tickets.count_documents(
            {"status": "checked_in", "checked_in_at": {"$gte": today_start}}
        )
    except Exception:
        tickets_checked_in_today = 0

    # Average request latency (from request_logs, last 5 min)
    avg_latency = 0.0
    try:
        pipeline = [
            {"$match": {"timestamp": {"$gte": five_min_ago}}},
            {"$group": {"_id": None, "avg_latency": {"$avg": "$latency_ms"}}},
        ]
        result = await db.request_logs.aggregate(pipeline).to_list(length=1)
        if result:
            avg_latency = round(result[0].get("avg_latency", 0), 2)
    except Exception:
        avg_latency = 0.0

    # Error rate (status >= 500 in last 5 min)
    error_rate = 0.0
    try:
        total_requests = await db.request_logs.count_documents(
            {"timestamp": {"$gte": five_min_ago}}
        )
        error_requests = await db.request_logs.count_documents(
            {"timestamp": {"$gte": five_min_ago}, "status_code": {"$gte": 500}}
        )
        if total_requests > 0:
            error_rate = round((error_requests / total_requests) * 100, 2)
    except Exception:
        error_rate = 0.0

    # Disk usage
    try:
        usage = shutil.disk_usage("/")
        disk_usage_percent = round((usage.used / usage.total) * 100, 2)
    except Exception:
        disk_usage_percent = 0.0

    return {
        "active_tenants": active_tenants,
        "total_users": total_users,
        "invoices_today": invoices_today,
        "sms_sent_today": sms_sent_today,
        "tickets_checked_in_today": tickets_checked_in_today,
        "avg_request_latency_ms": avg_latency,
        "error_rate_percent": error_rate,
        "disk_usage_percent": disk_usage_percent,
        "computed_at": now.isoformat(),
    }


async def log_slow_request(
    path: str,
    method: str,
    latency_ms: float,
    request_id: str,
    status_code: int,
) -> None:
    """Log a slow request (>1000ms) as a system warning."""
    db = await get_db()
    signature = f"slow_request_{method}_{path}"

    await db.system_errors.update_one(
        {"signature": signature},
        {
            "$set": {
                "message": f"Slow request: {method} {path} took {latency_ms}ms",
                "stack_trace": f"status_code={status_code}, latency_ms={latency_ms}",
                "severity": "warning",
                "last_seen": now_utc(),
                "request_id": request_id,
            },
            "$inc": {"count": 1},
            "$setOnInsert": {
                "_id": str(uuid.uuid4()),
                "signature": signature,
                "first_seen": now_utc(),
            },
        },
        upsert=True,
    )


async def aggregate_exception(
    message: str,
    stack_trace: str,
    request_id: Optional[str] = None,
) -> None:
    """Aggregate an unhandled exception by signature."""
    db = await get_db()
    # Use first line of stack trace as signature
    signature = f"exception_{message[:100]}" if message else "exception_unknown"

    await db.system_errors.update_one(
        {"signature": signature},
        {
            "$set": {
                "message": message[:500],
                "stack_trace": stack_trace[:5000],
                "severity": "error",
                "last_seen": now_utc(),
                "request_id": request_id,
            },
            "$inc": {"count": 1},
            "$setOnInsert": {
                "_id": str(uuid.uuid4()),
                "signature": signature,
                "first_seen": now_utc(),
            },
        },
        upsert=True,
    )


async def list_system_errors(
    skip: int = 0, limit: int = 50, severity: Optional[str] = None
) -> list[dict[str, Any]]:
    """List aggregated system errors."""
    db = await get_db()
    query: dict[str, Any] = {}
    if severity:
        query["severity"] = severity

    cursor = db.system_errors.find(query).sort("last_seen", -1).skip(skip).limit(limit)
    items = await cursor.to_list(length=limit)
    for item in items:
        for field in ("first_seen", "last_seen"):
            if isinstance(item.get(field), datetime):
                item[field] = item[field].isoformat()
    return items


async def store_request_log(
    path: str,
    method: str,
    status_code: int,
    latency_ms: float,
    request_id: str,
    tenant_id: str = "",
    user_id: str = "",
) -> None:
    """Store a request log entry for metrics computation."""
    db = await get_db()
    await db.request_logs.insert_one({
        "_id": str(uuid.uuid4()),
        "path": path,
        "method": method,
        "status_code": status_code,
        "latency_ms": latency_ms,
        "request_id": request_id,
        "tenant_id": tenant_id,
        "user_id": user_id,
        "timestamp": now_utc(),
    })
