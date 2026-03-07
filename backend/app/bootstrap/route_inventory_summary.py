from __future__ import annotations

import hashlib
import json
import math
import os
from collections import OrderedDict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from app.bootstrap.route_inventory_diff import build_route_inventory_diff
from app.bootstrap.v1_manifest import derive_target_path

DEFAULT_ROUTE_INVENTORY_SUMMARY_PATH = Path("/app/backend/app/bootstrap/route_inventory_summary.json")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _inventory_hash(inventory: list[dict[str, Any]]) -> str:
    payload = json.dumps(inventory, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _namespace_bucket(entry: Mapping[str, Any]) -> str:
    path = str(entry.get("path", ""))
    current_namespace = str(entry.get("current_namespace", ""))
    target_namespace = str(entry.get("target_namespace", ""))
    owner = str(entry.get("owner", ""))

    if path.startswith("/api/v1/mobile") or current_namespace == "/api/v1/mobile" or target_namespace == "/api/v1/mobile":
        return "mobile"
    if current_namespace.startswith("/api/auth") or target_namespace.startswith("/api/v1/auth") or owner == "auth":
        return "auth"
    if current_namespace.startswith("/api/admin") or target_namespace.startswith("/api/v1/admin") or owner == "admin":
        return "admin"
    if (
        current_namespace.startswith("/api/public")
        or current_namespace in {"/web", "/storefront"}
        or target_namespace.startswith("/api/v1/public")
        or owner == "public"
    ):
        return "public"
    if (
        current_namespace in {"/api/health", "/api/system", "/api/settings", "/api/dashboard", "/api/notifications", "/api"}
        or target_namespace.startswith("/api/v1/health")
        or target_namespace.startswith("/api/v1/system")
        or target_namespace.startswith("/api/v1/settings")
        or owner == "system"
    ):
        return "system"
    if (
        current_namespace.startswith("/api/tenant")
        or current_namespace.startswith("/api/agency")
        or current_namespace.startswith("/api/b2b")
        or target_namespace.startswith("/api/v1/tenant")
        or target_namespace.startswith("/api/v1/agency")
        or target_namespace.startswith("/api/v1/b2b")
        or owner in {"tenant", "agency", "b2b"}
    ):
        return "tenant"
    if (
        current_namespace.startswith("/api/finance")
        or current_namespace.startswith("/api/payments")
        or current_namespace.startswith("/api/pricing")
        or target_namespace.startswith("/api/v1/finance")
        or owner in {"finance", "payments", "pricing"}
    ):
        return "finance"
    return "misc"


def build_namespace_breakdown(inventory: list[dict[str, Any]]) -> dict[str, int]:
    ordered_buckets = ("auth", "admin", "public", "system", "mobile", "tenant", "finance", "misc")
    counts = {bucket: 0 for bucket in ordered_buckets}
    for entry in inventory:
        counts[_namespace_bucket(entry)] += 1
    return OrderedDict((bucket, counts[bucket]) for bucket in ordered_buckets)


def _route_key(entry: Mapping[str, Any]) -> tuple[str, str]:
    return str(entry.get("method", "")), str(entry.get("path", ""))


def _expected_v1_alias(entry: Mapping[str, Any]) -> tuple[str, str] | None:
    if entry.get("legacy_or_v1") != "legacy":
        return None

    path = str(entry.get("path", ""))
    source = str(entry.get("source", "unknown"))
    target_path = derive_target_path(path, source)
    if target_path == path or not target_path.startswith("/api/v1/"):
        return None
    return str(entry.get("method", "")), target_path


def build_domain_v1_progress(inventory: list[dict[str, Any]]) -> dict[str, dict[str, int | float]]:
    ordered_buckets = ("auth", "admin", "public", "system", "mobile", "tenant", "finance", "misc")
    inventory_map = {_route_key(entry): entry for entry in inventory}
    target_routes = {bucket: set() for bucket in ordered_buckets}
    migrated_routes = {bucket: set() for bucket in ordered_buckets}

    for entry in inventory:
        bucket = _namespace_bucket(entry)
        route_key = _route_key(entry)

        if entry.get("legacy_or_v1") == "v1":
            target_routes[bucket].add(route_key)
            migrated_routes[bucket].add(route_key)
            continue

        expected_alias = _expected_v1_alias(entry)
        if expected_alias is None:
            target_routes[bucket].add(route_key)
            continue

        target_routes[bucket].add(expected_alias)
        if expected_alias in inventory_map:
            migrated_routes[bucket].add(expected_alias)

    return OrderedDict(
        (
            bucket,
            {
                "target_route_count": len(target_routes[bucket]),
                "migrated_v1_route_count": len(migrated_routes[bucket]),
                "remaining_route_count": max(len(target_routes[bucket]) - len(migrated_routes[bucket]), 0),
                "v1_migration_percent": 100.0
                if not target_routes[bucket]
                else round((len(migrated_routes[bucket]) / len(target_routes[bucket])) * 100, 2),
            },
        )
        for bucket in ordered_buckets
    )


def build_migration_velocity(
    inventory: list[dict[str, Any]],
    *,
    previous_inventory: list[dict[str, Any]] | None = None,
    routes_remaining: int,
) -> dict[str, int]:
    routes_migrated_this_pr = 0
    if previous_inventory is not None:
        diff_report = build_route_inventory_diff(previous_inventory, inventory)
        routes_migrated_this_pr = int(diff_report["summary"]["new_v1_route_count"])

    estimated_prs_remaining = 0 if routes_remaining <= 0 else math.ceil(routes_remaining / 60)
    return OrderedDict(
        (
            ("routes_migrated_this_pr", routes_migrated_this_pr),
            ("routes_remaining", routes_remaining),
            ("estimated_prs_remaining", estimated_prs_remaining),
        )
    )


def summarize_route_inventory(
    inventory: list[dict[str, Any]],
    *,
    environment: str | None = None,
    inventory_path: str | Path | None = None,
    previous_inventory: list[dict[str, Any]] | None = None,
    runtime_name: str = "api",
) -> dict[str, Any]:
    route_count = len(inventory)
    v1_count = sum(1 for entry in inventory if entry["legacy_or_v1"] == "v1")
    legacy_count = route_count - v1_count
    compat_required_count = sum(1 for entry in inventory if entry["compat_required"])
    namespace_breakdown = build_namespace_breakdown(inventory)
    domain_v1_progress = build_domain_v1_progress(inventory)
    migration_velocity = build_migration_velocity(
        inventory,
        previous_inventory=previous_inventory,
        routes_remaining=compat_required_count,
    )

    return {
        "environment": environment or os.environ.get("APP_ENV_NAME") or os.environ.get("ENV") or "unknown",
        "domain_v1_progress": domain_v1_progress,
        "generated_at": _utc_now_iso(),
        "inventory_hash": _inventory_hash(inventory),
        "inventory_path": str(inventory_path) if inventory_path else None,
        "legacy_routes_remaining": legacy_count,
        "legacy_count": legacy_count,
        "migration_velocity": migration_velocity,
        "namespaces": namespace_breakdown,
        "route_count": route_count,
        "runtime_name": runtime_name,
        "v1_count": v1_count,
        "compat_required_count": compat_required_count,
    }


def write_route_inventory_summary_json(
    inventory: list[dict[str, Any]],
    destination: str | Path,
    *,
    environment: str | None = None,
    inventory_path: str | Path | None = None,
    previous_inventory: list[dict[str, Any]] | None = None,
    runtime_name: str = "api",
) -> Path:
    target_path = Path(destination)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    payload = summarize_route_inventory(
        inventory,
        environment=environment,
        inventory_path=inventory_path,
        previous_inventory=previous_inventory,
        runtime_name=runtime_name,
    )
    target_path.write_text(json.dumps(payload, indent=2) + "\n")
    return target_path


def load_route_inventory_summary(source: str | Path) -> dict[str, Any]:
    return json.loads(Path(source).read_text())


def build_route_inventory_parity_report(
    summaries: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    environment_names = list(summaries.keys())
    counts = {
        name: {
            "route_count": int(summary.get("route_count", 0)),
            "v1_count": int(summary.get("v1_count", 0)),
            "legacy_count": int(summary.get("legacy_count", 0)),
        }
        for name, summary in summaries.items()
    }
    hashes = {name: str(summary.get("inventory_hash", "")) for name, summary in summaries.items()}

    baseline_name = environment_names[0] if environment_names else None
    baseline_counts = counts.get(baseline_name, {})
    baseline_hash = hashes.get(baseline_name, "")
    mismatches: list[dict[str, Any]] = []

    for name in environment_names[1:]:
        if counts[name] != baseline_counts:
            mismatches.append(
                {
                    "environment": name,
                    "kind": "counts",
                    "expected": baseline_counts,
                    "actual": counts[name],
                }
            )
        if hashes[name] != baseline_hash:
            mismatches.append(
                {
                    "environment": name,
                    "kind": "inventory_hash",
                    "expected": baseline_hash,
                    "actual": hashes[name],
                }
            )

    return {
        "all_match": not mismatches,
        "baseline_environment": baseline_name,
        "counts": counts,
        "environment_names": environment_names,
        "inventory_hashes": hashes,
        "mismatches": mismatches,
    }
