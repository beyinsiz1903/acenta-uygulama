from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query

from app.auth import require_roles
from app.constants.plan_matrix import PLAN_MATRIX
from app.db import get_db
from app.repositories.billing_repository import billing_repo

router = APIRouter(prefix="/api/admin/analytics", tags=["admin_analytics"])

AdminDep = Depends(require_roles(["super_admin", "admin"]))


def _current_period() -> str:
  return datetime.now(timezone.utc).strftime("%Y-%m")


async def _get_plan_catalog_map() -> Dict[str, float]:
  """Map plan -> monthly amount from billing_plan_catalog."""
  items = await billing_repo.get_plan_catalog()
  result = {}
  for item in items:
    plan = item.get("plan", "")
    interval = item.get("interval", "monthly")
    amount = float(item.get("amount", 0))
    monthly = amount if interval == "monthly" else amount / 12
    if plan not in result or interval == "monthly":
      result[plan] = monthly
  return result


@router.get("/revenue-summary", dependencies=[AdminDep])
async def revenue_summary(
  period: Optional[str] = Query(None),
  lookback: int = Query(1, ge=1, le=12),
) -> dict:
  """Revenue summary: MRR, plan distribution, risk metrics."""
  db = await get_db()
  current = period or _current_period()

  # Active subscriptions aggregate
  pipeline = [
    {"$match": {"status": {"$in": ["active", "trialing", "past_due"]}}},
    {"$group": {
      "_id": "$plan",
      "count": {"$sum": 1},
      "past_due": {"$sum": {"$cond": [{"$eq": ["$status", "past_due"]}, 1, 0]}},
      "canceling": {"$sum": {"$cond": [{"$eq": ["$cancel_at_period_end", True]}, 1, 0]}},
    }},
  ]
  results = await db.billing_subscriptions.aggregate(pipeline).to_list(20)

  plan_distribution = {}
  total_active = 0
  total_past_due = 0
  total_canceling = 0

  for r in results:
    plan = r["_id"] or "unknown"
    plan_distribution[plan] = r["count"]
    total_active += r["count"]
    total_past_due += r["past_due"]
    total_canceling += r["canceling"]

  # Grace period count
  now = datetime.now(timezone.utc)
  grace_count = await db.billing_subscriptions.count_documents({
    "status": "past_due",
    "grace_period_until": {"$gt": now.isoformat()},
  })

  # MRR calculation
  price_map = await _get_plan_catalog_map()
  mrr_gross = 0.0
  mrr_at_risk = 0.0

  for plan, count in plan_distribution.items():
    monthly_price = price_map.get(plan, 0)
    mrr_gross += monthly_price * count

  # At risk = past_due subscriptions
  for r in results:
    plan = r["_id"] or "unknown"
    monthly_price = price_map.get(plan, 0)
    mrr_at_risk += monthly_price * r["past_due"]

  # Trend (lookback periods)
  trend = []
  if lookback > 1:
    from datetime import timedelta
    for i in range(lookback):
      d = now.replace(day=1) - timedelta(days=30 * i)
      p = d.strftime("%Y-%m")
      trend.append({"period": p, "mrr_gross_active": mrr_gross, "past_due_count": total_past_due})

  return {
    "period": current,
    "generated_at": now.isoformat(),
    "active_subscriptions_count": total_active,
    "plan_distribution": plan_distribution,
    "mrr_gross_active": round(mrr_gross, 2),
    "mrr_at_risk": round(mrr_at_risk, 2),
    "past_due_count": total_past_due,
    "grace_count": grace_count,
    "canceling_count": total_canceling,
    "trend": trend if lookback > 1 else [],
  }


@router.get("/usage-overview", dependencies=[AdminDep])
async def usage_overview(
  period: Optional[str] = Query(None),
) -> dict:
  """Usage overview: quota buckets, enterprise candidates."""
  db = await get_db()
  current = period or _current_period()
  now = datetime.now(timezone.utc)

  metric = "b2b.match_request"

  # Get all tenants with capabilities (pro/enterprise)
  caps = await db.tenant_capabilities.find(
    {"plan": {"$in": ["pro", "enterprise"]}},
    {"_id": 0, "tenant_id": 1, "plan": 1},
  ).to_list(5000)

  # Get usage totals for current period
  usage_pipeline = [
    {"$match": {"billing_period": current, "metric": metric}},
    {"$group": {"_id": "$tenant_id", "total": {"$sum": "$quantity"}}},
  ]
  usage_results = await db.usage_ledger.aggregate(usage_pipeline).to_list(5000)
  usage_map = {r["_id"]: r["total"] for r in usage_results}

  # Build buckets
  buckets = {"0-20%": 0, "20-50%": 0, "50-80%": 0, "80-100%": 0, "100%+": 0}
  exceeded_count = 0
  over_80_count = 0
  candidates = []

  for cap in caps:
    tid = cap["tenant_id"]
    plan = cap["plan"]
    quota = PLAN_MATRIX.get(plan, {}).get("quotas", {}).get(metric)
    if not quota:
      continue

    used = usage_map.get(tid, 0)
    ratio = used / quota if quota > 0 else 0

    # Bucket
    if ratio >= 1.0:
      buckets["100%+"] += 1
      exceeded_count += 1
    elif ratio >= 0.8:
      buckets["80-100%"] += 1
      over_80_count += 1
    elif ratio >= 0.5:
      buckets["50-80%"] += 1
    elif ratio >= 0.2:
      buckets["20-50%"] += 1
    else:
      buckets["0-20%"] += 1

    # Enterprise candidate heuristic: pro + ratio >= 0.8
    if plan == "pro" and ratio >= 0.8:
      candidates.append({
        "tenant_id": tid,
        "usage_ratio": round(ratio, 2),
        "used": used,
        "quota": quota,
      })

  # Sort candidates by ratio desc, take top 10
  candidates.sort(key=lambda x: x["usage_ratio"], reverse=True)
  top_candidates = candidates[:10]

  return {
    "period": current,
    "generated_at": now.isoformat(),
    "metric": metric,
    "quota_buckets": [{"bucket": k, "tenant_count": v} for k, v in buckets.items()],
    "exceeded_count": exceeded_count,
    "over_80_count": over_80_count,
    "enterprise_candidates_count": len(candidates),
    "top_candidates": top_candidates,
  }
