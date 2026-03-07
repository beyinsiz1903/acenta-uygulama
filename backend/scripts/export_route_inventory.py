from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.bootstrap.route_inventory import (
    DEFAULT_ROUTE_INVENTORY_PATH,
    export_route_inventory_artifacts,
)
from app.bootstrap.route_inventory_summary import DEFAULT_ROUTE_INVENTORY_SUMMARY_PATH
from server import app


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Export deterministic route inventory artifacts")
    parser.add_argument("--destination", default=str(DEFAULT_ROUTE_INVENTORY_PATH), help="Inventory JSON output path")
    parser.add_argument("--summary-out", default=str(DEFAULT_ROUTE_INVENTORY_SUMMARY_PATH), help="Summary JSON output path")
    parser.add_argument(
        "--environment",
        default=os.environ.get("APP_ENV_NAME") or os.environ.get("ENV") or "runtime",
        help="Environment label written into the summary artifact",
    )
    return parser


def main() -> None:
    args = _build_parser().parse_args()
    artifacts = export_route_inventory_artifacts(
        app,
        inventory_destination=args.destination,
        summary_destination=args.summary_out,
        environment=args.environment,
    )
    if artifacts is None:
        raise SystemExit(1)
    print(artifacts["inventory"])
    print(artifacts["summary"])


if __name__ == "__main__":
    main()