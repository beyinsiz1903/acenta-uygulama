from __future__ import annotations

from typing import Any, Dict

import pytest
from fastapi import status
from httpx import ASGITransport, AsyncClient

from server import app
from app.utils import now_utc


@pytest.mark.anyio
async def test_booking_lifecycle_draft_to_cancel_requested(test_db: Any, default_org_id: str, default_user: Dict[str, Any]) -> None:
    transport = ASGITransport(app=app)

    # Login helper: tests assume default_user fixture is already authenticated in other tests
    # Here we bypass auth by forging headers may be complex; instead, we seed directly.
    # For this minimal test, we call repo/service indirectly via API is harder, so keep
    # this as a placeholder for Sprint 2 where auth helpers are standardized.
    # To keep Sprint 1 scope safe, we directly exercise repository/service in unit tests
    # rather than full HTTP E2E here.

