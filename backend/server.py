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
from app.routers.agency import router as agency_router
from app.routers.search import router as search_router
from app.routers.reports import router as reports_router
from app.routers.settings import router as settings_router

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

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
app.include_router(agency_router)
app.include_router(reports_router)
app.include_router(settings_router)


@app.get("/api/health")
async def health() -> dict[str, Any]:
    db = await get_db()
    ok = False
    try:
        await db.command("ping")
        ok = True
    except Exception:
        ok = False
    return {"ok": ok, "service": "acenta-master"}


@app.on_event("startup")
async def _startup() -> None:
    await connect_mongo()
    await ensure_seed_data()
    logger.info("Startup complete")


@app.on_event("shutdown")
async def _shutdown() -> None:
    await close_mongo()
    logger.info("Shutdown complete")
