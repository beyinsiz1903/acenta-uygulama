from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


OpsIncidentStatus = Literal["open", "resolved"]
OpsIncidentType = Literal[
    "risk_review",
    "supplier_partial_failure",
    "supplier_all_failed",
]
OpsIncidentSeverity = Literal["low", "medium", "high", "critical"]


class SupplierHealthBadgeOut(BaseModel):
    supplier_code: str
    window_sec: int = 900

    # metrics (all optional, fail-open)
    success_rate: Optional[float] = None
    error_rate: Optional[float] = None
    avg_latency_ms: Optional[int] = None
    p95_latency_ms: Optional[int] = None
    last_error_codes: list[str] = Field(default_factory=list)

    # circuit (all optional, fail-open)
    circuit_state: Optional[Literal["closed", "open"]] = None
    circuit_until: Optional[str] = None  # ISO
    reason_code: Optional[str] = None
    consecutive_failures: Optional[int] = None

    # trace/help
    updated_at: Optional[str] = None  # ISO
    notes: list[str] = Field(default_factory=list)


class OpsIncidentSourceRef(BaseModel):
    booking_id: Optional[str] = None
    session_id: Optional[str] = None
    offer_token: Optional[str] = None
    supplier_code: Optional[str] = None
    risk_decision: Optional[str] = None


class OpsIncidentSummaryOut(BaseModel):
    incident_id: str
    type: OpsIncidentType
    severity: OpsIncidentSeverity
    status: OpsIncidentStatus
    summary: str
    created_at: datetime
    source_ref: OpsIncidentSourceRef
    supplier_health: Optional[SupplierHealthBadgeOut] = None


class OpsIncidentDetailOut(BaseModel):
    incident_id: str
    organization_id: str
    type: OpsIncidentType
    severity: OpsIncidentSeverity
    status: OpsIncidentStatus
    summary: str
    source_ref: OpsIncidentSourceRef
    meta: dict[str, Any]
    created_at: datetime
    updated_at: datetime
    resolved_at: Optional[datetime] = None
    resolved_by_user_id: Optional[str] = None


class OpsIncidentListResponse(BaseModel):
    total: int
    items: list[OpsIncidentSummaryOut]
