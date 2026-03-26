"""B2B domain — all B2B network, marketplace, exchange, partner routers.

Phase 2, Dalga 5 additions: partner_graph, partner_v1, admin_partners.
"""
from fastapi import APIRouter

from app.config import API_PREFIX

from app.routers.b2b import router as b2b_router
from app.routers.b2b_bookings import router as b2b_bookings_router
from app.routers.b2b_bookings_list import router as b2b_bookings_list_router
from app.routers.b2b_cancel import router as b2b_cancel_router
from app.routers.b2b_quotes import router as b2b_quotes_router
from app.routers.b2b_hotels_search import router as b2b_hotels_search_router
from app.routers.b2b_portal import router as b2b_portal_router
from app.routers.b2b_announcements import router as b2b_announcements_router
from app.routers.b2b_events import router as b2b_events_router
from app.routers.b2b_exchange import router as b2b_exchange_router
from app.routers.b2b_marketplace_booking import router as b2b_marketplace_booking_router
from app.routers.b2b_network_bookings import router as b2b_network_bookings_router
from app.routers.admin_b2b_agencies import router as admin_b2b_agencies_router
from app.routers.admin_b2b_announcements import router as admin_b2b_announcements_router
from app.routers.admin_b2b_discounts import router as admin_b2b_discounts_router
from app.routers.admin_b2b_funnel import router as admin_b2b_funnel_router
from app.routers.admin_b2b_marketplace import router as admin_b2b_marketplace_router
from app.routers.admin_b2b_pricing import router as admin_b2b_pricing_router
from app.routers.admin_b2b_visibility import router as admin_b2b_visibility_router
from app.routers.ops_b2b import router as ops_b2b_router

# --- Phase 2, Dalga 5 additions ---
from app.routers.partner_graph import router as partner_graph_router
from app.routers.partner_v1 import router as partner_v1_router
from app.routers.admin_partners import router as admin_partners_router

domain_router = APIRouter()
domain_router.include_router(b2b_router)
domain_router.include_router(b2b_bookings_router)
domain_router.include_router(b2b_bookings_list_router)
domain_router.include_router(b2b_cancel_router)
domain_router.include_router(b2b_quotes_router)
domain_router.include_router(b2b_hotels_search_router)
domain_router.include_router(b2b_portal_router)
domain_router.include_router(b2b_announcements_router)
domain_router.include_router(b2b_events_router)
domain_router.include_router(b2b_exchange_router)
domain_router.include_router(b2b_marketplace_booking_router, prefix=API_PREFIX)
domain_router.include_router(b2b_network_bookings_router)
domain_router.include_router(admin_b2b_agencies_router)
domain_router.include_router(admin_b2b_announcements_router)
domain_router.include_router(admin_b2b_discounts_router)
domain_router.include_router(admin_b2b_funnel_router)
domain_router.include_router(admin_b2b_marketplace_router)
domain_router.include_router(admin_b2b_pricing_router)
domain_router.include_router(admin_b2b_visibility_router)
domain_router.include_router(ops_b2b_router)

# Partner network
domain_router.include_router(partner_graph_router)
domain_router.include_router(partner_v1_router)
domain_router.include_router(admin_partners_router)
