from __future__ import annotations

from fastapi import FastAPI

from app.modules.mobile.router import router as mobile_router


def register_v1_routers(app: FastAPI) -> None:
    app.include_router(mobile_router, prefix="/api/v1/mobile", tags=["mobile"])