#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
exec uvicorn app.bootstrap.api_app:create_app --factory --host 0.0.0.0 --port 8001