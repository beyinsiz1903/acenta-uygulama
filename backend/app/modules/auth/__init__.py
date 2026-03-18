"""Auth domain — aggregates all authentication/authorization routers."""
from fastapi import APIRouter

from app.routers.auth import router as auth_core_router
from app.routers.auth_password_reset import router as password_reset_router
from app.routers.enterprise_2fa import router as enterprise_2fa_router

domain_router = APIRouter()
domain_router.include_router(auth_core_router)
domain_router.include_router(password_reset_router)
domain_router.include_router(enterprise_2fa_router)
