from __future__ import annotations

import json
from collections import Counter

from app.bootstrap.route_inventory import build_route_inventory, write_route_inventory_json
from server import app


def test_auth_routes_are_not_registered_twice() -> None:
    route_counts = Counter()
    for route in app.routes:
        methods = sorted(method for method in (getattr(route, "methods", set()) or set()) if method not in {"HEAD", "OPTIONS"})
        path = getattr(route, "path", None)
        if not path or not path.startswith("/api/auth/"):
            continue
        for method in methods:
            route_counts[(method, path)] += 1

    assert route_counts[("POST", "/api/auth/login")] == 1
    assert route_counts[("POST", "/api/auth/logout")] == 1
    assert route_counts[("GET", "/api/auth/me")] == 1


def test_route_inventory_has_required_fields_and_stable_sorting(tmp_path) -> None:
    inventory = build_route_inventory(app)
    assert inventory == sorted(inventory, key=lambda item: (item["path"], item["method"], item["source"]))
    assert inventory

    sample = inventory[0]
    assert {
        "path",
        "method",
        "source",
        "current_namespace",
        "target_namespace",
        "legacy_or_v1",
        "compat_required",
        "risk_level",
        "owner",
    }.issubset(sample.keys())

    first = tmp_path / "inventory-a.json"
    second = tmp_path / "inventory-b.json"
    write_route_inventory_json(app, first)
    write_route_inventory_json(app, second)
    assert first.read_text() == second.read_text()
    assert json.loads(first.read_text())


def test_mobile_v1_route_is_preserved_in_inventory() -> None:
    inventory = build_route_inventory(app)
    mobile_me = next(
        item
        for item in inventory
        if item["path"] == "/api/v1/mobile/auth/me" and item["method"] == "GET"
    )
    assert mobile_me["legacy_or_v1"] == "v1"
    assert mobile_me["compat_required"] is False
    assert mobile_me["target_namespace"] == "/api/v1/mobile"