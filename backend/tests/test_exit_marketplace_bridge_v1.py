from __future__ import annotations

from typing import Any

import jwt
import pytest
from bson import Decimal128
from fastapi import status
from httpx import AsyncClient

from app.auth import _jwt_secret
from app.utils import now_utc


@pytest.mark.exit_marketplace_bridge_v1
@pytest.mark.anyio
async def test_marketplace_to_storefront_bridge_flow(test_db: Any, async_client: AsyncClient) -> None:
    """Publishing listing + access grant should allow creating storefront session and fetching offer.

    Flow:
    - Org with seller tenant and buyer tenant
    - Seller creates + publishes listing
    - Admin grants marketplace_access seller->buyer
    - Buyer calls bridge endpoint -> storefront session created under seller tenant
    - Using redirect_url, storefront offer can be fetched
    - After revoke, bridge should no longer allow session creation
    """

    client: AsyncClient = async_client
    now = now_utc()

    # Org + tenants
    org = await test_db.organizations.insert_one(
        {"name": "MP-BR Org", "slug": "mpbr_org", "created_at": now, "updated_at": now}
    )
    org_id = str(org.inserted_id)

    seller_tenant = await test_db.tenants.insert_one(
        {
            "tenant_key": "seller-tenant-br",
            "organization_id": org_id,
            "brand_name": "Seller Tenant BR",
            "primary_domain": "seller-br.example.com",
            "subdomain": "seller-br",
            "theme_config": {},
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
    )
    seller_tenant_id = str(seller_tenant.inserted_id)

    buyer_tenant = await test_db.tenants.insert_one(
        {
            "tenant_key": "buyer-tenant-br",
            "organization_id": org_id,
            "brand_name": "Buyer Tenant BR",
            "primary_domain": "buyer-br.example.com",
            "subdomain": "buyer-br",
            "theme_config": {},
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
    )
    buyer_tenant_id = str(buyer_tenant.inserted_id)

    # Users
    seller_email = "seller_bridge@example.com"
    buyer_email = "buyer_bridge@example.com"

    await test_db.users.insert_one(
        {
            "organization_id": org_id,
            "email": seller_email,
            "roles": ["admin"],
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
    )

    await test_db.users.insert_one(
        {
            "organization_id": org_id,
            "email": buyer_email,
            "roles": ["admin"],
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
    )

    seller_token = jwt.encode({"sub": seller_email, "org": org_id}, _jwt_secret(), algorithm="HS256")
    buyer_token = jwt.encode({"sub": buyer_email, "org": org_id}, _jwt_secret(), algorithm="HS256")

    seller_headers = {"Authorization": f"Bearer {seller_token}", "X-Tenant-Key": "seller-tenant-br"}

    # Seller creates + publishes listing
    payload = {
        "title": "Bridge Listing",
        "description": "Bridge test product",
        "category": "hotel",
        "currency": "TRY",
        "base_price": "150.00",
        "tags": ["bridge", "hotel"],
    }

    resp_create = await client.post("/api/marketplace/listings", json=payload, headers=seller_headers)
    assert resp_create.status_code == status.HTTP_201_CREATED, resp_create.text
    listing = resp_create.json()
    listing_id = listing["id"]

    resp_publish = await client.post(f"/api/marketplace/listings/{listing_id}/publish", headers=seller_headers)
    assert resp_publish.status_code == status.HTTP_200_OK, resp_publish.text

    # Grant access seller->buyer
    admin_headers = {"Authorization": f"Bearer {seller_token}"}
    grant_payload = {"seller_tenant_id": seller_tenant_id, "buyer_tenant_id": buyer_tenant_id}
    resp_grant = await client.post("/api/marketplace/access/grant", json=grant_payload, headers=admin_headers)
    assert resp_grant.status_code == status.HTTP_201_CREATED, resp_grant.text

    # Buyer calls bridge endpoint
    buyer_headers = {"Authorization": f"Bearer {buyer_token}", "X-Tenant-Key": "buyer-tenant-br"}
    resp_bridge = await client.post(
        f"/api/marketplace/catalog/{listing_id}/create-storefront-session", headers=buyer_headers
    )
    assert resp_bridge.status_code == status.HTTP_200_OK, resp_bridge.text
    data = resp_bridge.json()
    redirect_url = data.get("redirect_url")
    search_id = data.get("storefront_search_id")
    assert redirect_url
    assert search_id
    assert data.get("seller_tenant_id") == seller_tenant_id

    # Check that a storefront_session exists for seller tenant
    session = await test_db.storefront_sessions.find_one(
        {"tenant_id": seller_tenant_id, "search_id": search_id}
    )
    assert session is not None
    offers = session.get("offers_snapshot") or []
    assert len(offers) == 1
    offer = offers[0]
    assert offer["offer_id"] == f"MP-{listing_id}"
    assert offer["supplier"] == "marketplace"
    assert isinstance(offer["total_amount"], Decimal128)

    # Use redirect_url to fetch offer via storefront API (as seller tenant)
    from urllib.parse import urlparse, parse_qs

    parsed = urlparse(redirect_url)
    path = parsed.path
    qs = parse_qs(parsed.query)
    search_id_from_url = qs.get("search_id", [None])[0]
    assert search_id_from_url == search_id

    # GET /storefront/offers/MP-{listing_id}?search_id=...
    resp_offer = await client.get(
        f"/storefront/offers/MP-{listing_id}",
        params={"search_id": search_id},
        headers={"X-Tenant-Key": "seller-tenant-br"},
    )
    assert resp_offer.status_code == status.HTTP_200_OK, resp_offer.text
    offer_json = resp_offer.json()
    assert offer_json["offer_id"] == f"MP-{listing_id}"
    assert offer_json["supplier"] == "marketplace"

    # Revoke access -> bridge should no longer work
    resp_revoke = await client.post("/api/marketplace/access/revoke", json=grant_payload, headers=admin_headers)
    assert resp_revoke.status_code == status.HTTP_200_OK, resp_revoke.text

    resp_bridge_after_revoke = await client.post(
        f"/api/marketplace/catalog/{listing_id}/create-storefront-session", headers=buyer_headers
    )
    assert resp_bridge_after_revoke.status_code in {status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND}

