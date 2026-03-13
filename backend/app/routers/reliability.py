"""Integration Reliability Layer — API Router.

Namespace: /api/reliability/*

Covers all 10 parts:
  P1 — Supplier API Resilience
  P2 — Supplier Sandbox
  P3 — Retry Strategy & DLQ
  P4 — Identity & Idempotency
  P5 — API Versioning
  P6 — Contract Validation
  P7 — Integration Metrics
  P8 — Supplier Incident Response
  P9 — Integration Dashboard
  P10 — Reliability Roadmap
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from app.auth import require_roles
from app.db import get_db

logger = logging.getLogger("routers.reliability")

router = APIRouter(prefix="/api/reliability", tags=["integration_reliability"])

REL_ADMIN_ROLES = ["super_admin"]
REL_OPS_ROLES = ["super_admin", "ops_admin"]
REL_VIEW_ROLES = ["super_admin", "ops_admin", "finance_admin", "agency_admin"]


def _org_id(request: Request) -> str:
    user = getattr(request.state, "user", {}) or {}
    return user.get("organization_id", "")


def _user_email(request: Request) -> str:
    user = getattr(request.state, "user", {}) or {}
    return user.get("email", "system")


# ============================================================================
# PART 1 — SUPPLIER API RESILIENCE
# ============================================================================

class ResilienceConfigUpdate(BaseModel):
    supplier_code: str
    timeout_ms: Optional[int] = None
    max_retries: Optional[int] = None
    rate_limit_rps: Optional[int] = None


@router.get("/resilience/config", summary="[P1] Get resilience configuration")
async def get_resilience_config(request: Request, user=Depends(require_roles(REL_VIEW_ROLES))):
    from app.domain.reliability.resilience_service import get_resilience_config as _get
    db = await get_db()
    return await _get(db, _org_id(request))


@router.put("/resilience/config", summary="[P1] Update supplier resilience config")
async def update_resilience_config(
    body: ResilienceConfigUpdate, request: Request, user=Depends(require_roles(REL_OPS_ROLES))
):
    from app.domain.reliability.resilience_service import update_supplier_resilience
    db = await get_db()
    config = body.model_dump(exclude_none=True)
    sc = config.pop("supplier_code")
    return await update_supplier_resilience(db, _org_id(request), sc, config, _user_email(request))


@router.get("/resilience/stats", summary="[P1] Get resilience stats")
async def get_resilience_stats(
    request: Request,
    supplier_code: Optional[str] = Query(None),
    window_minutes: int = Query(15),
    user=Depends(require_roles(REL_VIEW_ROLES)),
):
    from app.domain.reliability.resilience_service import get_resilience_stats as _get
    db = await get_db()
    return await _get(db, _org_id(request), supplier_code, window_minutes)


# ============================================================================
# PART 2 — SUPPLIER SANDBOX
# ============================================================================

class SandboxConfigUpdate(BaseModel):
    enabled: bool = False
    mode: str = "mock"
    fault_injection_enabled: bool = False
    fault_probability: float = 0.0
    fault_types: list[str] = Field(default_factory=list)


class SandboxCallBody(BaseModel):
    supplier_code: str
    method: str = "search"
    payload: dict = Field(default_factory=dict)


@router.get("/sandbox/config", summary="[P2] Get sandbox configuration")
async def get_sandbox_config(request: Request, user=Depends(require_roles(REL_OPS_ROLES))):
    from app.domain.reliability.sandbox_service import get_sandbox_config as _get
    db = await get_db()
    return await _get(db, _org_id(request))


@router.put("/sandbox/config", summary="[P2] Update sandbox configuration")
async def update_sandbox_config(
    body: SandboxConfigUpdate, request: Request, user=Depends(require_roles(REL_ADMIN_ROLES))
):
    from app.domain.reliability.sandbox_service import update_sandbox_config as _update
    db = await get_db()
    config = {
        "enabled": body.enabled,
        "mode": body.mode,
        "fault_injection": {
            "enabled": body.fault_injection_enabled,
            "probability": body.fault_probability,
            "fault_types": body.fault_types,
        },
    }
    return await _update(db, _org_id(request), config, _user_email(request))


@router.post("/sandbox/call", summary="[P2] Execute sandbox adapter call")
async def execute_sandbox_call(
    body: SandboxCallBody, request: Request, user=Depends(require_roles(REL_OPS_ROLES))
):
    from app.domain.reliability.sandbox_service import execute_sandbox_call as _exec
    db = await get_db()
    return await _exec(db, _org_id(request), body.supplier_code, body.method, body.payload)


@router.get("/sandbox/log", summary="[P2] Get sandbox call history")
async def get_sandbox_log(
    request: Request,
    supplier_code: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    user=Depends(require_roles(REL_OPS_ROLES)),
):
    from app.domain.reliability.sandbox_service import get_sandbox_log as _get
    db = await get_db()
    return await _get(db, _org_id(request), supplier_code, limit)


# ============================================================================
# PART 3 — RETRY STRATEGY & DLQ
# ============================================================================

class DLQEnqueueBody(BaseModel):
    category: str
    operation: str
    supplier_code: str = ""
    payload: dict = Field(default_factory=dict)
    error: str = ""
    attempts: int = 0


@router.get("/retry/config", summary="[P3] Get retry configuration")
async def get_retry_config(request: Request, user=Depends(require_roles(REL_VIEW_ROLES))):
    from app.domain.reliability.retry_service import get_retry_config as _get
    db = await get_db()
    return await _get(db, _org_id(request))


@router.get("/dlq", summary="[P3] List dead-letter queue entries")
async def list_dlq(
    request: Request,
    category: Optional[str] = Query(None),
    status: str = Query("pending"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, le=200),
    user=Depends(require_roles(REL_OPS_ROLES)),
):
    from app.domain.reliability.retry_service import list_dlq as _list
    db = await get_db()
    return await _list(db, _org_id(request), category, status, skip, limit)


@router.post("/dlq", summary="[P3] Enqueue to dead-letter queue")
async def enqueue_dlq(body: DLQEnqueueBody, request: Request, user=Depends(require_roles(REL_OPS_ROLES))):
    from app.domain.reliability.retry_service import enqueue_dlq as _enqueue
    db = await get_db()
    return await _enqueue(
        db, _org_id(request), body.category, body.operation,
        body.payload, body.error, body.attempts, body.supplier_code,
    )


@router.post("/dlq/{entry_id}/retry", summary="[P3] Retry a DLQ entry")
async def retry_dlq_entry(entry_id: str, request: Request, user=Depends(require_roles(REL_OPS_ROLES))):
    from app.domain.reliability.retry_service import retry_dlq_entry as _retry
    db = await get_db()
    return await _retry(db, _org_id(request), entry_id)


@router.delete("/dlq/{entry_id}", summary="[P3] Discard a DLQ entry")
async def discard_dlq_entry(
    entry_id: str,
    request: Request,
    reason: str = Query(""),
    user=Depends(require_roles(REL_OPS_ROLES)),
):
    from app.domain.reliability.retry_service import discard_dlq_entry as _discard
    db = await get_db()
    return await _discard(db, _org_id(request), entry_id, reason)


@router.get("/dlq/stats", summary="[P3] DLQ statistics")
async def get_dlq_stats(request: Request, user=Depends(require_roles(REL_VIEW_ROLES))):
    from app.domain.reliability.retry_service import get_dlq_stats as _stats
    db = await get_db()
    return await _stats(db, _org_id(request))


# ============================================================================
# PART 4 — IDENTITY & IDEMPOTENCY
# ============================================================================

class IdempotencyCheckBody(BaseModel):
    idempotency_key: str
    operation: str


@router.post("/idempotency/check", summary="[P4] Check idempotency key")
async def check_idempotency(body: IdempotencyCheckBody, request: Request, user=Depends(require_roles(REL_VIEW_ROLES))):
    from app.domain.reliability.idempotency_service import check_idempotency as _check
    db = await get_db()
    result = await _check(db, _org_id(request), body.idempotency_key, body.operation)
    if result is not None:
        return {"duplicate": True, "cached_result": result}
    return {"duplicate": False, "cached_result": None}


@router.get("/idempotency/stats", summary="[P4] Idempotency statistics")
async def get_idempotency_stats(request: Request, user=Depends(require_roles(REL_VIEW_ROLES))):
    from app.domain.reliability.idempotency_service import get_idempotency_stats as _stats
    db = await get_db()
    return await _stats(db, _org_id(request))


# ============================================================================
# PART 5 — API VERSIONING
# ============================================================================

class RegisterVersionBody(BaseModel):
    supplier_code: str
    version: str
    schema_hash: str = ""


class DeprecateVersionBody(BaseModel):
    supplier_code: str
    version: str


@router.get("/versions", summary="[P5] Get version registry")
async def get_version_registry(request: Request, user=Depends(require_roles(REL_VIEW_ROLES))):
    from app.domain.reliability.versioning_service import get_version_registry as _get
    db = await get_db()
    return await _get(db, _org_id(request))


@router.post("/versions", summary="[P5] Register new API version")
async def register_api_version(
    body: RegisterVersionBody, request: Request, user=Depends(require_roles(REL_ADMIN_ROLES))
):
    from app.domain.reliability.versioning_service import register_api_version as _reg
    db = await get_db()
    return await _reg(db, _org_id(request), body.supplier_code, body.version, body.schema_hash, _user_email(request))


@router.post("/versions/deprecate", summary="[P5] Deprecate an API version")
async def deprecate_api_version(
    body: DeprecateVersionBody, request: Request, user=Depends(require_roles(REL_ADMIN_ROLES))
):
    from app.domain.reliability.versioning_service import deprecate_api_version as _dep
    db = await get_db()
    return await _dep(db, _org_id(request), body.supplier_code, body.version, _user_email(request))


@router.get("/versions/history", summary="[P5] Get version change history")
async def get_version_history(
    request: Request,
    supplier_code: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    user=Depends(require_roles(REL_VIEW_ROLES)),
):
    from app.domain.reliability.versioning_service import get_version_history as _hist
    db = await get_db()
    return await _hist(db, _org_id(request), supplier_code, limit)


# ============================================================================
# PART 6 — CONTRACT VALIDATION
# ============================================================================

class ContractValidateBody(BaseModel):
    supplier_code: str
    method: str
    payload: dict = Field(default_factory=dict)
    mode: str = "strict"


@router.post("/contracts/validate", summary="[P6] Validate a supplier response")
async def validate_contract(
    body: ContractValidateBody, request: Request, user=Depends(require_roles(REL_OPS_ROLES))
):
    from app.domain.reliability.contract_service import validate_and_log
    db = await get_db()
    return await validate_and_log(
        db, _org_id(request), body.supplier_code, body.method, body.payload, body.mode,
    )


@router.get("/contracts/status", summary="[P6] Get contract validation status")
async def get_contract_status(request: Request, user=Depends(require_roles(REL_VIEW_ROLES))):
    from app.domain.reliability.contract_service import get_contract_status as _get
    db = await get_db()
    return await _get(db, _org_id(request))


# ============================================================================
# PART 7 — INTEGRATION METRICS
# ============================================================================

@router.get("/metrics/suppliers", summary="[P7] Get aggregated supplier metrics")
async def get_supplier_metrics(
    request: Request,
    supplier_code: Optional[str] = Query(None),
    window: str = Query("15m"),
    user=Depends(require_roles(REL_VIEW_ROLES)),
):
    from app.domain.reliability.metrics_service import get_supplier_metrics as _get
    db = await get_db()
    return await _get(db, _org_id(request), supplier_code, window)


@router.get("/metrics/latency/{supplier_code}", summary="[P7] Get latency percentiles")
async def get_latency_percentiles(
    supplier_code: str,
    request: Request,
    window: str = Query("15m"),
    user=Depends(require_roles(REL_VIEW_ROLES)),
):
    from app.domain.reliability.metrics_service import get_latency_percentiles as _get
    db = await get_db()
    return await _get(db, _org_id(request), supplier_code, window)


@router.get("/metrics/error-rate", summary="[P7] Get error rate timeline")
async def get_error_rate_timeline(
    request: Request,
    supplier_code: Optional[str] = Query(None),
    window: str = Query("1h"),
    user=Depends(require_roles(REL_VIEW_ROLES)),
):
    from app.domain.reliability.metrics_service import get_error_rate_timeline as _get
    db = await get_db()
    return await _get(db, _org_id(request), supplier_code, window)


@router.get("/metrics/success-rate", summary="[P7] Get success rate summary")
async def get_success_rate_summary(
    request: Request,
    window: str = Query("1h"),
    user=Depends(require_roles(REL_VIEW_ROLES)),
):
    from app.domain.reliability.metrics_service import get_success_rate_summary as _get
    db = await get_db()
    return await _get(db, _org_id(request), window)


# ============================================================================
# PART 8 — SUPPLIER INCIDENT RESPONSE
# ============================================================================

class IncidentCreateBody(BaseModel):
    supplier_code: str
    incident_type: str
    severity: str = "medium"
    details: dict = Field(default_factory=dict)


class IncidentResolveBody(BaseModel):
    resolution: str


@router.post("/incidents", summary="[P8] Create reliability incident")
async def create_incident(
    body: IncidentCreateBody, request: Request, user=Depends(require_roles(REL_OPS_ROLES))
):
    from app.domain.reliability.incident_service import create_incident as _create
    db = await get_db()
    return await _create(
        db, _org_id(request), body.supplier_code, body.incident_type,
        body.severity, body.details,
    )


@router.get("/incidents", summary="[P8] List reliability incidents")
async def list_incidents(
    request: Request,
    status: Optional[str] = Query(None),
    supplier_code: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, le=200),
    user=Depends(require_roles(REL_VIEW_ROLES)),
):
    from app.domain.reliability.incident_service import list_incidents as _list
    db = await get_db()
    return await _list(db, _org_id(request), status, supplier_code, severity, skip, limit)


@router.post("/incidents/{incident_id}/acknowledge", summary="[P8] Acknowledge incident")
async def acknowledge_incident(
    incident_id: str, request: Request, user=Depends(require_roles(REL_OPS_ROLES))
):
    from app.domain.reliability.incident_service import acknowledge_incident as _ack
    db = await get_db()
    return await _ack(db, _org_id(request), incident_id, _user_email(request))


@router.post("/incidents/{incident_id}/resolve", summary="[P8] Resolve incident")
async def resolve_incident(
    incident_id: str, body: IncidentResolveBody, request: Request, user=Depends(require_roles(REL_OPS_ROLES))
):
    from app.domain.reliability.incident_service import resolve_incident as _resolve
    db = await get_db()
    return await _resolve(db, _org_id(request), incident_id, body.resolution, _user_email(request))


@router.post("/incidents/detect", summary="[P8] Auto-detect supplier issues")
async def detect_supplier_issues(
    request: Request,
    window_minutes: int = Query(15),
    user=Depends(require_roles(REL_OPS_ROLES)),
):
    from app.domain.reliability.incident_service import detect_supplier_issues as _detect
    db = await get_db()
    return await _detect(db, _org_id(request), window_minutes)


@router.get("/incidents/stats", summary="[P8] Incident statistics")
async def get_incident_stats(request: Request, user=Depends(require_roles(REL_VIEW_ROLES))):
    from app.domain.reliability.incident_service import get_incident_stats as _stats
    db = await get_db()
    return await _stats(db, _org_id(request))


# ============================================================================
# PART 9 — INTEGRATION DASHBOARD
# ============================================================================

@router.get("/dashboard", summary="[P9] Integration reliability dashboard")
async def get_dashboard(request: Request, user=Depends(require_roles(REL_VIEW_ROLES))):
    from app.domain.reliability.dashboard_service import get_dashboard_overview
    db = await get_db()
    return await get_dashboard_overview(db, _org_id(request))


@router.get("/dashboard/supplier/{supplier_code}", summary="[P9] Supplier detail view")
async def get_supplier_detail(
    supplier_code: str, request: Request, user=Depends(require_roles(REL_VIEW_ROLES))
):
    from app.domain.reliability.dashboard_service import get_supplier_detail as _detail
    db = await get_db()
    return await _detail(db, _org_id(request), supplier_code)


# ============================================================================
# PART 10 — RELIABILITY ROADMAP
# ============================================================================

@router.get("/roadmap", summary="[P10] Reliability roadmap & maturity score")
async def get_roadmap(request: Request, user=Depends(require_roles(REL_VIEW_ROLES))):
    from app.domain.reliability.roadmap_service import get_reliability_roadmap
    db = await get_db()
    return await get_reliability_roadmap(db, _org_id(request))


@router.get("/maturity", summary="[P10] Platform reliability maturity score")
async def get_maturity(request: Request, user=Depends(require_roles(REL_VIEW_ROLES))):
    from app.domain.reliability.roadmap_service import compute_maturity_score
    db = await get_db()
    return await compute_maturity_score(db, _org_id(request))
