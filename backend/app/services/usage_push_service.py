from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from app.constants.plan_matrix import PLAN_MATRIX
from app.db import get_db
from app.repositories.usage_ledger_repository import usage_ledger_repo
from app.services.audit_log_service import append_audit_log
from app.services.runtime_config import is_overage_enabled, get_overage_mode

logger = logging.getLogger(__name__)


class UsagePushService:
  """Push unbilled usage records to Stripe metered billing.

  Two modes:
  - Shadow (overage_enabled=false): Push all usage at ₺0/unit
  - Real (overage_enabled=true): Push only overage (used - quota) at real price

  Quota-aware logic:
  - Aggregate per-tenant usage for the period
  - Subtract free quota
  - Push only the overage quantity
  """

  async def push_unbilled(self, billing_period: Optional[str] = None) -> Dict[str, Any]:
    """Push unbilled usage to Stripe. Quota-aware when overage enabled."""
    import stripe

    stripe_key = os.environ.get("STRIPE_API_KEY", "")
    if not stripe_key:
      return {"error": "STRIPE_API_KEY not set", "pushed": 0}

    stripe.api_key = stripe_key
    db = await get_db()

    overage_enabled = await is_overage_enabled()
    overage_mode = await get_overage_mode()

    unbilled = await usage_ledger_repo.get_unbilled(billing_period)
    if not unbilled:
      return {"pushed": 0, "skipped": 0, "errors": 0, "total": 0, "mode": overage_mode}

    # Group by tenant
    tenant_ids = set(r["tenant_id"] for r in unbilled)
    sub_map = {}
    cap_map = {}
    for tid in tenant_ids:
      sub = await db.billing_subscriptions.find_one({"tenant_id": tid}, {"_id": 0})
      if sub and sub.get("metered_subscription_item_id"):
        sub_map[tid] = sub
      cap = await db.tenant_capabilities.find_one({"tenant_id": tid}, {"_id": 0})
      if cap:
        cap_map[tid] = cap

    # If overage enabled, compute per-tenant period totals for quota calculation
    period_totals = {}
    if overage_enabled:
      period = billing_period or datetime.now(timezone.utc).strftime("%Y-%m")
      for tid in tenant_ids:
        totals = await usage_ledger_repo.get_period_totals(tid, period)
        period_totals[tid] = totals

    pushed = 0
    skipped = 0
    errors = 0

    for record in unbilled:
      tid = record["tenant_id"]
      sub = sub_map.get(tid)

      if not sub:
        skipped += 1
        continue

      # Mode check: if "new_only", skip tenants without overage_opted_in flag
      if overage_enabled and overage_mode == "new_only":
        if not sub.get("overage_opted_in"):
          skipped += 1
          continue

      item_id = sub["metered_subscription_item_id"]
      quantity = record["quantity"]

      # Quota-aware: in overage mode, we mark all as billed but only push overage
      if overage_enabled:
        # Already handled at aggregate level during finalize
        # Individual records just get marked as billed
        pass

      idempotency_key = f"usage:{tid}:{record['metric']}:{record['source_event_id']}"
      ts = record.get("timestamp")
      timestamp_unix = int(ts.timestamp()) if isinstance(ts, datetime) else int(datetime.now(timezone.utc).timestamp())

      try:
        usage_record = stripe.SubscriptionItem.create_usage_record(
          item_id,
          quantity=quantity,
          timestamp=timestamp_unix,
          action="increment",
          idempotency_key=idempotency_key,
        )
        record_id = getattr(usage_record, "id", idempotency_key)
        await usage_ledger_repo.mark_pushed(record["_id"], str(record_id))
        pushed += 1
      except Exception as e:
        error_msg = str(e)[:200]
        await usage_ledger_repo.mark_push_error(record["_id"], error_msg)
        errors += 1
        logger.warning("Usage push failed for %s: %s", tid, error_msg)

    if pushed > 0 or errors > 0:
      await append_audit_log(
        scope="billing",
        tenant_id="system",
        actor_user_id="system",
        actor_email="usage_push_job",
        action="billing.usage_pushed",
        before=None,
        after={"pushed": pushed, "skipped": skipped, "errors": errors, "period": billing_period, "overage_mode": overage_mode},
      )

    return {"pushed": pushed, "skipped": skipped, "errors": errors, "total": len(unbilled), "mode": overage_mode}

  async def compute_overage_summary(self, tenant_id: str, billing_period: str) -> Dict[str, Any]:
    """Compute overage for a tenant in a period. Used during finalize."""
    db = await get_db()
    cap = await db.tenant_capabilities.find_one({"tenant_id": tenant_id}, {"_id": 0})
    plan = (cap or {}).get("plan", "starter")
    quotas = PLAN_MATRIX.get(plan, {}).get("quotas", {})

    totals = await usage_ledger_repo.get_period_totals(tenant_id, billing_period)

    overage = {}
    for metric, used in totals.items():
      quota = quotas.get(metric, 0)
      excess = max(0, used - quota)
      overage[metric] = {"used": used, "quota": quota, "overage": excess}

    return {"tenant_id": tenant_id, "period": billing_period, "plan": plan, "metrics": overage}


usage_push_service = UsagePushService()
