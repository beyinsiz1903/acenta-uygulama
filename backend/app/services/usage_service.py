from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from app.constants.usage_metrics import UsageMetric, VALID_USAGE_METRICS
from app.constants.plan_matrix import DEFAULT_PLAN
from app.errors import AppError
from app.repositories.usage_daily_repository import usage_daily_repo
from app.repositories.usage_ledger_repository import usage_ledger_repo
from app.services.audit_log_service import append_audit_log
from app.services.entitlement_service import entitlement_service

logger = logging.getLogger(__name__)


def _current_billing_period() -> str:
  return datetime.now(timezone.utc).strftime("%Y-%m")


async def _resolve_organization_id_for_tenant(tenant_id: str) -> Optional[str]:
  from app.db import get_db

  db = await get_db()
  tenant = await db.tenants.find_one({"_id": tenant_id}, {"_id": 1, "organization_id": 1})
  if tenant and tenant.get("organization_id") is not None:
    return str(tenant.get("organization_id"))
  tenant = await db.tenants.find_one({"slug": tenant_id}, {"_id": 1, "organization_id": 1})
  if tenant and tenant.get("organization_id") is not None:
    return str(tenant.get("organization_id"))
  return None


async def _resolve_usage_organization_id(tenant_id: str, billing_period: Optional[str] = None) -> Optional[str]:
  organization_id = await _resolve_organization_id_for_tenant(tenant_id)
  if organization_id:
    return organization_id

  from app.db import get_db

  db = await get_db()
  period = billing_period or _current_billing_period()
  daily_doc = await db.usage_daily.find_one(
    {"tenant_id": tenant_id, "organization_id": {"$exists": True, "$ne": None}},
    {"_id": 0, "organization_id": 1},
    sort=[("date", -1)],
  )
  if daily_doc and daily_doc.get("organization_id") is not None:
    return str(daily_doc.get("organization_id"))

  ledger_doc = await db.usage_ledger.find_one(
    {
      "tenant_id": tenant_id,
      "billing_period": period,
      "organization_id": {"$exists": True, "$ne": None},
    },
    {"_id": 0, "organization_id": 1},
    sort=[("timestamp", -1)],
  )
  if ledger_doc and ledger_doc.get("organization_id") is not None:
    return str(ledger_doc.get("organization_id"))
  return None


async def _resolve_usage_tenant_id(
  organization_id: Optional[str],
  tenant_id: Optional[str] = None,
) -> Optional[str]:
  if tenant_id:
    return str(tenant_id)
  if not organization_id:
    return None

  from app.db import get_db

  db = await get_db()
  tenant = await db.tenants.find_one(
    {"organization_id": str(organization_id)},
    {"_id": 1},
    sort=[("created_at", 1)],
  )
  if tenant and tenant.get("_id") is not None:
    return str(tenant.get("_id"))
  return None


def _validate_usage_metric(metric: str) -> None:
  if metric not in VALID_USAGE_METRICS:
    raise AppError(422, "invalid_usage_metric", "Geçersiz usage metriği.", {"metric": metric})


async def track_usage_event(
  tenant_id: str,
  organization_id: Optional[str],
  metric: str,
  quantity: int = 1,
  source: Optional[str] = None,
  source_event_id: Optional[str] = None,
  metadata: Optional[Dict[str, Any]] = None,
) -> bool:
  """Canonical metering write path.

  Returns True if inserted, False if duplicate.
  """
  _validate_usage_metric(metric)
  if quantity <= 0:
    raise AppError(422, "invalid_usage_quantity", "Usage quantity sıfırdan büyük olmalı.", {"quantity": quantity})

  event_at = datetime.now(timezone.utc)
  billing_period = event_at.strftime("%Y-%m")
  event_source = source or "system"
  dedupe_key = source_event_id or f"adhoc:{metric}:{uuid.uuid4()}"

  inserted_id = await usage_ledger_repo.insert_event(
    tenant_id=tenant_id,
    organization_id=organization_id,
    metric=metric,
    quantity=quantity,
    source=event_source,
    source_event_id=dedupe_key,
    billing_period=billing_period,
    timestamp=event_at,
    metadata=metadata,
  )
  if inserted_id is None:
    logger.debug("Usage duplicate skipped: %s/%s/%s", tenant_id, metric, dedupe_key)
    return False

  try:
    await usage_daily_repo.increment(
      tenant_id=tenant_id,
      organization_id=organization_id,
      metric=metric,
      quantity=quantity,
      event_at=event_at,
    )
  except Exception:
    await usage_ledger_repo.delete_event(inserted_id)
    raise

  return True


async def track_reservation_created(
  *,
  organization_id: Optional[str],
  reservation: Dict[str, Any],
  tenant_id: Optional[str] = None,
  source: str = "reservations",
  source_event_id: Optional[str] = None,
) -> bool:
  """Best-effort metering helper for newly created reservations only."""

  resolved_tenant_id = await _resolve_usage_tenant_id(organization_id, tenant_id)
  if not resolved_tenant_id:
    logger.warning(
      "reservation.created usage skipped: tenant could not be resolved for org=%s reservation=%s",
      organization_id,
      reservation.get("_id"),
    )
    return False

  reservation_id = reservation.get("_id")
  dedupe_key = str(source_event_id or reservation_id or "")
  if not dedupe_key:
    logger.warning(
      "reservation.created usage skipped: dedupe key missing for tenant=%s org=%s",
      resolved_tenant_id,
      organization_id,
    )
    return False

  metadata = {
    "reservation_id": str(reservation_id) if reservation_id is not None else None,
    "channel": reservation.get("channel"),
    "status": reservation.get("status"),
    "product_id": str(reservation.get("product_id")) if reservation.get("product_id") is not None else None,
    "agency_id": str(reservation.get("agency_id")) if reservation.get("agency_id") is not None else None,
  }
  metadata = {k: v for k, v in metadata.items() if v not in (None, "")}

  try:
    return await track_usage_event(
      tenant_id=resolved_tenant_id,
      organization_id=str(organization_id) if organization_id is not None else None,
      metric=UsageMetric.RESERVATION_CREATED,
      quantity=1,
      source=source,
      source_event_id=dedupe_key,
      metadata=metadata,
    )
  except Exception:
    logger.warning(
      "reservation.created usage track failed tenant=%s reservation=%s",
      resolved_tenant_id,
      reservation_id,
      exc_info=True,
    )
    return False


async def track_usage(
  tenant_id: str,
  metric: str,
  quantity: int,
  source: str,
  source_event_id: str,
) -> None:
  """Backward-compatible best-effort tracking helper."""
  try:
    plan = await entitlement_service.get_plan(tenant_id)
    if plan == "starter":
      return  # Starter has no metered features

    organization_id = await _resolve_usage_organization_id(tenant_id)
    inserted = await track_usage_event(
      tenant_id=tenant_id,
      organization_id=organization_id,
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
  entitlements = await entitlement_service.get_tenant_entitlements(tenant_id)
  quotas = entitlements.get("usage_allowances") or {}
  quota = quotas.get(metric)

  period = _current_billing_period()
  organization_id = await _resolve_usage_organization_id(tenant_id, period)
  totals = await usage_daily_repo.get_period_totals(tenant_id, period, organization_id=organization_id)
  if not totals:
    totals = await usage_ledger_repo.get_period_totals(tenant_id, period, organization_id=organization_id)
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


async def get_usage_summary(tenant_id: str, billing_period: Optional[str] = None) -> Dict[str, Any]:
  """Get full usage summary for a tenant (current period)."""
  entitlements = await entitlement_service.get_tenant_entitlements(tenant_id)
  plan = entitlements.get("plan") or DEFAULT_PLAN
  quotas = entitlements.get("usage_allowances") or {}
  period = billing_period or _current_billing_period()
  organization_id = await _resolve_usage_organization_id(tenant_id, period)
  totals = await usage_daily_repo.get_period_totals(tenant_id, period, organization_id=organization_id)
  totals_source = "usage_daily"
  if not totals:
    totals = await usage_ledger_repo.get_period_totals(tenant_id, period, organization_id=organization_id)
    totals_source = "usage_ledger"

  metrics = {}
  all_metric_keys = set(list(quotas.keys()) + list(totals.keys()))
  for m in sorted(all_metric_keys):
    quota = quotas.get(m)
    used = totals.get(m, 0)
    ratio = round((used / quota), 4) if quota not in (None, 0) else 0
    metrics[m] = {
      "quota": quota,
      "used": used,
      "remaining": max(0, quota - used) if quota is not None else None,
      "exceeded": used >= quota if quota is not None else False,
      "ratio": ratio,
    }

  return {
    "tenant_id": tenant_id,
    "organization_id": organization_id,
    "plan": plan,
    "plan_label": entitlements.get("plan_label"),
    "billing_period": period,
    "limits": entitlements.get("limits") or {},
    "metrics": metrics,
    "totals_source": totals_source,
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
