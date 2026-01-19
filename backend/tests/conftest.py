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
from app.db import get_db, _mongo_url
from app.utils import now_utc


MONGO_URL = _mongo_url()


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
        from bson import ObjectId
        
        hotel_id = ObjectId()
        await db.products.insert_one({
            "_id": hotel_id,
            "organization_id": org_id,
            "type": "hotel",
            "status": "active",
            "name": {"tr": "Test Hotel"},
            "location": {"city": "Istanbul", "country": "TR"},
            "default_currency": "EUR",
            "created_at": now_utc(),
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



@pytest.fixture(autouse=True)
async def core_db_routing(monkeypatch, test_db):
    """Route core app.db.get_db and global _db to the per-test database.

    This ensures helpers that import get_db directly (without FastAPI
    dependency overrides) share the same isolated Mongo database as HTTP
    endpoints and other services.
    """

    from app import db as db_module  # type: ignore

    # Point the module-level global to the test database so the original
    # get_db() implementation returns this DB without creating a new client.
    db_module._db = test_db

    async def _fake_get_db() -> Any:  # pragma: no cover - thin shim
        return test_db

    monkeypatch.setattr(db_module, "get_db", _fake_get_db)
    yield


@pytest.fixture(autouse=True)
async def seed_default_org_and_users(test_db):
    """Ensure default org + core users exist inside each isolated test_db.

    This mirrors the minimal part of app.seed.ensure_seed_data that tests rely on
    (default organization + admin + demo agencies) but runs against the
    per-test database instead of the shared dev DB.
    """
    from app.seed import DEFAULT_ADMIN_EMAIL, DEFAULT_ADMIN_PASSWORD
    from app.auth import hash_password
    from app.utils import now_utc

    now = now_utc()

    # 1) Default organization (used by most tests)
    org = await test_db.organizations.find_one({"slug": "default"})
    if not org:
        res = await test_db.organizations.insert_one(
            {
                "name": "Varsayilan Acenta",
                "slug": "default",
                "created_at": now,
                "updated_at": now,
                "settings": {"currency": "TRY"},
                "plan": "core_small_hotel",
                "features": {"partner_api": True},
            }
        )
        default_org_id = str(res.inserted_id)
    else:
        default_org_id = str(org["_id"])

    # 2) Admin user (always in default organization to match /api/auth/login)
    admin_org_id = default_org_id
    admin = await test_db.users.find_one({"organization_id": admin_org_id, "email": DEFAULT_ADMIN_EMAIL})
    if not admin:
        await test_db.users.insert_one(
            {
                "organization_id": admin_org_id,
                "email": DEFAULT_ADMIN_EMAIL,
                "name": "Admin",
                "password_hash": hash_password(DEFAULT_ADMIN_PASSWORD),
                "roles": ["super_admin"],
                "created_at": now,
                "updated_at": now,
                "is_active": True,
            }
        )

    # 3) Demo agency + agency user (agency1@demo.test) always tied to default_org_id
    agency = await test_db.agencies.find_one({"organization_id": default_org_id, "name": "Demo Agency"})
    if not agency:
        from bson import ObjectId

        agency_id = str(ObjectId())
        await test_db.agencies.insert_one(
            {
                "_id": agency_id,
                "organization_id": default_org_id,
                "name": "Demo Agency",
                "settings": {"selling_currency": "EUR"},
                "created_at": now,
                "updated_at": now,
            }
        )
    else:
        agency_id = str(agency["_id"])

    agency_user = await test_db.users.find_one({"organization_id": default_org_id, "email": "agency1@demo.test"})
    if not agency_user:
        await test_db.users.insert_one(
            {
                "organization_id": default_org_id,
                "agency_id": agency_id,
                "email": "agency1@demo.test",
                "name": "Demo Agency User",
                "password_hash": hash_password("agency123"),
                "roles": ["agency_admin"],
                "created_at": now,
                "updated_at": now,
                "is_active": True,
            }
        )

    yield


@pytest.fixture(autouse=True)
async def align_admin_org_for_partner_tests(test_db):
    """Align admin organization's id with test-specific orgs for Partner API tests.

    This keeps production behavior unchanged while letting tests create
    organization-scoped API keys for org_a / org_rate_limit / org_partner_flow.
    """
    import os
    from app.seed import DEFAULT_ADMIN_EMAIL

    current_test = os.environ.get("PYTEST_CURRENT_TEST", "")
    target_org = None

    if "test_partner_api_v1.py::test_partner_key_cannot_access_other_org" in current_test:
        target_org = "org_a"
    elif "test_partner_api_v1.py::test_partner_rate_limit_returns_429" in current_test:
        target_org = "org_rate_limit"
    elif "test_partner_api_v1.py::test_partner_happy_path_search_quote_booking_docs" in current_test:
        target_org = "org_partner_flow"

    if not target_org:
        yield
        return

    await test_db.users.update_one(
        {"email": DEFAULT_ADMIN_EMAIL},
        {"$set": {"organization_id": target_org}},
    )

    yield




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
    )
    assert response.status_code == 200, f"Admin login failed: {response.text}"
    data = response.json()
    return data["access_token"]


@pytest.fixture(autouse=True)
async def minimal_search_seed(test_db, async_client: httpx.AsyncClient, agency_token: str):
    """Seed minimal catalog (products + rate_plans) directly into test_db.

    Ensures P0.2 /api/b2b/hotels/search returns at least one item for FX tests.
    """

    # Only run the HTTP validation for FX / cancel tests to avoid slowing full suite
    import os
    from datetime import timedelta

    current_test = os.environ.get("PYTEST_CURRENT_TEST", "")
    run_http_check = any(
        key in current_test
        for key in [
            "test_booking_financials_fx",
            "test_fx_snapshots",
            "test_booking_cancel_reverses_ledger_net0",
            "test_non_eur_booking_fx_and_ledger",
        ]
    )

    # Resolve org/agency from /api/auth/me using agency_token
    headers = {"Authorization": f"Bearer {agency_token}"}
    me_resp = await async_client.get("/api/auth/me", headers=headers)
    assert me_resp.status_code == 200, f"/auth/me failed: {me_resp.text}"
    me = me_resp.json()
    org_id = me.get("organization_id")

    from bson import ObjectId

    # Upsert product (hotel) in test_db
    prod_filter = {
        "organization_id": org_id,
        "type": "hotel",
        "status": "active",
        "location.city": "Istanbul",
        "code": "FXTEST-HOTEL",
    }
    existing_prod = await test_db.products.find_one(prod_filter)
    if existing_prod:
        product_id = existing_prod["_id"]
    else:
        product_id = ObjectId()
        prod_doc = {
            "_id": product_id,
            "organization_id": org_id,
            "type": "hotel",
            "status": "active",
            "code": "FXTEST-HOTEL",
            "name": {"tr": "FX Test Hotel"},
            "location": {"city": "Istanbul", "country": "TR"},
            "default_currency": "EUR",
            "created_at": now_utc(),
        }
        await test_db.products.insert_one(prod_doc)

    # Upsert active EUR rate plan with base_net_price > 0
    rp_filter = {
        "organization_id": org_id,
        "product_id": product_id,
        "status": "active",
        "currency": "EUR",
        "code": "FXTEST-RP",
    }
    existing_rp = await test_db.rate_plans.find_one(rp_filter)
    if not existing_rp:
        rp_doc = {
            "organization_id": org_id,
            "product_id": product_id,
            "status": "active",
            "currency": "EUR",
            "code": "FXTEST-RP",
            "board": "BB",
            "base_net_price": 100.0,
        }
        await test_db.rate_plans.insert_one(rp_doc)

    # Seed minimal inventory/availability for inventory-based availability check
    # (b2b_pricing._price_item reads from `inventory` collection)
    today = now_utc().date()
    check_in_date = today.replace(year=2026, month=1, day=10)
    for offset in range(0, 2):
        d = check_in_date + timedelta(days=offset)
        await test_db.inventory.update_one(
            {
                "organization_id": org_id,
                "product_id": product_id,
                "date": d.isoformat(),
            },
            {
                "$set": {
                    "organization_id": org_id,
                    "product_id": product_id,
                    "date": d.isoformat(),
                    "capacity_available": 10,
                    "price": 100.0,
                    "restrictions": {"closed": False},
                    "updated_at": now_utc(),
                }
            },
            upsert=True,
        )

    # Optional HTTP-level validation only for FX-related tests
    if run_http_check:
        today = now_utc().date()
        check_in = today.replace(year=2026, month=1, day=10)
        check_out = today.replace(year=2026, month=1, day=12)
        params = {
            "city": "Istanbul",
            "check_in": check_in.isoformat(),
            "check_out": check_out.isoformat(),
            "adults": "2",
            "children": "0",
        }
        resp = await async_client.get("/api/b2b/hotels/search", headers=headers, params=params)
        assert resp.status_code == 200, f"seed search failed: {resp.text}"
        data = resp.json()
        items = data.get("items") or []
        assert items, f"Seeded search returned no items: {data}"

    yield


@pytest.fixture(autouse=True)
async def minimal_finance_seed(test_db, async_client: httpx.AsyncClient, agency_token: str):
    """Seed minimal finance data so bookings can be created in FX tests.

    This creates agency and platform finance accounts, a credit profile and
    a zero balance for the agency account in the isolated test_db.
    """

    import os

    current_test = os.environ.get("PYTEST_CURRENT_TEST", "")
    if not any(
        key in current_test
        for key in [
            "test_booking_financials_fx",
            "test_fx_snapshots",
            "test_booking_cancel_reverses_ledger_net0",
            "test_non_eur_booking_fx_and_ledger",
            "test_refund_fx_ledger",
            "test_booking_amend_quote_and_confirm_zero_delta",
            "test_booking_amend_quote_and_confirm_increase_delta",
            "test_booking_amend_quote_and_confirm_decrease_delta",
        ]
    ):
        yield
        return

    # Resolve org/agency from /api/auth/me using agency_token
    headers = {"Authorization": f"Bearer {agency_token}"}
    me_resp = await async_client.get("/api/auth/me", headers=headers)
    assert me_resp.status_code == 200, f"/auth/me failed: {me_resp.text}"
    me = me_resp.json()

    org_id = me.get("organization_id")
    agency_id = me.get("agency_id")
    assert org_id and agency_id, f"Missing org/agency in /auth/me: {me}"

    now = now_utc()

    # Ensure organization document exists with cancel penalty settings
    await test_db.organizations.update_one(
        {"_id": org_id},
        {
            "$setOnInsert": {
                "_id": org_id,
                "slug": "default",
                "name": "Demo Org",
                "created_at": now,
                "updated_at": now,
            },
            "$set": {"settings.cancel_penalty_percent": 20.0},
        },
        upsert=True,
    )

    # 1) Agency finance account required by booking finance checks
    agency_acct_filter = {
        "organization_id": org_id,
        "type": "agency",
        "owner_id": agency_id,
    }
    from bson import ObjectId

    agency_acct_id = str(ObjectId())
    agency_acct_doc = {
        "_id": agency_acct_id,
        **agency_acct_filter,
        "currency": "EUR",
        "code": "AGENCY_AR",
        "name": "Agency Receivable",
        "status": "active",
        "created_at": now,
        "updated_at": now,
    }
    await test_db.finance_accounts.update_one(
        {"_id": agency_acct_id},
        {"$setOnInsert": agency_acct_doc},
        upsert=True,
    )

    agency_account = agency_acct_doc

    # 2) Platform finance account required by booking_confirmed posting
    platform_acct_filter = {
        "organization_id": org_id,
        "type": "platform",
    }
    platform_acct_id = str(ObjectId())
    platform_acct_doc = {
        "_id": platform_acct_id,
        **platform_acct_filter,
        "currency": "EUR",
        "code": "PLATFORM",
        "name": "Platform Clearing",
        "status": "active",
        "created_at": now,
        "updated_at": now,
    }
    await test_db.finance_accounts.update_one(
        {"_id": platform_acct_id},
        {"$setOnInsert": platform_acct_doc},
        upsert=True,
    )

    # 3) Credit profile for the agency (high limit to avoid limit errors)
    credit_profile_filter = {
        "organization_id": org_id,
        "agency_id": agency_id,
    }
    credit_profile_doc = {
        **credit_profile_filter,
        "limit": 1_000_000.0,
        "soft_limit": 500_000.0,
        "created_at": now,
        "updated_at": now,
    }
    await test_db.credit_profiles.update_one(
        credit_profile_filter,
        {"$setOnInsert": credit_profile_doc},
        upsert=True,
    )

    # 4) Zero balance for the agency account
    balance_filter = {
        "organization_id": org_id,
        "account_id": agency_account["_id"],
        "currency": "EUR",
    }
    balance_doc = {
        **balance_filter,
        "balance": 0.0,
        "created_at": now,
        "updated_at": now,
    }
    await test_db.account_balances.update_one(
        balance_filter,
        {"$setOnInsert": balance_doc},
        upsert=True,
    )

    yield


@pytest.fixture(autouse=True)
def patch_cancel_test_get_db(monkeypatch, test_db):
    """Ensure cancel net0 test's local get_db binding returns test_db only.

    We do NOT patch app.db.get_db itself to avoid impacting auth/other routes.
    Instead we patch the test module's imported symbol.
    """
    import os

    current_test = os.environ.get("PYTEST_CURRENT_TEST", "")
    if "test_booking_cancel_reverses_ledger_net0.py" not in current_test:
        return

    async def _get_test_db():
        return test_db

    # Patch common module import paths for the test module
    try:
        import tests.test_booking_cancel_reverses_ledger_net0 as m
        monkeypatch.setattr(m, "get_db", _get_test_db, raising=False)
    except Exception:
        pass

    try:
        import test_booking_cancel_reverses_ledger_net0 as m2
        monkeypatch.setattr(m2, "get_db", _get_test_db, raising=False)
    except Exception:
        pass


@pytest.fixture(autouse=True)
async def patch_cancel_net0_get_db(monkeypatch, test_db):
    """Ensure cancel net0 test uses test_db for both direct get_db and ledger posting.

    - Patches the test module's local get_db binding
    - Patches app.services.ledger_posting.get_db so LedgerPostingService writes to test_db
    """
    import os

    current_test = os.environ.get("PYTEST_CURRENT_TEST", "")
    if "test_booking_cancel_reverses_ledger_net0.py" not in current_test:
        yield
        return

    async def _get_test_db():
        return test_db

    # Patch common module import paths for the cancel net0 test module
    for modname in [
        "tests.test_booking_cancel_reverses_ledger_net0",
        "test_booking_cancel_reverses_ledger_net0",
    ]:
        try:
            m = __import__(modname, fromlist=["*"])
            monkeypatch.setattr(m, "get_db", _get_test_db, raising=False)
        except Exception:
            pass

    # Patch bound get_db inside ledger_posting so postings go to test_db
    try:
        import app.services.ledger_posting as lp_mod
        monkeypatch.setattr(lp_mod, "get_db", _get_test_db, raising=False)
    except Exception:
        pass

    yield


@pytest.fixture(autouse=True)
async def seed_confirmed_booking_for_cancel_net0(test_db, async_client: httpx.AsyncClient, agency_token: str):
    """Ensure there is at least one real CONFIRMED booking for cancel net0 test.

    Uses the existing P0.2 HTTP flow (search -> quote -> booking) so that
    booking_financials and FX snapshots are correctly populated.
    """
    import os

    current_test = os.environ.get("PYTEST_CURRENT_TEST", "")
    if "test_booking_cancel_reverses_ledger_net0.py" not in current_test:
        return

    headers = {"Authorization": f"Bearer {agency_token}"}

    # Resolve org/agency
    me_resp = await async_client.get("/api/auth/me", headers=headers)
    assert me_resp.status_code == 200, f"/auth/me failed in seed_confirmed_booking: {me_resp.text}"
    me = me_resp.json()
    org_id = me["organization_id"]
    agency_id = me["agency_id"]

    # If there is already a CONFIRMED booking for this agency/org in test_db, do nothing
    existing = await test_db.bookings.find_one(
        {"organization_id": org_id, "agency_id": agency_id, "status": "CONFIRMED"},
        {"_id": 1},
    )
    if existing:
        return

    # 1) Hotel search (dates chosen to align with FX tests)
    params = {
        "city": "Istanbul",
        "check_in": "2026-01-10",
        "check_out": "2026-01-12",
        "adults": "2",
        "children": "0",
    }
    s = await async_client.get("/api/b2b/hotels/search", headers=headers, params=params)
    assert s.status_code == 200, f"hotel search failed: {s.text}"
    data = s.json() or {}
    items = data.get("items") or []
    assert items, f"hotel search returned empty: {data}"

    item = items[0]
    product_id = item.get("product_id") or item.get("id") or item.get("_id")
    assert product_id, f"cannot resolve product_id from search item: {item}"
    rate_plan_id = item.get("rate_plan_id") or item.get("ratePlanId")
    assert rate_plan_id, f"cannot resolve rate_plan_id from search item: {item}"

    # 2) Quote create (reuse P0.2 payload shape from FX tests)
    quote_payload = {
        "channel_id": "agency_extranet",
        "items": [
            {
                "product_id": product_id,
                "room_type_id": "default_room",
                "rate_plan_id": rate_plan_id,
                "check_in": params["check_in"],
                "check_out": params["check_out"],
                "occupancy": 2,
            }
        ],
        "client_context": {"source": "cancel-net0-seed"},
    }
    q = await async_client.post("/api/b2b/quotes", headers=headers, json=quote_payload)
    assert q.status_code == 200, f"quote create failed: {q.status_code} - {q.text}"
    quote = q.json() or {}
    quote_id = quote.get("quote_id") or quote.get("id") or quote.get("_id")
    assert quote_id, f"cannot resolve quote_id from quote response: {quote}"

    # 3) Booking create via P0.2 endpoint
    booking_payload = {
        "quote_id": quote_id,
        "customer": {"name": "Cancel Test", "email": "cancel@test.com"},
        "travellers": [{"first_name": "Cancel", "last_name": "Test"}],
        "notes": "Cancel net0 seed booking",
    }
    from uuid import uuid4

    b = await async_client.post(
        "/api/b2b/bookings",
        headers={**headers, "Idempotency-Key": f"cancel-net0-seed-{uuid4().hex[:8]}"},
        json=booking_payload,
    )
    assert b.status_code == 200, f"booking create failed: {b.status_code} - {b.text}"


@pytest.fixture(autouse=True)
async def patch_fx_tests_get_db(monkeypatch, test_db):
    """Route FX-related tests + ledger_posting to the isolated test_db.

    Ensures:
    - tests/test_booking_financials_fx.py and tests/test_fx_snapshots.py use test_db
      for their get_db calls
    - LedgerPostingService.post_event also writes to test_db for these tests
    """
    import os

    current_test = os.environ.get("PYTEST_CURRENT_TEST", "")
    if not any(
        key in current_test
        for key in [
            "test_booking_financials_fx.py",
            "test_fx_snapshots.py",
            "test_non_eur_booking_fx_and_ledger.py",
        ]
    ):
        yield
    else:
        async def _get_test_db():
            return test_db

        # Patch test modules' local get_db bindings
        for modname in [
            "tests.test_booking_financials_fx",
            "test_booking_financials_fx",
            "tests.test_fx_snapshots",
            "test_fx_snapshots",
        ]:
            try:
                m = __import__(modname, fromlist=["*"])
                monkeypatch.setattr(m, "get_db", _get_test_db, raising=False)
            except Exception:
                pass

        # Ensure ledger_posting service also uses test_db
        try:
            import app.services.ledger_posting as lp_mod
            monkeypatch.setattr(lp_mod, "get_db", _get_test_db, raising=False)
        except Exception:
            pass

        yield


@pytest.fixture
async def admin_headers(admin_token: str) -> Dict[str, str]:
    """Convenience fixture returning Authorization header for admin."""

    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture
async def agency_token(async_client: httpx.AsyncClient, seed_default_org_and_users) -> str:
    """Login as agency user and return access token.

    Depends on seed_default_org_and_users to ensure the default organization
    and demo agency user exist inside the isolated test_db before login.
    """

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