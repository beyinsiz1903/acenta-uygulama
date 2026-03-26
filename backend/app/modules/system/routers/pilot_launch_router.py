"""Production Pilot Launch API Router — 10-Part Go-Live Engine.

Part 1   — Pilot Environment        GET/POST /api/pilot/environment
Part 2   — Supplier Traffic          GET/POST /api/pilot/supplier-traffic
Part 3   — Monitoring Stack          GET      /api/pilot/monitoring
Part 4   — Incident Detection        GET/POST /api/pilot/incidents
Part 5   — Agency Onboarding         GET/POST /api/pilot/agencies
Part 6   — Booking Flow              POST     /api/pilot/booking-flow
Part 7   — Production Incident Test  POST     /api/pilot/incident-test/{scenario}
Part 8   — Performance Metrics       GET      /api/pilot/performance
Part 9   — Pilot Report              GET      /api/pilot/report
Part 10  — Go-Live Decision          GET      /api/pilot/go-live
Dashboard                            GET      /api/pilot/dashboard
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from typing import Any

from app.db import get_db
from app.auth import require_roles

router = APIRouter(prefix="/api/pilot", tags=["pilot_launch"])

_OPS = ["admin", "ops", "super_admin", "agency_admin"]


# Part 1 — Pilot Environment
@router.get("/environment")
async def get_environment(
    current_user=Depends(require_roles(_OPS)), db=Depends(get_db),
) -> dict[str, Any]:
    from app.domain.pilot_launch.pilot_launch_service import get_pilot_environment as _f
    return await _f(db)


@router.post("/environment/activate")
async def activate_environment(
    current_user=Depends(require_roles(["admin", "super_admin"])), db=Depends(get_db),
) -> dict[str, Any]:
    from app.domain.pilot_launch.pilot_launch_service import activate_pilot_environment as _f
    return await _f(db)


# Part 2 — Supplier Traffic
@router.get("/supplier-traffic")
async def get_supplier_traffic(
    current_user=Depends(require_roles(_OPS)), db=Depends(get_db),
) -> dict[str, Any]:
    from app.domain.pilot_launch.pilot_launch_service import get_supplier_traffic_status as _f
    return await _f(db)


@router.post("/supplier-traffic/{supplier_code}/{mode}")
async def activate_supplier(
    supplier_code: str, mode: str,
    current_user=Depends(require_roles(["admin", "super_admin"])), db=Depends(get_db),
) -> dict[str, Any]:
    from app.domain.pilot_launch.pilot_launch_service import activate_supplier_traffic as _f
    return await _f(db, supplier_code, mode)


# Part 3 — Monitoring Stack
@router.get("/monitoring")
async def get_monitoring(
    current_user=Depends(require_roles(_OPS)), db=Depends(get_db),
) -> dict[str, Any]:
    from app.domain.pilot_launch.pilot_launch_service import get_monitoring_status as _f
    return await _f(db)


# Part 4 — Incident Detection
@router.get("/incidents")
async def get_incidents(
    current_user=Depends(require_roles(_OPS)), db=Depends(get_db),
) -> dict[str, Any]:
    from app.domain.pilot_launch.pilot_launch_service import get_incident_detection_status as _f
    return await _f(db)


@router.post("/incidents/simulate/{incident_type}")
async def simulate_incident_ep(
    incident_type: str,
    current_user=Depends(require_roles(_OPS)), db=Depends(get_db),
) -> dict[str, Any]:
    from app.domain.pilot_launch.pilot_launch_service import simulate_incident as _f
    return await _f(db, incident_type)


# Part 5 — Agency Onboarding
@router.get("/agencies")
async def get_agencies(
    current_user=Depends(require_roles(_OPS)), db=Depends(get_db),
) -> dict[str, Any]:
    from app.domain.pilot_launch.pilot_launch_service import get_pilot_agencies as _f
    return await _f(db)


@router.post("/agencies/onboard")
async def onboard_agency_ep(
    agency_name: str = Query(...),
    current_user=Depends(require_roles(["admin", "super_admin"])), db=Depends(get_db),
) -> dict[str, Any]:
    from app.domain.pilot_launch.pilot_launch_service import onboard_agency as _f
    return await _f(db, agency_name)


# Part 6 — Booking Flow
@router.post("/booking-flow/{flow_type}")
async def execute_booking(
    flow_type: str = "hotel",
    current_user=Depends(require_roles(_OPS)), db=Depends(get_db),
) -> dict[str, Any]:
    from app.domain.pilot_launch.pilot_launch_service import execute_booking_flow as _f
    return await _f(db, flow_type)


# Part 7 — Production Incident Test
@router.post("/incident-test/{scenario}")
async def run_incident_test(
    scenario: str,
    current_user=Depends(require_roles(_OPS)), db=Depends(get_db),
) -> dict[str, Any]:
    from app.domain.pilot_launch.pilot_launch_service import run_production_incident_test as _f
    return await _f(db, scenario)


# Part 8 — Performance Metrics
@router.get("/performance")
async def get_performance(
    current_user=Depends(require_roles(_OPS)), db=Depends(get_db),
) -> dict[str, Any]:
    from app.domain.pilot_launch.pilot_launch_service import get_real_performance_metrics as _f
    return await _f(db)


# Part 9 — Pilot Report
@router.get("/report")
async def get_report(
    current_user=Depends(require_roles(_OPS)), db=Depends(get_db),
) -> dict[str, Any]:
    from app.domain.pilot_launch.pilot_launch_service import generate_pilot_report as _f
    return await _f(db)


# Part 10 — Go-Live Decision
@router.get("/go-live")
async def get_go_live(
    current_user=Depends(require_roles(_OPS)), db=Depends(get_db),
) -> dict[str, Any]:
    from app.domain.pilot_launch.pilot_launch_service import get_go_live_decision as _f
    return await _f(db)


# Dashboard
@router.get("/dashboard")
async def get_dashboard(
    current_user=Depends(require_roles(_OPS)), db=Depends(get_db),
) -> dict[str, Any]:
    from app.domain.pilot_launch.pilot_launch_service import get_pilot_dashboard as _f
    return await _f(db)
