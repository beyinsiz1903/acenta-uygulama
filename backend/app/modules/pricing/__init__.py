"""Pricing domain — pricing engine, rules, quotes, offers, marketplace.

Owner: Pricing Domain
Boundary: All pricing lifecycle — pricing rules, engine, quotes, offers,
          marketplace listings, and supplier mapping.

Phase 2, Dalga 4 consolidation.
"""
from fastapi import APIRouter

from app.config import API_PREFIX

# --- Core pricing ---
from app.modules.pricing.routers.pricing import router as pricing_router
from app.modules.pricing.routers.pricing_rules import router as pricing_rules_router
from app.modules.pricing.routers.pricing_quote import router as pricing_quote_router
from app.modules.pricing.routers.pricing_engine_router import router as pricing_engine_router

# --- Admin pricing ---
from app.modules.pricing.routers.admin_pricing import router as admin_pricing_router
from app.modules.pricing.routers.admin_pricing_incidents import router as admin_pricing_incidents_router
from app.modules.pricing.routers.admin_pricing_trace import router as admin_pricing_trace_router

# --- Offers & quotes ---
from app.modules.pricing.routers.offers import router as offers_router
from app.modules.pricing.routers.offers_booking import router as offers_booking_router
from app.modules.pricing.routers.quotes import router as quotes_router

# --- Marketplace ---
from app.modules.pricing.routers.marketplace import router as marketplace_router
from app.modules.pricing.routers.marketplace_supplier_mapping import router as marketplace_supplier_mapping_router

domain_router = APIRouter()

# Core pricing (prefix: /pricing → needs /api)
domain_router.include_router(pricing_router, prefix=API_PREFIX)
domain_router.include_router(pricing_rules_router, prefix=API_PREFIX)
domain_router.include_router(pricing_quote_router)       # /api/pricing (built-in)
domain_router.include_router(pricing_engine_router)      # /api/pricing-engine (built-in)

# Admin pricing (all /api/admin/pricing/* built-in)
domain_router.include_router(admin_pricing_router)
domain_router.include_router(admin_pricing_incidents_router)
domain_router.include_router(admin_pricing_trace_router)

# Offers & quotes (/api/offers, /api/bookings, /api/quotes — built-in)
domain_router.include_router(offers_router)
domain_router.include_router(offers_booking_router)
domain_router.include_router(quotes_router)

# Marketplace (/marketplace → needs /api)
domain_router.include_router(marketplace_router, prefix=API_PREFIX)
domain_router.include_router(marketplace_supplier_mapping_router, prefix=API_PREFIX)
