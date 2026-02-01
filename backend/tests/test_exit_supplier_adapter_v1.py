from __future__ import annotations

from typing import Any

import jwt
import pytest
from bson import ObjectId
from fastapi import status
from httpx import AsyncClient

from app.auth import _jwt_secret
from app.services.suppliers.registry import registry as supplier_registry
from app.services.suppliers.contracts import SupplierAdapterError
from app.utils import now_utc


@pytest.mark.exit_supplier_adapter_registry
@pytest.mark.anyio
async def test_supplier_registry_alias_and_normalization() -> None:
    adapter = supplier_registry.get("Mock")
    same = supplier_registry.get("mock_supplier_v1")
    assert adapter is same

    with pytest.raises(SupplierAdapterError) as exc_info:
        supplier_registry.get("unknown_supplier")
    err = exc_info.value
    assert err.code == "adapter_not_found"


@pytest.mark.exit_supplier_confirm_flow
@pytest.mark.anyio
async def test_supplier_confirm_flow_mock_happy_path(test_db: Any, async_client: AsyncClient) -> None:
    client: AsyncClient = async_client
    now = now_utc()

    org = await test_db.organizations.insert_one(
        {"name": "SUP-Adapter Org", "slug": "sup_adapter_org", "created_at": now, "updated_at": now}
    )
    org_id = str(org.inserted_id)

    tenant = await test_db.tenants.insert_one(
        {
            "tenant_key": "tenant-sup-adapter",
            "organization_id": org_id,
            "brand_name": "Tenant Sup Adapter",
            "primary_domain": "tenant-sup-adapter.example.com",
            "subdomain": "tenant-sup-adapter",
            "theme_config": {},
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
    )
    tenant_id = str(tenant.inserted_id)

    email = "supadapter@example.com"
    await test_db.users.insert_one(
        {
            "organization_id": org_id,
            "email": email,
            "roles": ["admin"],
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
    )
    token = jwt.encode({"sub": email, "org": org_id}, _jwt_secret(), algorithm="HS256")

    # Booking with mock supplier mapping
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
            "supplier_offer_id": "MOCK-ADAPTER-1",
        },
        "created_at": now,
        "updated_at": now,
    }
    res = await test_db.bookings.insert_one(booking_doc)
    booking_id = str(res.inserted_id)

    headers = {
        "Authorization": f"Bearer {token}",
        "X-Tenant-Key": "tenant-sup-adapter",
    }

    resp_confirm = await client.post(f"/api/b2b/bookings/{booking_id}/confirm", headers=headers)
    assert resp_confirm.status_code == status.HTTP_200_OK, resp_confirm.text
    body = resp_confirm.json()
    assert body["booking_id"] == booking_id
    assert body["state"] == "confirmed"

    stored = await test_db.bookings.find_one({"_id": ObjectId(booking_id)})
    assert stored is not None
    assert stored.get("status") == "CONFIRMED"
    offer_ref = stored.get("offer_ref") or {}
    assert offer_ref.get("supplier_booking_id") is not None
    supplier = stored.get("supplier") or {}
    assert supplier.get("code") == "mock"
    assert supplier.get("offer_id") == "MOCK-ADAPTER-1"
    assert supplier.get("booking_id") is not None
    assert isinstance(supplier.get("confirm_snapshot"), dict)


@pytest.mark.exit_supplier_unresolved
@pytest.mark.anyio
async def test_supplier_unresolved_returns_400_and_audit(test_db: Any, async_client: AsyncClient) -> None:
    client: AsyncClient = async_client
    now = now_utc()

    org = await test_db.organizations.insert_one(
        {"name": "SUP-Adapter Org2", "slug": "sup_adapter_org2", "created_at": now, "updated_at": now}
    )
    org_id = str(org.inserted_id)

    tenant = await test_db.tenants.insert_one(
        {
            "tenant_key": "tenant-sup-adapter-2",
            "organization_id": org_id,
            "brand_name": "Tenant Sup Adapter 2",
            "primary_domain": "tenant-sup-adapter-2.example.com",
            "subdomain": "tenant-sup-adapter-2",
            "theme_config": {},
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
    )
    tenant_id = str(tenant.inserted_id)

    email = "supadapter2@example.com"
    await test_db.users.insert_one(
        {
            "organization_id": org_id,
            "email": email,
            "roles": ["admin"],
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
            # no supplier fields
        },
        "created_at": now,
        "updated_at": now,
    }
    res = await test_db.bookings.insert_one(booking_doc)
    booking_id = str(res.inserted_id)

    headers = {
        "Authorization": f"Bearer {token}",
        "X-Tenant-Key": "tenant-sup-adapter-2",
    }

    resp_confirm = await client.post(f"/api/b2b/bookings/{booking_id}/confirm", headers=headers)
    # In v1 we reuse INVALID_SUPPLIER_MAPPING for unresolved supplier cases
    assert resp_confirm.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    err = resp_confirm.json().get("error", {})
    assert err.get("code") == "INVALID_SUPPLIER_MAPPING"


@pytest.mark.exit_supplier_not_supported
@pytest.mark.anyio
async def test_supplier_not_supported_for_paximum(test_db: Any, async_client: AsyncClient) -> None:
    client: AsyncClient = async_client
    now = now_utc()

    org = await test_db.organizations.insert_one(
        {"name": "SUP-Adapter Org3", "slug": "sup_adapter_org3", "created_at": now, "updated_at": now}
    )
    org_id = str(org.inserted_id)

    tenant = await test_db.tenants.insert_one(
        {
            "tenant_key": "tenant-sup-adapter-3",
            "organization_id": org_id,
            "brand_name": "Tenant Sup Adapter 3",
            "primary_domain": "tenant-sup-adapter-3.example.com",
            "subdomain": "tenant-sup-adapter-3",
            "theme_config": {},
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
    )
    tenant_id = str(tenant.inserted_id)

    email = "supadapter3@example.com"
    await test_db.users.insert_one(
        {
            "organization_id": org_id,
            "email": email,
            "roles": ["admin"],
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
            "supplier": "paximum",
            "supplier_offer_id": "PAX-1",
        },
        "created_at": now,
        "updated_at": now,
    }
    res = await test_db.bookings.insert_one(booking_doc)
    booking_id = str(res.inserted_id)

    headers = {
        "Authorization": f"Bearer {token}",
        "X-Tenant-Key": "tenant-sup-adapter-3",
    }

    resp_confirm = await client.post(f"/api/b2b/bookings/{booking_id}/confirm", headers=headers)
    assert resp_confirm.status_code == status.HTTP_501_NOT_IMPLEMENTED
    err = resp_confirm.json().get("error", {})
    assert err.get("code") == "supplier_not_supported"


@pytest.mark.exit_supplier_error_propagation
@pytest.mark.anyio
async def test_supplier_error_propagation_retryable(test_db: Any, async_client: AsyncClient, monkeypatch: Any) -> None:
    from app.services.suppliers.mock_adapter import MockSupplierAdapter

    client: AsyncClient = async_client
    now = now_utc()

    org = await test_db.organizations.insert_one(
        {"name": "SUP-Adapter Org4", "slug": "sup_adapter_org4", "created_at": now, "updated_at": now}
    )
    org_id = str(org.inserted_id)

    tenant = await test_db.tenants.insert_one(
        {
            "tenant_key": "tenant-sup-adapter-4",
            "organization_id": org_id,
            "brand_name": "Tenant Sup Adapter 4",
            "primary_domain": "tenant-sup-adapter-4.example.com",
            "subdomain": "tenant-sup-adapter-4",
            "theme_config": {},
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
    )
    tenant_id = str(tenant.inserted_id)

    email = "supadapter4@example.com"
    await test_db.users.insert_one(
        {
            "organization_id": org_id,
            "email": email,
            "roles": ["admin"],
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
            "supplier_offer_id": "MOCK-ERR-1",
        },
        "created_at": now,
        "updated_at": now,
    }
    res = await test_db.bookings.insert_one(booking_doc)
    booking_id = str(res.inserted_id)

    async def failing_confirm(*args: Any, **kwargs: Any):  # type: ignore[override]
        raise SupplierAdapterError(
            code="upstream_timeout",
            message="Timeout from upstream supplier",
            retryable=True,
            details={"upstream": "mock"},
        )

    monkeypatch.setattr(MockSupplierAdapter, "confirm_booking", failing_confirm)

    headers = {
        "Authorization": f"Bearer {token}",
        "X-Tenant-Key": "tenant-sup-adapter-4",
    }

    resp_confirm = await client.post(f"/api/b2b/bookings/{booking_id}/confirm", headers=headers)
    assert resp_confirm.status_code == status.HTTP_502_BAD_GATEWAY
    err = resp_confirm.json().get("error", {})
    assert err.get("code") == "upstream_timeout"
    details = err.get("details") or {}
    assert details.get("retryable") is True
