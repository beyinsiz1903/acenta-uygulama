from __future__ import annotations

from typing import Any, Dict

from fastapi import Depends, HTTPException, status

from app.auth import get_current_user, load_org_doc


async def get_current_org(
    user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Resolve current organization document from authenticated user.

    - Never reads org_id from client payload
    - Uses only server-side user -> organization mapping
    - Raises 401/403 style errors when org cannot be resolved
    """

    org_id = user.get("organization_id")
    if not org_id:
        # User is authenticated but not linked to any organization
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Organization membership required",
        )

    org_doc = await load_org_doc(org_id)
    if not org_doc:
        # Organization not found or soft-deleted
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )

    return org_doc
