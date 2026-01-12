from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import API_PREFIX, APP_NAME, APP_VERSION, CORS_ORIGINS
from app.db import close_mongo, connect_mongo, get_db
from app.routers.admin import router as admin_router
from app.routers.admin_catalog import router as admin_catalog_router
from app.routers.admin_inbox import router as admin_inbox_router
from app.routers.admin_metrics import router as admin_metrics_router
from app.routers.admin_org import router as admin_org_router
from app.routers.admin_pricing import router as admin_pricing_router
from app.routers.admin_products import router as admin_products_router
from app.routers.admin_users import router as admin_users_router
from app.routers.admin_workflows import router as admin_workflows_router
from app.routers.analysis import router as analysis_router
from app.routers.auth import router as auth_router
from app.routers.b2b_bookings import router as b2b_bookings_router
from app.routers.b2b_bookings_list import router as b2b_bookings_list_router
from app.routers.b2b_hotels_search import router as b2b_hotels_search_router
from app.routers.bookings import router as bookings_router
from app.routers.booking_outcomes import router as booking_outcomes_router
from app.routers.coupons import router as coupons_router
from app.routers.deals import router as deals_router
from app.routers.demo import router as demo_router
from app.routers.ledger import router as ledger_router
from app.routers.matches import router as matches_router
from app.routers.ops_b2b import router as ops_b2b_router
from app.routers.ops_booking_events import router as ops_booking_events_router
from app.routers.ops_finance import router as ops_finance_router
from app.routers.ops_inbox import router as ops_inbox_router
from app.routers.ops_unified import router as ops_unified_router
from app.routers.payments import router as payments_router
from app.routers.payments_stripe import router as payments_stripe_router
from app.routers.pricing import router as pricing_router
from app.routers.products import router as products_router
from app.routers.public_click_to_pay import router as public_click_to_pay_router
from app.routers.public_my_booking import router as public_my_booking_router
from app.routers.public_search import router as public_search_router
from app.routers.public_checkout import router as public_checkout_router
from app.routers.search import router as search_router
from app.routers.supplier import router as supplier_router
from app.routers.vouchers import router as vouchers_router
from app.routers.web_booking import router as web_booking_router
from app.routers.web_catalog import router as web_catalog_router
from app.email_worker import email_dispatch_loop
from app.indexes import finance_indexes, inbox_indexes, pricing_indexes, public_indexes, voucher_indexes
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
app.include_router(admin_inbox_router, prefix=API_PREFIX)
app.include_router(admin_metrics_router, prefix=API_PREFIX)
app.include_router(admin_org_router, prefix=API_PREFIX)
app.include_router(admin_pricing_router, prefix=API_PREFIX)
app.include_router(admin_products_router, prefix=API_PREFIX)
app.include_router(admin_users_router, prefix=API_PREFIX)
app.include_router(admin_workflows_router, prefix=API_PREFIX)
app.include_router(analysis_router, prefix=API_PREFIX)
app.include_router(b2b_bookings_router, prefix=API_PREFIX)
app.include_router(b2b_bookings_list_router, prefix=API_PREFIX)
app.include_router(b2b_hotels_search_router, prefix=API_PREFIX)
app.include_router(bookings_router, prefix=API_PREFIX)
app.include_router(booking_outcomes_router, prefix=API_PREFIX)
app.include_router(coupons_router, prefix=API_PREFIX)
app.include_router(deals_router, prefix=API_PREFIX)
app.include_router(demo_router, prefix=API_PREFIX)
app.include_router(ledger_router, prefix=API_PREFIX)
app.include_router(matches_router, prefix=API_PREFIX)
app.include_router(ops_b2b_router, prefix=API_PREFIX)
app.include_router(ops_booking_events_router, prefix=API_PREFIX)
app.include_router(ops_finance_router, prefix=API_PREFIX)
app.include_router(ops_inbox_router, prefix=API_PREFIX)
app.include_router(ops_unified_router, prefix=API_PREFIX)
app.include_router(payments_router, prefix=API_PREFIX)
app.include_router(payments_stripe_router, prefix=API_PREFIX)
app.include_router(pricing_router, prefix=API_PREFIX)
app.include_router(products_router, prefix=API_PREFIX)
app.include_router(public_click_to_pay_router, prefix=API_PREFIX)
app.include_router(public_my_booking_router, prefix=API_PREFIX)
app.include_router(public_search_router, prefix=API_PREFIX)
app.include_router(public_checkout_router, prefix=API_PREFIX)
app.include_router(search_router, prefix=API_PREFIX)
app.include_router(supplier_router, prefix=API_PREFIX)
app.include_router(vouchers_router, prefix=API_PREFIX)
app.include_router(web_booking_router, prefix=API_PREFIX)
app.include_router(web_catalog_router, prefix=API_PREFIX)

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
