from __future__ import annotations

from app.bootstrap.route_inventory import build_route_inventory
from app.bootstrap.route_inventory_summary import (
    build_route_inventory_parity_report,
    summarize_route_inventory,
)
from server import app


def test_route_inventory_summary_counts_are_consistent() -> None:
    inventory = build_route_inventory(app)
    summary = summarize_route_inventory(inventory, environment="preview")

    assert summary["route_count"] == len(inventory)
    assert summary["v1_count"] == sum(1 for entry in inventory if entry["legacy_or_v1"] == "v1")
    assert summary["legacy_count"] == sum(1 for entry in inventory if entry["legacy_or_v1"] == "legacy")
    assert summary["route_count"] == summary["v1_count"] + summary["legacy_count"]
    assert len(summary["inventory_hash"]) == 64


def test_route_inventory_parity_report_detects_match_and_mismatch() -> None:
    inventory = build_route_inventory(app)
    preview = summarize_route_inventory(inventory, environment="preview")
    staging = summarize_route_inventory(inventory, environment="staging")
    prod = summarize_route_inventory(inventory, environment="prod")

    matching_report = build_route_inventory_parity_report(
        {"preview": preview, "staging": staging, "prod": prod}
    )
    assert matching_report["all_match"] is True
    assert matching_report["mismatches"] == []

    drifted_prod = {**prod, "route_count": prod["route_count"] + 1}
    mismatch_report = build_route_inventory_parity_report(
        {"preview": preview, "staging": staging, "prod": drifted_prod}
    )
    assert mismatch_report["all_match"] is False
    assert any(item["environment"] == "prod" and item["kind"] == "counts" for item in mismatch_report["mismatches"])