from __future__ import annotations

from typing import Any

from datetime import timedelta
import jwt
import pytest
from httpx import AsyncClient

from app.auth import _jwt_secret
from app.errors import AppError
from app.utils import now_utc


def _make_search_headers(org_id: str, email: str, tenant_key: str) -> dict[str, str]:
    token = jwt.encode({"sub": email, "org": org_id}, _jwt_secret(), algorithm="HS256")
    return {"Authorization": f"Bearer {token}", "X-Tenant-Key": tenant_key}


async def _get_default_org_and_user_for_search(test_db: Any) -> tuple[str, str]:
    org = await test_db.organizations.find_one({"slug": "default"})
    assert org is not None
    org_id = str(org["_id"])
    email = "agency1@demo.test"
    return org_id, email


@pytest.mark.exit_supplier_health_snapshot_updates_on_calls
@pytest.mark.anyio
async def test_supplier_health_snapshot_updates_on_calls(test_db: Any, async_client: AsyncClient, monkeypatch: Any) -> None:
    """Health snapshot should reflect success/fail counts and last_error_codes from events."""

    from app.services.supplier_health_service import WINDOW_SEC_DEFAULT

    client: AsyncClient = async_client
    db = test_db

    now = now_utc()
    org_id, email = await _get_default_org_and_user_for_search(db)

    # Seed tenant for search
    await db.tenants.insert_one(
        {
            "tenant_key": "health-tenant-1",
            "organization_id": org_id,
            "brand_name": "Health Tenant 1",
            "primary_domain": "health-tenant-1.example.com",
            "subdomain": "health-tenant-1",
            "theme_config": {},
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
    )

    headers = _make_search_headers(org_id, email, "health-tenant-1")

    call_counter = {"n": 0}

    async def _mock_search_mock_offers(payload: dict[str, Any]) -> dict[str, Any]:  # type: ignore[no-untyped-def]
        call_counter["n"] += 1
        if call_counter["n"] < 3:
            # success
            return {
                "supplier": "mock",
                "offers": [
                    {
                        "id": f"MOCK-OFF-{call_counter['n']}",
                        "hotel": {"id": "H1"},
                        "room": {"id": "R1"},
                        "stay": {"nights": 2},
                        "price": {"amount": 100.0, "currency": "TRY"},
                    }
                ],
            }
        raise AppError(503, "SUPPLIER_TIMEOUT", "Mock timeout", {})

    monkeypatch.setattr("app.services.suppliers.mock_supplier_service.search_mock_offers", _mock_search_mock_offers)

    payload = {
        "destination": "IST",
        "check_in": "2026-01-10",
        "check_out": "2026-01-12",
        "adults": 2,
        "children": 0,
        "supplier_codes": ["mock"],
    }

    # Two successes and one failure
    for _ in range(3):
        await client.post("/api/offers/search", json=payload, headers=headers)

    health = await db.supplier_health.find_one({"organization_id": org_id, "supplier_code": "mock"})
    assert health is not None
    metrics = health.get("metrics") or {}
    assert metrics["total_calls"] == 3
    assert metrics["success_calls"] == 2
    assert metrics["fail_calls"] == 1
    assert 0.6 <= metrics["success_rate"] <= 0.8
    assert 0.2 <= metrics["error_rate"] <= 0.4
    assert "SUPPLIER_TIMEOUT" in (metrics.get("last_error_codes") or [])
    assert health.get("window_sec") == WINDOW_SEC_DEFAULT


@pytest.mark.exit_supplier_circuit_opens_after_consecutive_failures
@pytest.mark.anyio
async def test_supplier_circuit_opens_after_consecutive_failures(test_db: Any, async_client: AsyncClient, monkeypatch: Any) -> None:
    """Three consecutive failures should open paximum circuit and emit audit."""

    client: AsyncClient = async_client
    db = test_db

    now = now_utc()
    org_id, email = await _get_default_org_and_user_for_search(db)

    await db.tenants.insert_one(
        {
            "tenant_key": "circuit-tenant-1",
            "organization_id": org_id,
            "brand_name": "Circuit Tenant 1",
            "primary_domain": "circuit-tenant-1.example.com",
            "subdomain": "circuit-tenant-1",
            "theme_config": {},
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
    )
    headers = _make_search_headers(org_id, email, "circuit-tenant-1")

    async def _failing_paximum(*args: Any, **kwargs: Any) -> dict[str, Any]:  # type: ignore[no-untyped-def]
        raise AppError(503, "SUPPLIER_TIMEOUT", "Paximum timeout", {})

    monkeypatch.setattr("app.services.supplier_search_service.search_paximum_offers", _failing_paximum)

    payload = {
        "destination": "IST",
        "check_in": "2026-01-10",
        "check_out": "2026-01-12",
        "adults": 2,
        "children": 0,
        "supplier_codes": ["paximum"],
    }

    for _ in range(3):
        await client.post("/api/offers/search", json=payload, headers=headers)

    health = await db.supplier_health.find_one({"organization_id": org_id, "supplier_code": "paximum"})
    assert health is not None
    circuit = health.get("circuit") or {}
    assert circuit.get("state") == "open"
    assert circuit.get("until") is not None
    assert circuit.get("consecutive_failures", 0) >= 3

    audit = await db.audit_logs.find_one(
        {"organization_id": org_id, "action": "SUPPLIER_CIRCUIT_OPENED", "target.id": "paximum"}
    )
    assert audit is not None


@pytest.mark.exit_supplier_circuit_open_skips_supplier_and_emits_warning
@pytest.mark.anyio
async def test_supplier_circuit_open_skips_supplier_and_emits_warning(test_db: Any, async_client: AsyncClient, monkeypatch: Any) -> None:
    """When circuit is already open, paximum should be skipped and a SUPPLIER_CIRCUIT_OPEN warning emitted."""

    client: AsyncClient = async_client
    db = test_db

    now = now_utc()
    org_id, email = await _get_default_org_and_user_for_search(db)

    await db.tenants.insert_one(
        {
            "tenant_key": "circuit-tenant-2",
            "organization_id": org_id,
            "brand_name": "Circuit Tenant 2",
            "primary_domain": "circuit-tenant-2.example.com",
            "subdomain": "circuit-tenant-2",
            "theme_config": {},
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
    )
    headers = _make_search_headers(org_id, email, "circuit-tenant-2")

    # Seed open circuit with future until
    await db.supplier_health.insert_one(
        {
            "organization_id": org_id,
            "supplier_code": "paximum",
            "window_sec": 900,
            "metrics": {
                "total_calls": 10,
                "success_calls": 5,
                "fail_calls": 5,
                "success_rate": 0.5,
                "error_rate": 0.5,
                "avg_latency_ms": 1000,
                "p95_latency_ms": 2000,
                "last_error_codes": ["SUPPLIER_TIMEOUT"],
            },
            "circuit": {
                "state": "open",
                "opened_at": now,
                "until": now_utc() + timedelta(seconds=60),
                "reason_code": "SUPPLIER_TIMEOUT",
                "consecutive_failures": 3,
                "last_transition_at": now,
            },
            "updated_at": now,
        }
    )

    called = {"paximum": False}

    async def _paximum_should_not_be_called(*args: Any, **kwargs: Any) -> dict[str, Any]:  # type: ignore[no-untyped-def]
        called["paximum"] = True
        raise AssertionError("Paximum adapter should not be called when circuit is open")

    # Force circuit-open check to short-circuit paximum before adapter is called
    async def _always_open(*args: Any, **kwargs: Any) -> bool:  # type: ignore[no-untyped-def]
        return True

    monkeypatch.setattr("app.routers.offers.is_supplier_circuit_open", _always_open)
    monkeypatch.setattr("app.services.supplier_search_service.search_paximum_offers", _paximum_should_not_be_called)

    payload = {
        "destination": "IST",
        "check_in": "2026-01-10",
        "check_out": "2026-01-12",
        "adults": 2,
        "children": 0,
        "supplier_codes": ["mock", "paximum"],
    }

    resp = await client.post("/api/offers/search", json=payload, headers=headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()

    assert called["paximum"] is False
    warnings = body.get("warnings") or []
    assert any(w.get("supplier_code") == "paximum" and w.get("code") == "SUPPLIER_CIRCUIT_OPEN" for w in warnings)


@pytest.mark.exit_supplier_circuit_closes_after_until
@pytest.mark.anyio
async def test_supplier_circuit_closes_after_until(test_db: Any, async_client: AsyncClient) -> None:
    """If until is in the past, next check should auto-close circuit and emit CLOSED audit."""

    from datetime import timedelta as _td

    client: AsyncClient = async_client
    db = test_db

    now = now_utc()
    org_id, email = await _get_default_org_and_user_for_search(db)

    await db.tenants.insert_one(
        {
            "tenant_key": "circuit-tenant-3",
            "organization_id": org_id,
            "brand_name": "Circuit Tenant 3",
            "primary_domain": "circuit-tenant-3.example.com",
            "subdomain": "circuit-tenant-3",
            "theme_config": {},
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
    )
    headers = _make_search_headers(org_id, email, "circuit-tenant-3")

    # Seed open circuit with past until
    await db.supplier_health.insert_one(
        {
    from app.services.supplier_health_service import is_supplier_circuit_open

    # Trigger auto-close once via health check
    is_open = await is_supplier_circuit_open(db, organization_id=org_id, supplier_code="paximum")
    assert is_open is False


            "organization_id": org_id,
            "supplier_code": "paximum",
            "window_sec": 900,
            "metrics": {
                "total_calls": 3,
                "success_calls": 0,
                "fail_calls": 3,
                "success_rate": 0.0,
                "error_rate": 1.0,
                "avg_latency_ms": 1500,
                "p95_latency_ms": 2500,
                "last_error_codes": ["SUPPLIER_TIMEOUT"],
            },
            "circuit": {
                "state": "open",
                "opened_at": now - _td(seconds=300),
                "until": now - _td(seconds=60),
                "reason_code": "SUPPLIER_TIMEOUT",
                "consecutive_failures": 3,
                "last_transition_at": now - _td(seconds=300),
            },
            "updated_at": now - _td(seconds=60),
        }
    )

    payload = {
        "destination": "IST",
        "check_in": "2026-01-10",
        "check_out": "2026-01-12",
        "adults": 2,
        "children": 0,
        "supplier_codes": ["paximum"],
    }

    # First call should auto-close circuit and behave as normal (we don't care about supplier result here)
    await client.post("/api/offers/search", json=payload, headers=headers)

    health = await db.supplier_health.find_one({"organization_id": org_id, "supplier_code": "paximum"})
    assert health is not None
    circuit = health.get("circuit") or {}
    assert circuit.get("state") == "closed"

    audit = await db.audit_logs.find_one(
        {"organization_id": org_id, "action": "SUPPLIER_CIRCUIT_CLOSED", "target.id": "paximum"}
    )
    assert audit is not None


@pytest.mark.exit_admin_supplier_health_endpoint_rbac_and_shape
@pytest.mark.anyio
async def test_admin_supplier_health_endpoint_rbac_and_shape(test_db: Any, async_client: AsyncClient) -> None:
    """Admin can read supplier health snapshot; non-admin is rejected."""

    client: AsyncClient = async_client
    db = test_db

    now = now_utc()

    # Seed org + users
    org = await db.organizations.insert_one(
        {"name": "Ops Org", "slug": "ops_org_health", "created_at": now, "updated_at": now}
    )
    org_id = str(org.inserted_id)

    admin_email = "admin-health@example.com"
    agent_email = "agent-health@example.com"

    await db.users.insert_many(
        [
            {
                "organization_id": org_id,
                "email": admin_email,
                "roles": ["agency_admin"],
                "is_active": True,
                "created_at": now,
                "updated_at": now,
            },
            {
                "organization_id": org_id,
                "email": agent_email,
                "roles": ["agency_agent"],
                "is_active": True,
                "created_at": now,
                "updated_at": now,
            },
        ]
    )

    # Seed health snapshot
    await db.supplier_health.insert_one(
        {
            "organization_id": org_id,
            "supplier_code": "mock",
            "window_sec": 900,
            "metrics": {
                "total_calls": 5,
                "success_calls": 4,
                "fail_calls": 1,
                "success_rate": 0.8,
                "error_rate": 0.2,
                "avg_latency_ms": 500,
                "p95_latency_ms": 900,
                "last_error_codes": ["SUPPLIER_TIMEOUT"],
            },
            "circuit": {
                "state": "closed",
                "opened_at": None,
                "until": None,
                "reason_code": None,
                "consecutive_failures": 0,
                "last_transition_at": now,
            },
            "updated_at": now,
        }
    )

    # Admin access
    admin_headers = {"Authorization": f"Bearer {jwt.encode({'sub': admin_email, 'org': org_id, 'roles': ['agency_admin']}, _jwt_secret(), algorithm='HS256')}"}
    resp = await client.get("/api/admin/suppliers/health", headers=admin_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["window_sec"] == 900
    assert len(body.get("items") or []) == 1
    item = body["items"][0]
    assert item["supplier_code"] == "mock"
    assert item["metrics"]["total_calls"] == 5

    # Non-admin access
    agent_headers = {"Authorization": f"Bearer {jwt.encode({'sub': agent_email, 'org': org_id, 'roles': ['agency_agent']}, _jwt_secret(), algorithm='HS256')}"}
    resp2 = await client.get("/api/admin/suppliers/health", headers=agent_headers)
    assert resp2.status_code in (401, 403)


@pytest.mark.exit_admin_supplier_health_filtering_deterministic_order
@pytest.mark.anyio
async def test_admin_supplier_health_filtering_deterministic_order(test_db: Any, async_client: AsyncClient) -> None:
    """Filtering by supplier_codes should return deterministic order by supplier_code."""

    client: AsyncClient = async_client
    db = test_db

    now = now_utc()

    org = await db.organizations.insert_one(
        {"name": "Ops Org 2", "slug": "ops_org_health2", "created_at": now, "updated_at": now}
    )
    org_id = str(org.inserted_id)
    admin_email = "admin-health2@example.com"

    await db.users.insert_one(
        {
            "organization_id": org_id,
            "email": admin_email,
            "roles": ["agency_admin"],
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
    )

    docs = [
        {
            "organization_id": org_id,
            "supplier_code": "mock",
            "window_sec": 900,
            "metrics": {"total_calls": 1, "success_calls": 1, "fail_calls": 0, "success_rate": 1.0, "error_rate": 0.0, "avg_latency_ms": 100, "p95_latency_ms": 100, "last_error_codes": []},
            "circuit": {"state": "closed", "opened_at": None, "until": None, "reason_code": None, "consecutive_failures": 0, "last_transition_at": now},
            "updated_at": now,
        },
        {
            "organization_id": org_id,
            "supplier_code": "paximum",
            "window_sec": 900,
            "metrics": {"total_calls": 2, "success_calls": 2, "fail_calls": 0, "success_rate": 1.0, "error_rate": 0.0, "avg_latency_ms": 200, "p95_latency_ms": 200, "last_error_codes": []},
            "circuit": {"state": "closed", "opened_at": None, "until": None, "reason_code": None, "consecutive_failures": 0, "last_transition_at": now},
            "updated_at": now,
        },
        {
            "organization_id": org_id,
            "supplier_code": "other",
            "window_sec": 900,
            "metrics": {"total_calls": 3, "success_calls": 3, "fail_calls": 0, "success_rate": 1.0, "error_rate": 0.0, "avg_latency_ms": 300, "p95_latency_ms": 300, "last_error_codes": []},
            "circuit": {"state": "closed", "opened_at": None, "until": None, "reason_code": None, "consecutive_failures": 0, "last_transition_at": now},
            "updated_at": now,
        },
    ]
    await db.supplier_health.insert_many(docs)

    admin_headers = {"Authorization": f"Bearer {jwt.encode({'sub': admin_email, 'org': org_id, 'roles': ['agency_admin']}, _jwt_secret(), algorithm='HS256')}"}
    resp = await client.get("/api/admin/suppliers/health?supplier_codes=paximum,mock", headers=admin_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    items = body.get("items") or []
    assert len(items) == 2
    assert items[0]["supplier_code"] == "mock"
    assert items[1]["supplier_code"] == "paximum"
