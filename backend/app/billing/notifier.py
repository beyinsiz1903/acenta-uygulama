"""Billing alerting — Slack webhook notifications for finalize issues."""
from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger(__name__)

_TIMEOUT = 3.0


def _get_slack_url() -> Optional[str]:
  url = os.environ.get("SLACK_BILLING_WEBHOOK_URL", "").strip()
  return url if url else None


def _get_admin_url() -> str:
  return os.environ.get("ADMIN_ANALYTICS_URL", "") or os.environ.get("APP_URL", "") or ""


async def send_finalize_alert(job_summary: Dict[str, Any]) -> None:
  """Best-effort Slack alert for finalize issues. Never raises."""
  url = _get_slack_url()
  if not url:
    return

  status = job_summary.get("status", "unknown")
  errors = job_summary.get("errors", 0) or job_summary.get("error_count", 0)
  pending = job_summary.get("pending_after", 0)
  pushed = job_summary.get("pushed", 0) or job_summary.get("pushed_count", 0)
  period = job_summary.get("period", "?")

  # Only alert on problems
  if status == "success" and errors == 0 and pending == 0:
    return

  # Emoji based on severity
  if status == "failed":
    emoji = ":rotating_light:"
    title = f"{emoji} Billing Finalize FAILED — Period {period}"
  elif errors > 0:
    emoji = ":warning:"
    title = f"{emoji} Billing Finalize Alert — Period {period}"
  else:
    emoji = ":large_yellow_circle:"
    title = f"{emoji} Billing Finalize — Pending Records — Period {period}"

  admin_url = _get_admin_url()
  link = f"{admin_url}/app/admin/analytics" if admin_url else "/app/admin/analytics"

  blocks = [
    {"type": "header", "text": {"type": "plain_text", "text": title}},
    {"type": "section", "fields": [
      {"type": "mrkdwn", "text": f"*Status:* `{status}`"},
      {"type": "mrkdwn", "text": f"*Period:* `{period}`"},
      {"type": "mrkdwn", "text": f"*Pushed:* {pushed}"},
      {"type": "mrkdwn", "text": f"*Errors:* {errors}"},
      {"type": "mrkdwn", "text": f"*Pending After:* {pending}"},
      {"type": "mrkdwn", "text": f"*Dashboard:* <{link}|Open Analytics>"},
    ]},
  ]

  payload = {"text": title, "blocks": blocks}

  try:
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
      resp = await client.post(url, json=payload)
      if resp.status_code != 200:
        logger.warning("Slack alert response %d: %s", resp.status_code, resp.text[:100])
  except Exception:
    logger.warning("Slack billing alert failed", exc_info=True)
