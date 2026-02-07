"""O2 - Data Integrity Monitoring Service.

Verifies audit chain, ledger integrity, and detects orphaned records.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from app.db import get_db
from app.services.audit_hash_chain import verify_chain_integrity
from app.utils import now_utc


async def verify_audit_chain(tenant_id: str) -> dict[str, Any]:
    """Verify the audit hash chain for a specific tenant."""
    db = await get_db()
    result = await verify_chain_integrity(db, tenant_id)

    if not result["valid"]:
        # Insert system error for broken chain
        await db.system_errors.update_one(
            {"signature": f"audit_chain_broken_{tenant_id}"},
            {
                "$set": {
                    "message": f"Audit chain integrity broken for tenant {tenant_id}",
                    "stack_trace": str(result.get("errors", []))[:2000],
                    "severity": "critical",
                    "last_seen": now_utc(),
                },
                "$inc": {"count": 1},
                "$setOnInsert": {
                    "_id": str(uuid.uuid4()),
                    "signature": f"audit_chain_broken_{tenant_id}",
                    "first_seen": now_utc(),
                    "request_id": None,
                },
            },
            upsert=True,
        )
        # Create system incident
        await db.system_incidents.insert_one({
            "_id": str(uuid.uuid4()),
            "incident_id": str(uuid.uuid4()),
            "severity": "critical",
            "title": f"Audit chain broken - tenant {tenant_id}",
            "start_time": now_utc(),
            "end_time": None,
            "affected_tenants": [tenant_id],
            "root_cause": "Audit hash chain integrity verification failed",
            "resolution_notes": None,
            "created_at": now_utc(),
        })

    return result


async def verify_all_audit_chains() -> dict[str, Any]:
    """Verify audit chains for all tenants. Called by daily cron."""
    db = await get_db()
    # Get all distinct tenant_ids from audit_logs_chain
    tenant_ids = await db.audit_logs_chain.distinct("tenant_id")

    results = {}
    broken_count = 0
    for tid in tenant_ids:
        result = await verify_audit_chain(tid)
        results[tid] = result
        if not result["valid"]:
            broken_count += 1

    return {
        "tenants_checked": len(tenant_ids),
        "broken_chains": broken_count,
        "details": results,
    }


async def verify_ledger_integrity() -> dict[str, Any]:
    """Nightly ledger integrity check.
    Recompute balance from ledger entries and compare with stored balance.
    """
    db = await get_db()
    mismatches = []

    # Get all accounts with stored balance
    pipeline = [
        {"$group": {
            "_id": {"organization_id": "$organization_id", "account_id": "$account_id"},
            "computed_balance": {"$sum": "$amount"},
            "entry_count": {"$sum": 1},
        }}
    ]

    try:
        cursor = db.ledger_entries.aggregate(pipeline)
        entries = await cursor.to_list(length=10000)
    except Exception:
        # If ledger_entries collection doesn't exist yet
        entries = []

    for entry in entries:
        org_id = entry["_id"].get("organization_id")
        account_id = entry["_id"].get("account_id")
        computed = entry["computed_balance"]

        # Check against stored balance if available
        stored = await db.account_balances.find_one({
            "organization_id": org_id,
            "account_id": account_id,
        })

        if stored and abs(stored.get("balance", 0) - computed) > 0.01:
            mismatch = {
                "organization_id": org_id,
                "account_id": account_id,
                "stored_balance": stored.get("balance", 0),
                "computed_balance": computed,
                "difference": stored.get("balance", 0) - computed,
            }
            mismatches.append(mismatch)

            # Log system error
            await db.system_errors.update_one(
                {"signature": f"ledger_mismatch_{org_id}_{account_id}"},
                {
                    "$set": {
                        "message": f"Ledger balance mismatch: org={org_id}, account={account_id}",
                        "stack_trace": str(mismatch),
                        "severity": "critical",
                        "last_seen": now_utc(),
                    },
                    "$inc": {"count": 1},
                    "$setOnInsert": {
                        "_id": str(uuid.uuid4()),
                        "signature": f"ledger_mismatch_{org_id}_{account_id}",
                        "first_seen": now_utc(),
                        "request_id": None,
                    },
                },
                upsert=True,
            )

    return {
        "checked_accounts": len(entries),
        "mismatches": len(mismatches),
        "details": mismatches[:50],
    }


async def detect_orphans() -> dict[str, Any]:
    """Detect orphaned records across the system."""
    db = await get_db()
    orphans = {
        "invoices_without_payments": [],
        "tickets_without_reservation": [],
        "reservations_without_product": [],
    }

    # 1. Invoices without payments (invoices in completed status with no payment records)
    try:
        invoices = await db.efatura_invoices.find(
            {"status": {"$in": ["sent", "accepted"]}}
        ).to_list(length=500)

        for inv in invoices:
            payment = await db.payments.find_one({
                "$or": [
                    {"invoice_id": inv.get("invoice_id")},
                    {"source_id": inv.get("invoice_id")},
                ]
            })
            if not payment:
                orphans["invoices_without_payments"].append({
                    "invoice_id": inv.get("invoice_id"),
                    "tenant_id": inv.get("tenant_id"),
                    "status": inv.get("status"),
                    "created_at": inv.get("created_at").isoformat() if isinstance(inv.get("created_at"), datetime) else str(inv.get("created_at", "")),
                })
    except Exception:
        pass

    # 2. Tickets without valid reservation
    try:
        tickets = await db.tickets.find({"status": "active"}).to_list(length=500)
        for ticket in tickets:
            res_id = ticket.get("reservation_id")
            if res_id:
                reservation = await db.reservations.find_one({"_id": res_id})
                if not reservation:
                    reservation = await db.reservations.find_one({"reservation_id": res_id})
                if not reservation:
                    orphans["tickets_without_reservation"].append({
                        "ticket_code": ticket.get("ticket_code"),
                        "reservation_id": res_id,
                        "tenant_id": ticket.get("tenant_id"),
                    })
    except Exception:
        pass

    # 3. Reservations without product
    try:
        reservations = await db.reservations.find().to_list(length=500)
        for res in reservations:
            product_id = res.get("product_id")
            if product_id:
                product = await db.products.find_one({"_id": product_id})
                if not product:
                    orphans["reservations_without_product"].append({
                        "reservation_id": str(res.get("_id")),
                        "product_id": product_id,
                        "organization_id": res.get("organization_id"),
                    })
    except Exception:
        pass

    total_orphans = sum(len(v) for v in orphans.values())
    return {
        "total_orphans": total_orphans,
        "orphans": orphans,
        "checked_at": now_utc().isoformat(),
    }
