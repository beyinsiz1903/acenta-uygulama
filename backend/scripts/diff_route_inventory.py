from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.bootstrap.route_inventory_diff import diff_route_inventory_files


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Compare two route inventory snapshots")
    parser.add_argument("previous", help="Path to the previous route_inventory.json file")
    parser.add_argument("current", help="Path to the current route_inventory.json file")
    parser.add_argument("--format", choices=("json", "text"), default="text")
    return parser


def _render_text(report: dict) -> str:
    summary = report["summary"]
    lines = [
        "route_inventory diff",
        f"- previous_route_count: {summary['previous_route_count']}",
        f"- current_route_count: {summary['current_route_count']}",
        f"- added_route_count: {summary['added_route_count']}",
        f"- removed_route_count: {summary['removed_route_count']}",
        f"- current_v1_route_count: {summary['current_v1_route_count']}",
        f"- new_v1_route_count: {summary['new_v1_route_count']}",
        f"- legacy_only_route_count: {summary['legacy_only_route_count']}",
        f"- compat_required_route_count: {summary['compat_required_route_count']}",
        "- added_paths:",
    ]

    added_paths = report["added_paths"] or [{"method": "-", "path": "(none)", "legacy_or_v1": "-"}]
    removed_paths = report["removed_paths"] or [{"method": "-", "path": "(none)", "legacy_or_v1": "-"}]

    for item in added_paths:
        lines.append(f"  - [{item['method']}] {item['path']} ({item['legacy_or_v1']})")

    lines.append("- removed_paths:")
    for item in removed_paths:
        lines.append(f"  - [{item['method']}] {item['path']} ({item['legacy_or_v1']})")

    return "\n".join(lines)


def main() -> None:
    args = _build_parser().parse_args()
    report = diff_route_inventory_files(args.previous, args.current)

    if args.format == "json":
        print(json.dumps(report, indent=2, sort_keys=True))
        return

    print(_render_text(report))


if __name__ == "__main__":
    main()