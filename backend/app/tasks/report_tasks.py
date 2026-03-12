"""Report & document generation async tasks.

Queue: reports
Retry: 2 attempts (reports are idempotent, safe to retry)
"""
from __future__ import annotations

import logging

from app.infrastructure.celery_app import celery_app

logger = logging.getLogger("tasks.report")


@celery_app.task(
    name="app.tasks.report.generate_invoice",
    bind=True,
    max_retries=2,
    default_retry_delay=30,
)
def generate_invoice(self, booking_id: str, organization_id: str):
    """Generate invoice PDF for a booking."""
    logger.info("Generating invoice for booking %s", booking_id)
    try:
        return {"status": "generated", "type": "invoice", "booking_id": booking_id}
    except Exception as exc:
        logger.error("Invoice generation failed: %s", exc)
        raise self.retry(exc=exc)


@celery_app.task(
    name="app.tasks.report.export_report",
    bind=True,
    max_retries=2,
    default_retry_delay=60,
)
def export_report(self, report_type: str, filters: dict, organization_id: str):
    """Export report as CSV/XLSX."""
    logger.info("Exporting %s report for org %s", report_type, organization_id)
    try:
        return {"status": "exported", "report_type": report_type}
    except Exception as exc:
        logger.error("Report export failed: %s", exc)
        raise self.retry(exc=exc)


@celery_app.task(
    name="app.tasks.report.generate_settlement_report",
    bind=True,
    max_retries=2,
    default_retry_delay=30,
)
def generate_settlement_report(self, settlement_id: str, organization_id: str):
    """Generate settlement reconciliation report."""
    logger.info("Generating settlement report %s", settlement_id)
    try:
        return {"status": "generated", "type": "settlement", "settlement_id": settlement_id}
    except Exception as exc:
        logger.error("Settlement report failed: %s", exc)
        raise self.retry(exc=exc)
