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
    region = require_env("AWS_REGION")
    access_key = require_env("AWS_ACCESS_KEY_ID")
    secret_key = require_env("AWS_SECRET_ACCESS_KEY")

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
    """

    source = require_env("AWS_SES_FROM_EMAIL")

    client = _get_ses_client()

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
