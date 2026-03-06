#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.bootstrap.runtime_health import is_runtime_healthy, load_runtime_health, runtime_health_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Check dedicated runtime heartbeat freshness")
    parser.add_argument("runtime", choices=["worker", "scheduler"], help="Runtime heartbeat to validate")
    parser.add_argument("--ttl-seconds", type=int, default=60, help="Maximum heartbeat age in seconds")
    args = parser.parse_args()

    path = runtime_health_path(args.runtime)
    if not path.exists():
        print(f"missing heartbeat: {path}")
        return 1

    payload = load_runtime_health(args.runtime)
    if not is_runtime_healthy(payload, ttl_seconds=args.ttl_seconds):
        print(f"unhealthy runtime={args.runtime} path={path} payload={payload}")
        return 1

    print(f"healthy runtime={args.runtime} path={path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
