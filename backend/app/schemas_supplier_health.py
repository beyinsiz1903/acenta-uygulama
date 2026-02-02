from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel


class SupplierMetricsOut(BaseModel):
    total_calls: int
    success_calls: int
    fail_calls: int
    success_rate: float
    error_rate: float
    avg_latency_ms: int
    p95_latency_ms: int
    last_error_codes: list[str]


CircuitState = Literal["closed", "open"]


class SupplierCircuitOut(BaseModel):
    state: CircuitState
    opened_at: Optional[datetime] = None
    until: Optional[datetime] = None
    reason_code: Optional[str] = None
    consecutive_failures: int
    last_transition_at: Optional[datetime] = None


class SupplierHealthItemOut(BaseModel):
    supplier_code: str
    metrics: SupplierMetricsOut
    circuit: SupplierCircuitOut


class SupplierHealthListResponse(BaseModel):
    window_sec: int
    updated_at: Optional[datetime]
    items: list[SupplierHealthItemOut]
