from __future__ import annotations

from typing import Any

import jwt
import pytest
from httpx import AsyncClient

from app.auth import _jwt_secret
from app.utils import now_utc


def _make_admin_headers(org_id: str, email: str) -> dict[str, str]:
    token = jwt.encode({"sub": email, "org": org_id, "roles": ["agency_admin"]}, _jwt_secret(), algorithm="HS256")
    return {"Authorization": f"Bearer {token}"}


def _make_agent_headers(org_id: str, email: str) -> dict[str, str]:
    token = jwt.encode({"sub": email, "org": org_id, "roles": ["agency_agent"]}, _jwt_secret(), algorithm="HS256")
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.exit_ops_incidents_list_no_enrichment_by_default
@pytest.mark.anyio
async def test_ops_incidents_list_no_enrichment_by_default(test_db: Any, async_client: AsyncClient) -> None:
    """By default, list endpoint should not enrich supplier health badges."""

    client: AsyncClient = async_client
    db = test_db
    now = now_utc()

    # Seed org + admin user
    org = await db.organizations.insert_one(
        {"name": "Ops Org", "slug": "ops_org_incidents_enrich", "created_at": now, "updated_at": now}
    )
    org_id = str(org.inserted_id)
    email = "admin-enrich@example.com"
    await db.users.insert_one(
        {
            "organization_id": org_id,
            "email": email,
            "roles": ["agency_admin"],
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
    )

    # Seed one supplier incident + matching health snapshot
    await db.ops_incidents.insert_one(
        {
            "incident_id": "inc_sup_1",
            "organization_id": org_id,
            "type": "supplier_partial_failure",
            "severity": "medium",
            "status": "open",
            "summary": "Supplier partial failure",
            "source_ref": {"session_id": "sess1"},
            "meta": {
                "failed_suppliers": [
                    {"supplier_code": "paximum", "code": "SUPPLIER_TIMEOUT"},
                    {"supplier_code": "mock", "code": "SUPPLIER_TIMEOUT"},
                ],
            },
            "created_at": now,
            "updated_at": now,
        }
    )

    await db.supplier_health.insert_one(
        {
            "organization_id": org_id,
            "supplier_code": "paximum",
            "window_sec": 900,
            "metrics": {
                "total_calls": 10,
                "success_calls": 6,
                "fail_calls": 4,
                "success_rate": 0.6,
                "error_rate": 0.4,
                "avg_latency_ms": 800,
                "p95_latency_ms": 2000,
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

    headers = _make_admin_headers(org_id, email)
    resp = await client.get("/api/admin/ops/incidents", headers=headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    items = body.get("items") or []
    assert len(items) == 1
    item = items[0]
    # By default enrichment is off; field may be absent or null depending on serializer
    assert "supplier_health" not in item or item["supplier_health"] in (None, {})


@pytest.mark.exit_ops_incidents_list_enrichment_attaches_badge
@pytest.mark.anyio
async def test_ops_incidents_list_enrichment_attaches_badge(test_db: Any, async_client: AsyncClient) -> None:
    """List endpoint should attach supplier health badge when include_supplier_health=true."""

    client: AsyncClient = async_client
    db = test_db
    now = now_utc()

    org = await db.organizations.insert_one(
        {"name": "Ops Org2", "slug": "ops_org_incidents_enrich2", "created_at": now, "updated_at": now}
    )
    org_id = str(org.inserted_id)
    email = "admin-enrich2@example.com"
    await db.users.insert_one(
        {
            "organization_id": org_id,
            "email": email,
            "roles": ["agency_admin"],
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
    )

    await db.ops_incidents.insert_one(
        {
            "incident_id": "inc_sup_2",
            "organization_id": org_id,
            "type": "supplier_partial_failure",
            "severity": "medium",
            "status": "open",
            "summary": "Supplier partial failure 2",
            "source_ref": {"session_id": "sess2"},
            "meta": {
                "failed_suppliers": [
                    {"supplier_code": "paximum", "code": "SUPPLIER_TIMEOUT"},
                ],
            },
            "created_at": now,
            "updated_at": now,
        }
    )

    await db.supplier_health.insert_one(
        {
            "organization_id": org_id,
            "supplier_code": "paximum",
            "window_sec": 900,
            "metrics": {
                "total_calls": 5,
                "success_calls": 3,
                "fail_calls": 2,
                "success_rate": 0.6,
                "error_rate": 0.4,
                "avg_latency_ms": 700,
                "p95_latency_ms": 1500,
                "last_error_codes": ["SUPPLIER_TIMEOUT"],
            },
            "circuit": {
                "state": "open",
                "opened_at": now,
                "until": now,
                "reason_code": "SUPPLIER_TIMEOUT",
                "consecutive_failures": 3,
                "last_transition_at": now,
            },
            "updated_at": now,
        }
    )

    headers = _make_admin_headers(org_id, email)
    resp = await client.get("/api/admin/ops/incidents?include_supplier_health=true", headers=headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    items = body.get("items") or []
    assert len(items) == 1
    item = items[0]
    badge = item.get("supplier_health")
    assert badge is not None
    assert badge["supplier_code"] == "paximum"
    assert badge["circuit_state"] == "open"
    assert pytest.approx(badge["success_rate"], rel=1e-3) == 0.6
    assert pytest.approx(badge["error_rate"], rel=1e-3) == 0.4
    assert badge.get("notes") == []


@pytest.mark.exit_ops_incidents_detail_enrichment_default_true
@pytest.mark.anyio
async def test_ops_incidents_detail_enrichment_default_true(test_db: Any, async_client: AsyncClient) -> None:
    """Detail endpoint should enrich supplier health by default."""

    client: AsyncClient = async_client
    db = test_db
    now = now_utc()

    org = await db.organizations.insert_one(
        {"name": "Ops Org3", "slug": "ops_org_incidents_enrich3", "created_at": now, "updated_at": now}
    )
    org_id = str(org.inserted_id)
    email = "admin-enrich3@example.com"
    await db.users.insert_one(
        {
            "organization_id": org_id,
            "email": email,
            "roles": ["agency_admin"],
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
    )

    await db.ops_incidents.insert_one(
        {
            "incident_id": "inc_sup_3",
            "organization_id": org_id,
            "type": "supplier_all_failed",
            "severity": "critical",
            "status": "open",
            "summary": "Supplier all failed",
            "source_ref": {"session_id": "sess3"},
            "meta": {
                "failed_suppliers": [
                    {"supplier_code": "mock", "code": "SUPPLIER_TIMEOUT"},
                ],
            },
            "created_at": now,
            "updated_at": now,
        }
    )

    await db.supplier_health.insert_one(
        {
            "organization_id": org_id,
            "supplier_code": "mock",
            "window_sec": 900,
            "metrics": {
                "total_calls": 7,
                "success_calls": 4,
                "fail_calls": 3,
                "success_rate": 0.5714,
                "error_rate": 0.4286,
                "avg_latency_ms": 600,
                "p95_latency_ms": 1400,
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

    headers = _make_admin_headers(org_id, email)
    resp = await client.get("/api/admin/ops/incidents/inc_sup_3", headers=headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    badge = body.get("supplier_health")
    assert badge is not None
    assert badge["supplier_code"] == "mock"
    assert badge["circuit_state"] == "closed"


@pytest.mark.exit_ops_incidents_enrichment_health_not_found_fail_open
@pytest.mark.anyio
async def test_ops_incidents_enrichment_health_not_found_fail_open(test_db: Any, async_client: AsyncClient) -> None:
    """If health snapshot is missing, enrichment should still return 200 with notes flag."""

    client: AsyncClient = async_client
    db = test_db
    now = now_utc()

    org = await db.organizations.insert_one(
        {"name": "Ops Org4", "slug": "ops_org_incidents_enrich4", "created_at": now, "updated_at": now}
    )
    org_id = str(org.inserted_id)
    email = "admin-enrich4@example.com"
    await db.users.insert_one(
        {
            "organization_id": org_id,
            "email": email,
            "roles": ["agency_admin"],
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
    )

    await db.ops_incidents.insert_one(
        {
            "incident_id": "inc_sup_4",
            "organization_id": org_id,
            "type": "supplier_partial_failure",
            "severity": "medium",
            "status": "open",
            "summary": "Supplier partial failure no health",
            "source_ref": {"session_id": "sess4"},
            "meta": {
                "failed_suppliers": [
                    {"supplier_code": "paximum", "code": "SUPPLIER_TIMEOUT"},
                ],
            },
            "created_at": now,
            "updated_at": now,
        }
    )

    headers = _make_admin_headers(org_id, email)
    resp = await client.get("/api/admin/ops/incidents?include_supplier_health=true", headers=headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    items = body.get("items") or []
    assert len(items) == 1
    badge = items[0].get("supplier_health")
    assert badge is not None
    assert badge["supplier_code"] == "paximum"
    assert "health_not_found" in (badge.get("notes") or [])


@pytest.mark.exit_ops_incidents_enrichment_supplier_code_resolution_deterministic
@pytest.mark.anyio
async def test_ops_incidents_enrichment_supplier_code_resolution_deterministic(test_db: Any, async_client: AsyncClient) -> None:
    """Supplier code resolution should always prefer first failed_suppliers entry."""

    client: AsyncClient = async_client
    db = test_db
    now = now_utc()

    org = await db.organizations.insert_one(
        {"name": "Ops Org5", "slug": "ops_org_incidents_enrich5", "created_at": now, "updated_at": now}
    )
    org_id = str(org.inserted_id)
    email = "admin-enrich5@example.com"
    await db.users.insert_one(
        {
            "organization_id": org_id,
            "email": email,
            "roles": ["agency_admin"],
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
    )

    await db.ops_incidents.insert_one(
        {
            "incident_id": "inc_sup_5",
            "organization_id": org_id,
            "type": "supplier_partial_failure",
            "severity": "medium",
            "status": "open",
            "summary": "Supplier resolution test",
            "source_ref": {"session_id": "sess5"},
            "meta": {
                "failed_suppliers": [
                    {"supplier_code": "mock", "code": "SUPPLIER_TIMEOUT"},
                    {"supplier_code": "paximum", "code": "SUPPLIER_TIMEOUT"},
                ],
            },
            "created_at": now,
            "updated_at": now,
        }
    )

    await db.supplier_health.insert_many(
        [
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
        ]
    )

    headers = _make_admin_headers(org_id, email)
    resp = await client.get("/api/admin/ops/incidents?include_supplier_health=true", headers=headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    items = body.get("items") or []
    assert len(items) == 1
    badge = items[0].get("supplier_health")
    assert badge is not None
    # Must pick the first failed_suppliers entry (mock)
    assert badge["supplier_code"] == "mock"


@pytest.mark.exit_ops_incidents_enrichment_rbac_denied
@pytest.mark.anyio
async def test_ops_incidents_enrichment_rbac_denied(test_db: Any, async_client: AsyncClient) -> None:
    """Non-admin roles must not access ops incidents endpoints even with enrichment flags."""

    client: AsyncClient = async_client
    db = test_db
    now = now_utc()

    org = await db.organizations.insert_one(
        {"name": "Ops Org6", "slug": "ops_org_incidents_enrich6", "created_at": now, "updated_at": now}
    )
    org_id = str(org.inserted_id)
    email = "agent-enrich6@example.com"
    await db.users.insert_one(
        {
            "organization_id": org_id,
            "email": email,
            "roles": ["agency_agent"],
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
    )

    # Seed a dummy incident
    await db.ops_incidents.insert_one(
        {
            "incident_id": "inc_sup_6",
            "organization_id": org_id,
            "type": "supplier_partial_failure",
            "severity": "medium",
            "status": "open",
            "summary": "Supplier incident", 
            "source_ref": {"session_id": "sess6"},
            "meta": {"failed_suppliers": [{"supplier_code": "mock"}]},
            "created_at": now,
            "updated_at": now,
        }
    )

    headers = _make_agent_headers(org_id, email)
    resp = await client.get("/api/admin/ops/incidents?include_supplier_health=true", headers=headers)
    assert resp.status_code in (401, 403)

    resp2 = await client.get("/api/admin/ops/incidents/inc_sup_6?include_supplier_health=true", headers=headers)
    assert resp2.status_code in (401, 403)
