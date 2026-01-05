from __future__ import annotations

from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel


class RiskSnapshotMetrics(BaseModel):
    matches_evaluated: int
    high_risk_matches: int
    high_risk_rate: float
    verified_share_avg: float
    verified_only_used_matches: int


class RiskSnapshotTopOffender(BaseModel):
    match_id: str
    agency_name: Optional[str] = None
    hotel_name: Optional[str] = None
    high_risk: bool
    high_risk_reasons: list[str]
    no_show_rate: float
    repeat_no_show_7: int
    verified_share: float
    verified_only: bool


class RiskSnapshot(BaseModel):
    organization_id: str
    snapshot_key: str
    window: dict[str, Any]
    generated_at: datetime
    risk_profile: dict[str, Any]
    metrics: RiskSnapshotMetrics
    top_offenders: List[RiskSnapshotTopOffender]
    meta: dict[str, Any]
