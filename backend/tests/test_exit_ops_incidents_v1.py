from __future__ import annotations

from typing import Any

import pytest
from httpx import AsyncClient

from app.utils import now_utc


@pytest.mark.exit_ops_incident_created_for_risk_review
@pytest.mark.anyio
async def test_ops_incident_created_for_risk_review(test_db: Any, async_client: AsyncClient, monkeypatch: Any) -> None:
    """Risk REVIEW booking should create a high-severity risk_review incident (dedup-aware)."""

    from app.services.risk.engine import RiskDecision

    client: AsyncClient = async_client
    db = test_db

    from backend.tests.test_exit_risk_engine_v1 import _seed_booking_for_risk

    org_id, booking_id, email = await _seed_booking_for_risk(db, decision="REVIEW")

    from app.services.risk.engine import evaluate_booking_risk

    async def _fake_evaluate(*args, **kwargs):  # type: ignore[no-untyped-def]
        class Dummy:
            def __init__(self) -> None:
                self.score = 0.8
                self.decision = RiskDecision.REVIEW
                self.reasons = ["manual_test"]
                self.model_version = "risk_engine_v1"

        return Dummy()

    monkeypatch.setattr("app.services.risk.engine.evaluate_booking_risk", _fake_evaluate)

    headers = {"x-org-id": org_id, "x-user-email": email}
    resp = await client.post(f"/api/b2b/bookings/{booking_id}/confirm", headers=headers)
    assert resp.status_code == 202

    inc = await db.ops_incidents.find_one({"organization_id": org_id, "type": "risk_review"})
    assert inc is not None
    assert inc["status"] == "open"
    assert inc["severity"] == "high"
    assert inc["source_ref"]["booking_id"] == booking_id


@pytest.mark.exit_ops_incident_created_for_supplier_all_failed
@pytest.mark.anyio
async def test_ops_incident_created_for_supplier_all_failed(test_db: Any, async_client: AsyncClient, monkeypatch: Any) -> None:
    """All-suppliers-failed search should create a critical supplier_all_failed incident."""

    from app.errors import AppError

    client: AsyncClient = async_client
    db = test_db

    from backend.tests.test_exit_supplier_partial_results_v1 import _get_default_org_and_user

    org_id, email = await _get_default_org_and_user(db)

    async def _failing_mock(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise AppError(503, "SUPPLIER_UPSTREAM_UNAVAILABLE", "Mock unavailable", {})

    async def _failing_paximum(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise AppError(503, "SUPPLIER_UPSTREAM_UNAVAILABLE", "Paximum unavailable", {})

    monkeypatch.setattr("app.services.suppliers.mock_supplier_service.search_mock_offers", _failing_mock)
    monkeypatch.setattr("app.services.supplier_search_service.search_paximum_offers", _failing_paximum)

    now = now_utc().date()
    headers = {"x-org-id": org_id, "x-user-email": email}

    payload = {
        "destination": "IST",
        "check_in": now.isoformat(),
        "check_out": now.isoformat(),
        "adults": 2,
        "children": 0,
        "supplier_codes": ["mock", "paximum"],
    }

    resp = await client.post("/api/offers/search", json=payload, headers=headers)
    assert resp.status_code == 503
    body = resp.json()
    code = body.get("error", {}).get("code")
    assert code == "SUPPLIER_ALL_FAILED"

    inc = await db.ops_incidents.find_one({"organization_id": org_id, "type": "supplier_all_failed"})
    assert inc is not None
    assert inc["severity"] == "critical"
    assert inc["status"] == "open"
    assert inc["meta"].get("warnings_count") == 2


@pytest.mark.exit_ops_incident_list_filtering
@pytest.mark.anyio
async def test_ops_incident_list_filtering(test_db: Any, async_client: AsyncClient) -> None:
    """List endpoint should filter by type/status and apply deterministic ordering."""

    client: AsyncClient = async_client
    db = test_db

    from backend.tests.conftest import _get_default_org_and_user

    org_id, email = await _get_default_org_and_user(db)

    now = now_utc()
    docs = [
        {
            "incident_id": "inc_a",
            "organization_id": org_id,
            "type": "risk_review",
            "severity": "high",
            "status": "open",
            "summary": "r1",
            "source_ref": {"booking_id": "b1"},
            "meta": {},
            "created_at": now,
            "updated_at": now,
        },
        {
            "incident_id": "inc_b",
            "organization_id": org_id,
            "type": "supplier_all_failed",
            "severity": "critical",
            "status": "open",
            "summary": "s1",
            "source_ref": {"session_id": "s1"},
            "meta": {},
            "created_at": now,
            "updated_at": now,
        },
        {
            "incident_id": "inc_c",
            "organization_id": org_id,
            "type": "risk_review",
            "severity": "medium",
            "status": "resolved",
            "summary": "r2",
            "source_ref": {"booking_id": "b2"},
            "meta": {},
            "created_at": now,
            "updated_at": now,
        },
    ]
    await db.ops_incidents.insert_many(docs)

    headers = {"x-org-id": org_id, "x-user-email": email, "x-user-roles": "agency_admin"}
    resp = await client.get("/api/admin/ops/incidents?status=open&type=risk_review", headers=headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["total"] >= 1
    items = body["items"]
    assert len(items) == 1
    assert items[0]["incident_id"] == "inc_a"


@pytest.mark.exit_ops_incident_resolve_flow
@pytest.mark.anyio
async def test_ops_incident_resolve_flow(test_db: Any, async_client: AsyncClient) -> None:
    """Resolve endpoint should transition status and set resolved fields + audit."""

    client: AsyncClient = async_client
    db = test_db

    from backend.tests.conftest import _get_default_org_and_user

    org_id, email = await _get_default_org_and_user(db)

    now = now_utc()
    doc = {
        "incident_id": "inc_resolve_1",
        "organization_id": org_id,
        "type": "risk_review",
        "severity": "high",
        "status": "open",
        "summary": "to-resolve",
        "source_ref": {"booking_id": "b1"},
        "meta": {},
        "created_at": now,
        "updated_at": now,
        "resolved_at": None,
        "resolved_by_user_id": None,
    }
    await db.ops_incidents.insert_one(doc)

    headers = {"x-org-id": org_id, "x-user-email": email, "x-user-roles": "agency_admin"}
    resp = await client.patch("/api/admin/ops/incidents/inc_resolve_1/resolve", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body == {"incident_id": "inc_resolve_1", "status": "resolved"}

    updated = await db.ops_incidents.find_one({"organization_id": org_id, "incident_id": "inc_resolve_1"})
    assert updated is not None
    assert updated["status"] == "resolved"
    assert updated["resolved_at"] is not None
    assert updated["resolved_by_user_id"] is not None


@pytest.mark.exit_ops_incident_deduplication
@pytest.mark.anyio
async def test_ops_incident_deduplication(test_db: Any) -> None:
    """Risk review incident creation should dedup on (booking_id, open)."""

    db = test_db

    from app.services.ops_incidents_service import create_risk_review_incident

    org_id = "org_dedup"
    booking_id = "b_dedup"

    await create_risk_review_incident(
        db,
        organization_id=org_id,
        booking_id=booking_id,
        risk_score=0.9,
        tenant_id="t1",
        amount=1000.0,
        currency="EUR",
    )
    await create_risk_review_incident(
        db,
        organization_id=org_id,
        booking_id=booking_id,
        risk_score=0.7,
        tenant_id="t1",
        amount=900.0,
        currency="EUR",
    )

    count = await db.ops_incidents.count_documents({"organization_id": org_id, "type": "risk_review"})
    assert count == 1


@pytest.mark.exit_ops_incident_rbac_denied
@pytest.mark.anyio
async def test_ops_incident_rbac_denied(test_db: Any, async_client: AsyncClient) -> None:
    """Non-admin roles should not be able to access ops incidents endpoints."""

    client: AsyncClient = async_client
    db = test_db

    from backend.tests.conftest import _get_default_org_and_user

    org_id, email = await _get_default_org_and_user(db)

    headers = {"x-org-id": org_id, "x-user-email": email, "x-user-roles": "agency_agent"}
    resp = await client.get("/api/admin/ops/incidents", headers=headers)
    assert resp.status_code in (401, 403)
