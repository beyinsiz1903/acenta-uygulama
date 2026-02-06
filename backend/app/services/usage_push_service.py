from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.db import get_db
from app.repositories.usage_ledger_repository import usage_ledger_repo
from app.services.audit_log_service import append_audit_log

logger = logging.getLogger(__name__)


class UsagePushService:
  """Push unbilled usage records to Stripe metered billing.

  Guardrails:
  - Idempotency key per usage record (usage:{tenant_id}:{metric}:{source_event_id})
  - Only pushes if metered_subscription_item_id exists for tenant
  - Marks billed=True only after Stripe success
  - Tracks push_attempts and last_push_error
  """

  async def push_unbilled(self, billing_period: Optional[str] = None) -> Dict[str, Any]:
    """Push all unbilled usage records to Stripe.

    Returns summary of pushed/skipped/errors.
    """
    import stripe

    stripe_key = os.environ.get("STRIPE_API_KEY", "")
    if not stripe_key:
      return {"error": "STRIPE_API_KEY not set", "pushed": 0}

    stripe.api_key = stripe_key
    db = await get_db()

    unbilled = await usage_ledger_repo.get_unbilled(billing_period)
    if not unbilled:
      return {"pushed": 0, "skipped": 0, "errors": 0, "total": 0}

    # Group by tenant to batch lookups
    tenant_ids = set(r["tenant_id"] for r in unbilled)
    sub_map = {}
    for tid in tenant_ids:
      sub = await db.billing_subscriptions.find_one({"tenant_id": tid}, {"_id": 0})
      if sub and sub.get("metered_subscription_item_id"):
        sub_map[tid] = sub

    pushed = 0
    skipped = 0
    errors = 0

    for record in unbilled:
      tid = record["tenant_id"]
      sub = sub_map.get(tid)

      if not sub:
        skipped += 1
        continue

      item_id = sub["metered_subscription_item_id"]
      idempotency_key = f"usage:{tid}:{record['metric']}:{record['source_event_id']}"

      # Use original event timestamp for Stripe
      ts = record.get("timestamp")
      timestamp_unix = int(ts.timestamp()) if isinstance(ts, datetime) else int(datetime.now(timezone.utc).timestamp())

      try:
        usage_record = stripe.SubscriptionItem.create_usage_record(
          item_id,
          quantity=record["quantity"],
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

    # Audit log
    if pushed > 0 or errors > 0:
      await append_audit_log(
        scope="billing",
        tenant_id="system",
        actor_user_id="system",
        actor_email="usage_push_job",
        action="billing.usage_pushed",
        before=None,
        after={"pushed": pushed, "skipped": skipped, "errors": errors, "period": billing_period},
      )

    return {"pushed": pushed, "skipped": skipped, "errors": errors, "total": len(unbilled)}


usage_push_service = UsagePushService()
