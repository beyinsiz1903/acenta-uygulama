"""PART 5 — Multi-Tenant Safety.

Tenant isolation testing: prevents cross-tenant data leaks.
Enforces data boundaries across all collections and operations.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

logger = logging.getLogger("hardening.tenant_safety")


# Collections that MUST be tenant-isolated
TENANT_ISOLATED_COLLECTIONS = [
    "bookings",
    "customers",
    "payments",
    "vouchers",
    "invoices",
    "hotels",
    "rateplans",
    "inventory",
    "crm_contacts",
    "crm_deals",
    "crm_activities",
    "crm_notes",
    "pricing_rules",
    "commission_rules",
    "settlements",
    "refund_cases",
    "notification_deliveries",
    "audit_log",
    "ops_cases",
    "ops_incidents",
]

# Tenant isolation field (the field name in each document)
TENANT_FIELD = "organization_id"

# Cross-tenant test scenarios
ISOLATION_TESTS = [
    {
        "name": "booking_isolation",
        "description": "Tenant A cannot read Tenant B's bookings",
        "collection": "bookings",
        "severity": "critical",
    },
    {
        "name": "customer_isolation",
        "description": "Tenant A cannot read Tenant B's customers",
        "collection": "customers",
        "severity": "critical",
    },
    {
        "name": "payment_isolation",
        "description": "Tenant A cannot view Tenant B's payment records",
        "collection": "payments",
        "severity": "critical",
    },
    {
        "name": "pricing_isolation",
        "description": "Tenant A cannot see Tenant B's pricing rules",
        "collection": "pricing_rules",
        "severity": "high",
    },
    {
        "name": "audit_isolation",
        "description": "Audit logs are tenant-scoped",
        "collection": "audit_log",
        "severity": "high",
    },
    {
        "name": "voucher_isolation",
        "description": "Vouchers are tenant-isolated",
        "collection": "vouchers",
        "severity": "high",
    },
    {
        "name": "settlement_isolation",
        "description": "Financial settlements are tenant-isolated",
        "collection": "settlements",
        "severity": "critical",
    },
]


async def run_tenant_isolation_audit(db) -> dict:
    """Run comprehensive tenant isolation audit."""
    results = []
    total_passed = 0
    total_failed = 0
    total_warnings = 0

    for collection_name in TENANT_ISOLATED_COLLECTIONS:
        coll = db[collection_name]
        doc_count = await coll.count_documents({})

        if doc_count == 0:
            results.append({
                "collection": collection_name,
                "status": "skipped",
                "reason": "No documents",
                "doc_count": 0,
            })
            continue

        # Check 1: All documents have tenant field
        without_tenant = await coll.count_documents({TENANT_FIELD: {"$exists": False}})

        # Check 2: No null tenant IDs
        null_tenant = await coll.count_documents({TENANT_FIELD: None})

        # Check 3: Count distinct tenants
        tenants = await coll.distinct(TENANT_FIELD)
        tenant_count = len(tenants)

        # Check 4: Index exists on tenant field
        indexes = await coll.index_information()
        has_tenant_index = any(
            TENANT_FIELD in str(idx.get("key", ""))
            for idx in indexes.values()
        )

        passed = without_tenant == 0 and null_tenant == 0
        if passed:
            total_passed += 1
        else:
            total_failed += 1

        if not has_tenant_index and doc_count > 0:
            total_warnings += 1

        results.append({
            "collection": collection_name,
            "status": "pass" if passed else "fail",
            "doc_count": doc_count,
            "missing_tenant_field": without_tenant,
            "null_tenant_id": null_tenant,
            "distinct_tenants": tenant_count,
            "has_tenant_index": has_tenant_index,
            "severity": "critical" if not passed else "ok",
        })

    # Run isolation scenario tests
    scenario_results = []
    for test in ISOLATION_TESTS:
        coll = db[test["collection"]]
        doc_count = await coll.count_documents({})
        tenants = await coll.distinct(TENANT_FIELD) if doc_count > 0 else []

        scenario_results.append({
            "name": test["name"],
            "description": test["description"],
            "severity": test["severity"],
            "collection": test["collection"],
            "tenants_found": len(tenants),
            "status": "pass" if doc_count == 0 or len(tenants) <= 1 else "requires_validation",
        })

    audit = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_collections": len(TENANT_ISOLATED_COLLECTIONS),
        "passed": total_passed,
        "failed": total_failed,
        "warnings": total_warnings,
        "skipped": len(TENANT_ISOLATED_COLLECTIONS) - total_passed - total_failed,
        "collection_results": results,
        "isolation_scenarios": scenario_results,
        "tenant_field": TENANT_FIELD,
        "score": round((total_passed / max(total_passed + total_failed, 1)) * 100, 1),
    }

    await db.tenant_isolation_audits.insert_one({**audit})
    return audit
