"""Supplier Onboarding Router.

Generic supplier onboarding wizard API:
  GET  /api/supplier-onboarding/registry          — List available suppliers
  GET  /api/supplier-onboarding/dashboard          — All suppliers' onboarding status
  GET  /api/supplier-onboarding/detail/{supplier}  — Single supplier onboarding detail
  POST /api/supplier-onboarding/credentials        — Save credentials
  POST /api/supplier-onboarding/validate/{supplier} — Validate + health check
  POST /api/supplier-onboarding/certify/{supplier}  — Run certification suite
  GET  /api/supplier-onboarding/certification/{supplier} — Certification report
  GET  /api/supplier-onboarding/certification/{supplier}/history — Certification history
  POST /api/supplier-onboarding/go-live/{supplier}  — Toggle go-live
  POST /api/supplier-onboarding/reset/{supplier}    — Reset onboarding
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Body
from typing import Any

from app.db import get_db
from app.auth import require_roles

router = APIRouter(prefix="/api/supplier-onboarding", tags=["supplier_onboarding"])

_ADMIN_ROLES = ["admin", "super_admin"]


@router.get("/registry")
async def get_registry(
    current_user=Depends(require_roles(_ADMIN_ROLES)),
) -> dict[str, Any]:
    from app.services.supplier_onboarding_service import get_registry as _get
    return await _get()


@router.get("/dashboard")
async def get_dashboard(
    current_user=Depends(require_roles(_ADMIN_ROLES)),
    db=Depends(get_db),
) -> dict[str, Any]:
    from app.services.supplier_onboarding_service import get_onboarding_dashboard as _get
    return await _get(db)


@router.get("/detail/{supplier_code}")
async def get_detail(
    supplier_code: str,
    current_user=Depends(require_roles(_ADMIN_ROLES)),
    db=Depends(get_db),
) -> dict[str, Any]:
    from app.services.supplier_onboarding_service import get_supplier_detail as _get
    return await _get(db, supplier_code)


@router.post("/credentials")
async def save_credentials(
    payload: dict = Body(...),
    current_user=Depends(require_roles(_ADMIN_ROLES)),
    db=Depends(get_db),
) -> dict[str, Any]:
    from app.services.supplier_onboarding_service import save_onboarding_credentials as _save
    return await _save(db, payload.get("supplier_code", ""), payload.get("credentials", {}))


@router.post("/validate/{supplier_code}")
async def validate_health_check(
    supplier_code: str,
    current_user=Depends(require_roles(_ADMIN_ROLES)),
    db=Depends(get_db),
) -> dict[str, Any]:
    from app.services.supplier_onboarding_service import run_health_check as _run
    return await _run(db, supplier_code)


@router.post("/certify/{supplier_code}")
async def run_certification(
    supplier_code: str,
    current_user=Depends(require_roles(_ADMIN_ROLES)),
    db=Depends(get_db),
) -> dict[str, Any]:
    from app.services.supplier_onboarding_service import run_certification as _run
    return await _run(db, supplier_code)


@router.get("/certification/{supplier_code}")
async def get_certification(
    supplier_code: str,
    current_user=Depends(require_roles(_ADMIN_ROLES)),
    db=Depends(get_db),
) -> dict[str, Any]:
    from app.services.supplier_onboarding_service import get_certification_report as _get
    return await _get(db, supplier_code)


@router.get("/certification/{supplier_code}/history")
async def get_certification_history(
    supplier_code: str,
    current_user=Depends(require_roles(_ADMIN_ROLES)),
    db=Depends(get_db),
) -> dict[str, Any]:
    from app.services.supplier_onboarding_service import get_certification_history as _get
    return await _get(db, supplier_code)


@router.post("/go-live/{supplier_code}")
async def toggle_go_live(
    supplier_code: str,
    payload: dict = Body(...),
    current_user=Depends(require_roles(_ADMIN_ROLES)),
    db=Depends(get_db),
) -> dict[str, Any]:
    from app.services.supplier_onboarding_service import toggle_go_live as _toggle
    return await _toggle(db, supplier_code, payload.get("enabled", False))


@router.post("/reset/{supplier_code}")
async def reset_onboarding(
    supplier_code: str,
    current_user=Depends(require_roles(_ADMIN_ROLES)),
    db=Depends(get_db),
) -> dict[str, Any]:
    from app.services.supplier_onboarding_service import reset_onboarding as _reset
    return await _reset(db, supplier_code)
