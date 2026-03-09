from __future__ import annotations

from typing import Any, Dict, Optional

from app.constants.plan_matrix import DEFAULT_PLAN
from app.constants.usage_metrics import UsageMetric
from app.errors import AppError, ErrorCode
from app.repositories.usage_daily_repository import usage_daily_repo
from app.repositories.usage_ledger_repository import usage_ledger_repo
from app.services.audit_log_service import append_audit_log
from app.services.entitlement_service import entitlement_service
from app.services.quota_warning_service import METRIC_LIMIT_SUBJECTS, calculate_warning_level
from app.services.usage_service import (
  _current_billing_period,
  _resolve_usage_organization_id,
  _resolve_usage_tenant_id,
)

ACTION_LABELS = {
  UsageMetric.RESERVATION_CREATED: "Yeni rezervasyon oluşturma",
  UsageMetric.REPORT_GENERATED: "Rapor oluşturma",
  UsageMetric.EXPORT_GENERATED: "Export oluşturma",
  UsageMetric.INTEGRATION_CALL: "Entegrasyon çağrısı",
  UsageMetric.B2B_MATCH_REQUEST: "B2B talebi",
}


async def get_quota_guard_snapshot(
  *,
  metric: str,
  organization_id: Optional[str] = None,
  tenant_id: Optional[str] = None,
  increment: int = 1,
  action_label: Optional[str] = None,
) -> Dict[str, Any]:
  requested_increment = max(1, int(increment or 1))
  resolved_tenant_id = await _resolve_usage_tenant_id(organization_id, tenant_id)
  if not resolved_tenant_id:
    return {
      "enforced": False,
      "blocked": False,
      "metric": metric,
      "tenant_id": None,
      "organization_id": organization_id,
      "requested_increment": requested_increment,
    }

  entitlements = await entitlement_service.get_tenant_entitlements(resolved_tenant_id, refresh=True)
  quotas = entitlements.get("usage_allowances") or {}
  limit = quotas.get(metric)
  plan = entitlements.get("plan") or DEFAULT_PLAN
  plan_label = entitlements.get("plan_label") or str(plan).title()
  period = _current_billing_period()
  resolved_organization_id = organization_id or await _resolve_usage_organization_id(resolved_tenant_id, period)

  if limit is None:
    return {
      "enforced": False,
      "blocked": False,
      "metric": metric,
      "metric_label": METRIC_LIMIT_SUBJECTS.get(metric, metric),
      "tenant_id": resolved_tenant_id,
      "organization_id": resolved_organization_id,
      "plan": plan,
      "plan_label": plan_label,
      "limit": None,
      "used": 0,
      "remaining": None,
      "period": period,
      "requested_increment": requested_increment,
    }

  totals = await usage_daily_repo.get_period_totals(
    resolved_tenant_id,
    period,
    organization_id=resolved_organization_id,
  )
  if not totals:
    totals = await usage_ledger_repo.get_period_totals(
      resolved_tenant_id,
      period,
      organization_id=resolved_organization_id,
    )

  used = int(totals.get(metric, 0) or 0)
  remaining = max(0, int(limit) - used)
  projected_used = used + requested_increment
  blocked = projected_used > int(limit)
  metric_label = METRIC_LIMIT_SUBJECTS.get(metric, metric)

  return {
    "enforced": True,
    "blocked": blocked,
    "metric": metric,
    "metric_label": metric_label,
    "tenant_id": resolved_tenant_id,
    "organization_id": resolved_organization_id,
    "plan": plan,
    "plan_label": plan_label,
    "limit": int(limit),
    "used": used,
    "remaining": remaining,
    "period": period,
    "requested_increment": requested_increment,
    "projected_used": projected_used,
    "warning_level": calculate_warning_level(used, int(limit)),
    "next_warning_level": calculate_warning_level(projected_used, int(limit)),
    "action_label": action_label or ACTION_LABELS.get(metric, "İşlem"),
    "cta_href": "/pricing",
    "cta_label": "Planları Görüntüle",
  }


async def enforce_quota_or_raise(
  *,
  metric: str,
  organization_id: Optional[str] = None,
  tenant_id: Optional[str] = None,
  increment: int = 1,
  action_label: Optional[str] = None,
) -> Dict[str, Any]:
  snapshot = await get_quota_guard_snapshot(
    metric=metric,
    organization_id=organization_id,
    tenant_id=tenant_id,
    increment=increment,
    action_label=action_label,
  )
  if not snapshot.get("blocked"):
    return snapshot

  await append_audit_log(
    scope="usage",
    tenant_id=str(snapshot.get("tenant_id") or ""),
    actor_user_id="system",
    actor_email="quota_guard",
    action="usage.quota_blocked",
    before={
      "metric": snapshot.get("metric"),
      "used": snapshot.get("used"),
      "limit": snapshot.get("limit"),
      "remaining": snapshot.get("remaining"),
    },
    after={
      "metric": snapshot.get("metric"),
      "requested_increment": snapshot.get("requested_increment"),
      "projected_used": snapshot.get("projected_used"),
      "action_label": snapshot.get("action_label"),
    },
    metadata={
      "plan": snapshot.get("plan"),
      "period": snapshot.get("period"),
      "warning_level": snapshot.get("next_warning_level"),
    },
  )

  raise AppError(
    status_code=403,
    code=ErrorCode.QUOTA_EXCEEDED,
    message=(
      f"{snapshot.get('action_label')} için {snapshot.get('metric_label')} limitiniz doldu. "
      "Devam etmek için planınızı yükseltin."
    ),
    details={
      "metric": snapshot.get("metric"),
      "metric_label": snapshot.get("metric_label"),
      "tenant_id": snapshot.get("tenant_id"),
      "organization_id": snapshot.get("organization_id"),
      "plan": snapshot.get("plan"),
      "plan_label": snapshot.get("plan_label"),
      "limit": snapshot.get("limit"),
      "used": snapshot.get("used"),
      "remaining": snapshot.get("remaining"),
      "requested_increment": snapshot.get("requested_increment"),
      "period": snapshot.get("period"),
      "warning_level": snapshot.get("next_warning_level"),
      "action_label": snapshot.get("action_label"),
      "cta_href": snapshot.get("cta_href"),
      "cta_label": snapshot.get("cta_label"),
    },
  )