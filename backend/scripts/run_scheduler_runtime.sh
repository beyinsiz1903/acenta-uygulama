#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
python_bin="${PYTHON_BIN:-/root/.venv/bin/python}"
exec "$python_bin" -m app.bootstrap.scheduler_app