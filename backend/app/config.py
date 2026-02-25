from __future__ import annotations

"""Application-level feature flags and configuration.

FAZ 0: Env-based feature flag structure.

All flags default to **True** so that:
- If no env is set, existing behavior is maintained,
- Only risky modules can be disabled via env override in specific environments.
"""

import os
from pathlib import Path

# Ensure .env is loaded even when config.py is imported before server.py's load_dotenv
try:
    from dotenv import load_dotenv
    # Try multiple paths to find .env
    for _try_path in [
        Path(__file__).parent.parent / ".env",
        Path("/app/backend/.env"),
    ]:
        if _try_path.exists():
            load_dotenv(_try_path, override=False)
            break
except (ImportError, Exception):
    pass


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
# CORS origins - domain-based whitelist (comma-separated in env, fallback to regex for dev)
_cors_raw = os.environ.get("CORS_ORIGINS", "")
_env = os.environ.get("ENV", "dev").lower()

if _cors_raw and _cors_raw.strip() != "*":
    CORS_ORIGINS = [o.strip() for o in _cors_raw.split(",") if o.strip()]
elif _env in ("production", "prod", "staging"):
    CORS_ORIGINS = [
        "https://agency.syroce.com",
    ]
else:
    CORS_ORIGINS = ["*"]  # Development/preview fallback

# Sentry error tracking
SENTRY_DSN = os.environ.get("SENTRY_DSN", "")
SENTRY_ENVIRONMENT = os.environ.get("SENTRY_ENVIRONMENT", _env)
SENTRY_TRACES_SAMPLE_RATE = float(os.environ.get("SENTRY_TRACES_SAMPLE_RATE", "0.1"))
SENTRY_PROFILES_SAMPLE_RATE = float(os.environ.get("SENTRY_PROFILES_SAMPLE_RATE", "0.1"))

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
