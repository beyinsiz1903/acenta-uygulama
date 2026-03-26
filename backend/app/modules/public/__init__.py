"""Public domain — storefront, public search, checkout, booking view, tours, SEO.

Owner: Public Domain
Boundary: All public-facing endpoints — storefront, campaigns, checkout,
          booking view, partner pages, search, tours, SEO.

Phase 2, Dalga 5 consolidation.
"""
from fastapi import APIRouter

from app.config import API_PREFIX

from app.modules.public.routers.public_bookings import router as public_bookings_router
from app.modules.public.routers.public_campaigns import router as public_campaigns_router
from app.modules.public.routers.public_checkout import router as public_checkout_router
from app.modules.public.routers.public_cms_pages import router as public_cms_pages_router
from app.modules.public.routers.public_my_booking import router as public_my_booking_router
from app.modules.public.routers.public_partners import router as public_partners_router
from app.modules.public.routers.public_search import router as public_search_router
from app.modules.public.routers.public_tours import router as public_tours_router
from app.modules.public.routers.storefront import router as storefront_router
from app.modules.public.routers.seo import router as seo_router
from app.modules.public.routers.tours_browse import router as tours_browse_router
from app.modules.public.routers.web_booking import router as web_booking_router
from app.modules.public.routers.web_catalog import router as web_catalog_router

domain_router = APIRouter()

# Public endpoints (all have /api/* built-in prefix)
domain_router.include_router(public_bookings_router)
domain_router.include_router(public_campaigns_router)
domain_router.include_router(public_checkout_router)
domain_router.include_router(public_cms_pages_router)
domain_router.include_router(public_my_booking_router)
domain_router.include_router(public_partners_router)
domain_router.include_router(public_search_router)
domain_router.include_router(public_tours_router)
domain_router.include_router(storefront_router)
domain_router.include_router(seo_router)
domain_router.include_router(tours_browse_router)
domain_router.include_router(web_booking_router, prefix=API_PREFIX)   # /web/booking → /api/web/booking
domain_router.include_router(web_catalog_router, prefix=API_PREFIX)   # /web/catalog → /api/web/catalog
