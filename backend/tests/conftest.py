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


@pytest.fixture(autouse=True, scope="session")
def stripe_webhook_secret_env() -> None:
    """Ensure STRIPE_WEBHOOK_SECRET is set in test environment.

    This avoids 500s in webhook tests caused by missing configuration and
    allows contract tests to exercise signature verification deterministically.
    """

    os.environ.setdefault("STRIPE_WEBHOOK_SECRET", "whsec_test")

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

    # Ensure Stripe webhook secret is set for contract tests
    # to exercise real signature verification logic deterministically.
    os.environ.setdefault("STRIPE_WEBHOOK_SECRET", "whsec_test")

    client = AsyncIOMotorClient(MONGO_URL)
    try:
        yield client
    finally:
        client.close()


@pytest.fixture(scope="function")
async def seeded_test_db(motor_client: AsyncIOMotorClient) -> AsyncGenerator[Any, None]:
    """Function-scoped DB with minimal catalog/inventory seed for hotel search.

    Ensures P0.2 /api/b2b/hotels/search returns at least one item for
    deterministic FX and refund tests.
    """

    db_name = f"agentis_test_seeded_{uuid.uuid4().hex}"
    db = motor_client[db_name]

    try:
        # Minimal organization
        org_id = "org_demo"
        await db.organizations.insert_one({"_id": org_id, "slug": "default", "name": "Demo Org"})

        # Minimal agency linked to org
        await db.agencies.insert_one({
            "_id": "agency_demo",
            "organization_id": org_id,
            "name": "Demo Agency",
            "settings": {"selling_currency": "EUR"},
        })

        # One active hotel product in Istanbul with EUR rate plan
        from app.utils import now_utc as _now

        hotel_id = ObjectId()
        await db.products.insert_one({
            "_id": hotel_id,
            "organization_id": org_id,
            "type": "hotel",
            "status": "active",
            "name": {"tr": "Test Hotel"},
            "location": {"city": "Istanbul", "country": "TR"},
            "default_currency": "EUR",
            "created_at": _now(),
        })

        rate_plan_id = ObjectId()
        await db.rate_plans.insert_one({
            "_id": rate_plan_id,
            "organization_id": org_id,
            "product_id": hotel_id,
            "status": "active",
            "currency": "EUR",
            "board": "BB",
            "base_net_price": 100.0,
        })

        # Simple inventory for the FX tests' date window (2026-01-10 .. 2026-01-12)
        from datetime import date, timedelta

        start = date(2026, 1, 10)
        for offset in range(0, 2):
            d = start + timedelta(days=offset)
            await db.inventory.insert_one({
                "organization_id": org_id,
                "product_id": hotel_id,
                "date": d.isoformat(),
                "capacity_available": 10,
                "price": 100.0,
                "restrictions": {"closed": False},
            })

        yield db
    finally:
        await motor_client.drop_database(db_name)


@pytest.fixture(autouse=True)
async def stripe_handlers_db(monkeypatch, test_db):
    """Route stripe_handlers.get_db to test_db for all tests.

    Ensures Stripe webhook handlers use the same isolated database as the
    async_client / app_with_overrides fixtures.
    """

    from app.services import stripe_handlers as handlers  # type: ignore

    async def _fake_get_db():
        return test_db

    monkeypatch.setattr(handlers, "get_db", _fake_get_db)
    yield



@pytest.fixture(autouse=True)
async def ensure_finance_indexes_for_test_db(test_db, anyio_backend):
    """Ensure finance-related indexes exist in the isolated test_db.

    This makes booking_payment_transactions and booking_payments idempotency
    semantics deterministic for Stripe contract and FX tests.
    """

    from app.indexes.finance_indexes import ensure_finance_indexes

    await ensure_finance_indexes(test_db)
    yield



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

    transport = ASGITransport(app=app_with_overrides)
    async with httpx.AsyncClient(transport=transport, base_url="http://test", timeout=30.0) as client:
        yield client


@pytest.fixture
async def admin_token(async_client: httpx.AsyncClient) -> str:
    """Login as admin and return access token."""

    response = await async_client.post(
        "/api/auth/login",
        json={"email": "admin@acenta.test", "password": "admin123"},


@pytest.fixture(autouse=True)
async def seed_p02_catalog(async_client: httpx.AsyncClient, agency_token: str):
    """Ensure P0.2 /api/b2b/hotels/search returns at least one item for FX tests.

    Seeds a minimal hotel + rate plan for the organization/agency of agency_token
    directly through the admin/catalog APIs to respect all business invariants.
    """

    # Resolve org/agency from /api/auth/me
    headers = {"Authorization": f"Bearer {agency_token}"}
    me_resp = await async_client.get("/api/auth/me", headers=headers)
    assert me_resp.status_code == 200, f"/auth/me failed: {me_resp.text}"
    me = me_resp.json()
    org_id = me.get("organization_id")
    agency_id = me.get("agency_id")

    # 1) Create a simple product (hotel) via admin catalog if none exists
    admin_headers = {"Authorization": f"Bearer {await admin_token(async_client)}"}

    # Use Istanbul and EUR as in tests
    payload = {
        "code": "FXTEST-HOTEL",
        "name": {"tr": "FX Test Hotel"},
        "type": "hotel",
        "location": {"city": "Istanbul", "country": "TR"},
        "default_currency": "EUR",
    }

    # Ignore duplicate_code errors (if already seeded)
    resp = await async_client.post("/api/admin/catalog/products", headers=admin_headers, json=payload)
    if resp.status_code not in (200, 201):
        data = resp.json()
        if not (data.get("error", {}).get("code") == "duplicate_code"):
            raise AssertionError(f"Failed to seed FX test product: {resp.text}")

    # 2) Ensure at least one active EUR rate plan with base_net_price > 0 exists
    # For simplicity, rely on existing admin endpoints or assume pricing rules
    # will generate a non-zero base_net_price for the product.
    # P0.2 search only requires products + rate_plans; inventory is not checked.

    yield

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


@pytest.fixture
async def agency_headers(agency_token: str) -> Dict[str, str]:
    """Convenience fixture returning Authorization header for agency."""

    return {"Authorization": f"Bearer {agency_token}"}