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
from app.routers.auth import router as auth_router
from app.routers.customers import router as customers_router
from app.routers.products import router as products_router
from app.routers.rateplans import router as rateplans_router
from app.routers.inventory import router as inventory_router
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
from app.routers.agency_payment_settings import router as agency_payment_settings_router
from app.routers.hotel_integrations import router as hotel_integrations_router
from app.routers.channels import router as channels_router
from app.routers.internal_ari import router as internal_ari_router
from app.routers.public_booking import router as public_booking_router
from app.routers.hotel_room_types import router as hotel_room_types_router
from app.routers.hotel_rate_plans import router as hotel_rate_plans_router
from app.routers.settlements import hotel_router as hotel_settlements_router
from app.routers.settlements import agency_router as agency_settlements_router
from app.routers.bookings import router as bookings_router
from app.routers.audit import router as audit_router
from app.routers.voucher import router as voucher_router
from app.routers.web_booking import router as web_booking_router
from app.routers.booking_payments import router as booking_payments_router
from app.routers.booking_voucher import router as booking_voucher_router
from app.routers.web_catalog import router as web_catalog_router
from app.routers.public_tours import router as public_tours_router
from app.routers.agency_tours import router as agency_tours_router
from app.routers.public_tour_bookings import router as public_tour_bookings_router
from app.routers.agency_tour_bookings import router as agency_tour_bookings_router
from app.routers.agency_catalog_products import router as agency_catalog_products_router
from app.routers.agency_catalog_variants import router as agency_catalog_variants_router
from app.routers.agency_catalog_bookings import router as agency_catalog_bookings_router
from app.routers.public_vouchers import router as public_vouchers_router
from app.routers.dev_tools import router as dev_tools_router
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
app.include_router(agency_payment_settings_router)
app.include_router(hotel_integrations_router)
app.include_router(channels_router)
app.include_router(internal_ari_router)
app.include_router(public_booking_router)
app.include_router(hotel_room_types_router)
app.include_router(hotel_rate_plans_router)
app.include_router(hotel_settlements_router)
app.include_router(agency_settlements_router)
app.include_router(bookings_router)
app.include_router(audit_router)
app.include_router(voucher_router)
app.include_router(web_booking_router)
app.include_router(booking_payments_router)
app.include_router(booking_voucher_router)
app.include_router(web_catalog_router)
app.include_router(public_tours_router)
app.include_router(agency_tours_router)
app.include_router(public_tour_bookings_router)
app.include_router(agency_tour_bookings_router)
app.include_router(agency_catalog_products_router)
app.include_router(agency_catalog_variants_router)
app.include_router(agency_catalog_bookings_router)
app.include_router(public_vouchers_router)

if os.getenv("ENABLE_DEV_ROUTERS") == "true":
    app.include_router(dev_tools_router)


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
    await ensure_seed_data()
    logger.info("Startup complete")

    # Start background email dispatch loop (FAZ-9.3)
    import asyncio

    asyncio.create_task(email_dispatch_loop())
    asyncio.create_task(integration_sync_loop())


@app.on_event("shutdown")
async def _shutdown() -> None:
    await close_mongo()
    logger.info("Shutdown complete")

