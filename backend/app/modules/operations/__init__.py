"""Operations domain — ops cases, tasks, incidents, booking events, tickets.

Phase 2, Dalga 5 additions: tickets.
"""
from fastapi import APIRouter

from app.config import API_PREFIX

from app.modules.operations.routers.ops_cases import router as ops_cases_router
from app.modules.operations.routers.ops_tasks import router as ops_tasks_router
from app.modules.operations.routers.ops_incidents import router as ops_incidents_router
from app.modules.operations.routers.ops_booking_events import router as ops_booking_events_router

# --- Phase 2, Dalga 5 ---
from app.modules.operations.routers.tickets import router as tickets_router

domain_router = APIRouter()
domain_router.include_router(ops_cases_router)
domain_router.include_router(ops_tasks_router)
domain_router.include_router(ops_incidents_router)
domain_router.include_router(ops_booking_events_router, prefix=API_PREFIX)
domain_router.include_router(tickets_router)
