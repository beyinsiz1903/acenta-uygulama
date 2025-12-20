from __future__ import annotations

import logging
import os
from typing import Any, Iterable
from datetime import timedelta

from app.services.email import EmailSendError, send_email_ses
from app.services.events import write_booking_event
from app.utils import now_utc
from app.routers.voucher import _get_or_create_voucher_for_booking  # reuse FAZ-9.2 helper

logger = logging.getLogger("email_outbox")


async def enqueue_booking_email(
    db,
    *,
    organization_id: str,
    booking: dict[str, Any],
    event_type: str,  # booking.confirmed | booking.cancelled
    to_addresses: Iterable[str],
) -> None:
    """Create an email_outbox job for a booking event.

    Body includes TR+EN text and voucher HTML/PDF links.
    """

    to_clean = sorted({a.strip() for a in to_addresses if a and "@" in a})
    if not to_clean:
        return

    booking_id = booking["_id"]

    # Ensure voucher token exists
    voucher = await _get_or_create_voucher_for_booking(db, organization_id, booking_id)
    token = voucher["token"]

    base = os.environ.get("PUBLIC_BASE_URL", "").rstrip("/")
    if base:
        html_url = f"{base}/api/voucher/public/{token}?format=html"
        pdf_url = f"{base}/api/voucher/public/{token}?format=pdf"
    else:
        html_url = f"/api/voucher/public/{token}?format=html"
        pdf_url = f"/api/voucher/public/{token}?format=pdf"

    hotel_name = booking.get("hotel_name") or "-"
    stay = booking.get("stay") or {}
    check_in = (stay.get("check_in") or "")[:10]
    check_out = (stay.get("check_out") or "")[:10]

    subject_prefix = "[Rezervasyon Onayı]" if event_type == "booking.confirmed" else "[Rezervasyon İptali]"
    subject = f"{subject_prefix} {hotel_name} / {check_in} - {check_out}".strip()

    guest = booking.get("guest") or {}
    guest_name = guest.get("full_name") or booking.get("guest_name") or "-"

    # Simple HTML body (TR + EN sections)
    html_body = f"""
<h2>Rezervasyon Bilgisi</h2>
<p><strong>Otel:</strong> {hotel_name}</p>
<p><strong>Misafir:</strong> {guest_name}</p>
<p><strong>Check-in:</strong> {check_in}</p>
<p><strong>Check-out:</strong> {check_out}</p>
<p><strong>Durum:</strong> {subject_prefix}</p>
<p><a href="{html_url}">Voucher'ı görüntüle</a> | <a href="{pdf_url}">PDF indir</a></p>
<hr />
<h2>Booking Details</h2>
<p><strong>Hotel:</strong> {hotel_name}</p>
<p><strong>Guest:</strong> {guest_name}</p>
<p><strong>Check-in:</strong> {check_in}</p>
<p><strong>Check-out:</strong> {check_out}</p>
<p><strong>Status:</strong> {subject_prefix}</p>
<p><a href="{html_url}">View voucher</a> | <a href="{pdf_url}">Download PDF</a></p>
""".strip()

    text_body = f"""Rezervasyon Bilgisi / Booking Details\nHotel: {hotel_name}\nGuest: {guest_name}\nCheck-in: {check_in}\nCheck-out: {check_out}\nStatus: {subject_prefix}\nVoucher HTML: {html_url}\nVoucher PDF: {pdf_url}\n""".strip()

    now = now_utc()

    doc = {
        "organization_id": organization_id,
        "booking_id": booking_id,
        "event_type": event_type,
        "to": to_clean,
        "subject": subject,
        "html_body": html_body,
        "text_body": text_body,
        "status": "pending",
        "attempt_count": 0,
        "last_error": None,
        "next_retry_at": now,
        "created_at": now,
        "sent_at": None,
    }

    await db.email_outbox.insert_one(doc)


async def dispatch_pending_emails(db, *, limit: int = 10) -> int:
    """Send pending emails from email_outbox via SES.

    Returns number of processed jobs.
    """

    now = now_utc()

    cursor = db.email_outbox.find(
        {"status": "pending", "next_retry_at": {"$lte": now}},
        limit=limit,
    )

    processed = 0
    async for job in cursor:
        processed += 1
        to = job.get("to") or []
        subject = job.get("subject") or ""
        html_body = job.get("html_body") or ""
        text_body = job.get("text_body") or None

        try:
            for addr in to:
                send_email_ses(to_address=addr, subject=subject, html_body=html_body, text_body=text_body)

            await db.email_outbox.update_one(
                {"_id": job["_id"]},
                {
                    "$set": {
                        "status": "sent",
                        "sent_at": now,
                        "attempt_count": job.get("attempt_count", 0) + 1,
                        "last_error": None,
                    }
                },
            )

            # Audit log for each job
            try:
                from app.services.audit import write_audit_log  # local import to avoid cycles
                from app.db import get_db
            except Exception:  # during offline scripts
                write_audit_log = None

            if write_audit_log is not None:
                try:
                    # We don't have request context here; use a stub.
                    class StubRequest:
                        def __init__(self) -> None:
                            self.headers = {}
                            self.client = None

                        @property
                        def method(self) -> str:
                            return "WORKER"

                        @property
                        def url(self):  # type: ignore[return-type]
                            class U:
                                path = "/worker/email_dispatch"

                            return U()

                    stub_request = StubRequest()
                    db2 = db  # already have db handle
                    await write_audit_log(
                        db2,
                        organization_id=job["organization_id"],
                        actor={
                            "actor_type": "system",
                            "actor_id": "email_worker",
                            "email": None,
                            "roles": ["system"],
                        },
                        request=stub_request,  # type: ignore[arg-type]
                        action="email.sent",
                        target_type="booking",
                        target_id=str(job.get("booking_id")),
                        before=None,
                        after=None,
                        meta={
                            "event_type": job.get("event_type"),
                            "to": to,
                            "subject": subject,
                        },
                    )
                except Exception as e:  # pragma: no cover - audit failures should not block
                    logger.error("Failed to write email.sent audit log: %s", e, exc_info=True)

        except EmailSendError as e:
            attempts = job.get("attempt_count", 0) + 1
            backoff_minutes = min(60, 2 ** min(attempts, 5))  # 2,4,8,16,32,60
            next_retry = now + timedelta(minutes=backoff_minutes)

            await db.email_outbox.update_one(
                {"_id": job["_id"]},
                {
                    "$set": {
                        "status": "pending" if attempts < 5 else "failed",
                        "attempt_count": attempts,
                        "last_error": str(e),
                        "next_retry_at": next_retry,
                    }
                },
            )

            logger.error("Email send failed for job %s: %s", job.get("_id"), e, exc_info=True)

        except Exception as e:  # pragma: no cover
            logger.error("Unexpected error in dispatch_pending_emails: %s", e, exc_info=True)

    return processed
