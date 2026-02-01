from __future__ import annotations

from typing import Any

import asyncio
import jwt
import pytest
from bson import ObjectId
from fastapi import status
from httpx import AsyncClient

from app.auth import _jwt_secret
from app.services.suppliers.contracts import ConfirmResult, ConfirmStatus, SupplierAdapterError
from app.utils import now_utc


@pytest.mark.exit_confirm_timeout_enforced
@pytest.mark.anyio
async def test_confirm_timeout_enforced_returns_upstream_timeout(test_db: Any, async_client: AsyncClient, monkeypatch: Any) -> None:
    """Confirm should enforce timeout via run_with_deadline and surface upstream_timeout.

    We monkeypatch MockSupplierAdapter.confirm_booking to sleep longer than
    ctx.timeout_ms and expect a 502 upstream_timeout with retryable=True.
    """

    from app.services.suppliers.mock_adapter import MockSupplierAdapter
    import app.routers.b2b_bookings as b2b_bookings

    client: AsyncClient = async_client
    now = now_utc()

    org = await test_db.organizations.insert_one(
        {"name": "HARDEN Org1", "slug": "harden_org1", "created_at": now, "updated_at": now}
    )
    org_id = str(org.inserted_id)

    tenant = await test_db.tenants.insert_one(
        {
            "tenant_key": "harden-tenant-1",
            "organization_id": org_id,
            "brand_name": "Harden Tenant 1",
            "primary_domain": "harden-tenant-1.example.com",
            "subdomain": "harden-tenant-1",
            "theme_config": {},
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
    )
    tenant_id = str(tenant.inserted_id)

    email = "harden1@example.com"
    await test_db.users.insert_one(
        {
            "organization_id": org_id,
            "email": email,
            "roles": ["agency_agent"],
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
    )
    token = jwt.encode({"sub": email, "org": org_id}, _jwt_secret(), algorithm="HS256")

    booking_doc = {
        "organization_id": org_id,
        "state": "draft",
        "status": "PENDING",
        "source": "b2b_marketplace",
        "currency": "TRY",
        "amount": 100.0,
        "offer_ref": {
            "source": "marketplace",
            "listing_id": "dummy",
            "seller_tenant_id": tenant_id,
            "buyer_tenant_id": tenant_id,
            "supplier": "mock_supplier_v1",
            "supplier_offer_id": "MOCK-TIMEOUT-1",
        },
        "created_at": now,
        "updated_at": now,
    }
    res = await test_db.bookings.insert_one(booking_doc)
    booking_id = str(res.inserted_id)

    async def slow_confirm(self, ctx, booking):  # type: ignore[override]
        # Force a very small timeout_ms and sleep beyond it
        ctx.timeout_ms = 50
        ctx.deadline_at = None  # force re-compute based on new timeout
        await asyncio.sleep(0.1)
        return ConfirmResult(
            supplier_code="mock",
            supplier_booking_id=None,
            status=ConfirmStatus.PENDING,
            raw={},
        )

    monkeypatch.setattr(MockSupplierAdapter, "confirm_booking", slow_confirm)

    headers = {
        "Authorization": f"Bearer {token}",
        "X-Tenant-Key": "harden-tenant-1",
    }

    resp = await client.post(f"/api/b2b/bookings/{booking_id}/confirm", headers=headers)
    assert resp.status_code == status.HTTP_502_BAD_GATEWAY
    err = resp.json().get("error", {})
    assert err.get("code") == "upstream_timeout"
    details = err.get("details") or {}
    assert details.get("retryable") is True


@pytest.mark.exit_confirm_snapshot_redacted
@pytest.mark.anyio
async def test_confirm_snapshot_redacted_does_not_store_pii(test_db: Any, async_client: AsyncClient, monkeypatch: Any) -> None:
    """Confirm should store only redacted confirm_snapshot in booking.supplier.confirm_snapshot."""

    from app.services.suppliers.mock_adapter import MockSupplierAdapter

    client: AsyncClient = async_client
    now = now_utc()

    org = await test_db.organizations.insert_one(
        {"name": "HARDEN Org2", "slug": "harden_org2", "created_at": now, "updated_at": now}
    )
    org_id = str(org.inserted_id)

    tenant = await test_db.tenants.insert_one(
        {
            "tenant_key": "harden-tenant-2",
            "organization_id": org_id,
            "brand_name": "Harden Tenant 2",
            "primary_domain": "harden-tenant-2.example.com",
            "subdomain": "harden-tenant-2",
            "theme_config": {},
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
    )
    tenant_id = str(tenant.inserted_id)

    email = "harden2@example.com"
    await test_db.users.insert_one(
        {
            "organization_id": org_id,
            "email": email,
            "roles": ["agency_agent"],
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
    )
    token = jwt.encode({"sub": email, "org": org_id}, _jwt_secret(), algorithm="HS256")

    booking_doc = {
        "organization_id": org_id,
        "state": "draft",
        "status": "PENDING",
        "source": "b2b_marketplace",
        "currency": "TRY",
        "amount": 100.0,
        "offer_ref": {
            "source": "marketplace",
            "listing_id": "dummy",
            "seller_tenant_id": tenant_id,
            "buyer_tenant_id": tenant_id,
            "supplier": "mock_supplier_v1",
            "supplier_offer_id": "MOCK-REDACT-1",
        },
        "created_at": now,
        "updated_at": now,
    }
    res = await test_db.bookings.insert_one(booking_doc)
    booking_id = str(res.inserted_id)

    raw_payload = {
        "email": "secret@example.com",
        "card": "4111111111111111",
        "nested": {"phone": "+900000000000"},
    }

    async def confirming(self, ctx, booking):  # type: ignore[override]
        return ConfirmResult(
            supplier_code="mock",
            supplier_booking_id="MOCK-BKG-REDACT",
            status=ConfirmStatus.CONFIRMED,
            raw=raw_payload,
        )

    monkeypatch.setattr(MockSupplierAdapter, "confirm_booking", confirming)

    headers = {
        "Authorization": f"Bearer {token}",
        "X-Tenant-Key": "harden-tenant-2",
    }

    resp = await client.post(f"/api/b2b/bookings/{booking_id}/confirm", headers=headers)
    assert resp.status_code == status.HTTP_200_OK, resp.text

    stored = await test_db.bookings.find_one({"_id": ObjectId(booking_id)})
    supplier = stored.get("supplier") or {}
    snapshot = supplier.get("confirm_snapshot") or {}

    # Original values must not be present
    assert snapshot.get("email") == "***REDACTED***"
    assert snapshot.get("card") == "***REDACTED***"
    assert snapshot.get("nested", {}).get("phone") == "***REDACTED***"

    # Ensure original raw was not mutated
    assert raw_payload["email"] == "secret@example.com"
    assert raw_payload["card"] == "4111111111111111"
    assert raw_payload["nested"]["phone"] == "+900000000000"
