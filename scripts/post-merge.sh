#!/bin/bash
# Post-merge setup for Syroce.
# Runs automatically after every task merge. Must be idempotent and
# non-interactive (stdin is closed). Keep it fast — the user is waiting.
set -e

# Frontend deps (yarn). --frozen-lockfile keeps it deterministic and a
# no-op when nothing in package.json/yarn.lock changed.
if [ -f frontend/package.json ]; then
  (cd frontend && yarn install --frozen-lockfile --silent) || \
    (cd frontend && yarn install --silent)
fi

# Backend deps (pip). Skip silently if requirements already satisfied.
if [ -f backend/requirements.txt ]; then
  pip install --quiet --disable-pip-version-check -r backend/requirements.txt
fi

echo "post-merge: done"
