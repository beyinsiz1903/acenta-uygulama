"""Paximum integration errors."""
from __future__ import annotations


class PaximumError(Exception):
    """Raised when a Paximum API call fails or is misconfigured."""

    def __init__(self, status_code: int, message: str, payload: dict | None = None):
        self.status_code = status_code
        self.message = message
        self.payload = payload or {}
        super().__init__(f"[{status_code}] {message}")
