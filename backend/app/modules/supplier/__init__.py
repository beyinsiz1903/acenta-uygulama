"""Supplier domain — supplier adapters, aggregation, health, credentials."""
from fastapi import APIRouter

from app.config import API_PREFIX

from app.routers.suppliers import router as suppliers_router
from app.routers.paximum_router import router as paximum_router
from app.routers.admin_supplier_health import router as admin_supplier_health_router
from app.routers.ops_supplier_operations import router as ops_supplier_operations_router

domain_router = APIRouter()
domain_router.include_router(suppliers_router, prefix=API_PREFIX)
domain_router.include_router(paximum_router, prefix=API_PREFIX)
domain_router.include_router(admin_supplier_health_router)
domain_router.include_router(ops_supplier_operations_router)
