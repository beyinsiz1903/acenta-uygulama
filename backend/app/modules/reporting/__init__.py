"""Reporting domain — reports, advanced reports, exports, analytics, dashboard.

Owner: Reporting Domain
Boundary: All reporting and analytics — standard reports, advanced reports,
          data exports, analytics, dashboard, insights, funnel.

Phase 2, Dalga 5 consolidation.
"""
from fastapi import APIRouter

from app.routers.reports import router as reports_router
from app.routers.advanced_reports import router as advanced_reports_router
from app.routers.exports import router as exports_router
from app.routers.exports import public_router as public_exports_router
from app.routers.admin_analytics import router as admin_analytics_router
from app.routers.admin_reporting import router as admin_reporting_router
from app.routers.admin_reports import router as admin_reports_router
from app.routers.admin_funnel import router as admin_funnel_router
from app.routers.admin_insights import router as admin_insights_router
from app.routers.dashboard_enhanced import router as dashboard_enhanced_router
from app.routers.revenue_router import router as revenue_router

domain_router = APIRouter()

# Reports (all /api/* built-in)
domain_router.include_router(reports_router)
domain_router.include_router(advanced_reports_router)
domain_router.include_router(exports_router)
domain_router.include_router(public_exports_router)

# Admin analytics & reporting
domain_router.include_router(admin_analytics_router)
domain_router.include_router(admin_reporting_router)
domain_router.include_router(admin_reports_router)
domain_router.include_router(admin_funnel_router)
domain_router.include_router(admin_insights_router)

# Dashboard & revenue
domain_router.include_router(dashboard_enhanced_router)
domain_router.include_router(revenue_router)
