"""Shared Syroce client errors."""
from __future__ import annotations

from typing import Any, Dict, Optional


class SyroceError(Exception):
    """Marketplace API hatası — http_status + Türkçe detail içerir."""

    def __init__(self, http_status: int, detail: str, payload: Optional[Dict[str, Any]] = None):
        self.http_status = http_status
        self.detail = detail
        self.payload = payload or {}
        super().__init__(f"[{http_status}] {detail}")
