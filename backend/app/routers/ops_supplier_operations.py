"""Travel Platform Operations Layer — API Router.

Namespace: /api/ops/suppliers/*

Covers all 10 parts of the Operations Architecture:
  PART 1 — Supplier Performance Dashboard
  PART 2 — Booking Funnel Analytics
  PART 3 — Failover Visibility
  PART 4 — Booking Incident Tracking
  PART 5 — Supplier Debugging Tools
  PART 6 — Real-Time Alerting
  PART 7 — Voucher Pipeline
  PART 8 — OPS Admin Panel
  PART 9 — Operations Metrics (Prometheus)
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query, Request, Response
from pydantic import BaseModel, Field

from app.db import get_db
from app.auth import require_roles

logger = logging.getLogger("routers.ops_supplier_operations")

router = APIRouter(prefix="/api/ops/suppliers", tags=["ops_supplier_operations"])

OPS_ROLES = ["agency_admin", "admin", "super_admin"]


def _org_id(request: Request) -> str:
    user = getattr(request.state, "user", {}) or {}
    return user.get("organization_id", "")


def _user_id(request: Request) -> str:
    user = getattr(request.state, "user", {}) or {}
    return user.get("user_id") or user.get("email", "system")


# ============================================================================
# PART 1 — SUPPLIER PERFORMANCE DASHBOARD
# ============================================================================

@router.get("/performance/dashboard", summary="[P1] Supplier performance dashboard")
async def performance_dashboard(
    request: Request,
    window_minutes: int = Query(60, ge=5, le=1440),
    supplier_code: Optional[str] = Query(None),
    user=Depends(require_roles(OPS_ROLES)),
):
    from app.suppliers.operations.performance import get_supplier_performance_dashboard
    db = await get_db()
    return await get_supplier_performance_dashboard(
        db, _org_id(request), window_minutes=window_minutes, supplier_code=supplier_code,
    )


@router.get("/performance/timeseries/{supplier_code}", summary="[P1] Supplier latency timeseries")
async def performance_timeseries(
    supplier_code: str,
    request: Request,
    window_hours: int = Query(24, ge=1, le=168),
    bucket_minutes: int = Query(15, ge=5, le=60),
    user=Depends(require_roles(OPS_ROLES)),
):
    from app.suppliers.operations.performance import get_supplier_latency_timeseries
    db = await get_db()
    return await get_supplier_latency_timeseries(
        db, _org_id(request), supplier_code,
        window_hours=window_hours, bucket_minutes=bucket_minutes,
    )


# ============================================================================
# PART 2 — BOOKING FUNNEL ANALYTICS
# ============================================================================

@router.get("/funnel/analytics", summary="[P2] Booking funnel analytics")
async def booking_funnel(
    request: Request,
    window_hours: int = Query(24, ge=1, le=720),
    supplier_code: Optional[str] = Query(None),
    user=Depends(require_roles(OPS_ROLES)),
):
    from app.suppliers.operations.funnel import get_booking_funnel
    db = await get_db()
    return await get_booking_funnel(
        db, _org_id(request), window_hours=window_hours, supplier_code=supplier_code,
    )


@router.get("/funnel/timeseries", summary="[P2] Booking funnel timeseries")
async def funnel_timeseries(
    request: Request,
    window_hours: int = Query(24, ge=1, le=168),
    bucket_hours: int = Query(1, ge=1, le=24),
    user=Depends(require_roles(OPS_ROLES)),
):
    from app.suppliers.operations.funnel import get_funnel_timeseries
    db = await get_db()
    return await get_funnel_timeseries(
        db, _org_id(request), window_hours=window_hours, bucket_hours=bucket_hours,
    )


# ============================================================================
# PART 3 — FAILOVER VISIBILITY
# ============================================================================

@router.get("/failover/dashboard", summary="[P3] Failover visibility dashboard")
async def failover_dashboard(
    request: Request,
    window_hours: int = Query(24, ge=1, le=168),
    user=Depends(require_roles(OPS_ROLES)),
):
    from datetime import timedelta
    db = await get_db()
    org_id = _org_id(request)
    now = datetime.now(timezone.utc)
    window_start = now - timedelta(hours=window_hours)

    # Failover logs
    failover_pipeline = [
        {
            "$match": {
                "organization_id": org_id,
                "created_at": {"$gte": window_start},
            }
        },
        {
            "$group": {
                "_id": "$primary_supplier",
                "failover_count": {"$sum": 1},
                "targets": {"$push": "$selected_supplier"},
                "reasons": {"$push": "$reason"},
            }
        },
        {"$sort": {"failover_count": -1}},
    ]
    failover_results = await db.supplier_failover_logs.aggregate(failover_pipeline).to_list(50)

    # Circuit breaker states
    from app.suppliers.failover import failover_engine
    from app.suppliers.registry import supplier_registry
    circuit_states = []
    for adapter in supplier_registry.get_all():
        code = adapter.supplier_code
        rank = failover_engine._rankings.get(code)
        circuit_states.append({
            "supplier_code": code,
            "circuit_open": rank.circuit_open if rank else False,
            "health_score": round(rank.health_score, 4) if rank else 1.0,
            "composite_score": round(rank.composite_score, 4) if rank else 0.0,
            "disabled": rank.disabled if rank else False,
        })

    # Recent failover events
    recent_cursor = db.supplier_failover_logs.find(
        {"organization_id": org_id, "created_at": {"$gte": window_start}},
        {"_id": 0},
    ).sort("created_at", -1).limit(20)
    recent_events = await recent_cursor.to_list(20)

    # Supplier degradation timeline
    health_cursor = db.supplier_ecosystem_health.find(
        {"organization_id": org_id}, {"_id": 0}
    )
    health_states = []
    async for h in health_cursor:
        health_states.append({
            "supplier_code": h.get("supplier_code"),
            "state": h.get("state", "unknown"),
            "score": h.get("score"),
            "auto_disabled": h.get("auto_disabled", False),
        })

    return {
        "failover_summary": [
            {
                "primary_supplier": r["_id"],
                "failover_count": r["failover_count"],
                "targets": list(set(r["targets"])),
                "reasons": list(set(r["reasons"])),
            }
            for r in failover_results
        ],
        "circuit_breaker_states": circuit_states,
        "health_states": health_states,
        "recent_events": recent_events,
        "window_hours": window_hours,
    }


# ============================================================================
# PART 4 — BOOKING INCIDENT TRACKING
# ============================================================================

@router.get("/incidents/detect", summary="[P4] Detect booking incidents")
async def detect_incidents(
    request: Request,
    user=Depends(require_roles(OPS_ROLES)),
):
    from app.suppliers.operations.incidents import (
        detect_stuck_bookings,
        detect_failed_confirmations,
        detect_payment_mismatches,
    )
    db = await get_db()
    org_id = _org_id(request)

    stuck = await detect_stuck_bookings(db, org_id)
    failed = await detect_failed_confirmations(db, org_id)
    mismatches = await detect_payment_mismatches(db, org_id)

    return {
        "stuck_bookings": stuck,
        "failed_confirmations": failed,
        "payment_mismatches": mismatches,
        "total_issues": len(stuck) + len(failed) + len(mismatches),
    }


@router.get("/incidents", summary="[P4] List incidents")
async def list_incidents_endpoint(
    request: Request,
    status: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    user=Depends(require_roles(OPS_ROLES)),
):
    from app.suppliers.operations.incidents import list_incidents
    db = await get_db()
    incidents = await list_incidents(db, _org_id(request), status=status, severity=severity, limit=limit)
    return {"incidents": incidents, "total": len(incidents)}


class CreateIncidentBody(BaseModel):
    incident_type: str
    booking_id: Optional[str] = None
    supplier_code: Optional[str] = None
    severity: str = "warning"
    description: str = ""
    metadata: Dict[str, Any] = Field(default_factory=dict)


@router.post("/incidents", summary="[P4] Create incident", status_code=201)
async def create_incident_endpoint(
    body: CreateIncidentBody,
    request: Request,
    user=Depends(require_roles(OPS_ROLES)),
):
    from app.suppliers.operations.incidents import create_incident
    db = await get_db()
    return await create_incident(
        db, _org_id(request),
        incident_type=body.incident_type,
        booking_id=body.booking_id,
        supplier_code=body.supplier_code,
        severity=body.severity,
        description=body.description,
        metadata=body.metadata,
    )


class ResolveIncidentBody(BaseModel):
    resolution: str


@router.post("/incidents/{incident_id}/resolve", summary="[P4] Resolve incident")
async def resolve_incident_endpoint(
    incident_id: str,
    body: ResolveIncidentBody,
    request: Request,
    user=Depends(require_roles(OPS_ROLES)),
):
    from app.suppliers.operations.incidents import resolve_incident
    db = await get_db()
    return await resolve_incident(
        db, _org_id(request), incident_id,
        resolution=body.resolution, resolved_by=_user_id(request),
    )


class ForceStateBody(BaseModel):
    target_state: str
    reason: str


@router.post("/incidents/recovery/force-state/{booking_id}", summary="[P4] Force booking state")
async def force_state_endpoint(
    booking_id: str,
    body: ForceStateBody,
    request: Request,
    user=Depends(require_roles(OPS_ROLES)),
):
    from app.suppliers.operations.incidents import force_booking_state
    db = await get_db()
    return await force_booking_state(
        db, _org_id(request), booking_id,
        target_state=body.target_state,
        reason=body.reason,
        actor=_user_id(request),
    )


# ============================================================================
# PART 5 — SUPPLIER DEBUGGING TOOLS
# ============================================================================

@router.get("/debug/interactions", summary="[P5] List supplier interactions")
async def list_debug_interactions(
    request: Request,
    supplier_code: Optional[str] = Query(None),
    operation: Optional[str] = Query(None),
    trace_id: Optional[str] = Query(None),
    window_hours: int = Query(24, ge=1, le=168),
    limit: int = Query(50, le=200),
    user=Depends(require_roles(OPS_ROLES)),
):
    from app.suppliers.operations.debug_tools import get_supplier_interactions
    db = await get_db()
    interactions = await get_supplier_interactions(
        db, _org_id(request),
        supplier_code=supplier_code, operation=operation,
        trace_id=trace_id, window_hours=window_hours, limit=limit,
    )
    return {"interactions": interactions, "total": len(interactions)}


@router.get("/debug/interactions/{trace_id}", summary="[P5] Get interaction detail")
async def get_debug_interaction(
    trace_id: str,
    request: Request,
    user=Depends(require_roles(OPS_ROLES)),
):
    from app.suppliers.operations.debug_tools import get_interaction_detail
    db = await get_db()
    detail = await get_interaction_detail(db, _org_id(request), trace_id)
    if not detail:
        return {"error": "not_found"}
    return detail


@router.post("/debug/replay/{trace_id}", summary="[P5] Replay supplier request")
async def replay_interaction(
    trace_id: str,
    request: Request,
    dry_run: bool = Query(True),
    user=Depends(require_roles(OPS_ROLES)),
):
    from app.suppliers.operations.debug_tools import replay_supplier_request
    db = await get_db()
    return await replay_supplier_request(
        db, _org_id(request), trace_id, dry_run=dry_run,
    )


# ============================================================================
# PART 6 — REAL-TIME ALERTING
# ============================================================================

@router.get("/alerts", summary="[P6] List alerts")
async def list_alerts_endpoint(
    request: Request,
    status: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    alert_type: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    user=Depends(require_roles(OPS_ROLES)),
):
    from app.suppliers.operations.alerting import list_alerts
    db = await get_db()
    alerts = await list_alerts(
        db, _org_id(request),
        status=status, severity=severity, alert_type=alert_type, limit=limit,
    )
    return {"alerts": alerts, "total": len(alerts)}


@router.post("/alerts/{alert_id}/acknowledge", summary="[P6] Acknowledge alert")
async def acknowledge_alert_endpoint(
    alert_id: str,
    request: Request,
    user=Depends(require_roles(OPS_ROLES)),
):
    from app.suppliers.operations.alerting import acknowledge_alert
    db = await get_db()
    return await acknowledge_alert(
        db, _org_id(request), alert_id, acknowledged_by=_user_id(request),
    )


@router.post("/alerts/{alert_id}/resolve", summary="[P6] Resolve alert")
async def resolve_alert_endpoint(
    alert_id: str,
    request: Request,
    user=Depends(require_roles(OPS_ROLES)),
):
    from app.suppliers.operations.alerting import resolve_alert
    db = await get_db()
    return await resolve_alert(db, _org_id(request), alert_id)


@router.post("/alerts/evaluate", summary="[P6] Evaluate alert rules")
async def evaluate_alerts_endpoint(
    request: Request,
    user=Depends(require_roles(OPS_ROLES)),
):
    from app.suppliers.operations.alerting import evaluate_alert_rules
    db = await get_db()
    fired = await evaluate_alert_rules(db, _org_id(request))
    return {"fired_alerts": fired, "total_fired": len(fired)}


class AlertConfigBody(BaseModel):
    slack_webhook_url: Optional[str] = None
    email_recipients: Optional[List[str]] = None


@router.post("/alerts/config", summary="[P6] Configure alert channels")
async def configure_alerts_endpoint(
    body: AlertConfigBody,
    request: Request,
    user=Depends(require_roles(OPS_ROLES)),
):
    from app.suppliers.operations.alerting import configure_alert_channels
    db = await get_db()
    return await configure_alert_channels(
        db, _org_id(request),
        slack_webhook_url=body.slack_webhook_url,
        email_recipients=body.email_recipients,
    )


# ============================================================================
# PART 7 — VOUCHER PIPELINE
# ============================================================================

class CreateVoucherBody(BaseModel):
    booking_id: str
    supplier_booking_id: Optional[str] = None
    confirmation_code: Optional[str] = None
    guest_names: List[str] = Field(default_factory=list)
    hotel_name: Optional[str] = None
    check_in: Optional[str] = None
    check_out: Optional[str] = None
    room_type: Optional[str] = None
    total_price: Optional[float] = None
    currency: str = "TRY"


@router.post("/vouchers", summary="[P7] Create voucher record", status_code=201)
async def create_voucher_endpoint(
    body: CreateVoucherBody,
    request: Request,
    user=Depends(require_roles(OPS_ROLES)),
):
    from app.suppliers.operations.voucher_pipeline import create_voucher_record
    db = await get_db()
    return await create_voucher_record(
        db, _org_id(request), body.booking_id,
        supplier_booking_id=body.supplier_booking_id,
        confirmation_code=body.confirmation_code,
        guest_names=body.guest_names,
        hotel_name=body.hotel_name,
        check_in=body.check_in,
        check_out=body.check_out,
        room_type=body.room_type,
        total_price=body.total_price,
        currency=body.currency,
    )


@router.post("/vouchers/{voucher_id}/generate", summary="[P7] Generate voucher PDF")
async def generate_voucher_endpoint(
    voucher_id: str,
    request: Request,
    user=Depends(require_roles(OPS_ROLES)),
):
    from app.suppliers.operations.voucher_pipeline import generate_voucher
    db = await get_db()
    return await generate_voucher(db, _org_id(request), voucher_id)


class SendVoucherBody(BaseModel):
    recipient_email: str


@router.post("/vouchers/{voucher_id}/send", summary="[P7] Send voucher email")
async def send_voucher_endpoint(
    voucher_id: str,
    body: SendVoucherBody,
    request: Request,
    user=Depends(require_roles(OPS_ROLES)),
):
    from app.suppliers.operations.voucher_pipeline import send_voucher_email
    db = await get_db()
    return await send_voucher_email(
        db, _org_id(request), voucher_id, recipient_email=body.recipient_email,
    )


@router.get("/vouchers/pipeline", summary="[P7] Voucher pipeline status")
async def voucher_pipeline_status(
    request: Request,
    status_filter: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    user=Depends(require_roles(OPS_ROLES)),
):
    from app.suppliers.operations.voucher_pipeline import get_voucher_pipeline_status
    db = await get_db()
    return await get_voucher_pipeline_status(
        db, _org_id(request), status_filter=status_filter, limit=limit,
    )


@router.post("/vouchers/retry-failed", summary="[P7] Retry failed vouchers")
async def retry_failed_vouchers_endpoint(
    request: Request,
    user=Depends(require_roles(OPS_ROLES)),
):
    from app.suppliers.operations.voucher_pipeline import retry_failed_vouchers
    db = await get_db()
    return await retry_failed_vouchers(db, _org_id(request))


# ============================================================================
# PART 8 — OPS ADMIN PANEL
# ============================================================================

@router.get("/admin/booking/{booking_id}", summary="[P8] Inspect booking")
async def inspect_booking(
    booking_id: str,
    request: Request,
    user=Depends(require_roles(OPS_ROLES)),
):
    db = await get_db()
    org_id = _org_id(request)

    booking = await db.bookings.find_one(
        {"_id": booking_id, "organization_id": org_id},
        {"_id": 0},
    )
    if not booking:
        return {"error": "booking_not_found"}

    # Get orchestration runs
    runs_cursor = db.booking_orchestration_runs.find(
        {"booking_id": booking_id, "organization_id": org_id},
        {"_id": 0},
    ).sort("created_at", -1).limit(10)
    runs = await runs_cursor.to_list(10)

    # Get vouchers
    voucher_cursor = db.voucher_pipeline.find(
        {"booking_id": booking_id, "organization_id": org_id},
        {"_id": 0, "pdf_base64": 0, "html_content": 0},
    )
    vouchers = await voucher_cursor.to_list(10)

    # Get incidents
    incident_cursor = db.ops_incidents.find(
        {"booking_id": booking_id, "organization_id": org_id},
        {"_id": 0},
    ).sort("created_at", -1)
    incidents = await incident_cursor.to_list(10)

    return {
        "booking": booking,
        "orchestration_runs": runs,
        "vouchers": vouchers,
        "incidents": incidents,
    }


class SupplierOverrideBody(BaseModel):
    action: str  # "circuit_open", "circuit_close", "disable", "enable"
    reason: str


@router.post("/admin/supplier/{supplier_code}/override", summary="[P8] Override supplier state")
async def supplier_override(
    supplier_code: str,
    body: SupplierOverrideBody,
    request: Request,
    user=Depends(require_roles(OPS_ROLES)),
):
    from app.suppliers.failover import failover_engine, SupplierRank

    action = body.action
    if action == "circuit_open":
        failover_engine.mark_circuit_open(supplier_code)
    elif action == "circuit_close":
        failover_engine.mark_circuit_closed(supplier_code)
    elif action == "disable":
        if supplier_code not in failover_engine._rankings:
            failover_engine._rankings[supplier_code] = SupplierRank(supplier_code=supplier_code)
        failover_engine._rankings[supplier_code].disabled = True
    elif action == "enable":
        if supplier_code in failover_engine._rankings:
            failover_engine._rankings[supplier_code].disabled = False
    else:
        return {"error": f"Unknown action: {action}"}

    # Audit log
    db = await get_db()
    now = datetime.now(timezone.utc)
    await db.ops_audit_log.insert_one({
        "organization_id": _org_id(request),
        "action": f"supplier_override_{action}",
        "supplier_code": supplier_code,
        "reason": body.reason,
        "actor": _user_id(request),
        "created_at": now,
    })

    return {
        "supplier_code": supplier_code,
        "action": action,
        "reason": body.reason,
        "applied": True,
    }


@router.post("/admin/supplier/{supplier_code}/manual-failover", summary="[P8] Trigger manual failover")
async def manual_failover(
    supplier_code: str,
    request: Request,
    user=Depends(require_roles(OPS_ROLES)),
):
    from app.suppliers.failover import failover_engine

    decision = failover_engine.get_fallback(supplier_code)

    db = await get_db()
    await failover_engine.log_failover(db, decision, _org_id(request))

    now = datetime.now(timezone.utc)
    await db.ops_audit_log.insert_one({
        "organization_id": _org_id(request),
        "action": "manual_failover",
        "supplier_code": supplier_code,
        "selected_supplier": decision.selected_supplier,
        "actor": _user_id(request),
        "created_at": now,
    })

    return {
        "primary_supplier": decision.primary_supplier,
        "selected_supplier": decision.selected_supplier,
        "fallback_chain": decision.fallback_chain,
        "reason": decision.reason,
    }


class PriceOverrideBody(BaseModel):
    booking_id: str
    override_price: float
    currency: str = "TRY"
    reason: str


@router.post("/admin/price-override", summary="[P8] Override booking price")
async def price_override(
    body: PriceOverrideBody,
    request: Request,
    user=Depends(require_roles(OPS_ROLES)),
):
    db = await get_db()
    org_id = _org_id(request)
    now = datetime.now(timezone.utc)

    booking = await db.bookings.find_one(
        {"_id": body.booking_id, "organization_id": org_id}
    )
    if not booking:
        return {"error": "booking_not_found"}

    old_price = booking.get("total_price")

    await db.bookings.update_one(
        {"_id": body.booking_id},
        {
            "$set": {
                "total_price": body.override_price,
                "price_currency": body.currency,
                "price_overridden": True,
                "price_override_reason": body.reason,
                "price_override_by": _user_id(request),
                "price_override_at": now,
                "updated_at": now,
            }
        },
    )

    await db.ops_audit_log.insert_one({
        "organization_id": org_id,
        "action": "price_override",
        "booking_id": body.booking_id,
        "old_price": old_price,
        "new_price": body.override_price,
        "reason": body.reason,
        "actor": _user_id(request),
        "created_at": now,
    })

    return {
        "booking_id": body.booking_id,
        "old_price": old_price,
        "new_price": body.override_price,
        "overridden": True,
    }


@router.get("/admin/audit-log", summary="[P8] OPS audit log")
async def ops_audit_log(
    request: Request,
    limit: int = Query(50, le=200),
    user=Depends(require_roles(OPS_ROLES)),
):
    db = await get_db()
    cursor = db.ops_audit_log.find(
        {"organization_id": _org_id(request)},
        {"_id": 0},
    ).sort("created_at", -1).limit(limit)
    logs = await cursor.to_list(length=limit)
    return {"logs": logs, "total": len(logs)}


# ============================================================================
# PART 9 — OPERATIONS METRICS (Prometheus)
# ============================================================================

@router.get("/metrics", summary="[P9] Operations metrics (JSON)")
async def operations_metrics_json(
    request: Request,
    user=Depends(require_roles(OPS_ROLES)),
):
    from app.suppliers.operations.prometheus import collect_operations_metrics
    db = await get_db()
    return await collect_operations_metrics(db, _org_id(request))


@router.get("/metrics/prometheus", summary="[P9] Prometheus exposition format")
async def operations_metrics_prometheus(
    request: Request,
    user=Depends(require_roles(OPS_ROLES)),
):
    from app.suppliers.operations.prometheus import collect_operations_metrics, format_prometheus
    db = await get_db()
    org_id = _org_id(request)
    metrics = await collect_operations_metrics(db, org_id)
    text = format_prometheus(metrics, org_id)
    return Response(content=text, media_type="text/plain; version=0.0.4")
