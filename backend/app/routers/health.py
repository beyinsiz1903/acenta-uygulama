from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    """Simple unauthenticated health endpoint.

    Used to verify that the FastAPI app and ingress routing are working.
    """

    return {"status": "ok"}


@router.get("/healthz")
async def healthz() -> dict[str, str]:
    """Kubernetes/Emergent readiness probe endpoint.

    Production deploy logs show the platform probes `/api/healthz` directly.
    Keep this route unauthenticated and lightweight so startup/readiness checks
    can succeed deterministically.
    """

    return {"status": "ok"}


@router.get("/health/ready")
async def health_ready() -> dict[str, str]:
    """Explicit ready endpoint for infrastructure probes."""

    return {"status": "ok"}
