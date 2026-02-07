"""Enterprise Health endpoints (E3.2).

GET /api/health/live  - Simple liveness
GET /api/health/ready - Readiness (check DB)
"""
from __future__ import annotations

from fastapi import APIRouter

from app.db import get_db

router = APIRouter(prefix="/api/health", tags=["enterprise_health"])


@router.get("/live")
async def liveness():
    """Simple liveness check. Always returns 200 if app is running."""
    return {"status": "alive"}


@router.get("/ready")
async def readiness():
    """Readiness check. Verifies DB connectivity."""
    try:
        db = await get_db()
        # Simple ping to verify MongoDB is responsive
        await db.command("ping")
        return {"status": "ready", "database": "connected"}
    except Exception as e:
        return {"status": "not_ready", "database": "disconnected", "error": str(e)}
