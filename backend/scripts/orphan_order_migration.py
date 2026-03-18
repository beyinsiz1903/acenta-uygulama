"""
Orphan Order Organization Recovery Script v1

Two-phase, evidence-based migration for orders missing organization_id.
Phase 1 (analyze): Produces a report with match strategy & confidence per order.
Phase 2 (apply):   Updates only high-confidence matches; quarantines the rest.

Usage:
    python scripts/orphan_order_migration.py analyze
    python scripts/orphan_order_migration.py apply --threshold 0.9
    python scripts/orphan_order_migration.py rollback --batch-id <BATCH_ID>

Safety guarantees:
    - Only updates documents where organization_id is missing (optimistic guard)
    - Every change logged to tenant_migration_audit collection
    - Rollback by batch_id supported
    - Conflicting evidence → quarantine, never auto-assign
"""
from __future__ import annotations

import argparse
import json
import sys
import uuid
from collections import Counter
from datetime import datetime, timezone
from typing import Any, Optional

import pymongo
from bson import ObjectId

SCRIPT_NAME = "orphan_recovery_script_v1"
AUDIT_COLLECTION = "tenant_migration_audit"
QUARANTINE_COLLECTION = "tenant_migration_quarantine"

# Confidence thresholds (aligned with CTO specification)
CONFIDENCE = {
    "agency_direct": 1.0,          # booking/agency org match → exact
    "tenant_direct": 0.95,         # tenant collection cross-ref → high
    "invoice_chain": 0.95,         # invoice/payment chain exact match
    "order_financial_summary_agency": 0.9,  # financial summary agency match
    "demo_seed_single_org": 0.9,   # demo seed in single-org env → high
    "customer_exact_match": 0.9,   # customer collection org match
    "created_by_user_org": 0.7,    # user who created → medium
    "test_artifact_single_org": 0.7,  # test data in single-org → medium
    "legacy_org_id_single_org": 0.4,  # legacy text/domain inference → low
    "no_evidence": 0.0,
}

ALLOWED_AUTO_STRATEGIES = {
    "agency_direct",
    "tenant_direct",
    "invoice_chain",
    "order_financial_summary_agency",
    "demo_seed_single_org",
    "customer_exact_match",
}


class OrphanAnalyzer:
    """Analyze orphaned orders and propose organization assignments."""

    def __init__(self, db):
        self.db = db
        self._org_cache: dict[str, str] = {}
        self._agency_org_map: dict[str, str] = {}
        self._tenant_org_map: dict[str, str] = {}
        self._user_org_map: dict[str, str] = {}
        self._all_org_ids: list[str] = []

    def warm_caches(self):
        """Pre-load lookup tables from reference collections."""
        # Organizations
        for org in self.db.organizations.find({}, {"_id": 1}):
            self._all_org_ids.append(str(org["_id"]))

        # Agencies → organization_id
        for ag in self.db.agencies.find(
            {"organization_id": {"$exists": True, "$ne": None, "$ne": ""}},
            {"_id": 1, "organization_id": 1, "name": 1},
        ):
            self._agency_org_map[str(ag["_id"])] = ag["organization_id"]
            if ag.get("name"):
                self._agency_org_map[ag["name"]] = ag["organization_id"]

        # Tenants → organization_id
        for t in self.db.tenants.find(
            {"organization_id": {"$exists": True, "$ne": None, "$ne": ""}},
            {"_id": 1, "organization_id": 1, "slug": 1},
        ):
            self._tenant_org_map[str(t["_id"])] = t["organization_id"]
            if t.get("slug"):
                self._tenant_org_map[t["slug"]] = t["organization_id"]

        # Users → organization_id
        for u in self.db.users.find(
            {"organization_id": {"$exists": True, "$ne": None, "$ne": ""}},
            {"_id": 1, "email": 1, "organization_id": 1},
        ):
            self._user_org_map[str(u["_id"])] = u["organization_id"]
            if u.get("email"):
                self._user_org_map[u["email"]] = u["organization_id"]

        print(f"  Caches warmed: {len(self._all_org_ids)} orgs, "
              f"{len(self._agency_org_map)} agency mappings, "
              f"{len(self._tenant_org_map)} tenant mappings, "
              f"{len(self._user_org_map)} user mappings")

    def find_orphans(self) -> list[dict]:
        """Find all orders missing organization_id."""
        return list(self.db.orders.find({
            "$or": [
                {"organization_id": {"$exists": False}},
                {"organization_id": None},
                {"organization_id": ""},
            ]
        }))

    def analyze_order(self, order: dict) -> dict[str, Any]:
        """Analyze a single orphan order and return a match proposal."""
        order_id = order.get("order_id") or str(order["_id"])
        raw_id = order["_id"]  # Keep actual type (ObjectId or str)
        candidates: list[dict] = []

        # Strategy 1: agency_id → agencies.organization_id
        agency_id = order.get("agency_id")
        if agency_id and agency_id in self._agency_org_map:
            candidates.append({
                "strategy": "agency_direct",
                "confidence": CONFIDENCE["agency_direct"],
                "organization_id": self._agency_org_map[agency_id],
                "evidence": f"agency_id={agency_id} found in agencies collection",
            })

        # Strategy 2: tenant_id → tenants.organization_id
        tenant_id = order.get("tenant_id")
        if tenant_id and tenant_id in self._tenant_org_map:
            candidates.append({
                "strategy": "tenant_direct",
                "confidence": CONFIDENCE["tenant_direct"],
                "organization_id": self._tenant_org_map[tenant_id],
                "evidence": f"tenant_id={tenant_id} found in tenants collection",
            })

        # Strategy 3: order_financial_summaries cross-reference
        ofs = self.db.order_financial_summaries.find_one(
            {"order_id": order_id},
            {"_id": 0, "agency_id": 1, "tenant_id": 1},
        )
        if ofs:
            ofs_agency = ofs.get("agency_id")
            if ofs_agency and ofs_agency in self._agency_org_map:
                candidates.append({
                    "strategy": "order_financial_summary_agency",
                    "confidence": CONFIDENCE["order_financial_summary_agency"],
                    "organization_id": self._agency_org_map[ofs_agency],
                    "evidence": f"order_financial_summaries.agency_id={ofs_agency}",
                })

        # Strategy 4: invoice chain (source_id = order_id or booking linked to order)
        invoice = self.db.invoices.find_one(
            {"source_id": order_id, "organization_id": {"$exists": True, "$ne": None, "$ne": ""}},
            {"_id": 0, "organization_id": 1, "invoice_id": 1},
        )
        if invoice:
            candidates.append({
                "strategy": "invoice_chain",
                "confidence": 0.95,
                "organization_id": invoice["organization_id"],
                "evidence": f"invoice {invoice['invoice_id']} references this order",
            })

        # Strategy 5: created_by → users.organization_id
        created_by = order.get("created_by")
        if created_by and created_by in self._user_org_map:
            candidates.append({
                "strategy": "created_by_user_org",
                "confidence": CONFIDENCE["created_by_user_org"],
                "organization_id": self._user_org_map[created_by],
                "evidence": f"created_by={created_by} maps to user org",
            })

        # Strategy 6: demo_seed source + single org environment
        if order.get("source") == "demo_seed" and len(self._all_org_ids) == 1:
            candidates.append({
                "strategy": "demo_seed_single_org",
                "confidence": CONFIDENCE["demo_seed_single_org"],
                "organization_id": self._all_org_ids[0],
                "evidence": "source=demo_seed in single-org environment",
            })

        # Strategy 7: legacy org_id field + single org
        legacy_org_id = order.get("org_id")
        if legacy_org_id and len(self._all_org_ids) == 1:
            candidates.append({
                "strategy": "legacy_org_id_single_org",
                "confidence": CONFIDENCE["legacy_org_id_single_org"],
                "organization_id": self._all_org_ids[0],
                "evidence": f"legacy org_id={legacy_org_id} in single-org environment",
            })

        # Strategy 8: test artifact — TEST_ prefix in tenant_id, single org
        if tenant_id and str(tenant_id).startswith("TEST_") and len(self._all_org_ids) == 1:
            candidates.append({
                "strategy": "test_artifact_single_org",
                "confidence": CONFIDENCE["test_artifact_single_org"],
                "organization_id": self._all_org_ids[0],
                "evidence": f"test artifact tenant_id={tenant_id} in single-org env",
            })

        return self._resolve_candidates(order, candidates, raw_id)

    def _resolve_candidates(self, order: dict, candidates: list[dict], raw_id: Any) -> dict[str, Any]:
        """Resolve candidate list into a single proposal.

        Decision matrix:
          - All evidence agrees + high-confidence strategy → auto_fix
          - All evidence agrees but only weak signals → manual_review
          - Conflicting org evidence → quarantine (never auto-assign)
        """
        order_id = order.get("order_id") or str(order["_id"])
        mongo_id = raw_id  # preserve actual ObjectId / str

        if not candidates:
            return {
                "order_id": order_id,
                "mongo_id": mongo_id,
                "resolution": "unresolved",
                "proposed_organization_id": None,
                "match_strategy": "no_evidence",
                "confidence_score": 0.0,
                "candidates": [],
                "reason": "No evidence found for any organization",
            }

        # Check for conflicting org proposals
        unique_orgs = set(c["organization_id"] for c in candidates)

        if len(unique_orgs) > 1:
            # Conflicting evidence — quarantine, NEVER auto-assign
            return {
                "order_id": order_id,
                "mongo_id": mongo_id,
                "resolution": "quarantine",
                "proposed_organization_id": None,
                "match_strategy": "conflicting_evidence",
                "confidence_score": 0.0,
                "candidates": candidates,
                "reason": f"Conflicting orgs: {unique_orgs}",
            }

        # All evidence points to same org
        best = max(candidates, key=lambda c: c["confidence"])

        # Check if at least one candidate uses a high-confidence strategy
        has_strong_signal = any(
            c["strategy"] in ALLOWED_AUTO_STRATEGIES for c in candidates
        )

        if has_strong_signal:
            resolution = "auto_fix"
            reason = f"All {len(candidates)} evidence(s) agree on org (strong signal)"
        else:
            resolution = "manual_review"
            reason = f"All {len(candidates)} evidence(s) agree but only weak signals"

        return {
            "order_id": order_id,
            "mongo_id": mongo_id,
            "resolution": resolution,
            "proposed_organization_id": best["organization_id"],
            "match_strategy": best["strategy"],
            "confidence_score": best["confidence"],
            "candidates": candidates,
            "reason": reason,
        }


class OrphanMigrator:
    """Apply analyzed proposals to the database."""

    def __init__(self, db, threshold: float = 0.9):
        self.db = db
        self.threshold = threshold
        self.batch_id = f"batch_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"

    def apply(self, proposals: list[dict]) -> dict[str, Any]:
        """Apply proposals that meet the confidence threshold and strategy filter."""
        stats = {
            "applied": 0,
            "quarantined": 0,
            "manual_review": 0,
            "skipped": 0,
            "already_assigned": 0,
            "errors": 0,
        }

        for p in proposals:
            try:
                if p["resolution"] == "unresolved":
                    self._quarantine(p, reason="no_evidence")
                    stats["skipped"] += 1
                    continue

                if p["resolution"] == "quarantine":
                    self._quarantine(p, reason="conflicting_evidence")
                    stats["quarantined"] += 1
                    continue

                if p["resolution"] == "manual_review":
                    self._quarantine(p, reason=f"manual_review: {p.get('reason', 'weak signals only')}")
                    stats["manual_review"] += 1
                    continue

                if p["confidence_score"] < self.threshold:
                    self._quarantine(p, reason=f"confidence {p['confidence_score']:.2f} < threshold {self.threshold}")
                    stats["quarantined"] += 1
                    continue

                if p["match_strategy"] not in ALLOWED_AUTO_STRATEGIES:
                    self._quarantine(p, reason=f"strategy {p['match_strategy']} not in auto-allow list")
                    stats["quarantined"] += 1
                    continue

                # Apply with optimistic guard
                result = self.db.orders.update_one(
                    {
                        "_id": p["mongo_id"],
                        "$or": [
                            {"organization_id": {"$exists": False}},
                            {"organization_id": None},
                            {"organization_id": ""},
                        ],
                    },
                    {
                        "$set": {
                            "organization_id": p["proposed_organization_id"],
                            "tenant_assignment_source": p["match_strategy"],
                            "tenant_assignment_confidence": p["confidence_score"],
                            "tenant_assignment_migrated_at": datetime.now(timezone.utc).isoformat(),
                            "tenant_assignment_migrated_by": SCRIPT_NAME,
                            "tenant_assignment_batch_id": self.batch_id,
                        }
                    },
                )

                if result.modified_count == 1:
                    self._audit_log(p, action="applied")
                    stats["applied"] += 1
                else:
                    stats["already_assigned"] += 1

            except Exception as e:
                print(f"  ERROR processing {p['order_id']}: {e}")
                stats["errors"] += 1

        return {"batch_id": self.batch_id, **stats}

    def _audit_log(self, proposal: dict, action: str):
        """Write audit record to tenant_migration_audit."""
        self.db[AUDIT_COLLECTION].insert_one({
            "batch_id": self.batch_id,
            "action": action,
            "order_id": proposal["order_id"],
            "mongo_id": str(proposal["mongo_id"]),
            "previous_organization_id": None,
            "new_organization_id": proposal["proposed_organization_id"],
            "match_strategy": proposal["match_strategy"],
            "confidence_score": proposal["confidence_score"],
            "evidence_chain": proposal.get("candidates", []),
            "migrated_by": SCRIPT_NAME,
            "migrated_at": datetime.now(timezone.utc),
        })

    def _quarantine(self, proposal: dict, reason: str):
        """Write quarantine record."""
        self.db[QUARANTINE_COLLECTION].update_one(
            {"order_id": proposal["order_id"]},
            {
                "$set": {
                    "mongo_id": str(proposal["mongo_id"]),
                    "resolution": proposal["resolution"],
                    "proposed_organization_id": proposal.get("proposed_organization_id"),
                    "match_strategy": proposal.get("match_strategy"),
                    "confidence_score": proposal.get("confidence_score", 0),
                    "candidates": proposal.get("candidates", []),
                    "reason": reason,
                    "batch_id": self.batch_id,
                    "quarantined_at": datetime.now(timezone.utc),
                    "reviewed": False,
                }
            },
            upsert=True,
        )


class OrphanRollback:
    """Rollback a specific migration batch."""

    def __init__(self, db):
        self.db = db

    def rollback(self, batch_id: str) -> dict[str, Any]:
        """Undo all changes from a migration batch."""
        audit_records = list(self.db[AUDIT_COLLECTION].find(
            {"batch_id": batch_id, "action": "applied"}
        ))

        if not audit_records:
            return {"status": "no_records", "batch_id": batch_id, "rolled_back": 0}

        rolled_back = 0
        errors = 0

        for record in audit_records:
            try:
                # Reconstruct proper _id type
                raw_id = record["mongo_id"]
                try:
                    query_id = ObjectId(raw_id)
                except Exception:
                    query_id = raw_id

                result = self.db.orders.update_one(
                    {
                        "_id": query_id,
                        "tenant_assignment_batch_id": batch_id,
                    },
                    {
                        "$unset": {
                            "organization_id": "",
                            "tenant_assignment_source": "",
                            "tenant_assignment_confidence": "",
                            "tenant_assignment_migrated_at": "",
                            "tenant_assignment_migrated_by": "",
                            "tenant_assignment_batch_id": "",
                        }
                    },
                )
                if result.modified_count == 1:
                    rolled_back += 1
                    # Mark audit record as rolled back
                    self.db[AUDIT_COLLECTION].update_one(
                        {"_id": record["_id"]},
                        {"$set": {
                            "rolled_back": True,
                            "rolled_back_at": datetime.now(timezone.utc),
                        }},
                    )
            except Exception as e:
                print(f"  ERROR rolling back {record['order_id']}: {e}")
                errors += 1

        # Clean quarantine records for this batch
        self.db[QUARANTINE_COLLECTION].delete_many({"batch_id": batch_id})

        return {
            "status": "rolled_back",
            "batch_id": batch_id,
            "rolled_back": rolled_back,
            "errors": errors,
            "total_records": len(audit_records),
        }


def run_analyze(db) -> list[dict]:
    """Phase 1: Analyze orphans and produce a report."""
    print("=" * 70)
    print("PHASE 1 — ORPHAN ORDER ANALYSIS (DRY RUN)")
    print("=" * 70)

    analyzer = OrphanAnalyzer(db)
    print("\nWarming lookup caches...")
    analyzer.warm_caches()

    orphans = analyzer.find_orphans()
    total = len(orphans)
    print(f"\nFound {total} orphaned orders\n")

    if total == 0:
        print("No orphaned orders found. Exiting.")
        return []

    proposals = []
    for order in orphans:
        proposal = analyzer.analyze_order(order)
        proposals.append(proposal)

    # Summary statistics
    resolutions = Counter(p["resolution"] for p in proposals)
    strategies = Counter(p["match_strategy"] for p in proposals)
    confidence_buckets = {
        "1.0 (exact)": sum(1 for p in proposals if p["confidence_score"] == 1.0),
        "0.9-0.99 (high)": sum(1 for p in proposals if 0.9 <= p["confidence_score"] < 1.0),
        "0.7-0.89 (medium)": sum(1 for p in proposals if 0.7 <= p["confidence_score"] < 0.9),
        "0.0-0.69 (low/none)": sum(1 for p in proposals if p["confidence_score"] < 0.7),
    }

    print("-" * 70)
    print("ANALYSIS REPORT")
    print("-" * 70)
    print(f"\nTotal orphaned orders: {total}")
    print(f"\nResolution breakdown:")
    for res, count in resolutions.items():
        symbol = {"auto_fix": "+", "quarantine": "!", "manual_review": "?", "unresolved": "x"}
        print(f"  [{symbol.get(res, ' ')}] {res}: {count}")

    print(f"\nMatch strategy breakdown:")
    for strat, count in strategies.items():
        print(f"  {strat}: {count}")

    print(f"\nConfidence distribution:")
    for bucket, count in confidence_buckets.items():
        print(f"  {bucket}: {count}")

    # At default threshold 0.9
    auto_apply_count = sum(
        1 for p in proposals
        if p["resolution"] == "auto_fix" and p["confidence_score"] >= 0.9
    )
    manual_review_count = total - auto_apply_count
    print(f"\nWith threshold >= 0.9:")
    print(f"  Auto-apply: {auto_apply_count}")
    print(f"  Manual review / quarantine: {manual_review_count}")

    # Write JSON report
    report_path = "/app/backend/scripts/orphan_analysis_report.json"
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_orphans": total,
        "resolutions": dict(resolutions),
        "strategies": dict(strategies),
        "confidence_distribution": confidence_buckets,
        "auto_apply_at_0_9": auto_apply_count,
        "manual_review": manual_review_count,
        "proposals": [
            {k: v for k, v in p.items() if k != "candidates"}
            for p in proposals
        ],
        "detailed_proposals": proposals,
    }
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2, default=str)
    print(f"\nFull report written to: {report_path}")

    return proposals


def run_apply(db, proposals: list[dict], threshold: float):
    """Phase 2: Apply high-confidence proposals."""
    print("\n" + "=" * 70)
    print(f"PHASE 2 — APPLY MIGRATION (threshold >= {threshold})")
    print("=" * 70)

    eligible = [
        p for p in proposals
        if p["resolution"] == "auto_fix" and p["confidence_score"] >= threshold
    ]
    print(f"\nEligible for auto-apply: {len(eligible)} / {len(proposals)}")

    if not eligible and not any(p["resolution"] in ("quarantine", "unresolved") for p in proposals):
        print("Nothing to apply or quarantine.")
        return

    migrator = OrphanMigrator(db, threshold=threshold)
    print(f"Batch ID: {migrator.batch_id}")

    result = migrator.apply(proposals)

    print(f"\nMigration results:")
    print(f"  Batch ID: {result['batch_id']}")
    print(f"  Applied: {result['applied']}")
    print(f"  Manual review: {result.get('manual_review', 0)}")
    print(f"  Quarantined: {result['quarantined']}")
    print(f"  Skipped (unresolved): {result['skipped']}")
    print(f"  Already assigned: {result['already_assigned']}")
    print(f"  Errors: {result['errors']}")

    # Verify: re-count orphans
    remaining = db.orders.count_documents({
        "$or": [
            {"organization_id": {"$exists": False}},
            {"organization_id": None},
            {"organization_id": ""},
        ]
    })
    print(f"\n  Remaining orphans: {remaining}")
    print(f"  Quarantine records: {db[QUARANTINE_COLLECTION].count_documents({'batch_id': result['batch_id']})}")
    print(f"  Audit records: {db[AUDIT_COLLECTION].count_documents({'batch_id': result['batch_id']})}")

    return result


def run_rollback(db, batch_id: str):
    """Rollback a migration batch."""
    print("\n" + "=" * 70)
    print(f"ROLLBACK — Batch: {batch_id}")
    print("=" * 70)

    rollback = OrphanRollback(db)
    result = rollback.rollback(batch_id)

    print(f"\nRollback results:")
    print(f"  Status: {result['status']}")
    print(f"  Rolled back: {result['rolled_back']} / {result['total_records']}")
    print(f"  Errors: {result['errors']}")

    return result


def run_health_check(db):
    """Post-migration health check."""
    print("\n" + "=" * 70)
    print("POST-MIGRATION HEALTH CHECK")
    print("=" * 70)

    total_orders = db.orders.count_documents({})
    orphans = db.orders.count_documents({
        "$or": [
            {"organization_id": {"$exists": False}},
            {"organization_id": None},
            {"organization_id": ""},
        ]
    })
    assigned = total_orders - orphans
    quarantined = db[QUARANTINE_COLLECTION].count_documents({"reviewed": False})
    audited = db[AUDIT_COLLECTION].count_documents({"action": "applied", "rolled_back": {"$ne": True}})

    print(f"\n  Total orders: {total_orders}")
    print(f"  With organization_id: {assigned}")
    print(f"  Orphaned (no org_id): {orphans}")
    print(f"  Quarantined (pending review): {quarantined}")
    print(f"  Audit log entries (active): {audited}")
    print(f"  Health score: {(assigned / total_orders * 100) if total_orders else 0:.1f}%")

    if orphans == 0 and quarantined == 0:
        print("\n  STATUS: FULLY RESOLVED")
    elif orphans == 0:
        print(f"\n  STATUS: AUTO-FIX COMPLETE — {quarantined} items awaiting manual review")
    else:
        print(f"\n  STATUS: {orphans} orphans remaining — review quarantine or lower threshold")


def main():
    parser = argparse.ArgumentParser(description="Orphan Order Organization Recovery")
    parser.add_argument("mode", choices=["analyze", "apply", "rollback", "health"],
                        help="Operation mode")
    parser.add_argument("--threshold", type=float, default=0.9,
                        help="Minimum confidence for auto-apply (default: 0.9)")
    parser.add_argument("--batch-id", type=str, default=None,
                        help="Batch ID for rollback")
    parser.add_argument("--mongo-url", type=str, default=None,
                        help="MongoDB URL (default: from MONGO_URL env)")
    parser.add_argument("--db-name", type=str, default=None,
                        help="Database name (default: from DB_NAME env)")

    args = parser.parse_args()

    import os
    mongo_url = args.mongo_url or os.environ.get("MONGO_URL", "mongodb://localhost:27017")
    db_name = args.db_name or os.environ.get("DB_NAME", "test_database")

    client = pymongo.MongoClient(mongo_url)
    db = client[db_name]

    print(f"Connected to {mongo_url}/{db_name}")

    if args.mode == "analyze":
        run_analyze(db)

    elif args.mode == "apply":
        proposals = run_analyze(db)
        if proposals:
            confirm = input(f"\nApply migration with threshold >= {args.threshold}? [y/N]: ")
            if confirm.lower() == "y":
                run_apply(db, proposals, args.threshold)
                run_health_check(db)
            else:
                print("Aborted.")

    elif args.mode == "rollback":
        if not args.batch_id:
            # List available batches
            batches = db[AUDIT_COLLECTION].distinct("batch_id")
            if batches:
                print("Available batches:")
                for b in batches:
                    count = db[AUDIT_COLLECTION].count_documents({"batch_id": b, "action": "applied"})
                    rolled = db[AUDIT_COLLECTION].count_documents({"batch_id": b, "rolled_back": True})
                    print(f"  {b}: {count} applied, {rolled} rolled back")
            else:
                print("No migration batches found.")
            return
        run_rollback(db, args.batch_id)
        run_health_check(db)

    elif args.mode == "health":
        run_health_check(db)


def run_non_interactive(mode: str = "analyze", threshold: float = 0.9) -> dict:
    """Non-interactive entry point for API/test usage."""
    import os
    mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
    db_name = os.environ.get("DB_NAME", "test_database")

    client = pymongo.MongoClient(mongo_url)
    db = client[db_name]

    if mode == "analyze":
        proposals = run_analyze(db)
        return {"proposals": proposals, "count": len(proposals)}

    elif mode == "apply":
        proposals = run_analyze(db)
        if proposals:
            result = run_apply(db, proposals, threshold)
            run_health_check(db)
            return result
        return {"status": "no_orphans"}

    elif mode == "health":
        run_health_check(db)
        total = db.orders.count_documents({})
        orphans = db.orders.count_documents({
            "$or": [
                {"organization_id": {"$exists": False}},
                {"organization_id": None},
                {"organization_id": ""},
            ]
        })
        return {
            "total_orders": total,
            "orphaned": orphans,
            "assigned": total - orphans,
            "health_score": round((total - orphans) / total * 100, 1) if total else 0,
        }

    return {"error": "unknown mode"}


if __name__ == "__main__":
    main()
