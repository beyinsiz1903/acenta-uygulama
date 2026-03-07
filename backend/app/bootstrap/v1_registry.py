from __future__ import annotations

from fastapi import FastAPI

from app.bootstrap.v1_aliases import register_low_risk_v1_aliases
from app.modules.mobile.router import router as mobile_router


def register_v1_routers(app: FastAPI) -> None:
    app.include_router(mobile_router, prefix="/api/v1/mobile", tags=["mobile"])
    register_low_risk_v1_aliases(app)
