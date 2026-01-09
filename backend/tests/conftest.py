"""Shared test configuration and fixtures for backend tests (F1.3 harness).

Key principles:
- No remote BASE_URL usage; all HTTP calls go through local ASGI app.
- Single Motor/Mongo client per test session via FastAPI get_db override.
- httpx.AsyncClient(app=app, base_url="http://test") used for all HTTP tests.
"""

from typing import AsyncGenerator, Callable, Dict, Any

import os
import sys
from pathlib import Path

import pytest
import httpx

# Ensure backend root is on sys.path so that `server` module is importable
ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from server import app
from app.db import get_db


@pytest.fixture(scope="session")
async def test_db() -> AsyncGenerator[Any, None]:
    """Provide a shared Motor database instance for tests.

    Uses the application's get_db helper so that connection lifecycle is
    aligned with the actual app's Mongo client.
    """

    db = await get_db()
    yield db
    # NOTE: We intentionally do not close the global client here; FastAPI
    # startup/shutdown hooks handle connect_mongo/close_mongo.


@pytest.fixture
async def db(test_db) -> Any:
    """Per-test database handle.

    This returns the same logical DB object but allows per-test cleanup if
    needed without touching the global Motor client.
    """

    return test_db


@pytest.fixture
async def async_client(test_db) -> AsyncGenerator[httpx.AsyncClient, None]:
    """Async HTTP client bound to the FastAPI app instance.

    All tests should use this client instead of remote preview URLs.
    """

    async with httpx.AsyncClient(app=app, base_url="http://test", timeout=30.0) as client:
        yield client


@pytest.fixture
async def admin_token(async_client: httpx.AsyncClient) -> str:
    """Login as admin and return access token."""

    response = await async_client.post(
        "/api/auth/login",
        json={"email": "admin@acenta.test", "password": "admin123"},
    )
    assert response.status_code == 200, f"Admin login failed: {response.text}"
    data = response.json()
    return data["access_token"]


@pytest.fixture
async def admin_headers(admin_token: str) -> Dict[str, str]:
    """Convenience fixture returning Authorization header for admin."""

    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture
async def agency_token(async_client: httpx.AsyncClient) -> str:
    """Login as agency user and return access token."""

    response = await async_client.post(
        "/api/auth/login",
        json={"email": "agency1@demo.test", "password": "agency123"},
    )
    assert response.status_code == 200, f"Agency login failed: {response.text}"
    data = response.json()
    return data["access_token"]