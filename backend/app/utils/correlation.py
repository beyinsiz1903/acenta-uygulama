from __future__ import annotations

from typing import Optional
from uuid import uuid4

from fastapi import Request


def get_or_create_correlation_id(request: Optional[Request], provided: Optional[str] = None) -> str:
    """Resolve correlation_id from header/body or generate a new one.

    Precedence:
    1) X-Correlation-Id header (if present and non-empty)
    2) provided argument (e.g. body.correlation_id)
    3) generated `fc_<uuid4hex>`
    """

    # 1) Header wins if present
    try:
        if request is not None:
            header_val = request.headers.get("X-Correlation-Id") or request.headers.get("x-correlation-id")
            if header_val and isinstance(header_val, str):
                header_val = header_val.strip()
                if header_val:
                    return header_val
    except Exception:
        # Ignore header parsing issues, fall back to provided / generated
        pass

    # 2) Body-provided / explicit value
    if provided:
        val = str(provided).strip()
        if val:
            return val

    # 3) Generate new
    return f"fc_{uuid4().hex}"
