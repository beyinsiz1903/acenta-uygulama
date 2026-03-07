from __future__ import annotations

from datetime import datetime, timezone
from email.utils import format_datetime

from fastapi import Response


def build_compat_headers(successor_path: str, *, sunset_at: datetime | None = None) -> dict[str, str]:
    if not successor_path.startswith("/"):
        raise ValueError("successor_path must start with '/'")

    headers = {
        "Deprecation": "true",
        "Link": f'<{successor_path}>; rel="successor-version"',
    }

    if sunset_at is not None:
        headers["Sunset"] = format_datetime(sunset_at.astimezone(timezone.utc), usegmt=True)

    return headers


def apply_compat_headers(response: Response, successor_path: str, *, sunset_at: datetime | None = None) -> Response:
    for key, value in build_compat_headers(successor_path, sunset_at=sunset_at).items():
        response.headers[key] = value
    return response
