from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    """Simple unauthenticated health endpoint.

    Used to verify that the FastAPI app and ingress routing are working.
    """

    return {"status": "ok"}
