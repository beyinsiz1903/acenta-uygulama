from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.constants.plan_matrix import DEFAULT_PLAN, PLAN_MATRIX
from app.repositories.usage_ledger_repository import usage_ledger_repo
from app.services.audit_log_service import append_audit_log
from app.services.feature_service import feature_service

logger = logging.getLogger(__name__)


def _current_billing_period() -> str:
  return datetime.now(timezone.utc).strftime("%Y-%m")


async def track_usage(
  tenant_id: str,
  metric: str,
  quantity: int,
  source: str,
  source_event_id: str,
) -> None:
  """Best-effort usage tracking. Never raises."""
  try:
    plan = await feature_service.get_plan(tenant_id)
    if plan == "starter":
      return  # Starter has no metered features

    inserted = await usage_ledger_repo.append(
      tenant_id=tenant_id,
      metric=metric,
      quantity=quantity,
      source=source,
      source_event_id=source_event_id,
    )
    if not inserted:
      logger.debug("Usage duplicate skipped: %s/%s/%s", tenant_id, metric, source_event_id)
  except Exception:
    logger.warning("usage track failed", exc_info=True)


async def check_quota(tenant_id: str, metric: str) -> Dict[str, Any]:
  """Check if tenant is within quota for a metric."""
  plan = await feature_service.get_plan(tenant_id) or DEFAULT_PLAN
  quotas = PLAN_MATRIX.get(plan, {}).get("quotas", {})
  quota = quotas.get(metric)

  period = _current_billing_period()
  totals = await usage_ledger_repo.get_period_totals(tenant_id, period)
  used = totals.get(metric, 0)

  if quota is None:
    return {"metric": metric, "quota": None, "used": used, "remaining": None, "exceeded": False}

  remaining = max(0, quota - used)
  exceeded = used >= quota

  if exceeded:
    await append_audit_log(
      scope="usage",
      tenant_id=tenant_id,
      actor_user_id="system",
      actor_email="quota_check",
      action="usage.quota_exceeded",
      before=None,
      after={"metric": metric, "quota": quota, "used": used, "period": period},
    )

  return {"metric": metric, "quota": quota, "used": used, "remaining": remaining, "exceeded": exceeded}


async def get_usage_summary(tenant_id: str) -> Dict[str, Any]:
  """Get full usage summary for a tenant (current period)."""
  plan = await feature_service.get_plan(tenant_id) or DEFAULT_PLAN
  quotas = PLAN_MATRIX.get(plan, {}).get("quotas", {})
  period = _current_billing_period()
  totals = await usage_ledger_repo.get_period_totals(tenant_id, period)

  metrics = {}
  all_metric_keys = set(list(quotas.keys()) + list(totals.keys()))
  for m in sorted(all_metric_keys):
    quota = quotas.get(m)
    used = totals.get(m, 0)
    metrics[m] = {
      "quota": quota,
      "used": used,
      "remaining": max(0, quota - used) if quota is not None else None,
      "exceeded": used >= quota if quota is not None else False,
    }

  return {
    "tenant_id": tenant_id,
    "plan": plan,
    "billing_period": period,
    "metrics": metrics,
  }


class UsageService:
  """Legacy compat class used by limits_service and dev_saas."""

  def __init__(self, db) -> None:
    self._db = db

  async def log(self, metric: str, org_id: str, tenant_id: Optional[str] = None, value: int = 1) -> None:
    """Log usage for org-level metrics (legacy compat)."""
    now = datetime.now(timezone.utc)
    await self._db.usage_log.update_one(
      {"org_id": org_id, "metric": metric, "period": now.strftime("%Y-%m")},
      {"$inc": {"value": value}, "$set": {"updated_at": now}, "$setOnInsert": {"created_at": now}},
      upsert=True,
    )

  async def get_current_value(self, metric: str, org_id: str) -> int:
    now = datetime.now(timezone.utc)
    doc = await self._db.usage_log.find_one(
      {"org_id": org_id, "metric": metric, "period": now.strftime("%Y-%m")},
    )
    return int(doc.get("value", 0)) if doc else 0
