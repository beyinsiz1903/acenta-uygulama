from __future__ import annotations

from fastapi import APIRouter, Depends, Request, status

from app.auth import get_current_user, require_roles
from app.db import get_db
from app.modules.mobile import schemas
from app.modules.mobile import service as mobile_service

router = APIRouter()

MobileAppAccess = Depends(require_roles(["super_admin", "admin", "agency_admin", "agency_agent"]))


@router.get("/auth/me", response_model=schemas.MobileAuthMeResponse)
async def mobile_me(user=Depends(get_current_user)):
    return mobile_service.build_mobile_user(user)


@router.get("/dashboard/summary", response_model=schemas.MobileDashboardSummary, dependencies=[MobileAppAccess])
async def dashboard_summary(db=Depends(get_db), user=Depends(get_current_user)):
    return await mobile_service.get_dashboard_summary(db, user)


@router.get("/bookings", response_model=schemas.MobileBookingsListResponse, dependencies=[MobileAppAccess])
async def list_bookings(limit: int = 20, status_filter: str | None = None, db=Depends(get_db), user=Depends(get_current_user)):
    return await mobile_service.list_bookings(db, user, limit=limit, status=status_filter)


@router.get("/bookings/{booking_id}", response_model=schemas.MobileBookingDetail, dependencies=[MobileAppAccess])
async def booking_detail(booking_id: str, db=Depends(get_db), user=Depends(get_current_user)):
    return await mobile_service.get_booking(db, booking_id, user)


@router.post(
    "/bookings",
    response_model=schemas.MobileBookingDetail,
    status_code=status.HTTP_201_CREATED,
    dependencies=[MobileAppAccess],
)
async def create_booking(payload: schemas.MobileBookingCreate, request: Request, db=Depends(get_db), user=Depends(get_current_user)):
    return await mobile_service.create_booking(db, payload.model_dump(), user, request)


@router.get("/reports/summary", response_model=schemas.MobileReportsSummary, dependencies=[MobileAppAccess])
async def reports_summary(db=Depends(get_db), user=Depends(get_current_user)):
    return await mobile_service.get_reports_summary(db, user)