"""Market Launch Router.

Endpoints for the market launch and first customers phase:
  /api/market-launch/pilot-agencies — Pilot agency management
  /api/market-launch/usage-metrics — Real usage metrics
  /api/market-launch/feedback — Feedback collection
  /api/market-launch/pricing — SaaS pricing model
  /api/market-launch/launch-kpis — Launch KPI dashboard
  /api/market-launch/launch-report — Full launch report
  /api/market-launch/support — Support channels
  /api/market-launch/positioning — Market positioning
"""
from __future__ import annotations

from typing import Any
from fastapi import APIRouter, Depends, Body, Query

from app.db import get_db
from app.auth import require_roles

router = APIRouter(prefix="/api/market-launch", tags=["market_launch"])

_OPS = ["admin", "super_admin"]


# =========================================================================
# Pilot Agency Management
# =========================================================================

@router.get("/pilot-agencies")
async def list_pilot_agencies(
    db=Depends(get_db),
    current_user=Depends(require_roles(_OPS)),
) -> dict[str, Any]:
    from app.services.market_launch_service import get_pilot_agencies
    return await get_pilot_agencies(db)


@router.post("/pilot-agencies/onboard")
async def onboard_agency(
    payload: dict = Body(...),
    db=Depends(get_db),
    current_user=Depends(require_roles(_OPS)),
) -> dict[str, Any]:
    """Onboard a new pilot agency.

    Body: { company_name, contact_name, contact_email, contact_phone, pricing_tier }
    """
    from app.services.market_launch_service import onboard_pilot_agency
    return await onboard_pilot_agency(db, payload)


@router.put("/pilot-agencies/update")
async def update_agency(
    payload: dict = Body(...),
    db=Depends(get_db),
    current_user=Depends(require_roles(_OPS)),
) -> dict[str, Any]:
    """Update pilot agency status or metrics.

    Body: { company_name, status?, supplier_credentials_status?, total_searches?, ... }
    """
    from app.services.market_launch_service import update_pilot_agency
    company = payload.pop("company_name", "")
    return await update_pilot_agency(db, company, payload)


# =========================================================================
# Usage Metrics
# =========================================================================

@router.get("/usage-metrics")
async def usage_metrics(
    days: int = Query(default=7, ge=1, le=90),
    db=Depends(get_db),
    current_user=Depends(require_roles(_OPS)),
) -> dict[str, Any]:
    from app.services.market_launch_service import get_usage_metrics
    return await get_usage_metrics(db, days)


# =========================================================================
# Feedback
# =========================================================================

@router.post("/feedback")
async def submit_feedback(
    payload: dict = Body(...),
    db=Depends(get_db),
    current_user=Depends(require_roles(["admin", "super_admin", "agency_admin"])),
) -> dict[str, Any]:
    """Submit agency feedback.

    Body: { agency_name, ratings: { search_speed: 1-5, ... }, comments }
    """
    from app.services.market_launch_service import submit_feedback as _submit
    return await _submit(db, payload)


@router.get("/feedback")
async def get_feedback(
    db=Depends(get_db),
    current_user=Depends(require_roles(_OPS)),
) -> dict[str, Any]:
    from app.services.market_launch_service import get_feedback_summary
    return await get_feedback_summary(db)


# =========================================================================
# Pricing
# =========================================================================

@router.get("/pricing")
async def get_pricing(
    current_user=Depends(require_roles(["admin", "super_admin", "agency_admin"])),
) -> dict[str, Any]:
    from app.services.market_launch_service import PRICING_TIERS
    return {"tiers": PRICING_TIERS}


# =========================================================================
# Launch KPIs & Report
# =========================================================================

@router.get("/launch-kpis")
async def launch_kpis(
    db=Depends(get_db),
    current_user=Depends(require_roles(_OPS)),
) -> dict[str, Any]:
    from app.services.market_launch_service import get_launch_kpis
    return await get_launch_kpis(db)


@router.get("/launch-report")
async def launch_report(
    db=Depends(get_db),
    current_user=Depends(require_roles(_OPS)),
) -> dict[str, Any]:
    from app.services.market_launch_service import generate_launch_report
    return await generate_launch_report(db)


# =========================================================================
# Support & Positioning
# =========================================================================

@router.get("/support")
async def get_support(
    current_user=Depends(require_roles(["admin", "super_admin", "agency_admin"])),
) -> dict[str, Any]:
    from app.services.market_launch_service import SUPPORT_CHANNELS
    return {"channels": SUPPORT_CHANNELS}


@router.get("/positioning")
async def get_positioning(
    current_user=Depends(require_roles(_OPS)),
) -> dict[str, Any]:
    from app.services.market_launch_service import MARKET_POSITIONING
    return MARKET_POSITIONING
