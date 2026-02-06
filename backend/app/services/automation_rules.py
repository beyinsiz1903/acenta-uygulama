from __future__ import annotations

import uuid
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

from app.db import get_db

logger = logging.getLogger(__name__)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _today_key() -> str:
    return _now().strftime("%Y-%m-%d")


async def _is_rule_run_today(db, tenant_id: str, rule_key: str) -> bool:
    """Check if a rule has already run today for this tenant."""
    existing = await db.rule_runs.find_one({
        "tenant_id": tenant_id,
        "rule_key": rule_key,
        "date": _today_key(),
    })
    return existing is not None


async def _mark_rule_run(db, tenant_id: str, rule_key: str) -> None:
    """Mark a rule as having run today."""
    await db.rule_runs.update_one(
        {"tenant_id": tenant_id, "rule_key": rule_key, "date": _today_key()},
        {"$set": {
            "tenant_id": tenant_id,
            "rule_key": rule_key,
            "date": _today_key(),
            "ran_at": _now(),
        }},
        upsert=True,
    )


async def run_overdue_payment_rule(tenant_id: str, org_id: str) -> int:
    """Rule 1: If WebPOS payment overdue > 7 days → create task for owner."""
    db = await get_db()
    rule_key = "overdue_payment_task"

    if await _is_rule_run_today(db, tenant_id, rule_key):
        return 0

    cutoff = _now() - timedelta(days=7)
    overdue_reservations = await db.reservations.find({
        "organization_id": org_id,
        "status": "pending",
        "created_at": {"$lt": cutoff},
    }).to_list(length=100)

    tasks_created = 0
    for res in overdue_reservations:
        res_id = str(res.get("_id", ""))
        # Check if task already exists for this reservation
        existing_task = await db.crm_tasks.find_one({
            "organization_id": org_id,
            "related_type": "reservation",
            "related_id": res_id,
            "source": "automation_rule",
        })
        if existing_task:
            continue

        task_id = f"task_{uuid.uuid4().hex}"
        await db.crm_tasks.insert_one({
            "id": task_id,
            "organization_id": org_id,
            "tenant_id": tenant_id,
            "title": f"Ödeme gecikmiş: Rezervasyon {res_id[:12]}...",
            "status": "open",
            "priority": "high",
            "due_date": _now(),
            "related_type": "reservation",
            "related_id": res_id,
            "owner_user_id": res.get("created_by"),
            "source": "automation_rule",
            "rule_key": rule_key,
            "created_at": _now(),
            "updated_at": _now(),
        })
        tasks_created += 1

    await _mark_rule_run(db, tenant_id, rule_key)
    logger.info("Rule %s: created %d tasks for tenant %s", rule_key, tasks_created, tenant_id)
    return tasks_created


async def run_deal_overdue_rule(tenant_id: str, org_id: str) -> int:
    """Rule 2: If deal in 'proposal' with next_action_at overdue → notify + create task."""
    db = await get_db()
    rule_key = "deal_proposal_overdue"

    if await _is_rule_run_today(db, tenant_id, rule_key):
        return 0

    now = _now()
    overdue_deals = await db.crm_deals.find({
        "organization_id": org_id,
        "stage": "proposal",
        "status": "open",
        "next_action_at": {"$lt": now},
    }).to_list(length=100)

    tasks_created = 0
    for deal in overdue_deals:
        deal_id = deal.get("id", "")
        # Check if task already exists
        existing_task = await db.crm_tasks.find_one({
            "organization_id": org_id,
            "related_type": "deal",
            "related_id": deal_id,
            "source": "automation_rule",
            "rule_key": rule_key,
        })
        if existing_task:
            continue

        task_id = f"task_{uuid.uuid4().hex}"
        owner = deal.get("owner_user_id")
        await db.crm_tasks.insert_one({
            "id": task_id,
            "organization_id": org_id,
            "tenant_id": tenant_id,
            "title": f"Teklif takibi: {deal.get('title', deal_id[:12])}",
            "status": "open",
            "priority": "high",
            "due_date": now,
            "related_type": "deal",
            "related_id": deal_id,
            "owner_user_id": owner,
            "source": "automation_rule",
            "rule_key": rule_key,
            "created_at": now,
            "updated_at": now,
        })
        tasks_created += 1

        # Create notification for owner
        try:
            from app.services.notification_service import notification_service
            await notification_service.create(
                tenant_id=tenant_id,
                user_id=owner,
                notification_type="system",
                title="Teklif Takibi Gerekli",
                message=f"Deal '{deal.get('title', '')}' teklifinde aksiyons tarihi geçmiş.",
                link=f"/app/crm/pipeline",
            )
        except Exception as e:
            logger.warning("Notification failed for deal overdue rule: %s", e)

    await _mark_rule_run(db, tenant_id, rule_key)
    logger.info("Rule %s: created %d tasks for tenant %s", rule_key, tasks_created, tenant_id)
    return tasks_created


async def trigger_all_rules(tenant_id: str, org_id: str) -> dict:
    """Run all automation rules for a tenant. Idempotent per day."""
    results = {}
    try:
        results["overdue_payment_tasks"] = await run_overdue_payment_rule(tenant_id, org_id)
    except Exception as e:
        logger.error("overdue_payment_rule failed: %s", e)
        results["overdue_payment_tasks"] = -1

    try:
        results["deal_overdue_tasks"] = await run_deal_overdue_rule(tenant_id, org_id)
    except Exception as e:
        logger.error("deal_overdue_rule failed: %s", e)
        results["deal_overdue_tasks"] = -1

    return results
