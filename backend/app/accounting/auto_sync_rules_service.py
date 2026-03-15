"""Auto Sync Rule Engine for Accounting.

Manages automation rules that determine when and how invoices
should be automatically synced to accounting providers.

DB Collection: auto_sync_rules

Trigger events:
- invoice_issued: sync immediately after invoice is issued
- invoice_approved: sync only after manual approval
- manual_trigger: no auto-sync, manual only
"""
from __future__ import annotations

import uuid
from typing import Any

from app.db import get_db
from app.utils import now_utc, serialize_doc

RULES_COL = "auto_sync_rules"

# Trigger event constants
TRIGGER_INVOICE_ISSUED = "invoice_issued"
TRIGGER_INVOICE_APPROVED = "invoice_approved"
TRIGGER_BOOKING_CONFIRMED = "booking_confirmed"
TRIGGER_MANUAL = "manual_trigger"

VALID_TRIGGERS = [TRIGGER_INVOICE_ISSUED, TRIGGER_INVOICE_APPROVED, TRIGGER_BOOKING_CONFIRMED, TRIGGER_MANUAL]


async def create_rule(
    tenant_id: str,
    rule_data: dict[str, Any],
    created_by: str = "",
) -> dict[str, Any]:
    """Create a new auto-sync rule."""
    db = await get_db()

    trigger = rule_data.get("trigger_event", TRIGGER_MANUAL)
    if trigger not in VALID_TRIGGERS:
        return {"error": f"Gecersiz trigger: {trigger}. Gecerli: {VALID_TRIGGERS}"}

    now = now_utc()
    rule_id = f"RULE-{uuid.uuid4().hex[:8].upper()}"

    doc = {
        "rule_id": rule_id,
        "tenant_id": tenant_id,
        "rule_name": rule_data.get("rule_name", f"Kural {rule_id}"),
        "trigger_event": trigger,
        "provider": rule_data.get("provider", "luca"),
        "invoice_type": rule_data.get("invoice_type"),  # e_fatura, e_arsiv, None=all
        "agency_plan": rule_data.get("agency_plan"),  # starter, professional, None=all
        "requires_approval": rule_data.get("requires_approval", False),
        "enabled": rule_data.get("enabled", True),
        "created_by": created_by,
        "created_at": now,
        "updated_at": now,
    }
    await db[RULES_COL].insert_one(doc)
    return serialize_doc(doc)


async def update_rule(
    tenant_id: str,
    rule_id: str,
    update_data: dict[str, Any],
) -> dict[str, Any] | None:
    """Update an existing auto-sync rule."""
    db = await get_db()
    doc = await db[RULES_COL].find_one({
        "tenant_id": tenant_id,
        "rule_id": rule_id,
    })
    if not doc:
        return None

    allowed = {"rule_name", "trigger_event", "provider", "invoice_type",
               "agency_plan", "requires_approval", "enabled"}
    update = {k: v for k, v in update_data.items() if k in allowed}

    if "trigger_event" in update and update["trigger_event"] not in VALID_TRIGGERS:
        return {"error": f"Gecersiz trigger: {update['trigger_event']}"}

    update["updated_at"] = now_utc()
    await db[RULES_COL].update_one({"_id": doc["_id"]}, {"$set": update})
    updated = await db[RULES_COL].find_one({"_id": doc["_id"]})
    return serialize_doc(updated)


async def delete_rule(tenant_id: str, rule_id: str) -> bool:
    """Delete an auto-sync rule."""
    db = await get_db()
    result = await db[RULES_COL].delete_one({
        "tenant_id": tenant_id,
        "rule_id": rule_id,
    })
    return result.deleted_count > 0


async def list_rules(
    tenant_id: str,
    enabled_only: bool = False,
) -> list[dict[str, Any]]:
    """List all auto-sync rules for a tenant."""
    db = await get_db()
    q: dict[str, Any] = {"tenant_id": tenant_id}
    if enabled_only:
        q["enabled"] = True
    cursor = db[RULES_COL].find(q).sort("created_at", -1)
    docs = await cursor.to_list(length=100)
    return [serialize_doc(d) for d in docs]


async def evaluate_rules(
    tenant_id: str,
    invoice_data: dict[str, Any],
    trigger_event: str = TRIGGER_INVOICE_ISSUED,
) -> dict[str, Any]:
    """Evaluate auto-sync rules for an invoice.

    Returns whether this invoice should be auto-synced and which provider to use.
    """
    rules = await list_rules(tenant_id, enabled_only=True)

    if not rules:
        return {
            "should_sync": False,
            "reason": "Aktif otomasyon kurali bulunamadi",
            "matched_rule": None,
        }

    invoice_type = invoice_data.get("e_document_type")

    for rule in rules:
        # Check trigger match
        if rule.get("trigger_event") != trigger_event:
            continue

        # Check invoice type filter
        rule_type = rule.get("invoice_type")
        if rule_type and rule_type != invoice_type:
            continue

        # Check agency plan filter
        rule_plan = rule.get("agency_plan")
        if rule_plan:
            # Would check tenant's plan here
            pass

        # Rule matches
        return {
            "should_sync": True,
            "provider": rule.get("provider", "luca"),
            "requires_approval": rule.get("requires_approval", False),
            "matched_rule": rule,
            "reason": f"Kural eslesti: {rule.get('rule_name', rule.get('rule_id'))}",
        }

    return {
        "should_sync": False,
        "reason": "Eslesen kural bulunamadi",
        "matched_rule": None,
    }
