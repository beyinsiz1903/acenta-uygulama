"""
Route Inventory Parity Tooling Tests

Tests for:
- route_inventory_summary.json generation (route_count, v1_count, legacy_count, legacy_routes_remaining, inventory_hash, namespace breakdown)
- export_route_inventory.py CLI (custom path support for inventory + summary)
- check_route_inventory_parity.py CLI (mismatch detection, --fail-on-mismatch)
- Deterministic route inventory generation
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT_DIR = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT_DIR / "scripts"
BOOTSTRAP_DIR = ROOT_DIR / "app" / "bootstrap"


class TestRouteInventorySummaryGeneration:
    """Tests for route_inventory_summary.json required fields"""

    def test_summary_contains_required_fields(self, tmp_path: Path) -> None:
        """Summary JSON must have route_count, v1_count, legacy_count, inventory_hash"""
        inventory_path = tmp_path / "inventory.json"
        summary_path = tmp_path / "summary.json"
        
        result = subprocess.run(
            [
                sys.executable, str(SCRIPTS_DIR / "export_route_inventory.py"),
                "--destination", str(inventory_path),
                "--summary-out", str(summary_path),
                "--environment", "test",
            ],
            capture_output=True,
            text=True,
            cwd=str(ROOT_DIR),
        )
        assert result.returncode == 0, f"Export failed: {result.stderr}"
        
        summary = json.loads(summary_path.read_text())
        
        # Required fields
        assert "route_count" in summary
        assert "v1_count" in summary
        assert "legacy_count" in summary
        assert "inventory_hash" in summary
        assert "legacy_routes_remaining" in summary
        assert "namespaces" in summary
        
        # Type checks
        assert isinstance(summary["route_count"], int)
        assert isinstance(summary["v1_count"], int)
        assert isinstance(summary["legacy_count"], int)
        assert isinstance(summary["legacy_routes_remaining"], int)
        assert isinstance(summary["inventory_hash"], str)
        assert isinstance(summary["namespaces"], dict)
        assert len(summary["inventory_hash"]) == 64  # SHA-256 hex
        
        # Count consistency
        assert summary["route_count"] == summary["v1_count"] + summary["legacy_count"]
        assert summary["legacy_routes_remaining"] == summary["legacy_count"]
        assert sum(summary["namespaces"].values()) == summary["route_count"]

    def test_summary_includes_namespace_breakdown(self, tmp_path: Path) -> None:
        """Summary should include deterministic namespace buckets for migration tracking"""
        summary_path = tmp_path / "summary.json"

        result = subprocess.run(
            [
                sys.executable, str(SCRIPTS_DIR / "export_route_inventory.py"),
                "--destination", str(tmp_path / "inventory.json"),
                "--summary-out", str(summary_path),
                "--environment", "test",
            ],
            capture_output=True,
            text=True,
            cwd=str(ROOT_DIR),
        )
        assert result.returncode == 0

        summary = json.loads(summary_path.read_text())
        assert list(summary["namespaces"].keys()) == ["auth", "admin", "public", "system", "mobile", "tenant", "finance", "misc"]
        assert sum(summary["namespaces"].values()) == summary["route_count"]

    def test_summary_includes_compat_required_count(self, tmp_path: Path) -> None:
        """Summary should include compat_required_count for migration tracking"""
        summary_path = tmp_path / "summary.json"
        
        result = subprocess.run(
            [
                sys.executable, str(SCRIPTS_DIR / "export_route_inventory.py"),
                "--destination", str(tmp_path / "inventory.json"),
                "--summary-out", str(summary_path),
                "--environment", "test",
            ],
            capture_output=True,
            text=True,
            cwd=str(ROOT_DIR),
        )
        assert result.returncode == 0
        
        summary = json.loads(summary_path.read_text())
        assert "compat_required_count" in summary
        assert isinstance(summary["compat_required_count"], int)


class TestExportRouteInventoryCLI:
    """Tests for scripts/export_route_inventory.py CLI"""

    def test_exports_to_custom_paths(self, tmp_path: Path) -> None:
        """export_route_inventory.py must support custom output paths"""
        custom_inventory = tmp_path / "custom" / "inventory.json"
        custom_summary = tmp_path / "custom" / "summary.json"
        
        result = subprocess.run(
            [
                sys.executable, str(SCRIPTS_DIR / "export_route_inventory.py"),
                "--destination", str(custom_inventory),
                "--summary-out", str(custom_summary),
                "--environment", "custom_env",
            ],
            capture_output=True,
            text=True,
            cwd=str(ROOT_DIR),
        )
        
        assert result.returncode == 0, f"Export failed: {result.stderr}"
        assert custom_inventory.exists(), "Inventory not created at custom path"
        assert custom_summary.exists(), "Summary not created at custom path"
        
        # Verify inventory is valid JSON array
        inventory = json.loads(custom_inventory.read_text())
        assert isinstance(inventory, list)
        assert len(inventory) > 0
        
        # Verify summary contains environment label
        summary = json.loads(custom_summary.read_text())
        assert summary["environment"] == "custom_env"

    def test_creates_parent_directories(self, tmp_path: Path) -> None:
        """CLI should create parent directories if they don't exist"""
        nested_inventory = tmp_path / "a" / "b" / "c" / "inventory.json"
        nested_summary = tmp_path / "d" / "e" / "summary.json"
        
        result = subprocess.run(
            [
                sys.executable, str(SCRIPTS_DIR / "export_route_inventory.py"),
                "--destination", str(nested_inventory),
                "--summary-out", str(nested_summary),
            ],
            capture_output=True,
            text=True,
            cwd=str(ROOT_DIR),
        )
        
        assert result.returncode == 0
        assert nested_inventory.exists()
        assert nested_summary.exists()


class TestCheckRouteInventoryParityCLI:
    """Tests for scripts/check_route_inventory_parity.py CLI"""

    @pytest.fixture
    def matching_summaries(self, tmp_path: Path) -> dict[str, Path]:
        """Generate matching summaries for multiple environments"""
        paths = {}
        for env_name in ["preview", "staging", "prod"]:
            summary_path = tmp_path / f"summary.{env_name}.json"
            result = subprocess.run(
                [
                    sys.executable, str(SCRIPTS_DIR / "export_route_inventory.py"),
                    "--destination", str(tmp_path / f"inventory.{env_name}.json"),
                    "--summary-out", str(summary_path),
                    "--environment", env_name,
                ],
                capture_output=True,
                text=True,
                cwd=str(ROOT_DIR),
            )
            assert result.returncode == 0
            paths[env_name] = summary_path
        return paths

    def test_reports_matching_parity_for_same_code_path(
        self, tmp_path: Path, matching_summaries: dict[str, Path]
    ) -> None:
        """Parity check should report all_match=True for identical code paths"""
        result = subprocess.run(
            [
                sys.executable, str(SCRIPTS_DIR / "check_route_inventory_parity.py"),
                f"preview={matching_summaries['preview']}",
                f"staging={matching_summaries['staging']}",
                f"prod={matching_summaries['prod']}",
                "--format", "json",
            ],
            capture_output=True,
            text=True,
            cwd=str(ROOT_DIR),
        )
        
        assert result.returncode == 0
        report = json.loads(result.stdout)
        
        assert report["all_match"] is True
        assert report["mismatches"] == []
        assert "preview" in report["counts"]
        assert "staging" in report["counts"]
        assert "prod" in report["counts"]

    def test_detects_count_mismatch(
        self, tmp_path: Path, matching_summaries: dict[str, Path]
    ) -> None:
        """Parity check should detect when route counts drift"""
        # Create drifted summary
        drifted_summary = matching_summaries["staging"]
        data = json.loads(drifted_summary.read_text())
        data["route_count"] = data["route_count"] + 100  # Simulate drift
        data["v1_count"] = data["v1_count"] + 50
        drifted_summary.write_text(json.dumps(data))
        
        result = subprocess.run(
            [
                sys.executable, str(SCRIPTS_DIR / "check_route_inventory_parity.py"),
                f"preview={matching_summaries['preview']}",
                f"staging={drifted_summary}",
                "--format", "json",
            ],
            capture_output=True,
            text=True,
            cwd=str(ROOT_DIR),
        )
        
        assert result.returncode == 0
        report = json.loads(result.stdout)
        
        assert report["all_match"] is False
        assert len(report["mismatches"]) > 0
        assert any(m["environment"] == "staging" and m["kind"] == "counts" for m in report["mismatches"])

    def test_fail_on_mismatch_flag_exits_nonzero(
        self, tmp_path: Path, matching_summaries: dict[str, Path]
    ) -> None:
        """--fail-on-mismatch should exit 1 when mismatch detected"""
        # Create drifted summary
        drifted_path = tmp_path / "drifted.json"
        data = json.loads(matching_summaries["preview"].read_text())
        data["route_count"] = 999
        drifted_path.write_text(json.dumps(data))
        
        result = subprocess.run(
            [
                sys.executable, str(SCRIPTS_DIR / "check_route_inventory_parity.py"),
                f"preview={matching_summaries['preview']}",
                f"drifted={drifted_path}",
                "--format", "json",
                "--fail-on-mismatch",
            ],
            capture_output=True,
            text=True,
            cwd=str(ROOT_DIR),
        )
        
        assert result.returncode == 1  # Should fail due to mismatch

    def test_text_output_format(
        self, tmp_path: Path, matching_summaries: dict[str, Path]
    ) -> None:
        """Text output format should be human-readable"""
        result = subprocess.run(
            [
                sys.executable, str(SCRIPTS_DIR / "check_route_inventory_parity.py"),
                f"preview={matching_summaries['preview']}",
                f"staging={matching_summaries['staging']}",
                "--format", "text",
            ],
            capture_output=True,
            text=True,
            cwd=str(ROOT_DIR),
        )
        
        assert result.returncode == 0
        assert "route_inventory parity" in result.stdout
        assert "all_match: True" in result.stdout
        assert "preview:" in result.stdout
        assert "staging:" in result.stdout


class TestDeterministicRouteInventory:
    """Tests for deterministic route inventory generation"""

    def test_inventory_is_deterministic_across_runs(self, tmp_path: Path) -> None:
        """Same codebase should produce identical inventory hashes"""
        hashes = []
        
        for i in range(3):
            summary_path = tmp_path / f"summary_{i}.json"
            result = subprocess.run(
                [
                    sys.executable, str(SCRIPTS_DIR / "export_route_inventory.py"),
                    "--destination", str(tmp_path / f"inventory_{i}.json"),
                    "--summary-out", str(summary_path),
                    "--environment", f"run_{i}",
                ],
                capture_output=True,
                text=True,
                cwd=str(ROOT_DIR),
            )
            assert result.returncode == 0
            summary = json.loads(summary_path.read_text())
            hashes.append(summary["inventory_hash"])
        
        # All hashes should be identical
        assert len(set(hashes)) == 1, f"Non-deterministic hashes: {hashes}"

    def test_inventory_entries_are_sorted(self, tmp_path: Path) -> None:
        """Inventory entries should be sorted by (path, method, source)"""
        inventory_path = tmp_path / "inventory.json"
        
        result = subprocess.run(
            [
                sys.executable, str(SCRIPTS_DIR / "export_route_inventory.py"),
                "--destination", str(inventory_path),
                "--summary-out", str(tmp_path / "summary.json"),
            ],
            capture_output=True,
            text=True,
            cwd=str(ROOT_DIR),
        )
        assert result.returncode == 0
        
        inventory = json.loads(inventory_path.read_text())
        sorted_inventory = sorted(inventory, key=lambda x: (x["path"], x["method"], x["source"]))
        
        assert inventory == sorted_inventory, "Inventory is not sorted correctly"
