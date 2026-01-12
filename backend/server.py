from __future__ import annotations

import os
import logging
from pathlib import Path
from typing import Any, Optional

from dotenv import load_dotenv
from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from app.db import close_mongo, connect_mongo, get_db
from app.seed import ensure_seed_data
from app.indexes.catalog_indexes import ensure_catalog_indexes
from app.indexes.pricing_indexes import ensure_pricing_indexes
from app.indexes.finance_indexes import ensure_finance_indexes
from app.indexes.phase2a_indexes import ensure_phase2a_indexes
from app.indexes.voucher_indexes import ensure_voucher_indexes
from app.indexes.public_indexes import ensure_public_indexes
from app.indexes.inbox_indexes import ensure_inbox_indexes
from app.indexes.coupon_indexes import ensure_coupon_indexes
from app.exception_handlers import register_exception_handlers
from app.config import ENABLE_VOUCHER_PDF, ENABLE_SELF_SERVICE_PORTAL, ENABLE_PARTNER_API
from app.routers.auth import router as auth_router
from app.routers.customers import router as customers_router
from app.routers.products import router as products_router
from app.routers.rateplans import router as rateplans_router
from app.routers.inventory import router as inventory_router
from app.routers.inbox import router as inbox_router
from app.routers.reservations import router as reservations_router
from app.routers.leads import router as leads_router
from app.routers.quotes import router as quotes_router
from app.routers.payments import router as payments_router
from app.routers.b2b import router as b2b_router
from app.routers.admin import router as admin_router
from app.routers.admin_metrics import router as admin_metrics_router
from app.routers.admin_demo_seed import router as admin_demo_seed_router
from app.routers.admin_insights import router as admin_insights_router
from app.routers.agency import router as agency_router
from app.routers.search import router as search_router
from app.routers.agency_booking import router as agency_booking_router
from app.routers.reports import router as reports_router
from app.routers.settings import router as settings_router
from app.routers.hotel import router as hotel_router
from app.routers.hotel_integrations import router as hotel_integrations_router
from app.routers.settlements import hotel_router as hotel_settlements_router
from app.routers.settlements import agency_router as agency_settlements_router
from app.routers.bookings import router as bookings_router
from app.routers.booking_outcomes import router as booking_outcomes_router
from app.routers.action_policies import router as action_policies_router
from app.routers.approval_tasks import router as approval_tasks_router
from app.routers.audit import router as audit_router
from app.routers.voucher import router as voucher_router
from app.routers.admin_catalog import router as admin_catalog_router
from app.routers.admin_pricing import router as admin_pricing_router
from app.routers.web_booking import router as web_booking_router
from app.routers.risk_snapshots import router as risk_snapshots_router
from app.routers.web_catalog import router as web_catalog_router
from app.routers.matches import router as matches_router
from app.routers.match_alerts import router as match_alerts_router
from app.routers.match_unblock import router as match_unblock_router
from app.routers.exports import router as exports_router, public_router as exports_public_router
from app.routers.admin_reports import router as admin_reports_router
from app.routers.demo_scale_ui_proof import router as demo_scale_ui_proof_router
from app.routers.public_my_booking import router as public_my_booking_router
from app.routers.b2b_quotes import router as b2b_quotes_router
from app.routers.b2b_bookings import router as b2b_bookings_router
from app.routers.b2b_cancel import router as b2b_cancel_router
from app.routers.ops_b2b import router as ops_b2b_router
from app.routers.ops_finance import router as ops_finance_router
from app.routers.vouchers import router as vouchers_router
from app.routers.b2b_bookings_list import router as b2b_bookings_list_router
from app.routers.ops_booking_events import router as ops_booking_events_router
from app.routers.b2b_hotels_search import router as b2b_hotels_search_router
from app.routers.ops_click_to_pay import router as ops_click_to_pay_router
from app.routers.public_click_to_pay import router as public_click_to_pay_router
from app.routers.public_search import router as public_search_router
from app.email_worker import email_dispatch_loop
from app.integration_sync_worker import integration_sync_loop

ROOT_DIR = Path(__file__).parent

# Load .env only if exists (development fallback)
# Production: Kubernetes secrets inject env vars directly
env_path = ROOT_DIR / ".env"
if env_path.exists():
    load_dotenv(env_path)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("acenta-master")

app = FastAPI(title="Acenta Master API", version="0.1.0")

# Register global exception handlers for unified error responses
register_exception_handlers(app)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers (/api prefix is on each router)
app.include_router(auth_router)
app.include_router(customers_router)
app.include_router(products_router)
app.include_router(rateplans_router)
app.include_router(inventory_router)
app.include_router(inbox_router)
app.include_router(reservations_router)
app.include_router(leads_router)
app.include_router(quotes_router)
app.include_router(payments_router)
app.include_router(b2b_router)
app.include_router(admin_router)
app.include_router(admin_metrics_router)
app.include_router(admin_demo_seed_router)
app.include_router(admin_insights_router)
app.include_router(agency_router)
app.include_router(search_router)
app.include_router(agency_booking_router)
app.include_router(reports_router)
app.include_router(settings_router)
app.include_router(hotel_router)
app.include_router(hotel_integrations_router)
app.include_router(hotel_settlements_router)
app.include_router(agency_settlements_router)
app.include_router(bookings_router)
app.include_router(booking_outcomes_router)
app.include_router(action_policies_router)
app.include_router(approval_tasks_router)
app.include_router(audit_router)
if ENABLE_VOUCHER_PDF:
    app.include_router(voucher_router)
else:
    logger.info("[config] ENABLE_VOUCHER_PDF is false - voucher routes disabled")

app.include_router(admin_catalog_router)
app.include_router(admin_pricing_router)

if ENABLE_SELF_SERVICE_PORTAL:
    app.include_router(web_booking_router)
    app.include_router(web_catalog_router)
else:
    logger.info("[config] ENABLE_SELF_SERVICE_PORTAL is false - web booking/catalog routes disabled")

app.include_router(risk_snapshots_router)
app.include_router(matches_router)
app.include_router(match_alerts_router)
app.include_router(match_unblock_router)

app.include_router(exports_router)

if ENABLE_PARTNER_API:
    app.include_router(exports_public_router)
    app.include_router(public_my_booking_router)
else:
    logger.info("[config] ENABLE_PARTNER_API is false - public export routes disabled")

app.include_router(admin_reports_router)
app.include_router(demo_scale_ui_proof_router)
app.include_router(b2b_quotes_router)
app.include_router(b2b_bookings_router)
app.include_router(b2b_cancel_router)
app.include_router(ops_b2b_router)
app.include_router(ops_finance_router)
app.include_router(vouchers_router)
app.include_router(b2b_bookings_list_router)
app.include_router(ops_booking_events_router)
from app.routers.ops_cases import router as ops_cases_router
from app.routers.payments_stripe import router as payments_stripe_router

app.include_router(b2b_hotels_search_router)
app.include_router(ops_cases_router)
app.include_router(payments_stripe_router)
app.include_router(ops_click_to_pay_router)
app.include_router(public_click_to_pay_router)
app.include_router(public_search_router)


@app.get("/api/health")
async def health() -> dict[str, Any]:
    """Main health check with database ping"""
    db = await get_db()
    ok = False
    try:
        await db.command("ping")
        ok = True
    except Exception:
        ok = False
    return {"ok": ok, "service": "acenta-master"}


# Deployment health check aliases (for Emergent/Kubernetes compatibility)
@app.get("/health")
@app.get("/health/")
async def deployment_health() -> dict[str, Any]:
    """Simple health check for deployment platforms"""
    return {"ok": True, "service": "acenta-master", "status": "healthy"}


@app.on_event("startup")
async def _startup() -> None:
    await connect_mongo()

    # Use shared DB instance for seed + indexes
    db = await get_db()
    await ensure_seed_data()
    await ensure_catalog_indexes(db)
    await ensure_pricing_indexes(db)
    await ensure_finance_indexes(db)
    await ensure_phase2a_indexes(db)
    await ensure_voucher_indexes(db)
    await ensure_public_indexes(db)
    await ensure_inbox_indexes(db)
    await ensure_coupon_indexes(db)

    logger.info("Startup complete")

    # Start background email dispatch loop (FAZ-9.3)
    import asyncio

    asyncio.create_task(email_dispatch_loop())
    asyncio.create_task(integration_sync_loop())


@app.on_event("shutdown")
async def _shutdown() -> None:
    await close_mongo()
    logger.info("Shutdown complete")
