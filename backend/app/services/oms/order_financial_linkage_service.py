"""Order Financial Linkage Service — OMS Phase 2.

Links orders to the financial ledger and settlement systems.
Builds and manages financial summaries for orders.

Responsibilities:
  - order <-> ledger mapping
  - summary generation
  - posting ref attachment
  - settlement ref attachment
  - refresh/rebuild summary
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from app.db import get_db
from app.services.order_event_service import append_event
from app.services.ledger_posting import LedgerPostingService, LedgerLine


# Financial status enum
FINANCIAL_STATUSES = {
    "not_posted",
    "partially_posted",
    "posted",
    "partially_settled",
    "settled",
    "reversed",
}


async def build_order_financial_summary(order_id: str) -> dict:
    """Build or rebuild the full financial summary for an order."""
    db = await get_db()
    order = await db.orders.find_one({"order_id": order_id})
    if not order:
        return {"error": "Order not found"}

    items = await db.order_items.find(
        {"order_id": order_id}, {"_id": 0}
    ).to_list(length=100)

    sell_total = sum(i.get("sell_amount", 0) for i in items)
    supplier_total = sum(i.get("supplier_amount", 0) for i in items)
    margin_total = sell_total - supplier_total
    commission_total = sum(i.get("commission_amount", 0) for i in items)
    tax_total = sum(i.get("tax_amount", 0) for i in items)

    ledger_refs = order.get("ledger_posting_refs", [])
    settlement_refs = order.get("settlement_run_refs", [])
    financial_status = await compute_financial_status(order_id)

    now = datetime.now(timezone.utc).isoformat()

    summary = {
        "order_id": order_id,
        "order_number": order.get("order_number", ""),
        "tenant_id": order.get("tenant_id", ""),
        "agency_id": order.get("agency_id", ""),
        "supplier_codes": list({i.get("supplier_code", "") for i in items if i.get("supplier_code")}),
        "sell_total": round(sell_total, 2),
        "supplier_total": round(supplier_total, 2),
        "margin_total": round(margin_total, 2),
        "commission_total": round(commission_total, 2),
        "tax_total": round(tax_total, 2),
        "currency": order.get("currency", "EUR"),
        "financial_status": financial_status,
        "ledger_posting_refs": ledger_refs,
        "ledger_posting_count": len(ledger_refs),
        "settlement_run_refs": settlement_refs,
        "settlement_status": order.get("settlement_status", "not_settled"),
        "settlement_run_count": len(settlement_refs),
        "last_posted_at": order.get("last_posted_at"),
        "last_settled_at": order.get("last_settled_at"),
        "item_count": len(items),
        "updated_at": now,
    }

    # Persist summary to order
    await db.orders.update_one(
        {"order_id": order_id},
        {"$set": {
            "financial_summary": summary,
            "total_sell_amount": round(sell_total, 2),
            "total_supplier_amount": round(supplier_total, 2),
            "total_margin_amount": round(margin_total, 2),
            "financial_status": financial_status,
            "updated_at": now,
        }},
    )

    # Also upsert into dedicated summary collection for fast queries
    await db.order_financial_summaries.update_one(
        {"order_id": order_id},
        {"$set": summary},
        upsert=True,
    )

    return summary


async def compute_financial_status(order_id: str) -> str:
    """Compute the current financial status based on ledger/settlement refs."""
    db = await get_db()
    order = await db.orders.find_one({"order_id": order_id})
    if not order:
        return "not_posted"

    # If explicitly set to reversed, keep it
    stored_status = order.get("financial_status", "not_posted")
    if stored_status == "reversed":
        return "reversed"

    ledger_refs = order.get("ledger_posting_refs", [])
    settlement_status = order.get("settlement_status", "not_settled")

    if not ledger_refs:
        return "not_posted"
    if settlement_status == "settled":
        return "settled"
    if settlement_status == "partially_settled":
        return "partially_settled"
    return "posted"


async def post_order_to_ledger(order_id: str, actor_name: str = "system") -> dict:
    """Create ledger postings for a confirmed order.

    Creates double-entry ledger entries:
      - agency receivable (debit) = sell_total
      - supplier payable (credit) = supplier_total
      - platform revenue (credit) = margin
    """
    db = await get_db()
    order = await db.orders.find_one({"order_id": order_id})
    if not order:
        return {"success": False, "error": "Order not found"}

    org_id = order.get("org_id", "default_org")
    currency = order.get("currency", "EUR")
    sell_total = order.get("total_sell_amount", 0)
    supplier_total = order.get("total_supplier_amount", 0)
    margin_total = sell_total - supplier_total
    agency_id = order.get("agency_id", "")

    if sell_total <= 0:
        return {"success": False, "error": "Order has no financial amounts"}

    # Check if already posted
    existing_refs = order.get("ledger_posting_refs", [])
    if existing_refs:
        return {"success": True, "message": "Already posted", "posting_refs": existing_refs}

    now = datetime.now(timezone.utc).isoformat()
    posting_refs = []

    # Create the posting via LedgerPostingService
    try:
        # Main posting: agency receivable and supplier payable
        lines = [
            LedgerLine(account_id=f"AGENCY_AR_{agency_id}_{currency}", direction="debit", amount=sell_total),
            LedgerLine(account_id=f"SUPPLIER_AP_{currency}", direction="credit", amount=supplier_total),
        ]
        # Add margin line if positive
        if margin_total > 0:
            lines.append(LedgerLine(account_id=f"PLATFORM_REVENUE_{currency}", direction="credit", amount=margin_total))

        posting = await LedgerPostingService.post_event(
            organization_id=org_id,
            source_type="order",
            source_id=order_id,
            event="ORDER_CONFIRMED",
            currency=currency,
            lines=lines,
            created_by=actor_name,
            meta={
                "order_id": order_id,
                "order_number": order.get("order_number", ""),
                "agency_id": agency_id,
                "sell_total": sell_total,
                "supplier_total": supplier_total,
                "margin_total": margin_total,
            },
        )
        posting_id = posting.get("_id", str(posting.get("posting_id", "")))
        posting_refs.append(str(posting_id))
    except Exception as e:
        return {"success": False, "error": f"Ledger posting failed: {str(e)}"}

    # Update order with posting refs
    await db.orders.update_one(
        {"order_id": order_id},
        {"$set": {
            "ledger_posting_refs": posting_refs,
            "financial_status": "posted",
            "last_posted_at": now,
            "updated_at": now,
        }},
    )

    # Record event
    await append_event(
        order_id=order_id,
        event_type="order_ledger_linked",
        actor_type="system",
        actor_id=actor_name,
        actor_name=actor_name,
        after_state={"financial_status": "posted", "posting_refs": posting_refs},
        payload={
            "sell_total": sell_total,
            "supplier_total": supplier_total,
            "margin_total": margin_total,
        },
        org_id=org_id,
    )

    # Build summary
    await build_order_financial_summary(order_id)

    # Record summary built event
    await append_event(
        order_id=order_id,
        event_type="order_financial_summary_built",
        actor_type="system",
        actor_id=actor_name,
        actor_name=actor_name,
        after_state={"financial_status": "posted"},
        payload={"posting_count": len(posting_refs)},
        org_id=org_id,
    )

    return {
        "success": True,
        "posting_refs": posting_refs,
        "financial_status": "posted",
    }


async def reverse_order_ledger(order_id: str, actor_name: str = "system") -> dict:
    """Reverse ledger postings when an order is cancelled."""
    db = await get_db()
    order = await db.orders.find_one({"order_id": order_id})
    if not order:
        return {"success": False, "error": "Order not found"}

    org_id = order.get("org_id", "default_org")
    currency = order.get("currency", "EUR")
    sell_total = order.get("total_sell_amount", 0)
    supplier_total = order.get("total_supplier_amount", 0)
    margin_total = sell_total - supplier_total
    agency_id = order.get("agency_id", "")

    if sell_total <= 0:
        return {"success": False, "error": "No amounts to reverse"}

    now = datetime.now(timezone.utc).isoformat()

    try:
        # Reverse: swap debit/credit
        lines = [
            LedgerLine(account_id=f"AGENCY_AR_{agency_id}_{currency}", direction="credit", amount=sell_total),
            LedgerLine(account_id=f"SUPPLIER_AP_{currency}", direction="debit", amount=supplier_total),
        ]
        if margin_total > 0:
            lines.append(LedgerLine(account_id=f"PLATFORM_REVENUE_{currency}", direction="debit", amount=margin_total))

        posting = await LedgerPostingService.post_event(
            organization_id=org_id,
            source_type="order",
            source_id=order_id,
            event="ORDER_CANCELLED",
            currency=currency,
            lines=lines,
            created_by=actor_name,
            meta={
                "order_id": order_id,
                "order_number": order.get("order_number", ""),
                "reversal": True,
            },
        )
        posting_id = str(posting.get("_id", posting.get("posting_id", "")))

        existing_refs = order.get("ledger_posting_refs", [])
        existing_refs.append(posting_id)

        await db.orders.update_one(
            {"order_id": order_id},
            {"$set": {
                "ledger_posting_refs": existing_refs,
                "financial_status": "reversed",
                "updated_at": now,
            }},
        )

        await append_event(
            order_id=order_id,
            event_type="order_financial_status_changed",
            actor_type="system",
            actor_id=actor_name,
            actor_name=actor_name,
            before_state={"financial_status": "posted"},
            after_state={"financial_status": "reversed"},
            payload={"reversal_posting_id": posting_id},
            org_id=org_id,
        )

        await build_order_financial_summary(order_id)

        return {"success": True, "reversal_posting_id": posting_id}
    except Exception as e:
        return {"success": False, "error": f"Reversal failed: {str(e)}"}


async def attach_settlement_run(
    order_id: str,
    run_id: str,
    actor_name: str = "system",
) -> dict:
    """Link a settlement run to an order."""
    db = await get_db()
    order = await db.orders.find_one({"order_id": order_id})
    if not order:
        return {"success": False, "error": "Order not found"}

    org_id = order.get("org_id", "default_org")
    now = datetime.now(timezone.utc).isoformat()

    existing_refs = order.get("settlement_run_refs", [])
    if run_id in existing_refs:
        return {"success": True, "message": "Already linked"}

    existing_refs.append(run_id)
    new_settlement_status = "partially_settled" if len(existing_refs) > 0 else "not_settled"

    await db.orders.update_one(
        {"order_id": order_id},
        {"$set": {
            "settlement_run_refs": existing_refs,
            "settlement_status": new_settlement_status,
            "last_settled_at": now,
            "updated_at": now,
        }},
    )

    await append_event(
        order_id=order_id,
        event_type="order_settlement_linked",
        actor_type="system",
        actor_id=actor_name,
        actor_name=actor_name,
        after_state={
            "settlement_status": new_settlement_status,
            "settlement_run_refs": existing_refs,
        },
        payload={"settlement_run_id": run_id},
        org_id=org_id,
    )

    await build_order_financial_summary(order_id)

    return {
        "success": True,
        "settlement_run_id": run_id,
        "settlement_status": new_settlement_status,
    }


async def mark_order_settled(order_id: str, actor_name: str = "system") -> dict:
    """Mark an order as fully settled."""
    db = await get_db()
    order = await db.orders.find_one({"order_id": order_id})
    if not order:
        return {"success": False, "error": "Order not found"}

    org_id = order.get("org_id", "default_org")
    now = datetime.now(timezone.utc).isoformat()
    old_status = order.get("settlement_status", "not_settled")

    await db.orders.update_one(
        {"order_id": order_id},
        {"$set": {
            "settlement_status": "settled",
            "financial_status": "settled",
            "last_settled_at": now,
            "updated_at": now,
        }},
    )

    await append_event(
        order_id=order_id,
        event_type="order_financial_status_changed",
        actor_type="user",
        actor_id=actor_name,
        actor_name=actor_name,
        before_state={"settlement_status": old_status},
        after_state={"settlement_status": "settled"},
        org_id=org_id,
    )

    await build_order_financial_summary(order_id)

    return {"success": True, "settlement_status": "settled"}
