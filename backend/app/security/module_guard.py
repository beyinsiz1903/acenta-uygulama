from __future__ import annotations

from fastapi import Depends, Request

from app.constants.org_modules import CORE_MODULES
from app.db import get_db
from app.errors import AppError


def require_org_module(module_key: str):
    async def _guard(request: Request, db=Depends(get_db)) -> None:
        if module_key in CORE_MODULES:
            return
        org_id = getattr(request.state, "organization_id", None)
        if not org_id:
            user = getattr(request.state, "user", None)
            if user:
                org_id = user.get("organization_id")
        if not org_id:
            return

        doc = await db.organization_modules.find_one(
            {"organization_id": org_id}, {"enabled_modules": 1}
        )
        if not doc:
            return
        enabled = doc.get("enabled_modules", [])
        if not enabled:
            return
        if module_key not in enabled:
            raise AppError(
                403,
                "module_disabled",
                "Bu modül organizasyonunuz için aktif değil.",
                {"module": module_key},
            )

    return Depends(_guard)
