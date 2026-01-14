from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import API_PREFIX, APP_NAME, APP_VERSION, CORS_ORIGINS
from app.db import close_mongo, connect_mongo, get_db
from app.routers.admin import router as admin_router
from app.routers.admin_catalog import router as admin_catalog_router
from app.routers.admin_metrics import router as admin_metrics_router
from app.routers.admin_pricing import router as admin_pricing_router
from app.routers.auth import router as auth_router
from app.routers.b2b_bookings import router as b2b_bookings_router
from app.routers.b2b_bookings_list import router as b2b_bookings_list_router
from app.routers.b2b_hotels_search import router as b2b_hotels_search_router
from app.routers.b2b_quotes import router as b2b_quotes_router
from app.routers.bookings import router as bookings_router
from app.routers.booking_outcomes import router as booking_outcomes_router
from app.routers.inbox import router as inbox_router
from app.routers.matches import router as matches_router
from app.routers.ops_b2b import router as ops_b2b_router
from app.routers.ops_booking_events import router as ops_booking_events_router
from app.routers.ops_finance import router as ops_finance_router
from app.routers.payments import router as payments_router
from app.routers.payments_stripe import router as payments_stripe_router
from app.routers.products import router as products_router
from app.routers.public_click_to_pay import router as public_click_to_pay_router
from app.routers.public_my_booking import router as public_my_booking_router
from app.routers.public_search import router as public_search_router
from app.routers.public_checkout import router as public_checkout_router
from app.routers.public_bookings import router as public_bookings_router
from app.routers.search import router as search_router
from app.routers.vouchers import router as vouchers_router
from app.routers.web_booking import router as web_booking_router
from app.routers.web_catalog import router as web_catalog_router
from app.routers.crm_customers import router as crm_customers_router
from app.routers.crm_deals import router as crm_deals_router
from app.routers.crm_tasks import router as crm_tasks_router
from app.routers.crm_activities import router as crm_activities_router
from app.routers.crm_events import router as crm_events_router
from app.email_worker import email_dispatch_loop
from app.indexes import finance_indexes, inbox_indexes, pricing_indexes, public_indexes, voucher_indexes
from app.indexes import crm_indexes
from app.integration_sync_worker import integration_sync_loop


@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_mongo()
    db = await get_db()

    # Ensure indexes at startup for critical collections
    await finance_indexes.ensure_finance_indexes(db)
    await inbox_indexes.ensure_inbox_indexes(db)
    await pricing_indexes.ensure_pricing_indexes(db)
    await voucher_indexes.ensure_voucher_indexes(db)
    await public_indexes.ensure_public_indexes(db)
    await crm_indexes.ensure_crm_indexes(db)

    yield

    await close_mongo()


app = FastAPI(
    title=APP_NAME,
    version=APP_VERSION,
    lifespan=lifespan,
    openapi_url=f"{API_PREFIX}/openapi.json",
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router, prefix=API_PREFIX)
app.include_router(admin_router, prefix=API_PREFIX)
app.include_router(admin_catalog_router, prefix=API_PREFIX)
app.include_router(admin_metrics_router, prefix=API_PREFIX)
app.include_router(admin_pricing_router, prefix=API_PREFIX)
app.include_router(b2b_bookings_router, prefix=API_PREFIX)
app.include_router(b2b_bookings_list_router, prefix=API_PREFIX)
app.include_router(b2b_hotels_search_router, prefix=API_PREFIX)
app.include_router(b2b_quotes_router, prefix=API_PREFIX)
app.include_router(bookings_router, prefix=API_PREFIX)
app.include_router(booking_outcomes_router, prefix=API_PREFIX)
app.include_router(inbox_router, prefix=API_PREFIX)
app.include_router(matches_router, prefix=API_PREFIX)
app.include_router(ops_b2b_router)  # No prefix - router has its own
app.include_router(ops_booking_events_router, prefix=API_PREFIX)
app.include_router(ops_finance_router, prefix=API_PREFIX)
app.include_router(payments_router, prefix=API_PREFIX)
app.include_router(payments_stripe_router, prefix=API_PREFIX)
app.include_router(products_router, prefix=API_PREFIX)
app.include_router(public_click_to_pay_router)  # No prefix - router has its own
app.include_router(public_my_booking_router)    # No prefix - router has its own
app.include_router(public_search_router)        # No prefix - router has its own
app.include_router(public_checkout_router)      # No prefix - router has its own
app.include_router(public_bookings_router)      # No prefix - router has its own
app.include_router(search_router, prefix=API_PREFIX)
app.include_router(vouchers_router, prefix=API_PREFIX)
app.include_router(web_booking_router, prefix=API_PREFIX)
app.include_router(web_catalog_router, prefix=API_PREFIX)
app.include_router(crm_customers_router)
app.include_router(crm_deals_router)
app.include_router(crm_tasks_router)
app.include_router(crm_activities_router)
app.include_router(crm_events_router)

app.include_router(auth_router)


@app.get("/")
async def read_root() -> dict[str, str]:
    return {"message": f"{APP_NAME} is running", "version": APP_VERSION}


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}


if os.environ.get("ENABLE_EMAIL_WORKER") == "1":
    email_dispatch_loop()

if os.environ.get("ENABLE_INTEGRATION_SYNC_WORKER") == "1":
    integration_sync_loop()
