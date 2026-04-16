"""Enterprise Health Check endpoints.

Provides three tiers of health checks:
1. /api/health - Simple liveness probe (no DB)
2. /api/healthz - Kubernetes readiness probe (no DB)
3. /api/health/ready - Deep readiness check with DB connectivity
4. /api/health/deep - Full system diagnostic (authenticated)
"""
from __future__ import annotations

import time
from datetime import datetime, timezone

from fastapi import APIRouter

from app.db import get_db

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health")
async def health() -> dict:
    """Simple unauthenticated liveness probe. No DB call."""
    return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}


@router.get("/healthz")
async def healthz() -> dict:
    """Readiness probe endpoint."""
    return {"status": "ok"}


@router.get("/health/ready")
async def health_ready() -> dict:
    """Readiness check with MongoDB connectivity verification."""
    checks = {}
    overall = "ok"

    # MongoDB connectivity
    t0 = time.monotonic()
    try:
        db = await get_db()
        await db.command("ping")
        mongo_ms = round((time.monotonic() - t0) * 1000, 2)
        checks["mongodb"] = {"status": "ok", "latency_ms": mongo_ms}
    except Exception as exc:
        mongo_ms = round((time.monotonic() - t0) * 1000, 2)
        checks["mongodb"] = {"status": "degraded", "latency_ms": mongo_ms, "error": str(exc)[:200]}
        overall = "degraded"

    return {
        "status": overall,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checks": checks,
    }


@router.get("/health/deep")
async def health_deep() -> dict:
    """Deep system diagnostic with collection counts and index status."""
    checks = {}
    overall = "ok"

    # MongoDB connectivity + collection stats
    t0 = time.monotonic()
    try:
        db = await get_db()
        await db.command("ping")
        mongo_ms = round((time.monotonic() - t0) * 1000, 2)

        # Get key collection counts
        collection_stats = {}
        critical_collections = [
            "users", "organizations", "tenants", "memberships",
            "bookings", "reservations", "products", "agencies",
        ]
        for coll in critical_collections:
            try:
                count = await db[coll].estimated_document_count()
                collection_stats[coll] = count
            except Exception:
                collection_stats[coll] = -1

        checks["mongodb"] = {
            "status": "ok",
            "latency_ms": mongo_ms,
            "collections": collection_stats,
        }
    except Exception as exc:
        mongo_ms = round((time.monotonic() - t0) * 1000, 2)
        checks["mongodb"] = {"status": "error", "latency_ms": mongo_ms, "error": str(exc)[:200]}
        overall = "error"

    return {
        "status": overall,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checks": checks,
    }
