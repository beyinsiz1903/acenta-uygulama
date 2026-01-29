from __future__ import annotations

from typing import Any

import jwt
import pytest
from fastapi import status
from httpx import ASGITransport, AsyncClient

from server import app
from app.auth import _jwt_secret, get_current_user
from app.context.org_context import get_current_org
from app.db import get_db


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
async def test_get_current_org_403_when_user_has_no_org(test_db: Any) -> None:
    """get_current_org must raise 403 when authenticated user has no organization_id."""

    # Seed user without organization_id
    email = "no-org@example.com"
    await test_db.users.insert_one({"email": email, "roles": ["super_admin"]})

    # Forge JWT for that user (no org claim)
    payload = {"sub": email}
    token = jwt.encode(payload, _jwt_secret(), algorithm="HS256")

    # Call get_current_user + get_current_org directly (service-level)
    # Simulate FastAPI dependency resolution using the real DB override from conftest
    from fastapi import HTTPException

    # get_current_user should succeed (user exists)
    user = await get_current_user(credentials=type("Cred", (), {"credentials": token})())  # type: ignore

    # get_current_org should raise 403 due to missing organization_id
    with pytest.raises(HTTPException) as exc:
        await get_current_org(user)  # type: ignore[arg-type]
    assert exc.value.status_code == status.HTTP_403_FORBIDDEN
    assert exc.value.detail == "Organization membership required"
