from __future__ import annotations

from app.bootstrap.route_inventory import build_route_inventory
from app.bootstrap.route_inventory_diff import build_route_inventory_diff
from server import app


def _inventory_map() -> dict[tuple[str, str], dict]:
    inventory = build_route_inventory(app)
    return {(entry["method"], entry["path"]): entry for entry in inventory}


def test_low_risk_v1_aliases_and_legacy_routes_coexist() -> None:
    inventory = _inventory_map()

    expected_pairs = {
        ("GET", "/api/health"):
            ("legacy", "/api/v1/health"),
        ("GET", "/api/v1/health"):
            ("v1", "/api/v1/health"),
        ("GET", "/api/system/ping"):
            ("legacy", "/api/v1/system"),
        ("GET", "/api/v1/system/ping"):
            ("v1", "/api/v1/system"),
        ("GET", "/api/system/health-dashboard"):
            ("legacy", "/api/v1/system"),
        ("GET", "/api/v1/system/health-dashboard"):
            ("v1", "/api/v1/system"),
        ("GET", "/api/system/prometheus"):
            ("legacy", "/api/v1/system"),
        ("GET", "/api/v1/system/prometheus"):
            ("v1", "/api/v1/system"),
        ("GET", "/api/public/theme"):
            ("legacy", "/api/v1/public"),
        ("GET", "/api/v1/public/theme"):
            ("v1", "/api/v1/public"),
        ("GET", "/api/admin/theme"):
            ("legacy", "/api/v1/admin"),
        ("GET", "/api/v1/admin/theme"):
            ("v1", "/api/v1/admin"),
        ("PUT", "/api/admin/theme"):
            ("legacy", "/api/v1/admin"),
        ("PUT", "/api/v1/admin/theme"):
            ("v1", "/api/v1/admin"),
        ("GET", "/api/public/cms/pages"):
            ("legacy", "/api/v1/public"),
        ("GET", "/api/v1/public/cms/pages"):
            ("v1", "/api/v1/public"),
        ("GET", "/api/public/cms/pages/{slug}"):
            ("legacy", "/api/v1/public"),
        ("GET", "/api/v1/public/cms/pages/{slug}"):
            ("v1", "/api/v1/public"),
        ("GET", "/api/public/campaigns"):
            ("legacy", "/api/v1/public"),
        ("GET", "/api/v1/public/campaigns"):
            ("v1", "/api/v1/public"),
        ("GET", "/api/public/campaigns/{slug}"):
            ("legacy", "/api/v1/public"),
        ("GET", "/api/v1/public/campaigns/{slug}"):
            ("v1", "/api/v1/public"),
    }

    for key, (namespace_version, target_namespace) in expected_pairs.items():
        entry = inventory.get(key)
        assert entry is not None, f"missing route inventory entry for {key}"
        assert entry["legacy_or_v1"] == namespace_version
        assert entry["target_namespace"] == target_namespace


def test_route_inventory_diff_reports_new_v1_aliases() -> None:
    current_inventory = build_route_inventory(app)
    previous_inventory = [
        entry
        for entry in current_inventory
        if entry["path"]
        not in {
            "/api/v1/health",
            "/api/v1/system/ping",
            "/api/v1/system/health-dashboard",
            "/api/v1/system/prometheus",
            "/api/v1/public/theme",
            "/api/v1/admin/theme",
            "/api/v1/public/cms/pages",
            "/api/v1/public/cms/pages/{slug}",
            "/api/v1/public/campaigns",
            "/api/v1/public/campaigns/{slug}",
        }
    ]

    report = build_route_inventory_diff(previous_inventory, current_inventory)

    assert report["summary"]["new_v1_route_count"] == 11
    assert report["summary"]["added_route_count"] == 11
    assert report["summary"]["compat_required_route_count"] > 0
    assert report["summary"]["legacy_only_route_count"] > 0
    assert report["removed_paths"] == []

    added_paths = {(item["method"], item["path"]) for item in report["added_paths"]}
    assert ("GET", "/api/v1/health") in added_paths
    assert ("GET", "/api/v1/public/theme") in added_paths
    assert ("PUT", "/api/v1/admin/theme") in added_paths