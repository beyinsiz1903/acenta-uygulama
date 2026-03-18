"""Operations domain — ops cases, tasks, incidents, booking events."""
from fastapi import APIRouter

from app.config import API_PREFIX

from app.routers.ops_cases import router as ops_cases_router
from app.routers.ops_tasks import router as ops_tasks_router
from app.routers.ops_incidents import router as ops_incidents_router
from app.routers.ops_booking_events import router as ops_booking_events_router

domain_router = APIRouter()
domain_router.include_router(ops_cases_router)
domain_router.include_router(ops_tasks_router)
domain_router.include_router(ops_incidents_router)
domain_router.include_router(ops_booking_events_router, prefix=API_PREFIX)
