from __future__ import annotations

"""Compat API entrypoint.

`server:app` remains available for backward compatibility only.
The long-term API runtime target is `app.bootstrap.api_app:create_app`.
"""

from app.bootstrap.api_app import app

__all__ = ["app"]

