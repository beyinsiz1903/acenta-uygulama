from __future__ import annotations

from fastapi import FastAPI

from app.bootstrap.v1_aliases import register_low_risk_v1_aliases
from app.modules.mobile.router import router as mobile_router


def register_v1_routers(app: FastAPI) -> None:
    # The API versioning middleware rewrites /api/v1/* → /api/*,
    # so routes must be registered at /api/mobile/* (not /api/v1/mobile/*)
    app.include_router(mobile_router, prefix="/api/mobile", tags=["mobile"])
    register_low_risk_v1_aliases(app)
