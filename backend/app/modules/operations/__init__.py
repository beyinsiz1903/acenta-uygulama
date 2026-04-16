"""Operations domain — ops cases, tasks, incidents, booking events, tickets.

Phase 2, Dalga 5 additions: tickets.
Phase 3: transfers, guides, vehicles, flights, visa, insurance, calendar, email-templates.
"""
from fastapi import APIRouter

from app.config import API_PREFIX

from app.modules.operations.routers.ops_cases import router as ops_cases_router
from app.modules.operations.routers.ops_tasks import router as ops_tasks_router
from app.modules.operations.routers.ops_incidents import router as ops_incidents_router
from app.modules.operations.routers.ops_booking_events import router as ops_booking_events_router

# --- Phase 2, Dalga 5 ---
from app.modules.operations.routers.tickets import router as tickets_router

# --- Phase 3: New modules ---
from app.modules.operations.routers.admin_transfers import router as admin_transfers_router
from app.modules.operations.routers.admin_guides import router as admin_guides_router
from app.modules.operations.routers.admin_vehicles import router as admin_vehicles_router
from app.modules.operations.routers.admin_flights import router as admin_flights_router
from app.modules.operations.routers.admin_visa import router as admin_visa_router
from app.modules.operations.routers.admin_insurance import router as admin_insurance_router
from app.modules.operations.routers.calendar import router as calendar_router
from app.modules.operations.routers.admin_email_templates import router as admin_email_templates_router
from app.modules.operations.routers.admin_portal_management import router as admin_portal_management_router
from app.modules.operations.routers.admin_activities import router as admin_activities_router

domain_router = APIRouter()
domain_router.include_router(ops_cases_router)
domain_router.include_router(ops_tasks_router)
domain_router.include_router(ops_incidents_router)
domain_router.include_router(ops_booking_events_router, prefix=API_PREFIX)
domain_router.include_router(tickets_router)

# Phase 3 routers (all have /api/* built-in prefix)
domain_router.include_router(admin_transfers_router)
domain_router.include_router(admin_guides_router)
domain_router.include_router(admin_vehicles_router)
domain_router.include_router(admin_flights_router)
domain_router.include_router(admin_visa_router)
domain_router.include_router(admin_insurance_router)
domain_router.include_router(calendar_router)
domain_router.include_router(admin_email_templates_router)
domain_router.include_router(admin_portal_management_router)
domain_router.include_router(admin_activities_router)
