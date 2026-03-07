from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.routing import APIRoute

from app.bootstrap.v1_manifest import classify_route


def build_route_inventory(app: FastAPI) -> list[dict[str, Any]]:
    inventory: list[dict[str, Any]] = []

    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue

        source_module = getattr(route.endpoint, "__module__", "unknown")
        methods = sorted(method for method in (route.methods or set()) if method not in {"HEAD", "OPTIONS"})
        route_meta = classify_route(route.path, source_module)
        version_status = "v1" if route.path.startswith("/api/v1/") else "legacy"
        compat_required = version_status == "legacy" and route_meta.target_namespace != route_meta.current_namespace

        for method in methods:
            inventory.append(
                {
                    "compat_required": compat_required,
                    "current_namespace": route_meta.current_namespace,
                    "legacy_or_v1": version_status,
                    "method": method,
                    "owner": route_meta.owner,
                    "path": route.path,
                    "risk_level": route_meta.risk_level,
                    "source": source_module,
                    "target_namespace": route_meta.target_namespace,
                }
            )

    inventory.sort(key=lambda item: (item["path"], item["method"], item["source"]))
    return inventory


def write_route_inventory_json(app: FastAPI, destination: str | Path) -> Path:
    target_path = Path(destination)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    payload = build_route_inventory(app)
    target_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return target_path