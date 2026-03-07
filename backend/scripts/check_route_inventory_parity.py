from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.bootstrap.route_inventory_summary import (
    build_route_inventory_parity_report,
    load_route_inventory_summary,
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Check route inventory parity across environment summaries")
    parser.add_argument(
        "summaries",
        nargs="+",
        help="Environment summary pairs in the form preview=/path/summary.json",
    )
    parser.add_argument("--format", choices=("json", "text"), default="text")
    parser.add_argument("--fail-on-mismatch", action="store_true", help="Exit non-zero when parity mismatches are detected")
    return parser


def _parse_summary_args(raw_pairs: list[str]) -> dict[str, dict]:
    parsed: dict[str, dict] = {}
    for raw_pair in raw_pairs:
        if "=" not in raw_pair:
            raise SystemExit(f"invalid summary argument: {raw_pair}")
        environment, source = raw_pair.split("=", 1)
        parsed[environment] = load_route_inventory_summary(source)
    return parsed


def _render_text(report: dict) -> str:
    lines = [
        "route_inventory parity",
        f"- baseline_environment: {report['baseline_environment']}",
        f"- all_match: {report['all_match']}",
        "- counts:",
    ]
    for environment in report["environment_names"]:
        counts = report["counts"][environment]
        lines.append(
            f"  - {environment}: route_count={counts['route_count']} v1_count={counts['v1_count']} legacy_count={counts['legacy_count']}"
        )
    lines.append("- inventory_hashes:")
    for environment in report["environment_names"]:
        lines.append(f"  - {environment}: {report['inventory_hashes'][environment]}")
    lines.append("- mismatches:")
    if not report["mismatches"]:
        lines.append("  - (none)")
    else:
        for mismatch in report["mismatches"]:
            lines.append(
                f"  - {mismatch['environment']} [{mismatch['kind']}] expected={mismatch['expected']} actual={mismatch['actual']}"
            )
    return "\n".join(lines)


def main() -> int:
    args = _build_parser().parse_args()
    report = build_route_inventory_parity_report(_parse_summary_args(args.summaries))

    if args.format == "json":
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(_render_text(report))

    if args.fail_on_mismatch and not report["all_match"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())