from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.auth import get_current_user, require_roles
from app.db import get_db

router = APIRouter(prefix="/api/agency", tags=["agency-users"])


@router.get(
    "/users",
    dependencies=[Depends(require_roles(["agency_admin", "agency_agent", "super_admin"]))],
)
async def list_agency_users(
    role: Optional[str] = Query("any"),
    user=Depends(get_current_user),
):
    """List agency users within the same organization/agency for assignee dropdown.

    - Only agency_admin / agency_agent / super_admin can call this.
    - Hotel roles are forbidden at require_roles level.
    - Scope: same organization_id, and same agency_id for agency roles.
    - role filter: "agency_agent" | "agency_admin" | "any" (default any).
    """

    db = await get_db()

    organization_id = str(user.get("organization_id"))
    agency_id = user.get("agency_id")
    if not agency_id and not user.get("roles") == ["super_admin"] and not user.get("roles", []) == [
        "super_admin"
    ]:
        # For simplicity: non-super_admin must have agency_id
        raise HTTPException(status_code=403, detail="FORBIDDEN")

    q: Dict[str, Any] = {"organization_id": organization_id, "is_active": {"$ne": False}}

    roles = set(user.get("roles") or [])
    if "super_admin" not in roles:
        # Restrict to same agency for agency users
        q["agency_id"] = agency_id

    # Apply role filter on user documents
    role_filter = (role or "any").strip().lower()

    cursor = db.users.find(q, {"password_hash": 0}).sort("created_at", -1)
    items: List[Dict[str, Any]] = []
    async for u in cursor:
        user_roles = set(u.get("roles") or [])
        # Normalize: prefer explicit role if present
        primary_role: Optional[str] = u.get("role")
        if not primary_role:
            if "agency_admin" in user_roles:
                primary_role = "agency_admin"
            elif "agency_agent" in user_roles:
                primary_role = "agency_agent"
            elif user_roles:
                # fall back to any other role string
                primary_role = next(iter(user_roles))

        if role_filter in {"agency_admin", "agency_agent"}:
            if primary_role != role_filter:
                continue

        name = (u.get("full_name") or u.get("name") or "").strip()
        if not name:
            fn = (u.get("first_name") or "").strip()
            ln = (u.get("last_name") or "").strip()
            tmp = (f"{fn} {ln}").strip()
            name = tmp or (u.get("email") or "")

        items.append(
            {
                "user_id": str(u.get("_id")),
                "name": name,
                "email": u.get("email"),
                "role": primary_role,
            }
        )

    return {"items": items}
