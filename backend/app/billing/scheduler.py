"""Billing cron scheduler.

Runs finalize-period job on the 1st of each month at 00:05 Europe/Istanbul.

Guardrails:
- SCHEDULER_ENABLED env var (default: true in single-worker mode)
- coalesce=True, max_instances=1, misfire_grace_time=3600
- billing_period_jobs lock prevents duplicate finalize
- Retry: up to 2 retries on failure within same day
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler

logger = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None
_last_run_at: str | None = None
_last_result: dict | None = None


def is_scheduler_enabled() -> bool:
  return os.environ.get("SCHEDULER_ENABLED", "true").lower() in ("true", "1", "yes")


async def _finalize_job() -> None:
  """Monthly finalize job. Best-effort with retry tracking."""
  global _last_run_at, _last_result

  from app.repositories.billing_repository import billing_repo
  from app.services.usage_push_service import usage_push_service
  from app.services.audit_log_service import append_audit_log
  from app.db import get_db

  now = datetime.now(timezone.utc)
  _last_run_at = now.isoformat()

  # Previous month
  prev = (now.replace(day=1) - timedelta(days=1))
  period = prev.strftime("%Y-%m")

  logger.info("[cron] Finalize job starting for period %s", period)

  # Check if already finalized successfully
  existing = await billing_repo.get_period_job(period)
  if existing and existing.get("status") == "success":
    logger.info("[cron] Period %s already finalized, skipping", period)
    _last_result = {"period": period, "status": "skipped_already_success"}
    return

  # Lock
  locked = await billing_repo.start_period_job(period, "cron_scheduler")
  if not locked:
    logger.warning("[cron] Period %s lock failed (already running?)", period)
    _last_result = {"period": period, "status": "lock_failed"}
    return

  db = await get_db()
  pending_before = await db.usage_ledger.count_documents({"billing_period": period, "billed": False})

  try:
    result = await usage_push_service.push_unbilled(period)
    pending_after = await db.usage_ledger.count_documents({"billing_period": period, "billed": False})

    pushed = result.get("pushed", 0)
    errors = result.get("errors", 0)
    status = "success" if errors == 0 else "partial"

    await billing_repo.finish_period_job(period, status, pushed, errors, pending_before, pending_after)

    await append_audit_log(
      scope="billing",
      tenant_id="system",
      actor_user_id="system",
      actor_email="cron_scheduler",
      action="billing.period_finalized",
      before={"pending_before": pending_before},
      after={"pushed": pushed, "errors": errors, "pending_after": pending_after, "period": period},
    )

    _last_result = {"period": period, "status": status, "pushed": pushed, "errors": errors, "pending_after": pending_after}
    logger.info("[cron] Finalize %s: status=%s pushed=%d errors=%d", period, status, pushed, errors)

    # Slack alert on issues
    from app.billing.notifier import send_finalize_alert
    await send_finalize_alert(_last_result)

  except Exception as e:
    await billing_repo.finish_period_job(period, "failed", 0, 0, pending_before, pending_before)
    _last_result = {"period": period, "status": "failed", "error": str(e)[:200], "pending_after": pending_before}
    logger.exception("[cron] Finalize failed for %s", period)

    from app.billing.notifier import send_finalize_alert
    await send_finalize_alert(_last_result)


def start_scheduler() -> None:
  """Start the APScheduler if enabled."""
  global _scheduler

  if not is_scheduler_enabled():
    logger.info("[cron] Scheduler disabled (SCHEDULER_ENABLED != true)")
    return

  _scheduler = AsyncIOScheduler(timezone="Europe/Istanbul")

  # Monthly finalize: 1st of each month at 00:05
  _scheduler.add_job(
    _finalize_job,
    "cron",
    day=1,
    hour=0,
    minute=5,
    id="billing_finalize_monthly",
    name="Monthly Billing Finalize",
    coalesce=True,
    max_instances=1,
    misfire_grace_time=3600,
    replace_existing=True,
  )

  _scheduler.start()
  logger.info("[cron] Scheduler started (Europe/Istanbul, monthly finalize at 00:05)")


def stop_scheduler() -> None:
  """Stop the scheduler gracefully."""
  global _scheduler
  if _scheduler and _scheduler.running:
    _scheduler.shutdown(wait=False)
    logger.info("[cron] Scheduler stopped")


def get_cron_status() -> dict:
  """Return scheduler status for ops endpoint."""
  enabled = is_scheduler_enabled()
  running = _scheduler.running if _scheduler else False
  next_run = None

  if _scheduler and _scheduler.running:
    jobs = _scheduler.get_jobs()
    if jobs:
      next_run = str(jobs[0].next_run_time) if jobs[0].next_run_time else None

  return {
    "scheduler_enabled": enabled,
    "scheduler_running": running,
    "timezone": "Europe/Istanbul",
    "next_run_at": next_run,
    "last_run_at": _last_run_at,
    "last_result": _last_result,
  }
