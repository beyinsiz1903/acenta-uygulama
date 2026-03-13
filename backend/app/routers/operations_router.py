"""Operations & Launch Readiness Router.

Endpoints for:
  /api/operations/validate-supplier — Single supplier validation
  /api/operations/validate-all — Validate all 4 suppliers
  /api/operations/capability-matrix — Supplier capability test matrix
  /api/operations/supplier-sla — Supplier SLA metrics
  /api/operations/cache-burst-test — Cache burst performance test
  /api/operations/rate-limit-test — Rate limit stress test
  /api/operations/fallback-test — Fallback chain validation
  /api/operations/reconciliation-test — Reconciliation accuracy test
  /api/operations/monitoring-test — Monitoring stack validation
  /api/operations/launch-readiness — Full launch readiness report
  /api/operations/onboarding-checklist — Agency onboarding flow
"""
from __future__ import annotations

from typing import Any
from fastapi import APIRouter, Depends, Body, Query

from app.db import get_db
from app.auth import require_roles

router = APIRouter(prefix="/api/operations", tags=["operations"])


# =========================================================================
# Supplier Validation
# =========================================================================

@router.post("/validate-supplier")
async def validate_supplier(
    payload: dict = Body(...),
    db=Depends(get_db),
    current_user=Depends(require_roles(["admin", "super_admin"])),
) -> dict[str, Any]:
    """Validate credentials for a specific supplier.

    Body: { "supplier_code": "ratehawk" | "tbo" | "paximum" | "wwtatil" }
    """
    from app.services.supplier_validation_service import validate_supplier_credentials
    org_id = current_user.get("organization_id", current_user.get("org_id", ""))
    return await validate_supplier_credentials(db, org_id, payload.get("supplier_code", ""))


@router.post("/validate-all")
async def validate_all(
    db=Depends(get_db),
    current_user=Depends(require_roles(["admin", "super_admin"])),
) -> dict[str, Any]:
    """Validate all 4 supplier credentials."""
    from app.services.supplier_validation_service import validate_all_suppliers
    org_id = current_user.get("organization_id", current_user.get("org_id", ""))
    return await validate_all_suppliers(db, org_id)


@router.get("/capability-matrix")
async def capability_matrix(
    current_user=Depends(require_roles(["admin", "super_admin"])),
) -> dict[str, Any]:
    """Get Supplier Capability Test Matrix."""
    from app.services.supplier_validation_service import get_capability_matrix
    return get_capability_matrix()


@router.get("/supplier-sla")
async def supplier_sla(
    db=Depends(get_db),
    current_user=Depends(require_roles(["admin", "super_admin"])),
) -> dict[str, Any]:
    """Get Supplier SLA monitoring metrics."""
    from app.services.supplier_validation_service import get_supplier_sla_metrics
    return await get_supplier_sla_metrics(db)


# =========================================================================
# Performance Validation
# =========================================================================

@router.post("/cache-burst-test")
async def cache_burst_test(
    payload: dict = Body(default={}),
    db=Depends(get_db),
    current_user=Depends(require_roles(["admin", "super_admin"])),
) -> dict[str, Any]:
    """Run cache burst test.

    Body (optional): { "burst_count": 5 }
    """
    from app.services.performance_validation_service import run_cache_burst_test
    org_id = current_user.get("organization_id", current_user.get("org_id", ""))
    burst = int(payload.get("burst_count", 5))
    return await run_cache_burst_test(db, org_id, min(burst, 20))


@router.post("/rate-limit-test")
async def rate_limit_test(
    payload: dict = Body(default={}),
    db=Depends(get_db),
    current_user=Depends(require_roles(["admin", "super_admin"])),
) -> dict[str, Any]:
    """Run rate limit stress test.

    Body (optional): { "supplier_code": "ratehawk", "request_count": 10 }
    """
    from app.services.performance_validation_service import run_rate_limit_stress_test
    return await run_rate_limit_stress_test(
        payload.get("supplier_code", "ratehawk"),
        min(int(payload.get("request_count", 10)), 50),
    )


@router.get("/fallback-test")
async def fallback_test(
    db=Depends(get_db),
    current_user=Depends(require_roles(["admin", "super_admin"])),
) -> dict[str, Any]:
    """Validate fallback chains."""
    from app.services.performance_validation_service import run_fallback_validation
    return await run_fallback_validation(db)


@router.get("/reconciliation-test")
async def reconciliation_test(
    db=Depends(get_db),
    current_user=Depends(require_roles(["admin", "super_admin"])),
) -> dict[str, Any]:
    """Validate reconciliation system."""
    from app.services.performance_validation_service import run_reconciliation_validation
    return await run_reconciliation_validation(db)


@router.get("/monitoring-test")
async def monitoring_test(
    db=Depends(get_db),
    current_user=Depends(require_roles(["admin", "super_admin"])),
) -> dict[str, Any]:
    """Validate monitoring stack."""
    from app.services.performance_validation_service import run_monitoring_validation
    return await run_monitoring_validation(db)


# =========================================================================
# Launch Readiness
# =========================================================================

@router.get("/launch-readiness")
async def launch_readiness(
    db=Depends(get_db),
    current_user=Depends(require_roles(["admin", "super_admin"])),
) -> dict[str, Any]:
    """Generate full Market Launch Readiness Report."""
    from app.services.launch_readiness_service import generate_launch_readiness_report
    org_id = current_user.get("organization_id", current_user.get("org_id", ""))
    return await generate_launch_readiness_report(db, org_id)


# =========================================================================
# Agency Onboarding
# =========================================================================

@router.get("/onboarding-checklist")
async def onboarding_checklist(
    current_user=Depends(require_roles(["admin", "super_admin"])),
) -> dict[str, Any]:
    """Get agency onboarding flow checklist."""
    return {
        "checklist": [
            {
                "step": 1,
                "title": "Acente Kaydi",
                "description": "Yeni acente hesabi olusturun (organizasyon adi, vergi no, yetkili kisi)",
                "endpoint": "POST /api/auth/register",
                "status": "available",
            },
            {
                "step": 2,
                "title": "Supplier Credential Girisi",
                "description": "Acente icin supplier API credential'larini yapilandirin (RateHawk, TBO, Paximum, WWTatil)",
                "endpoint": "POST /api/suppliers/credentials",
                "status": "available",
            },
            {
                "step": 3,
                "title": "Credential Dogrulama",
                "description": "Validation framework ile credential'lari test edin",
                "endpoint": "POST /api/operations/validate-all",
                "status": "available",
            },
            {
                "step": 4,
                "title": "Test Aramasi",
                "description": "Istanbul otel aramasi yaparak supplier baglantisini dogrulayin",
                "endpoint": "POST /api/unified/search",
                "status": "available",
            },
            {
                "step": 5,
                "title": "Ilk Rezervasyon",
                "description": "Test veya gercek rezervasyon yaparak tum akisi dogrulayin",
                "endpoint": "POST /api/unified/book",
                "status": "available",
            },
            {
                "step": 6,
                "title": "Dashboard Erisimi",
                "description": "Revenue, analytics ve monitoring dashboard'larina erisimi dogrulayin",
                "endpoint": "/app/admin/*",
                "status": "available",
            },
        ],
        "estimated_time_minutes": 30,
        "prerequisites": [
            "Supplier API credential'lari (en az 1 supplier)",
            "Acente vergi ve iletisim bilgileri",
        ],
    }
