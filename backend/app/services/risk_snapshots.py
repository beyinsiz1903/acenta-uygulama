from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List

from app.models.risk_snapshots import RiskSnapshot, RiskSnapshotMetrics, RiskSnapshotTopOffender
from app.utils import now_utc


async def insert_risk_snapshot(
    db,
    *,
    organization_id: str,
    snapshot_key: str,
    window: Dict[str, Any],
    risk_profile: Dict[str, Any],
    metrics: RiskSnapshotMetrics,
    top_offenders: List[RiskSnapshotTopOffender],
    meta: Dict[str, Any] | None = None,
) -> RiskSnapshot:
    """Insert a new risk snapshot document.

    v1: immutable snapshots - we always insert a new document.
    """
    generated_at = now_utc()
    snap = RiskSnapshot(
        organization_id=organization_id,
        snapshot_key=snapshot_key,
        window=window,
        generated_at=generated_at,
        risk_profile=risk_profile,
        metrics=metrics,
        top_offenders=top_offenders,
        meta=meta or {"source": "snapshot_job", "version": 1},
    )

    doc = snap.model_dump()
    await db.risk_snapshots.insert_one(doc)
    return snap
