from __future__ import annotations

from datetime import timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from pydantic import BaseModel

from app.auth import get_current_user, require_roles
from app.db import get_db
from app.models.risk_snapshots import RiskSnapshotMetrics, RiskSnapshotTopOffender
from app.services.risk_profile import load_risk_profile
from app.utils import now_utc

router = APIRouter(prefix="/api/admin/risk-snapshots", tags=["admin-risk-snapshots"])


@router.get("")
async def list_risk_snapshots(
    snapshot_key: str = Query("match_risk_daily"),
    limit: int = Query(10, ge=1, le=100),
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    """List risk snapshots for a given snapshot_key."""
    org_id = user.get("organization_id")
    
    # Find snapshots for this organization and snapshot_key
    cursor = db.risk_snapshots.find({
        "organization_id": org_id,
        "snapshot_key": snapshot_key
    }).sort("generated_at", -1).limit(limit)
    
    documents = await cursor.to_list(length=limit)
    
    # Convert ObjectId to string and format for JSON response
    items = []
    for doc in documents:
        if "_id" in doc:
            doc["_id"] = str(doc["_id"])
        items.append(doc)
    
    return {
        "items": items,
        "count": len(items)
    }


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


class TrendPoint(BaseModel):
    generated_at: str
    high_risk_rate: float
    verified_share_avg: float
    matches_evaluated: int
    high_risk_matches: int


class TrendDeltaMetric(BaseModel):
    start: float
    end: float
    abs_change: float
    pct_change: float
    direction: str  # up|down|flat


class TrendDelta(BaseModel):
    high_risk_rate: TrendDeltaMetric
    verified_share_avg: TrendDeltaMetric


@router.get("/trend")
async def get_risk_trend(
    snapshot_key: str = Query("match_risk_daily"),
    limit: int = Query(30, ge=1, le=365),
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    """Return time-series trend + delta summary for risk snapshots.

    - points: oldest                                                                             newest
    - delta: first vs last point for selected metrics.
    """
    org_id = user.get("organization_id")

    # Fetch last N snapshots (newest first)
    cursor = (
        db.risk_snapshots.find({"organization_id": org_id, "snapshot_key": snapshot_key})
        .sort("generated_at", -1)
        .limit(limit)
    )
    docs = await cursor.to_list(length=limit)

    if not docs:
        return {"points": [], "delta": None}

    # Oldest                                                                     newest
    docs_chrono = list(reversed(docs))

    points: list[TrendPoint] = []
    for d in docs_chrono:
        metrics = d.get("metrics") or {}
        points.append(
            TrendPoint(
                generated_at=d.get("generated_at").isoformat() if d.get("generated_at") else "",
                high_risk_rate=float(metrics.get("high_risk_rate", 0.0) or 0.0),
                verified_share_avg=float(metrics.get("verified_share_avg", 0.0) or 0.0),
                matches_evaluated=int(metrics.get("matches_evaluated", 0) or 0),
                high_risk_matches=int(metrics.get("high_risk_matches", 0) or 0),
            )
        )

    if len(points) < 2:
        return {"points": [p.model_dump() for p in points], "delta": None}

    first = points[0]
    last = points[-1]

    def _build_delta_metric(start: float, end: float) -> TrendDeltaMetric:
        abs_change = end - start
        pct_change = 0.0
        if start != 0:
            pct_change = (abs_change / start) * 100.0
        direction = "flat"
        if abs_change > 0:
            direction = "up"
        elif abs_change < 0:
            direction = "down"
        return TrendDeltaMetric(
            start=start,
            end=end,
            abs_change=abs_change,
            pct_change=pct_change,
            direction=direction,
        )

    delta = TrendDelta(
        high_risk_rate=_build_delta_metric(first.high_risk_rate, last.high_risk_rate),
        verified_share_avg=_build_delta_metric(first.verified_share_avg, last.verified_share_avg),
    )

    return {
        "points": [p.model_dump() for p in points],
        "delta": delta.model_dump(),
    }
