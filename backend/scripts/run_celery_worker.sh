#!/usr/bin/env bash
set -euo pipefail

cd /app/backend

export PYTHONPATH="/app/backend"
export PATH="/root/.venv/bin:$PATH"

# Start a unified Celery worker consuming all production queues
exec /root/.venv/bin/celery \
    -A app.infrastructure.celery_app:celery_app \
    worker \
    --hostname=syroce-unified@%h \
    --queues=booking_queue,voucher_queue,notification_queue,incident_queue,cleanup_queue,default,critical,supplier,notifications,reports,maintenance,email,alerts,incidents \
    --concurrency=4 \
    --prefetch-multiplier=2 \
    --max-tasks-per-child=500 \
    --without-gossip \
    --without-mingle \
    -l info
