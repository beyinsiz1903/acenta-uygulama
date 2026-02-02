from __future__ import annotations

from typing import Any

import jwt
import pytest
from httpx import AsyncClient

from app.auth import _jwt_secret
from app.utils import now_utc


def _make_headers(org_id: str, email: str, tenant_key: str) -> dict[str, str]:
    token = jwt.encode({"sub": email, "org": org_id}, _jwt_secret(), algorithm="HS256")
    return {"Authorization": f"Bearer {token}", "X-Tenant-Key": tenant_key}


async def _get_default_org_and_user(test_db: Any) -> tuple[str, str]:
    org = await test_db.organizations.find_one({"slug": "default"})
    assert org is not None
    org_id = str(org["_id"])

    # use seeded agency user
    email = "agency1@demo.test"
    return org_id, email


@pytest.mark.exit_supplier_partial_results_returns_200_with_warnings
@pytest.mark.anyio
async def test_supplier_partial_results_returns_200_with_warnings(test_db: Any, async_client: AsyncClient, monkeypatch: Any) -> None:
    """When one supplier fails and another succeeds, search should return 200 with warnings."""

    client: AsyncClient = async_client
    now = now_utc()

    org_id, email = await _get_default_org_and_user(test_db)

    # Create tenant for header
    await test_db.tenants.insert_one(
        {
            "tenant_key": "partial-tenant-1",
            "organization_id": org_id,
            "brand_name": "Partial Tenant 1",
            "primary_domain": "partial-tenant-1.example.com",
            "subdomain": "partial-tenant-1",
            "theme_config": {},
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
    )
    tenant_key = "partial-tenant-1"

    # Monkeypatch paximum search to always fail with AppError-like behaviour
    from app.services.supplier_search_service import search_paximum_offers
    from app.errors import AppError

    async def _failing_paximum(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise AppError(503, "SUPPLIER_UPSTREAM_UNAVAILABLE", "Paximum unavailable", {})

    monkeypatch.setattr("app.services.supplier_search_service.search_paximum_offers", _failing_paximum)

    headers = _make_headers(org_id, email, tenant_key)

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

    offers = body.get("offers") or []
    assert len(offers) >= 1

    warnings = body.get("warnings") or []
    assert len(warnings) >= 1
    pax_warnings = [w for w in warnings if w.get("supplier_code") == "paximum"]
    assert pax_warnings
    w0 = pax_warnings[0]
    assert w0.get("code") in {"SUPPLIER_UPSTREAM_UNAVAILABLE", "SUPPLIER_NETWORK_ERROR", "SUPPLIER_REQUEST_REJECTED"}
    assert w0.get("retryable") is True


@pytest.mark.exit_supplier_partial_results_audit_written
@pytest.mark.anyio
async def test_supplier_partial_results_audit_written(test_db: Any, async_client: AsyncClient, monkeypatch: Any) -> None:
    """Partial failure should write SUPPLIER_PARTIAL_FAILURE audit with meta."""

    client: AsyncClient = async_client
    now = now_utc()

    org_id, email = await _get_default_org_and_user(test_db)

    await test_db.tenants.insert_one(
        {
            "tenant_key": "partial-tenant-2",
            "organization_id": org_id,
            "brand_name": "Partial Tenant 2",
            "primary_domain": "partial-tenant-2.example.com",
            "subdomain": "partial-tenant-2",
            "theme_config": {},
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
    )
    tenant_key = "partial-tenant-2"

    from app.services.supplier_search_service import search_paximum_offers
    from app.errors import AppError

    async def _failing_paximum(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise AppError(503, "SUPPLIER_UPSTREAM_UNAVAILABLE", "Paximum unavailable", {})

    monkeypatch.setattr("app.services.supplier_search_service.search_paximum_offers", _failing_paximum)

    headers = _make_headers(org_id, email, tenant_key)

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
    session_id = body.get("session_id")
    assert session_id

    audit = await test_db.audit_logs.find_one(
        {"organization_id": org_id, "action": "SUPPLIER_PARTIAL_FAILURE", "target.id": session_id}
    )
    assert audit is not None
    meta = audit.get("meta") or {}
    assert meta.get("session_id") == session_id
    assert meta.get("offers_count") >= 1
    failed = meta.get("failed_suppliers") or []
    assert any(fs.get("supplier_code") == "paximum" for fs in failed)


@pytest.mark.exit_supplier_all_failed_returns_503
@pytest.mark.anyio
async def test_supplier_all_failed_returns_503(test_db: Any, async_client: AsyncClient, monkeypatch: Any) -> None:
    """If all suppliers fail, search should return 503 with SUPPLIER_ALL_FAILED and warnings in error.details."""

    client: AsyncClient = async_client
    now = now_utc()

    org_id, email = await _get_default_org_and_user(test_db)

    await test_db.tenants.insert_one(
        {
            "tenant_key": "partial-tenant-3",
            "organization_id": org_id,
            "brand_name": "Partial Tenant 3",
            "primary_domain": "partial-tenant-3.example.com",
            "subdomain": "partial-tenant-3",
            "theme_config": {},
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
    )
    tenant_key = "partial-tenant-3"

    from app.services.supplier_search_service import search_paximum_offers
    from app.services.suppliers.mock_supplier_service import search_mock_offers
    from app.errors import AppError

    async def _failing_paximum(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise AppError(503, "SUPPLIER_UPSTREAM_UNAVAILABLE", "Paximum unavailable", {})

    async def _failing_mock(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise AppError(503, "SUPPLIER_UPSTREAM_UNAVAILABLE", "Mock unavailable", {})

    monkeypatch.setattr("app.services.supplier_search_service.search_paximum_offers", _failing_paximum)
    monkeypatch.setattr("app.services.suppliers.mock_supplier_service.search_mock_offers", _failing_mock)

    headers = _make_headers(org_id, email, tenant_key)

    payload = {
        "destination": "IST",
        "check_in": "2026-01-10",
        "check_out": "2026-01-12",
        "adults": 2,
        "children": 0,
        "supplier_codes": ["mock", "paximum"],
    }

    resp = await client.post("/api/offers/search", json=payload, headers=headers)
    assert resp.status_code == 503, resp.text
    body = resp.json()
    assert body.get("error", {}).get("code") == "SUPPLIER_ALL_FAILED"
    details = body.get("error", {}).get("details") or {}
    warnings = details.get("warnings") or []
    assert len(warnings) == 2


@pytest.mark.exit_supplier_partial_results_offers_empty_but_successful_supplier
@pytest.mark.anyio
async def test_supplier_partial_results_offers_empty_but_successful_supplier(test_db: Any, async_client: AsyncClient, monkeypatch: Any) -> None:
    """If a supplier succeeds but returns no offers while another fails, should still be 200 with warnings and offers=[]."""

    client: AsyncClient = async_client
    now = now_utc()

    org_id, email = await _get_default_org_and_user(test_db)

    await test_db.tenants.insert_one(
        {
            "tenant_key": "partial-tenant-4",
            "organization_id": org_id,
            "brand_name": "Partial Tenant 4",
            "primary_domain": "partial-tenant-4.example.com",
            "subdomain": "partial-tenant-4",
            "theme_config": {},
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
    )
    tenant_key = "partial-tenant-4"

    from app.services.suppliers.mock_supplier_service import search_mock_offers
    from app.services.supplier_search_service import search_paximum_offers
    from app.errors import AppError

    async def _empty_mock(*args, **kwargs):  # type: ignore[no-untyped-def]
        return {"offers": [], "supplier": "mock"}

    async def _failing_paximum(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise AppError(503, "SUPPLIER_UPSTREAM_UNAVAILABLE", "Paximum unavailable", {})

    monkeypatch.setattr("app.services.suppliers.mock_supplier_service.search_mock_offers", _empty_mock)
    monkeypatch.setattr("app.services.supplier_search_service.search_paximum_offers", _failing_paximum)

    headers = _make_headers(org_id, email, tenant_key)

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

    assert body.get("offers") == []
    warnings = body.get("warnings") or []
    assert any(w.get("supplier_code") == "paximum" for w in warnings)


@pytest.mark.exit_supplier_warnings_ordering_deterministic
@pytest.mark.anyio
async def test_supplier_warnings_ordering_deterministic(test_db: Any, async_client: AsyncClient, monkeypatch: Any) -> None:
    """Warnings list ordering should be deterministic (by supplier_code, then code)."""

    client: AsyncClient = async_client
    now = now_utc()

    org_id, email = await _get_default_org_and_user(test_db)

    await test_db.tenants.insert_one(
        {
            "tenant_key": "partial-tenant-5",
            "organization_id": org_id,
            "brand_name": "Partial Tenant 5",
            "primary_domain": "partial-tenant-5.example.com",
            "subdomain": "partial-tenant-5",
            "theme_config": {},
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
    )
    tenant_key = "partial-tenant-5"

    from app.services.supplier_search_service import search_paximum_offers
    from app.services.suppliers.mock_supplier_service import search_mock_offers
    from app.errors import AppError

    async def _failing_paximum(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise AppError(503, "SUPPLIER_UPSTREAM_UNAVAILABLE", "Paximum unavailable", {})

    async def _failing_mock(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise AppError(500, "SUPPLIER_RESPONSE_INVALID", "Mock invalid response", {})

    monkeypatch.setattr("app.services.supplier_search_service.search_paximum_offers", _failing_paximum)
    monkeypatch.setattr("app.services.suppliers.mock_supplier_service.search_mock_offers", _failing_mock)

    headers = _make_headers(org_id, email, tenant_key)

    payload = {
        "destination": "IST",
        "check_in": "2026-01-10",
        "check_out": "2026-01-12",
        "adults": 2,
        "children": 0,
        "supplier_codes": ["paximum", "mock"],
    }

    resp1 = await client.post("/api/offers/search", json=payload, headers=headers)
    resp2 = await client.post("/api/offers/search", json=payload, headers=headers)

    assert resp1.status_code == 503
    assert resp2.status_code == 503

    w1 = (resp1.json().get("error", {}).get("details", {}).get("warnings") or [])
    w2 = (resp2.json().get("error", {}).get("details", {}).get("warnings") or [])

    assert [f"{w.get('supplier_code')}:{w.get('code')}" for w in w1] == [
        f"{w.get('supplier_code')}:{w.get('code')}" for w in w2
    ]
