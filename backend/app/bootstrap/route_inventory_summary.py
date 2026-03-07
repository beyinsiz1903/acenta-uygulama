from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

DEFAULT_ROUTE_INVENTORY_SUMMARY_PATH = Path("/app/backend/app/bootstrap/route_inventory_summary.json")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _inventory_hash(inventory: list[dict[str, Any]]) -> str:
    payload = json.dumps(inventory, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def summarize_route_inventory(
    inventory: list[dict[str, Any]],
    *,
    environment: str | None = None,
    inventory_path: str | Path | None = None,
    runtime_name: str = "api",
) -> dict[str, Any]:
    route_count = len(inventory)
    v1_count = sum(1 for entry in inventory if entry["legacy_or_v1"] == "v1")
    legacy_count = route_count - v1_count
    compat_required_count = sum(1 for entry in inventory if entry["compat_required"])

    return {
        "environment": environment or os.environ.get("APP_ENV_NAME") or os.environ.get("ENV") or "unknown",
        "generated_at": _utc_now_iso(),
        "inventory_hash": _inventory_hash(inventory),
        "inventory_path": str(inventory_path) if inventory_path else None,
        "legacy_count": legacy_count,
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
    runtime_name: str = "api",
) -> Path:
    target_path = Path(destination)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    payload = summarize_route_inventory(
        inventory,
        environment=environment,
        inventory_path=inventory_path,
        runtime_name=runtime_name,
    )
    target_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
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