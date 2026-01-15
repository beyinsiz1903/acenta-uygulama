from __future__ import annotations

from fastapi import APIRouter, Depends, BackgroundTasks, Request

from app.db import get_db
from app.security.deps_b2b import CurrentB2BUser, current_b2b_user
from app.services.crm_events import log_crm_event

router = APIRouter(prefix="/b2b", tags=["b2b-portal"])


async def _log_b2b_login_success(db, user: CurrentB2BUser):
    """Best-effort logging for B2B login success.

    Any exception here must not break the main /me response.
    """
    try:
        if user.organization_id:
            await log_crm_event(
                db,
                user.organization_id,
                entity_type="auth",
                entity_id=user.id,
                action="b2b.login.success",
                payload={"roles": user.roles},
                actor={"id": user.id, "roles": user.roles},
                source="b2b_portal",
            )
    except Exception:
        # Swallow all errors – logging is best-effort only
        pass


@router.get("/me")
async def b2b_me(
    request: Request,
    background: BackgroundTasks,
    user: CurrentB2BUser = Depends(current_b2b_user),
    db=Depends(get_db),
):
    """Return minimal identity + scope info for B2B users.

    - Only users with B2B-allowed roles can access (enforced by current_b2b_user)
    - Used by frontend B2BAuthGuard and login flows
    """

    # Fire-and-forget: log event in background so main response is not blocked
    background.add_task(_log_b2b_login_success, db, user)

    return {
        "user_id": user.id,
        "roles": user.roles,
        "organization_id": user.organization_id,
        "agency_id": user.agency_id,
    }
