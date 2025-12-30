from __future__ import annotations

import asyncio
import base64
import logging
import os
from typing import Iterable, List, Mapping, Optional

import httpx

from app.utils import now_utc

logger = logging.getLogger("email_resend")


class ResendNotConfigured(Exception):
    pass


class ResendEmailError(Exception):
    pass


async def send_catalog_offer_email(
    *,
    to_email: str,
    subject: str,
    html: str,
    text: Optional[str] = None,
    reply_to: Optional[str] = None,
    tags: Optional[Iterable[str]] = None,
    headers: Optional[Mapping[str, str]] = None,
) -> dict:
    """Send a generic catalog offer email via Resend (no attachment).

    - Reuses the same API key / from-email configuration as tour voucher emails
    - Returns parsed JSON response from Resend
    """

    api_key = _get_resend_api_key()
    sender = _get_resend_from_email()

    payload: dict = {
      "from": sender,
      "to": [to_email],
      "subject": subject,
      "html": html,
    }

    if text:
        payload["text"] = text

    if reply_to:
        payload["reply_to"] = [reply_to]
    elif os.environ.get("RESEND_REPLY_TO_EMAIL"):
        payload["reply_to"] = [os.environ["RESEND_REPLY_TO_EMAIL"]]

    if tags:
        payload["tags"] = list(tags)

    final_headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    if headers:
        final_headers.update(headers)

    url = "https://api.resend.com/emails"

    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            resp = await client.post(url, json=payload, headers=final_headers)
        except Exception as exc:  # network or timeout
            logger.exception("Resend email request failed: %s", exc)
            raise ResendEmailError("RESEND_REQUEST_FAILED") from exc

    if resp.status_code >= 400:
        try:
            data = resp.json()
        except Exception:
            data = {"error": resp.text}
        logger.error("Resend email API error %s: %s", resp.status_code, data)
        raise ResendEmailError("RESEND_API_ERROR")

    try:
        data = resp.json()
    except Exception:
        data = {"id": None}

    logger.info("Resend email sent to %s (id=%s)", to_email, data.get("id"))
    return data


def _get_resend_api_key() -> str:
    key = os.environ.get("RESEND_API_KEY")
    if not key:
        raise ResendNotConfigured("RESEND_API_KEY is not set")
    return key


def _get_resend_from_email() -> str:
    sender = os.environ.get("RESEND_FROM_EMAIL") or os.environ.get("SENDER_EMAIL")
    if not sender:
        raise ResendNotConfigured("RESEND_FROM_EMAIL is not set")
    return sender


async def send_tour_voucher_email(
    *,
    to_email: str,
    subject: str,
    html: str,
    pdf_bytes: bytes,
    pdf_filename: str,
    reply_to: Optional[str] = None,
    cc: Optional[Iterable[str]] = None,
    bcc: Optional[Iterable[str]] = None,
    headers: Optional[Mapping[str, str]] = None,
) -> dict:
    """Send a tour voucher email via Resend with PDF attachment.

    - Uses Resend /emails endpoint directly via httpx
    - Attaches PDF using base64 encoding
    - Returns parsed JSON response from Resend
    """

    api_key = _get_resend_api_key()
    sender = _get_resend_from_email()

    payload: dict = {
        "from": sender,
        "to": [to_email],
        "subject": subject,
        "html": html,
        "attachments": [
            {
                "filename": pdf_filename,
                "content": base64.b64encode(pdf_bytes).decode("ascii"),
                "content_type": "application/pdf",
            }
        ],
    }

    if reply_to:
        payload["reply_to"] = [reply_to]
    elif os.environ.get("RESEND_REPLY_TO_EMAIL"):
        payload["reply_to"] = [os.environ["RESEND_REPLY_TO_EMAIL"]]

    if cc:
        payload["cc"] = list(cc)
    if bcc:
        payload["bcc"] = list(bcc)

    final_headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    if headers:
        final_headers.update(headers)

    url = "https://api.resend.com/emails"

    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            resp = await client.post(url, json=payload, headers=final_headers)
        except Exception as exc:  # network or timeout
            logger.exception("Resend email request failed: %s", exc)
            raise ResendEmailError("RESEND_REQUEST_FAILED") from exc

    if resp.status_code >= 400:
        try:
            data = resp.json()
        except Exception:
            data = {"error": resp.text}
        logger.error("Resend email API error %s: %s", resp.status_code, data)
        raise ResendEmailError("RESEND_API_ERROR")

    try:
        data = resp.json()
    except Exception:
        data = {"id": None}

    logger.info("Resend email sent to %s (id=%s)", to_email, data.get("id"))
    return data
