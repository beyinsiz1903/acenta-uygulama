from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from app.constants.usage_metrics import UsageMetric
from app.db import get_db
from app.repositories.usage_daily_repository import usage_daily_repo
from app.repositories.usage_ledger_repository import usage_ledger_repo
from app.services.entitlement_service import entitlement_service
from app.services.quota_warning_service import (
  build_metric_warning_payload,
  build_trial_conversion_payload,
)
from app.services.usage_service import _current_billing_period, _resolve_usage_organization_id

PRIMARY_USAGE_METRICS = [
  UsageMetric.RESERVATION_CREATED,
  UsageMetric.REPORT_GENERATED,
  UsageMetric.EXPORT_GENERATED,
]

PRIMARY_USAGE_LABELS = {
  UsageMetric.RESERVATION_CREATED: "Reservations",
  UsageMetric.REPORT_GENERATED: "Reports",
  UsageMetric.EXPORT_GENERATED: "Exports",
  UsageMetric.INTEGRATION_CALL: "Integrations",
  UsageMetric.B2B_MATCH_REQUEST: "B2B Requests",
}


def _metric_payload(metric: str, quota: Any, used: int) -> Dict[str, Any]:
  limit = quota
  remaining = max(0, limit - used) if limit is not None else None
  exceeded = used >= limit if limit is not None else False
  ratio = round((used / limit), 4) if limit not in (None, 0) else 0
  percent = round(ratio * 100, 2) if limit not in (None, 0) else 0
  return {
    "label": PRIMARY_USAGE_LABELS.get(metric, metric),
    "metric": metric,
    "used": used,
    "quota": quota,
    "limit": limit,
    "remaining": remaining,
    "exceeded": exceeded,
    "ratio": ratio,
    "percent": percent,
  }


def _normalize_metric_order(metric_keys: list[str]) -> list[str]:
  ordered: list[str] = []
  for metric in [*PRIMARY_USAGE_METRICS, UsageMetric.INTEGRATION_CALL, UsageMetric.B2B_MATCH_REQUEST]:
    if metric in metric_keys and metric not in ordered:
      ordered.append(metric)
  for metric in sorted(metric_keys):
    if metric not in ordered:
      ordered.append(metric)
  return ordered


async def get_usage_overview(
  tenant_id: str,
  *,
  billing_period: Optional[str] = None,
  trend_days: int = 30,
  metric_filter: Optional[list[str]] = None,
) -> Dict[str, Any]:
  entitlements = await entitlement_service.get_tenant_entitlements(tenant_id)
  plan = entitlements.get("plan")
  period = billing_period or _current_billing_period()
  organization_id = await _resolve_usage_organization_id(tenant_id, period)
  billing_status = entitlements.get("billing_status")
  if not billing_status:
    db = await get_db()
    legacy_sub = await db.subscriptions.find_one(
      {
        "$or": [
          {"tenant_id": tenant_id},
          {"org_id": organization_id} if organization_id else {"tenant_id": tenant_id},
        ]
      },
      {"_id": 0, "status": 1},
      sort=[("updated_at", -1)],
    )
    if legacy_sub:
      billing_status = legacy_sub.get("status")
  is_trial = billing_status == "trialing" or str(plan or "").lower() in {"trial", "trialing"}
  quotas = entitlements.get("usage_allowances") or {}

  totals = await usage_daily_repo.get_period_totals(tenant_id, period, organization_id=organization_id)
  totals_source = "usage_daily"
  if not totals:
    totals = await usage_ledger_repo.get_period_totals(tenant_id, period, organization_id=organization_id)
    totals_source = "usage_ledger"

  metric_keys = set(metric_filter or [])
  metric_keys.update(quotas.keys())
  metric_keys.update(totals.keys())
  if metric_filter:
    metric_keys = set(metric_filter)

  ordered_metric_keys = _normalize_metric_order(list(metric_keys))
  metrics = {}
  for metric in ordered_metric_keys:
    used = int(totals.get(metric, 0) or 0)
    quota = quotas.get(metric)
    metrics[metric] = {
      **_metric_payload(metric, quota, used),
      **build_metric_warning_payload(metric=metric, used=used, limit=quota, is_trial=is_trial),
    }

  primary_ratios = [
    float(metrics.get(metric, {}).get("ratio") or 0)
    for metric in PRIMARY_USAGE_METRICS
    if metric in metrics
  ]
  reservation_ratio = float(metrics.get(UsageMetric.RESERVATION_CREATED, {}).get("ratio") or 0)
  overall_usage_ratio = reservation_ratio if reservation_ratio > 0 else (max(primary_ratios) if primary_ratios else 0)

  today = datetime.now(timezone.utc).date()
  start_date = today - timedelta(days=max(1, trend_days) - 1)
  trend_series = await usage_daily_repo.get_zero_filled_daily_counts(
    tenant_id,
    start_date=start_date,
    end_date=today,
    metrics=ordered_metric_keys,
    organization_id=organization_id,
  )

  trend_daily = []
  for idx in range(max(1, trend_days)):
    current_date = (start_date + timedelta(days=idx)).isoformat()
    daily_row: Dict[str, Any] = {"date": current_date}
    for metric in ordered_metric_keys:
      point = trend_series.get(metric, [])[idx] if idx < len(trend_series.get(metric, [])) else {"count": 0}
      daily_row[metric] = int(point.get("count") or 0)
    trend_daily.append(daily_row)

  return {
    "tenant_id": tenant_id,
    "organization_id": organization_id,
    "plan": plan,
    "plan_label": entitlements.get("plan_label"),
    "billing_status": billing_status,
    "is_trial": is_trial,
    "billing_period": period,
    "period": period,
    "metrics": metrics,
    "primary_metrics": PRIMARY_USAGE_METRICS,
    "overall_usage_ratio": round(overall_usage_ratio, 4),
    "trial_conversion": build_trial_conversion_payload(usage_ratio=overall_usage_ratio, is_trial=is_trial),
    "trend": {
      "days": max(1, trend_days),
      "start_date": start_date.isoformat(),
      "end_date": today.isoformat(),
      "daily": trend_daily,
      "series": trend_series,
    },
    "totals_source": totals_source,
    "generated_at": datetime.now(timezone.utc).isoformat(),
  }