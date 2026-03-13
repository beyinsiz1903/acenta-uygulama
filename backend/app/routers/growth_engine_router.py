"""Growth Engine Router.

Agency acquisition funnel, lead/demo management, referral system,
activation metrics, customer success, onboarding, segmentation,
supplier expansion, and growth KPIs.
"""
from __future__ import annotations

from typing import Any
from fastapi import APIRouter, Depends, Body, Query

from app.db import get_db
from app.auth import require_roles

router = APIRouter(prefix="/api/growth", tags=["growth_engine"])

_OPS = ["admin", "super_admin"]

# ── Funnel ──────────────────────────────────────────────────

@router.get("/funnel")
async def get_funnel(
    current_user=Depends(require_roles(_OPS)), db=Depends(get_db),
) -> dict[str, Any]:
    from app.services.growth_engine_service import get_funnel_metrics
    return await get_funnel_metrics(db)

# ── Leads ───────────────────────────────────────────────────

@router.get("/leads")
async def list_leads(
    stage: str = Query(None),
    current_user=Depends(require_roles(_OPS)), db=Depends(get_db),
) -> dict[str, Any]:
    from app.services.growth_engine_service import list_leads as _list
    return await _list(db, stage=stage)


@router.post("/leads")
async def create_lead(
    payload: dict = Body(...),
    current_user=Depends(require_roles(_OPS)), db=Depends(get_db),
) -> dict[str, Any]:
    from app.services.growth_engine_service import create_lead as _create
    return await _create(db, payload)


@router.put("/leads/{lead_id}/stage")
async def update_lead_stage(
    lead_id: str,
    payload: dict = Body(...),
    current_user=Depends(require_roles(_OPS)), db=Depends(get_db),
) -> dict[str, Any]:
    from app.services.growth_engine_service import update_lead_stage as _update
    return await _update(db, lead_id, payload.get("stage", ""))

# ── Demos ───────────────────────────────────────────────────

@router.get("/demos")
async def list_demos(
    status: str = Query(None),
    current_user=Depends(require_roles(_OPS)), db=Depends(get_db),
) -> dict[str, Any]:
    from app.services.growth_engine_service import list_demos as _list
    return await _list(db, status=status)


@router.post("/demos")
async def create_demo(
    payload: dict = Body(...),
    current_user=Depends(require_roles(_OPS)), db=Depends(get_db),
) -> dict[str, Any]:
    from app.services.growth_engine_service import create_demo as _create
    return await _create(db, payload)


@router.put("/demos/{demo_id}")
async def update_demo(
    demo_id: str,
    payload: dict = Body(...),
    current_user=Depends(require_roles(_OPS)), db=Depends(get_db),
) -> dict[str, Any]:
    from app.services.growth_engine_service import update_demo as _update
    return await _update(db, demo_id, payload)

# ── Referrals ───────────────────────────────────────────────

@router.get("/referrals")
async def list_referrals(
    referrer_agency_id: str = Query(None),
    current_user=Depends(require_roles(_OPS)), db=Depends(get_db),
) -> dict[str, Any]:
    from app.services.growth_engine_service import list_referrals as _list
    return await _list(db, referrer_agency_id=referrer_agency_id)


@router.post("/referrals")
async def create_referral(
    payload: dict = Body(...),
    current_user=Depends(require_roles(_OPS)), db=Depends(get_db),
) -> dict[str, Any]:
    from app.services.growth_engine_service import create_referral as _create
    return await _create(db, payload)


@router.put("/referrals/{referral_id}/status")
async def update_referral_status(
    referral_id: str,
    payload: dict = Body(...),
    current_user=Depends(require_roles(_OPS)), db=Depends(get_db),
) -> dict[str, Any]:
    from app.services.growth_engine_service import update_referral_status as _update
    return await _update(db, referral_id, payload.get("status", ""))

# ── Activation ──────────────────────────────────────────────

@router.get("/activation")
async def list_activations(
    current_user=Depends(require_roles(_OPS)), db=Depends(get_db),
) -> dict[str, Any]:
    from app.services.growth_engine_service import list_all_activations
    return await list_all_activations(db)


@router.get("/activation/{agency_id}")
async def get_activation(
    agency_id: str,
    current_user=Depends(require_roles(_OPS)), db=Depends(get_db),
) -> dict[str, Any]:
    from app.services.growth_engine_service import get_agency_activation
    return await get_agency_activation(db, agency_id)


@router.post("/activation/{agency_id}/event")
async def record_event(
    agency_id: str,
    payload: dict = Body(...),
    current_user=Depends(require_roles(_OPS)), db=Depends(get_db),
) -> dict[str, Any]:
    from app.services.growth_engine_service import record_activation_event
    return await record_activation_event(db, agency_id, payload.get("event_type", ""), payload.get("details", ""))

# ── Customer Success ────────────────────────────────────────

@router.get("/customer-success")
async def customer_success(
    current_user=Depends(require_roles(_OPS)), db=Depends(get_db),
) -> dict[str, Any]:
    from app.services.growth_engine_service import get_customer_success_dashboard
    return await get_customer_success_dashboard(db)

# ── Onboarding ──────────────────────────────────────────────

@router.get("/onboarding/{agency_id}")
async def get_onboarding(
    agency_id: str,
    current_user=Depends(require_roles(_OPS)), db=Depends(get_db),
) -> dict[str, Any]:
    from app.services.growth_engine_service import get_onboarding_status
    return await get_onboarding_status(db, agency_id)


@router.post("/onboarding/{agency_id}/complete")
async def complete_task(
    agency_id: str,
    payload: dict = Body(...),
    current_user=Depends(require_roles(_OPS)), db=Depends(get_db),
) -> dict[str, Any]:
    from app.services.growth_engine_service import complete_onboarding_task
    return await complete_onboarding_task(db, agency_id, payload.get("task_key", ""))

# ── Segmentation ────────────────────────────────────────────

@router.get("/segments")
async def get_segments(
    current_user=Depends(require_roles(_OPS)), db=Depends(get_db),
) -> dict[str, Any]:
    from app.services.growth_engine_service import get_agency_segments
    return await get_agency_segments(db)

# ── Supplier Expansion ──────────────────────────────────────

@router.get("/supplier-requests")
async def list_supplier_requests(
    current_user=Depends(require_roles(_OPS)), db=Depends(get_db),
) -> dict[str, Any]:
    from app.services.growth_engine_service import list_supplier_requests as _list
    return await _list(db)


@router.post("/supplier-requests")
async def create_supplier_request(
    payload: dict = Body(...),
    current_user=Depends(require_roles(_OPS)), db=Depends(get_db),
) -> dict[str, Any]:
    from app.services.growth_engine_service import create_supplier_request as _create
    return await _create(db, payload)


@router.put("/supplier-requests/{request_id}")
async def update_supplier_request(
    request_id: str,
    payload: dict = Body(...),
    current_user=Depends(require_roles(_OPS)), db=Depends(get_db),
) -> dict[str, Any]:
    from app.services.growth_engine_service import update_supplier_request as _update
    return await _update(db, request_id, payload)

# ── Growth KPIs ─────────────────────────────────────────────

@router.get("/kpis")
async def get_kpis(
    days: int = Query(30, le=365),
    current_user=Depends(require_roles(_OPS)), db=Depends(get_db),
) -> dict[str, Any]:
    from app.services.growth_engine_service import get_growth_kpis
    return await get_growth_kpis(db, days=days)

# ── Full Growth Report ──────────────────────────────────────

@router.get("/report")
async def get_report(
    current_user=Depends(require_roles(_OPS)), db=Depends(get_db),
) -> dict[str, Any]:
    from app.services.growth_engine_service import get_growth_report
    return await get_growth_report(db)
