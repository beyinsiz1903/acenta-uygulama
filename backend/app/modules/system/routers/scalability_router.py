"""Platform Scalability & Monitoring Router.

Exposes endpoints for:
  /api/scalability/cache-stats — Search cache hit/miss stats
  /api/scalability/rate-limit-stats — Rate limiter stats
  /api/scalability/scheduler-status — Job scheduler info
  /api/scalability/scheduler/trigger — Manual job trigger
  /api/scalability/metrics — Enhanced Prometheus metrics
  /api/scalability/supplier-metrics — Supplier-level metrics
  /api/scalability/search-metrics — Search cache metrics
  /api/scalability/monitoring-dashboard — Combined monitoring overview
  /api/scalability/redis-health — Redis health check
"""
from __future__ import annotations

from typing import Any
from fastapi import APIRouter, Depends, Body

from app.db import get_db
from app.auth import require_roles

router = APIRouter(prefix="/api/scalability", tags=["scalability"])


@router.get("/cache-stats")
async def cache_stats(
    current_user=Depends(require_roles(["admin", "super_admin"])),
) -> dict[str, Any]:
    """Get search cache hit/miss statistics."""
    from app.suppliers.cache import get_cache_hit_miss, get_cache_stats
    hit_miss = get_cache_hit_miss()
    try:
        org_id = current_user.get("organization_id", current_user.get("org_id", ""))
        detailed = await get_cache_stats(org_id)
    except Exception:
        detailed = {"status": "unavailable"}
    return {"hit_miss": hit_miss, "detailed": detailed}


@router.get("/rate-limit-stats")
async def rate_limit_stats(
    current_user=Depends(require_roles(["admin", "super_admin"])),
) -> dict[str, Any]:
    """Get rate limiter statistics."""
    from app.infrastructure.rate_limiter import get_rate_limit_stats, RATE_TIERS
    stats = await get_rate_limit_stats()
    return {"stats": stats, "tiers_config": RATE_TIERS}


@router.get("/scheduler-status")
async def scheduler_status(
    current_user=Depends(require_roles(["admin", "super_admin"])),
) -> dict[str, Any]:
    """Get job scheduler status and history."""
    from app.services.job_scheduler_service import get_scheduler_status
    return get_scheduler_status()


@router.post("/scheduler/trigger")
async def trigger_scheduler_job(
    payload: dict = Body(...),
    current_user=Depends(require_roles(["admin", "super_admin"])),
) -> dict[str, Any]:
    """Manually trigger a scheduled job.

    Body: { "job_name": "booking_status_sync" | "supplier_reconciliation" | ... }
    """
    from app.services.job_scheduler_service import trigger_job_manually
    job_name = payload.get("job_name", "")
    return await trigger_job_manually(job_name)


@router.get("/metrics")
async def prometheus_metrics(
    current_user=Depends(require_roles(["admin", "super_admin"])),
) -> dict[str, Any]:
    """Get enhanced Prometheus-format metrics."""
    from app.services.prometheus_metrics_service import generate_prometheus_metrics
    raw = await generate_prometheus_metrics()
    return {"format": "prometheus", "data": raw}


@router.get("/supplier-metrics")
async def supplier_metrics(
    current_user=Depends(require_roles(["admin", "super_admin"])),
) -> dict[str, Any]:
    """Get supplier-level operational metrics."""
    from app.services.prometheus_metrics_service import get_supplier_metrics_snapshot
    return {"suppliers": get_supplier_metrics_snapshot()}


@router.get("/search-metrics")
async def search_metrics(
    current_user=Depends(require_roles(["admin", "super_admin"])),
) -> dict[str, Any]:
    """Get search cache metrics by product type."""
    from app.services.prometheus_metrics_service import get_search_metrics_snapshot
    return {"search_metrics": get_search_metrics_snapshot()}


@router.get("/redis-health")
async def redis_health_check(
    current_user=Depends(require_roles(["admin", "super_admin"])),
) -> dict[str, Any]:
    """Check Redis health."""
    from app.infrastructure.redis_client import redis_health
    return await redis_health()


@router.get("/monitoring-dashboard")
async def monitoring_dashboard(
    current_user=Depends(require_roles(["admin", "super_admin"])),
    db=Depends(get_db),
) -> dict[str, Any]:
    """Combined monitoring dashboard data for frontend."""
    from app.suppliers.cache import get_cache_hit_miss
    from app.services.prometheus_metrics_service import (
        get_supplier_metrics_snapshot, get_search_metrics_snapshot,
    )
    from app.services.job_scheduler_service import get_scheduler_status
    from app.infrastructure.redis_client import redis_health
    from app.infrastructure.rate_limiter import get_rate_limit_stats

    # Parallel data gathering
    redis_status = await redis_health()
    rate_stats = await get_rate_limit_stats()

    # Recent bookings count (last 24h)
    from datetime import datetime, timezone, timedelta
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    recent_bookings = await db["unified_bookings"].count_documents({"created_at": {"$gte": cutoff}})
    recent_searches = await db["search_analytics"].count_documents({"timestamp": {"$gte": cutoff}})
    recent_commissions = await db["commission_records"].count_documents({"created_at": {"$gte": cutoff}})

    # Reconciliation mismatches
    recon_mismatches = await db["booking_reconciliation"].count_documents({
        "$or": [{"status_mismatch": True}, {"price_mismatch": True}]
    })

    return {
        "cache": get_cache_hit_miss(),
        "supplier_metrics": get_supplier_metrics_snapshot(),
        "search_metrics": get_search_metrics_snapshot(),
        "scheduler": get_scheduler_status(),
        "redis": redis_status,
        "rate_limits": rate_stats,
        "last_24h": {
            "bookings": recent_bookings,
            "searches": recent_searches,
            "commissions": recent_commissions,
            "recon_mismatches": recon_mismatches,
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }



# =========================================================================
# Multi-Currency & Tax Endpoints
# =========================================================================

@router.get("/tax-regions")
async def get_tax_regions(
    current_user=Depends(require_roles(["admin", "super_admin"])),
) -> dict[str, Any]:
    """Get supported tax regions and rates."""
    from app.services.tax_engine import get_supported_tax_regions
    return {"regions": await get_supported_tax_regions()}


@router.post("/tax-breakdown")
async def calculate_tax(
    payload: dict = Body(...),
    current_user=Depends(require_roles(["admin", "super_admin", "agency_admin"])),
) -> dict[str, Any]:
    """Calculate tax breakdown for a price.

    Body:
      base_price: float
      country_code: str (default TR)
      supplier_code: str (optional)
      nights: int (default 1)
      rooms: int (default 1)
    """
    from app.services.tax_engine import calculate_tax_breakdown
    return calculate_tax_breakdown(
        base_price=float(payload.get("base_price", 0)),
        country_code=payload.get("country_code", "TR"),
        supplier_code=payload.get("supplier_code", ""),
        nights=int(payload.get("nights", 1)),
        rooms=int(payload.get("rooms", 1)),
        guests=int(payload.get("guests", 2)),
    )


@router.post("/currency-convert")
async def convert_currency(
    payload: dict = Body(...),
    current_user=Depends(require_roles(["admin", "super_admin", "agency_admin"])),
) -> dict[str, Any]:
    """Convert a booking amount between currencies.

    Body:
      amount: float
      from_currency: str
      to_currency: str
    """
    from app.services.multicurrency_service import convert_booking_amount
    org_id = current_user.get("organization_id", current_user.get("org_id", ""))
    return await convert_booking_amount(
        org_id,
        float(payload.get("amount", 0)),
        payload.get("from_currency", "TRY"),
        payload.get("to_currency", "EUR"),
    )


@router.get("/currency-rates")
async def get_currency_rates(
    current_user=Depends(require_roles(["admin", "super_admin"])),
) -> dict[str, Any]:
    """Get current exchange rates."""
    from app.services.multicurrency_service import get_current_rates
    org_id = current_user.get("organization_id", current_user.get("org_id", ""))
    rates = await get_current_rates(org_id)
    return {"rates": rates, "supported_currencies": ["TRY", "EUR", "USD", "GBP"]}
