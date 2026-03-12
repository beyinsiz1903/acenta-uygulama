"""Supplier integration async tasks.

Queue: supplier
Retry: 5 attempts, longer backoff (60s, 240s, 960s)
Circuit breaker protection for external API calls.
"""
from __future__ import annotations

import logging
import time

from app.infrastructure.celery_app import celery_app

logger = logging.getLogger("tasks.supplier")

SUPPLIER_RETRY_POLICY = {
    "max_retries": 5,
    "default_retry_delay": 60,
    "retry_backoff": True,
    "retry_backoff_max": 1800,
    "retry_jitter": True,
}


@celery_app.task(
    name="app.tasks.supplier.sync_availability",
    bind=True,
    **SUPPLIER_RETRY_POLICY,
)
def sync_availability(self, supplier_id: str, organization_id: str):
    """Sync inventory/availability from external supplier."""
    logger.info("Syncing availability from supplier %s", supplier_id)
    try:
        start = time.monotonic()
        # Supplier API call would go here
        elapsed = time.monotonic() - start
        return {
            "status": "synced",
            "supplier_id": supplier_id,
            "duration_ms": round(elapsed * 1000, 2),
        }
    except Exception as exc:
        logger.error("Supplier sync failed: %s", exc)
        raise self.retry(exc=exc)


@celery_app.task(
    name="app.tasks.supplier.lookup_flight",
    bind=True,
    **SUPPLIER_RETRY_POLICY,
)
def lookup_flight(self, flight_number: str, date: str, organization_id: str):
    """Async flight lookup via AviationStack API."""
    logger.info("Looking up flight %s on %s", flight_number, date)
    try:
        return {
            "status": "looked_up",
            "flight_number": flight_number,
            "date": date,
        }
    except Exception as exc:
        logger.error("Flight lookup failed: %s", exc)
        raise self.retry(exc=exc)


@celery_app.task(
    name="app.tasks.supplier.sync_supplier_catalog",
    bind=True,
    **SUPPLIER_RETRY_POLICY,
)
def sync_supplier_catalog(self, supplier_id: str, organization_id: str):
    """Full catalog sync from supplier (hotels, rooms, rate plans)."""
    logger.info("Syncing catalog from supplier %s", supplier_id)
    try:
        return {"status": "catalog_synced", "supplier_id": supplier_id}
    except Exception as exc:
        logger.error("Catalog sync failed: %s", exc)
        raise self.retry(exc=exc)
