"""Shared test configuration and fixtures for backend tests (F1.3 harness).

Key principles:
- No remote BASE_URL usage; all HTTP calls go through local ASGI app.
- Single Motor/Mongo client per test session.
- httpx.AsyncClient(app=app, base_url="http://test") used for all HTTP tests.
- AnyIO is the single async runner via pytest-anyio (@pytest.mark.anyio).
"""

from typing import AsyncGenerator, Dict, Any

import os
import sys
from pathlib import Path
import uuid

import pytest
import httpx
from httpx import ASGITransport
from motor.motor_asyncio import AsyncIOMotorClient

# Ensure backend root is on sys.path so that `server` module is importable
ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from server import app
from app.db import get_db


MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    """Force pytest-anyio to use asyncio event loop."""

    return "asyncio"


@pytest.fixture(scope="session")
async def motor_client() -> AsyncGenerator[AsyncIOMotorClient, None]:
    """Session-scoped Motor client for all tests.

    This avoids creating/closing clients per test and keeps a single
    event loop / IO stack for Mongo.
    """

    client = AsyncIOMotorClient(MONGO_URL)
    try:
        yield client
    finally:
        client.close()


@pytest.fixture(scope="function")
async def test_db(motor_client: AsyncIOMotorClient) -> AsyncGenerator[Any, None]:
    """Function-scoped isolated database for each test.

    Each test gets its own temporary database, dropped on teardown.
    """

    db_name = f"agentis_test_{uuid.uuid4().hex}"
    db = motor_client[db_name]
    try:
        yield db
    finally:
        await motor_client.drop_database(db_name)


@pytest.fixture(scope="function")
async def app_with_overrides(test_db) -> AsyncGenerator[Any, None]:
    """FastAPI app instance whose get_db dependency points to test_db."""

    async def override_get_db():
        yield test_db

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield app
    finally:
        app.dependency_overrides.clear()


@pytest.fixture(scope="function")
async def async_client(app_with_overrides) -> AsyncGenerator[httpx.AsyncClient, None]:
    """Async HTTP client bound to the FastAPI app instance.

    All tests should use this client instead of remote preview URLs.
    """

    async with httpx.AsyncClient(app=app_with_overrides, base_url="http://test", timeout=30.0) as client:
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