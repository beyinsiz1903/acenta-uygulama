from __future__ import annotations

import logging
import sys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import CORS_ORIGINS
from app.middleware.correlation_id import CorrelationIdMiddleware
from app.middleware.error_tracking_middleware import ErrorTrackingMiddleware
from app.middleware.ip_whitelist_middleware import IPWhitelistMiddleware
from app.middleware.prometheus_middleware import PrometheusMiddleware
from app.middleware.rate_limit_middleware import RateLimitMiddleware
from app.middleware.security_headers_middleware import SecurityHeadersMiddleware
from app.middleware.structured_logging_middleware import StructuredLoggingMiddleware
from app.middleware.tenant_middleware import TenantResolutionMiddleware


def configure_middlewares(app: FastAPI) -> None:
    app.add_middleware(CorrelationIdMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(ErrorTrackingMiddleware)
    app.add_middleware(PrometheusMiddleware)
    app.add_middleware(StructuredLoggingMiddleware)
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(IPWhitelistMiddleware)
    app.add_middleware(TenantResolutionMiddleware)

    cors_logger = logging.getLogger("cors")
    if CORS_ORIGINS == ["*"]:
        cors_logger.warning("CORS: Allowing all origins (development/preview mode). Set CORS_ORIGINS env for production.")
        print("[CORS] Mode: allow-all", file=sys.stderr)
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=False,
            allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH"],
            allow_headers=["*"],
            expose_headers=["X-Request-ID", "X-RateLimit-Policy"],
        )
        return

    cors_logger.info("CORS: Whitelisted %d domains: %s", len(CORS_ORIGINS), CORS_ORIGINS)
    print(f"[CORS] Mode: whitelist ({len(CORS_ORIGINS)} domains)", file=sys.stderr)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID", "X-RateLimit-Policy"],
    )
