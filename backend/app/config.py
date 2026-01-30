from __future__ import annotations

"""Application-level feature flags and configuration.

FAZ 0: Env-based feature flag structure.

All flags default to **True** so that:
- If no env is set, existing behavior is maintained,
- Only risky modules can be disabled via env override in specific environments.
"""

from typing import Callable
import os


def _env_flag(name: str, default: bool = True) -> bool:
    """Read a boolean-like flag from environment.

    Accepted falsy values: "0", "false", "off", "no" (case-insensitive).
    Anything else (or unset) falls back to `default`.
    """

    raw = os.environ.get(name)
    if raw is None:
        return default
    value = raw.strip().lower()
    if value in {"0", "false", "off", "no"}:
        return False
    if value in {"1", "true", "on", "yes"}:
        return True
    return default


# Application constants
API_PREFIX = "/api"
APP_NAME = "Booking Suite API"
APP_VERSION = "1.0.0"
CORS_ORIGINS = ["*"]  # Allow all origins for development

# Feature flags (FAZ 0)
ENABLE_VOUCHER_PDF: bool = _env_flag("ENABLE_VOUCHER_PDF", default=True)
ENABLE_SELF_SERVICE_PORTAL: bool = _env_flag("ENABLE_SELF_SERVICE_PORTAL", default=True)
ENABLE_PARTNER_API: bool = _env_flag("ENABLE_PARTNER_API", default=True)
ENABLE_INBOX: bool = _env_flag("ENABLE_INBOX", default=True)
ENABLE_COUPONS: bool = _env_flag("ENABLE_COUPONS", default=True)
MYBOOKING_REQUIRE_EMAIL: bool = _env_flag("MYBOOKING_REQUIRE_EMAIL", default=False)


# External supplier configuration
PAXIMUM_BASE_URL = os.environ.get("PAXIMUM_BASE_URL", "https://api.stage.paximum.com")
PAXIMUM_API_KEY = os.environ.get("PAXIMUM_API_KEY", "")
PAXIMUM_TIMEOUT_SECONDS = float(os.environ.get("PAXIMUM_TIMEOUT_SECONDS", "10"))
