#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
uvicorn_bin="${UVICORN_BIN:-/root/.venv/bin/uvicorn}"
exec "$uvicorn_bin" app.bootstrap.api_app:create_app --factory --host 0.0.0.0 --port 8001