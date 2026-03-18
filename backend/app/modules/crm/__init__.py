"""CRM domain — customers, deals, tasks, activities, notes, timeline, leads."""
from fastapi import APIRouter

from app.routers.crm_customers import router as crm_customers_router
from app.routers.crm_deals import router as crm_deals_router
from app.routers.crm_tasks import router as crm_tasks_router
from app.routers.crm_activities import router as crm_activities_router
from app.routers.crm_notes import router as crm_notes_router
from app.routers.crm_events import router as crm_events_router
from app.routers.crm_timeline import router as crm_timeline_router
from app.routers.crm_customer_inbox import router as crm_customer_inbox_router
from app.routers.customers import router as customers_router
from app.routers.leads import router as leads_router

domain_router = APIRouter()
domain_router.include_router(crm_customers_router)
domain_router.include_router(crm_deals_router)
domain_router.include_router(crm_tasks_router)
domain_router.include_router(crm_activities_router)
domain_router.include_router(crm_notes_router)
domain_router.include_router(crm_events_router)
domain_router.include_router(crm_timeline_router)
domain_router.include_router(crm_customer_inbox_router)
domain_router.include_router(customers_router)
domain_router.include_router(leads_router)
