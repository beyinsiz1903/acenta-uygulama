from __future__ import annotations

from typing import Any, Dict

import httpx
import pytest

from app.db import get_db
from app.utils import now_utc


@pytest.mark.asyncio
async def test_list_cases_default_open(async_client: httpx.AsyncClient, minimal_search_seed):
    """Default listing returns only open cases for org."""

    db = await get_db()

    # Seed a few cases
    now = now_utc()
    org_id = "org_ops_test"

    cases = [
        {
            "case_id": "CASE-OPEN-CANCEL",
            "type": "cancel",
            "status": "open",
            "source": "guest_portal",
            "booking_id": "BKG1",
            "booking_code": "CODE1",
            "organization_id": org_id,
            "created_at": now,
            "updated_at": now,
        },
        {
            "case_id": "CASE-OPEN-AMEND",
            "type": "amend",
            "status": "open",
            "source": "guest_portal",
            "booking_id": "BKG2",
            "booking_code": "CODE2",
            "organization_id": org_id,
            "created_at": now,
            "updated_at": now,
        },
        {
            "case_id": "CASE-CLOSED-CANCEL",
            "type": "cancel",
            "status": "closed",
            "source": "guest_portal",
            "booking_id": "BKG3",
            "booking_code": "CODE3",
            "organization_id": org_id,
            "created_at": now,
            "updated_at": now,
        },
    ]

    await db.ops_cases.delete_many({"organization_id": org_id})
    await db.ops_cases.insert_many(cases)

    # Login as admin in this org
    # Reuse existing admin user but override organization_id for test scope
    admin_email = "admin@acenta.test"
    await db.users.update_one(
        {"email": admin_email},
        {"$set": {"organization_id": org_id}},
    )

    login_resp = await async_client.post(
        "/api/auth/login",
        json={"email": admin_email, "password": "admin123"},
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]

    resp = await async_client.get(
        "/api/ops/guest-cases", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200
    data = resp.json()
    items = data["items"]

    # Only the two open cases for this org
    case_ids = {c["case_id"] for c in items}
    assert "CASE-OPEN-CANCEL" in case_ids
    assert "CASE-OPEN-AMEND" in case_ids
    assert "CASE-CLOSED-CANCEL" not in case_ids


@pytest.mark.asyncio
async def test_list_cases_filter_type_and_status(async_client: httpx.AsyncClient):
    """Filtering by type and status works."""

    db = await get_db()
    org_id = "org_ops_test_filter"
    now = now_utc()

    await db.ops_cases.delete_many({"organization_id": org_id})
    await db.ops_cases.insert_many(
        [
            {
                "case_id": "CASE-F1",
                "type": "cancel",
                "status": "open",
                "source": "guest_portal",
                "booking_id": "BKG1",
                "booking_code": "C1",
                "organization_id": org_id,
                "created_at": now,
                "updated_at": now,
            },
            {
                "case_id": "CASE-F2",
                "type": "amend",
                "status": "open",
                "source": "guest_portal",
                "booking_id": "BKG2",
                "booking_code": "C2",
                "organization_id": org_id,
                "created_at": now,
                "updated_at": now,
            },
        ]
    )

    admin_email = "admin@acenta.test"
    await db.users.update_one(
        {"email": admin_email},
        {"$set": {"organization_id": org_id}},
    )
    login_resp = await async_client.post(
        "/api/auth/login",
        json={"email": admin_email, "password": "admin123"},
    )
    token = login_resp.json()["access_token"]

    resp = await async_client.get(
        "/api/ops/guest-cases?status=open&type=cancel",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    items = data["items"]

    assert len(items) == 1
    assert items[0]["case_id"] == "CASE-F1"


@pytest.mark.asyncio
async def test_get_case_wrong_org_404(async_client: httpx.AsyncClient):
    """Case from another org is not visible (404)."""

    db = await get_db()
    org_id_a = "org_ops_A"
    org_id_b = "org_ops_B"
    now = now_utc()

    await db.ops_cases.delete_many({"case_id": "CASE-ORG-A"})
    await db.ops_cases.insert_one(
        {
            "case_id": "CASE-ORG-A",
            "type": "cancel",
            "status": "open",
            "source": "guest_portal",
            "booking_id": "BKG1",
            "booking_code": "CODE1",
            "organization_id": org_id_a,
            "created_at": now,
            "updated_at": now,
        }
    )

    admin_email = "admin@acenta.test"
    await db.users.update_one(
        {"email": admin_email},
        {"$set": {"organization_id": org_id_b}},
    )

    login_resp = await async_client.post(
        "/api/auth/login",
        json={"email": admin_email, "password": "admin123"},
    )
    token = login_resp.json()["access_token"]

    resp = await async_client.get(
        "/api/ops/cases/CASE-ORG-A",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_close_case_sets_status_and_emits_event(async_client: httpx.AsyncClient):
    """Closing a case sets status=closed and emits OPS_CASE_CLOSED event."""

    db = await get_db()
    org_id = "org_ops_close"
    now = now_utc()

    await db.ops_cases.delete_many({"organization_id": org_id})
    await db.booking_events.delete_many({"organization_id": org_id})

    await db.ops_cases.insert_one(
        {
            "case_id": "CASE-CLOSE-1",
            "type": "cancel",
            "status": "open",
            "source": "guest_portal",
            "booking_id": "BKG-CLOSE-1",
            "booking_code": "CODE-CLOSE-1",
            "organization_id": org_id,
            "created_at": now,
            "updated_at": now,
        }
    )

    admin_email = "admin@acenta.test"
    await db.users.update_one(
        {"email": admin_email},
        {"$set": {"organization_id": org_id}},
    )

    login_resp = await async_client.post(
        "/api/auth/login",
        json={"email": admin_email, "password": "admin123"},
    )
    token = login_resp.json()["access_token"]

    resp = await async_client.post(
        "/api/ops/cases/CASE-CLOSE-1/close",
        json={"note": "Ops note"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["status"] == "closed"

    # Verify case document
    case_doc = await db.ops_cases.find_one({"organization_id": org_id, "case_id": "CASE-CLOSE-1"})
    assert case_doc is not None
    assert case_doc["status"] == "closed"
    assert "closed_at" in case_doc
    assert "closed_by" in case_doc

    # Verify booking_events
    events = await db.booking_events.find({"organization_id": org_id, "booking_id": "BKG-CLOSE-1"}).to_list(10)
    types = [e.get("type") for e in events]
    assert "OPS_CASE_CLOSED" in types


@pytest.mark.asyncio
async def test_close_case_idempotent(async_client: httpx.AsyncClient):
    """Closing the same case twice is idempotent and does not emit duplicate events."""

    db = await get_db()
    org_id = "org_ops_close_idem"
    now = now_utc()

    await db.ops_cases.delete_many({"organization_id": org_id})
    await db.booking_events.delete_many({"organization_id": org_id})

    await db.ops_cases.insert_one(
        {
            "case_id": "CASE-IDEM-1",
            "type": "amend",
            "status": "open",
            "source": "guest_portal",
            "booking_id": "BKG-IDEM-1",
            "booking_code": "CODE-IDEM-1",
            "organization_id": org_id,
            "created_at": now,
            "updated_at": now,
        }
    )

    admin_email = "admin@acenta.test"
    await db.users.update_one(
        {"email": admin_email},
        {"$set": {"organization_id": org_id}},
    )

    login_resp = await async_client.post(
        "/api/auth/login",
        json={"email": admin_email, "password": "admin123"},
    )
    token = login_resp.json()["access_token"]

    # First close
    resp1 = await async_client.post(
        "/api/ops/cases/CASE-IDEM-1/close",
        json={"note": "First"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp1.status_code == 200

    # Second close (idempotent)
    resp2 = await async_client.post(
        "/api/ops/cases/CASE-IDEM-1/close",
        json={"note": "Second"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp2.status_code == 200

    # There should be only one OPS_CASE_CLOSED event
    events = await db.booking_events.find({"organization_id": org_id, "booking_id": "BKG-IDEM-1"}).to_list(10)
    types = [e.get("type") for e in events]
    assert types.count("OPS_CASE_CLOSED") == 1
