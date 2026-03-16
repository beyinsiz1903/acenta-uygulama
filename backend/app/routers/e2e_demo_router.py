"""E2E Demo & Certification Console Router.

Endpoints:
  GET  /api/e2e-demo/scenarios          — Available test scenarios
  GET  /api/e2e-demo/suppliers          — Supplier health summary
  POST /api/e2e-demo/run                — Run E2E lifecycle test
  GET  /api/e2e-demo/history            — Test run history
  POST /api/e2e-demo/rerun-step         — Rerun a single failed step
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Body, Query
from typing import Any

from app.auth import require_roles

router = APIRouter(prefix="/api/e2e-demo", tags=["e2e_demo"])

_ADMIN_ROLES = ["admin", "super_admin"]


@router.get("/scenarios")
async def list_scenarios(
    current_user=Depends(require_roles(_ADMIN_ROLES)),
) -> dict[str, Any]:
    from app.services.e2e_demo_service import get_scenarios
    return await get_scenarios()


@router.get("/suppliers")
async def supplier_status(
    current_user=Depends(require_roles(_ADMIN_ROLES)),
) -> dict[str, Any]:
    from app.services.e2e_demo_service import get_supplier_status
    return await get_supplier_status()


@router.post("/run")
async def run_test(
    payload: dict = Body(...),
    current_user=Depends(require_roles(_ADMIN_ROLES)),
) -> dict[str, Any]:
    from app.services.e2e_demo_service import run_e2e_test
    return await run_e2e_test(
        supplier=payload.get("supplier", "ratehawk"),
        scenario=payload.get("scenario", "success"),
    )


@router.get("/history")
async def test_history(
    supplier: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    current_user=Depends(require_roles(_ADMIN_ROLES)),
) -> dict[str, Any]:
    from app.services.e2e_demo_service import get_test_history
    return await get_test_history(supplier, limit)


@router.post("/rerun-step")
async def rerun_step(
    payload: dict = Body(...),
    current_user=Depends(require_roles(_ADMIN_ROLES)),
) -> dict[str, Any]:
    from app.services.e2e_demo_service import rerun_failed_step
    return await rerun_failed_step(
        run_id=payload.get("run_id", ""),
        step_id=payload.get("step_id", ""),
    )
