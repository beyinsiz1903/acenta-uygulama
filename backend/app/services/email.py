from __future__ import annotations

import logging
from typing import Any, Mapping, Optional

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from app.utils import require_env

logger = logging.getLogger("email")


class EmailSendError(Exception):
    """Raised when SES email sending fails."""


def _get_ses_client():
    """Return a configured SES client or None if SES is not configured.

    For FAZ-1 we treat missing SES configuration as a non-fatal condition so
    that public flows (e.g. /my-booking request-link) never hard-fail just
    because email infra is not wired yet.
    """

    try:
        region = require_env("AWS_REGION")
        access_key = require_env("AWS_ACCESS_KEY_ID")
        secret_key = require_env("AWS_SECRET_ACCESS_KEY")
    except Exception as e:  # pragma: no cover - environment dependent
        logger.warning("SES not configured, skipping email send: %s", e)
        return None

    return boto3.client(
        "ses",
        region_name=region,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
    )


def send_email_ses(
    *,
    to_address: str,
    subject: str,
    html_body: str,
    text_body: Optional[str] = None,
    reply_to: Optional[list[str]] = None,
    headers: Optional[Mapping[str, str]] = None,
) -> dict[str, Any]:
    """Send an email using AWS SES.

    This is a synchronous helper intended to be called from FastAPI background
    tasks or short-lived request handlers.

    Phase-1 behavior: if SES is not configured (missing env vars), we log a
    warning and act as a no-op instead of raising. This keeps public flows
    (like /my-booking request-link) from failing with 500/520 just because
    email infra is not ready.
    """

    client = _get_ses_client()
    if client is None:
        logger.warning("send_email_ses called but SES is not configured; skipping send to %s", to_address)
        return {"ok": False, "skipped": True, "reason": "ses_not_configured"}

    try:
        source = require_env("AWS_SES_FROM_EMAIL")
    except Exception as e:  # pragma: no cover - environment dependent
        logger.warning("AWS_SES_FROM_EMAIL missing; skipping SES send: %s", e)
        return {"ok": False, "skipped": True, "reason": "ses_not_configured"}

    destination = {"ToAddresses": [to_address]}

    msg: dict[str, Any] = {
        "Subject": {"Data": subject, "Charset": "UTF-8"},
        "Body": {
            "Html": {"Data": html_body, "Charset": "UTF-8"},
        },
    }

    if text_body:
        msg["Body"]["Text"] = {"Data": text_body, "Charset": "UTF-8"}

    kwargs: dict[str, Any] = {
        "Source": source,
        "Destination": destination,
        "Message": msg,
    }

    if reply_to:
        kwargs["ReplyToAddresses"] = reply_to

    if headers:
        # SES supports custom headers via RawEmail; for simplicity we log only.
        logger.debug("Ignoring custom headers for simple SES send: %s", headers)

    try:
        resp = client.send_email(**kwargs)
        logger.info("SES send_email ok: MessageId=%s", resp.get("MessageId"))
        return resp
    except ClientError as e:
        logger.error("SES ClientError: %s", e, exc_info=True)
        raise EmailSendError(str(e))
    except BotoCoreError as e:
        logger.error("SES BotoCoreError: %s", e, exc_info=True)
        raise EmailSendError(str(e))
