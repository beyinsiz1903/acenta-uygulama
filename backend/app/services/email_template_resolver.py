from __future__ import annotations

import logging
import re
from typing import Any, Dict, Optional

logger = logging.getLogger("email_template_resolver")


async def resolve_template(
    db,
    *,
    organization_id: str,
    trigger_key: str,
    variables: Dict[str, Any] | None = None,
) -> Optional[Dict[str, str]]:
    tpl = await db.email_templates.find_one(
        {
            "organization_id": organization_id,
            "trigger_key": trigger_key,
            "status": "active",
        },
        {"_id": 0},
    )
    if not tpl:
        return None

    subject = tpl.get("subject", "")
    html_body = tpl.get("html_body", "")
    text_body = tpl.get("text_body", "")

    if variables:
        for key, value in variables.items():
            placeholder = "{{" + key + "}}"
            safe_val = str(value) if value is not None else ""
            subject = subject.replace(placeholder, safe_val)
            html_body = html_body.replace(placeholder, safe_val)
            text_body = text_body.replace(placeholder, safe_val)

    return {
        "subject": subject,
        "html_body": html_body,
        "text_body": text_body,
    }


async def send_templated_email(
    db,
    *,
    organization_id: str,
    trigger_key: str,
    to_addresses,
    variables: Dict[str, Any] | None = None,
    fallback_subject: str = "",
    fallback_html: str = "",
) -> str | None:
    from app.services.email_outbox import enqueue_generic_email

    resolved = await resolve_template(
        db,
        organization_id=organization_id,
        trigger_key=trigger_key,
        variables=variables,
    )

    if resolved:
        subject = resolved["subject"]
        html_body = resolved["html_body"]
        text_body = resolved["text_body"]
    else:
        subject = fallback_subject
        html_body = fallback_html
        text_body = ""

    if not subject and not html_body:
        logger.warning("No template found for trigger_key=%s and no fallback provided", trigger_key)
        return None

    return await enqueue_generic_email(
        db,
        organization_id=organization_id,
        to_addresses=to_addresses,
        subject=subject,
        html_body=html_body,
        text_body=text_body,
        event_type=f"template.{trigger_key}",
    )
