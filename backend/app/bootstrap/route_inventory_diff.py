from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.bootstrap.v1_manifest import derive_target_path


def load_route_inventory(source: str | Path) -> list[dict[str, Any]]:
    return json.loads(Path(source).read_text())


def _route_key(entry: dict[str, Any]) -> tuple[str, str]:
    return entry["method"], entry["path"]


def _expected_v1_alias(entry: dict[str, Any]) -> tuple[str, str] | None:
    if entry.get("legacy_or_v1") != "legacy":
        return None

    target_path = derive_target_path(entry["path"], entry.get("source", "unknown"))
    if target_path == entry["path"] or not target_path.startswith("/api/v1/"):
        return None

    return entry["method"], target_path


def build_route_inventory_diff(
    previous_inventory: list[dict[str, Any]],
    current_inventory: list[dict[str, Any]],
) -> dict[str, Any]:
    previous_map = {_route_key(entry): entry for entry in previous_inventory}
    current_map = {_route_key(entry): entry for entry in current_inventory}

    added_keys = sorted(set(current_map) - set(previous_map), key=lambda item: (item[1], item[0]))
    removed_keys = sorted(set(previous_map) - set(current_map), key=lambda item: (item[1], item[0]))

    current_v1_route_count = sum(1 for entry in current_inventory if entry["legacy_or_v1"] == "v1")
    new_v1_route_count = sum(
        1
        for key in added_keys
        if current_map[key]["legacy_or_v1"] == "v1"
    )
    compat_required_route_count = sum(1 for entry in current_inventory if entry["compat_required"])
    legacy_only_route_count = sum(
        1
        for entry in current_inventory
        if entry["legacy_or_v1"] == "legacy"
        and (_expected_v1_alias(entry) is None or _expected_v1_alias(entry) not in current_map)
    )

    return {
        "summary": {
            "previous_route_count": len(previous_inventory),
            "current_route_count": len(current_inventory),
            "added_route_count": len(added_keys),
            "removed_route_count": len(removed_keys),
            "current_v1_route_count": current_v1_route_count,
            "new_v1_route_count": new_v1_route_count,
            "legacy_only_route_count": legacy_only_route_count,
            "compat_required_route_count": compat_required_route_count,
        },
        "added_paths": [
            {
                "method": method,
                "path": path,
                "legacy_or_v1": current_map[(method, path)]["legacy_or_v1"],
            }
            for method, path in added_keys
        ],
        "removed_paths": [
            {
                "method": method,
                "path": path,
                "legacy_or_v1": previous_map[(method, path)]["legacy_or_v1"],
            }
            for method, path in removed_keys
        ],
    }


def diff_route_inventory_files(previous_source: str | Path, current_source: str | Path) -> dict[str, Any]:
    previous_inventory = load_route_inventory(previous_source)
    current_inventory = load_route_inventory(current_source)
    return build_route_inventory_diff(previous_inventory, current_inventory)