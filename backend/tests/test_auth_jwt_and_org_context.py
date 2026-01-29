from __future__ import annotations

from typing import Any

import jwt
import pytest
from fastapi import status
from httpx import ASGITransport, AsyncClient

from server import app
from app.auth import _jwt_secret


@pytest.mark.anyio
async def test_invalid_token_returns_401() -> None:
    """Requests with invalid/malformed JWT must return 401 and never hit handlers."""

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            "/api/admin/agencies",
            headers={"Authorization": "Bearer invalid.token"},
        )
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.anyio
async def test_missing_org_membership_returns_401_or_403(test_db: Any) -> None:
    """Authenticated user without organization_id must see 401/403 when resolving org context.

    This simulates a user record missing organization linkage.
    """

    # Create user without organization_id
    email = "no-org@example.com"
    await test_db.users.insert_one({"email": email, "roles": ["super_admin"]})

    # Forge a JWT for that user (no org claim)
    payload = {"sub": email}
    token = jwt.encode(payload, _jwt_secret(), algorithm="HS256")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            "/api/admin/agencies",
            headers={"Authorization": f"Bearer {token}"},
        )

    # Depending on get_current_user implementation, this may be 401 (user not found)
    # or 403 (org membership required) once get_current_org is applied broadly.
    assert resp.status_code in {status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN}
