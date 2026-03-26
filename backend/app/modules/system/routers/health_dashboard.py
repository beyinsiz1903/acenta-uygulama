"""Enhanced Health Dashboard Router.

Provides:
- Comprehensive health checks
- Service status monitoring
- DB connection health
- Worker status
- Cache stats
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse

from app.auth import require_roles
from app.services.health_dashboard_service import get_health_dashboard
from app.services.prometheus_metrics_service import generate_prometheus_metrics

router = APIRouter(prefix="/api/system", tags=["system-health"])


@router.get("/health-dashboard")
async def health_dashboard(
    _user=Depends(require_roles(["super_admin"])),
):
    """Get comprehensive health dashboard."""
    return await get_health_dashboard()


@router.get("/prometheus", response_class=PlainTextResponse)
async def prometheus_metrics(
    _user=Depends(require_roles(["super_admin"])),
):
    """Enhanced Prometheus-format metrics."""
    return await generate_prometheus_metrics()


# Public health endpoint (no auth required)
@router.get("/ping")
async def ping():
    """Simple ping/pong for load balancers."""
    return {"status": "pong"}
