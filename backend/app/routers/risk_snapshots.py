from __future__ import annotations

from datetime import timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.auth import get_current_user, require_roles
from app.db import get_db
from app.models.risk_snapshots import RiskSnapshotMetrics, RiskSnapshotTopOffender
from app.services.risk_profile import load_risk_profile
from app.utils import now_utc

router = APIRouter(prefix="/api/admin/risk-snapshots", tags=["admin-risk-snapshots"])


@router.post("/run")
async def run_risk_snapshot(
    snapshot_key: str = Query("match_risk_daily"),
    days: int = Query(30, ge=1, le=365),
    min_total: int = Query(3, ge=1, le=1000),
    top_n: int = Query(20, ge=1, le=100),
    dry_run: bool = Query(True),
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    """Run a match-risk snapshot using the existing /admin/matches aggregation.

    v1: computes metrics in-memory; persists to risk_snapshots when dry_run=False.
    """
    from app.routers.matches import list_matches

    org_id = user.get("organization_id")

    # Reuse matches aggregation
    matches_resp = await list_matches(
        days=days,
        min_total=min_total,
        include_action=True,
        only_high_risk=False,
        sort="high_risk_first",
        include_reasons=True,
        db=db,
        user=user,
    )

    items = matches_resp.get("items", [])  # Access as dict key, not attribute
    if not isinstance(items, list):
        raise HTTPException(status_code=500, detail="MATCH_SUMMARY_UNAVAILABLE")

    total_matches = len(items)
    high_risk_matches = sum(1 for m in items if getattr(m, "high_risk", False))
    high_risk_rate = float(high_risk_matches) / float(total_matches) if total_matches > 0 else 0.0

    # Verified-aware metrics
    verified_shares: List[float] = []
    verified_only_used = 0
    for m in items:
        vs = getattr(m, "verified_share", 0.0) or 0.0
        verified_shares.append(float(vs))
        if getattr(m, "risk_inputs", None) and getattr(m, "risk_inputs").get("verified_only"):
            verified_only_used += 1

    verified_share_avg = sum(verified_shares) / float(len(verified_shares)) if verified_shares else 0.0

    from app.services.risk_snapshots import insert_risk_snapshot

    # Build metrics & top_offenders
    metrics = RiskSnapshotMetrics(
        matches_evaluated=total_matches,
        high_risk_matches=high_risk_matches,
        high_risk_rate=high_risk_rate,
        verified_share_avg=verified_share_avg,
        verified_only_used_matches=verified_only_used,
    )

    # Top offenders: high_risk matches sorted by repeat_no_show_7 desc then no_show_rate desc
    high_risk_items = [m for m in items if getattr(m, "high_risk", False)]
    high_risk_items.sort(
        key=lambda m: (
            -getattr(m, "repeat_no_show_7", 0),
            -getattr(m, "no_show_rate", 0.0),
        )
    )
    top = []
    for m in high_risk_items[:top_n]:
        risk_inputs = getattr(m, "risk_inputs", {}) or {}
        top.append(
            RiskSnapshotTopOffender(
                match_id=m.id,
                agency_name=getattr(m, "agency_name", None),
                hotel_name=getattr(m, "hotel_name", None),
                high_risk=True,
                high_risk_reasons=list(getattr(m, "high_risk_reasons", []) or []),
                no_show_rate=float(getattr(m, "no_show_rate", 0.0) or 0.0),
                repeat_no_show_7=int(getattr(m, "repeat_no_show_7", 0) or 0),
                verified_share=float(getattr(m, "verified_share", 0.0) or 0.0),
                verified_only=bool(risk_inputs.get("verified_only")),
            )
        )

    # Risk profile snapshot
    rp = await load_risk_profile(db, org_id)
    risk_profile_dict = rp.to_dict()

    window = {"days": days, "min_total": min_total}

    if not dry_run:
        await insert_risk_snapshot(
            db,
            organization_id=org_id,
            snapshot_key=snapshot_key,
            window=window,
            risk_profile=risk_profile_dict,
            metrics=metrics,
            top_offenders=top,
            meta={"source": "snapshot_job", "version": 1},
        )

    return {
        "ok": True,
        "dry_run": dry_run,
        "snapshot_key": snapshot_key,
        "generated_at": now_utc().isoformat(),
        "metrics": metrics.model_dump(),
        "top_offenders_count": len(top),
    }
