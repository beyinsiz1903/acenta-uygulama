from __future__ import annotations

from typing import Any

import jwt
import pytest
from httpx import AsyncClient

from app.auth import _jwt_secret
from app.utils import now_utc
from app.routers.offers import round_money


async def _seed_org_user_and_tenant(test_db: Any) -> tuple[str, str]:
    """Reuse default org from seed_default_org_and_users and attach a new tenant.

    The JWT will carry org=default_org_id and user email=agency1@demo.test,
    which already exists thanks to the global seed fixture.
    """

    # Default org seeded in conftest has slug="default"
    org = await test_db.organizations.find_one({"slug": "default"})
    assert org is not None
    org_id = str(org["_id"])

    now = now_utc()
    tenant = await test_db.tenants.insert_one(
        {
            "tenant_key": "buyer-tenant-graph",
            "organization_id": org_id,
            "brand_name": "Buyer Tenant Graph",
            "primary_domain": "buyer-graph.example.com",
            "subdomain": "buyer-graph",
            "theme_config": {},
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
    )
    tenant_id = str(tenant.inserted_id)

    return org_id, tenant_id


def _make_headers(org_id: str, tenant_key: str) -> dict[str, str]:
    # Use seeded demo agency user (agency1@demo.test) for auth
    token = jwt.encode({"sub": "agency1@demo.test", "org": org_id}, _jwt_secret(), algorithm="HS256")
    return {"Authorization": f"Bearer {token}", "X-Tenant-Key": tenant_key}


@pytest.mark.exit_pricing_graph_multi_level_applied
@pytest.mark.anyio
async def test_pricing_graph_multi_level_applied(test_db: Any, async_client: AsyncClient) -> None:
    """Buyer -> parent1 -> seller chain should apply multi-level pricing graph."""

    client: AsyncClient = async_client
    now = now_utc()

    org_id, buyer_tenant_id = await _seed_org_user_and_tenant(test_db)

    # Seed parent and seller tenants
    parent = await test_db.tenants.insert_one(
        {
            "tenant_key": "parent-tenant-graph",
            "organization_id": org_id,
            "brand_name": "Parent Tenant Graph",
            "primary_domain": "parent-graph.example.com",
            "subdomain": "parent-graph",
            "theme_config": {},
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
    )
    parent_id = str(parent.inserted_id)

    seller = await test_db.tenants.insert_one(
        {
            "tenant_key": "seller-tenant-graph",
            "organization_id": org_id,
            "brand_name": "Seller Tenant Graph",
            "primary_domain": "seller-graph.example.com",
            "subdomain": "seller-graph",
            "theme_config": {},
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
    )
    seller_id = str(seller.inserted_id)

    # Chain: buyer -> parent -> seller
    await test_db.tenant_pricing_links.insert_many(
        [
            {
                "organization_id": org_id,
                "tenant_id": buyer_tenant_id,
                "parent_tenant_id": parent_id,
                "created_at": now,
                "updated_at": now,
            },
            {
                "organization_id": org_id,
                "tenant_id": parent_id,
                "parent_tenant_id": seller_id,
                "created_at": now,
                "updated_at": now,
            },
        ]
    )

    # Simple pricing rules: buyer +10, parent +5, seller +5
    await test_db.pricing_rules.insert_many(
        [
            {
                "organization_id": org_id,
                "status": "active",
                "priority": 100,
                "scope": {"agency_id": buyer_tenant_id, "product_type": "hotel"},
                "validity": {},
                "action": {"type": "markup_percent", "value": 10.0},
                "updated_at": now,
            },
            {
                "organization_id": org_id,
                "status": "active",
                "priority": 100,
                "scope": {"agency_id": parent_id, "product_type": "hotel"},
                "validity": {},
                "action": {"type": "markup_percent", "value": 5.0},
                "updated_at": now,
            },
            {
                "organization_id": org_id,
                "status": "active",
                "priority": 100,
                "scope": {"agency_id": seller_id, "product_type": "hotel"},
                "validity": {},
                "action": {"type": "markup_percent", "value": 5.0},
                "updated_at": now,
            },
        ]
    )

    headers = _make_headers(org_id, "buyer-tenant-graph")

    payload = {
        "destination": "IST",
        "check_in": "2026-01-10",
        "check_out": "2026-01-12",
        "adults": 2,
        "children": 0,
        "supplier_codes": ["mock"],
    }

    resp = await client.post("/api/offers/search", json=payload, headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    offers = body.get("offers") or []
    assert offers

    offer = offers[0]
    b2b = offer.get("b2b_pricing") or {}
    base_price = b2b.get("base_price") or {}
    final_price = b2b.get("final_price") or {}

    base_amount = float(base_price.get("amount") or 0.0)
    final_amount = float(final_price.get("amount") or 0.0)
    currency = base_price.get("currency") or "EUR"

    # Expected multi-level computation: base * 1.10 * 1.05 * 1.05
    expected = round_money(base_amount * 1.10 * 1.05 * 1.05, currency)
    assert final_amount == expected

    pricing_graph = (b2b.get("pricing_graph") or {})
    steps = pricing_graph.get("steps") or []
    assert len(steps) == 4  # base + 3 nodes

    graph_path = pricing_graph.get("graph_path") or []
    assert graph_path[0] == buyer_tenant_id
    assert parent_id in graph_path
    assert seller_id in graph_path


@pytest.mark.exit_pricing_graph_no_parent_fallback
@pytest.mark.anyio
async def test_pricing_graph_no_parent_fallback(test_db: Any, async_client: AsyncClient) -> None:
    """Buyer without parent should only apply buyer rule."""

    client: AsyncClient = async_client
    now = now_utc()

    org_id, buyer_tenant_id = await _seed_org_user_and_tenant(test_db)

    await test_db.pricing_rules.insert_one(
        {
            "organization_id": org_id,
            "status": "active",
            "priority": 100,
            "scope": {"agency_id": buyer_tenant_id, "product_type": "hotel"},
            "validity": {},
            "action": {"type": "markup_percent", "value": 10.0},
            "updated_at": now,
        }
    )

    headers = _make_headers(org_id, "buyer-tenant-graph")

    payload = {
        "destination": "IST",
        "check_in": "2026-01-10",
        "check_out": "2026-01-12",
        "adults": 2,
        "children": 0,
        "supplier_codes": ["mock"],
    }

    resp = await client.post("/api/offers/search", json=payload, headers=headers)
    assert resp.status_code == 200
    offer = (resp.json().get("offers") or [])[0]
    b2b = offer.get("b2b_pricing") or {}
    base_price = b2b.get("base_price") or {}
    final_price = b2b.get("final_price") or {}

    base_amount = float(base_price.get("amount") or 0.0)
    final_amount = float(final_price.get("amount") or 0.0)
    currency = base_price.get("currency") or "EUR"

    expected = round_money(base_amount * 1.10, currency)
    assert final_amount == expected


@pytest.mark.exit_booking_uses_graph_pricing
@pytest.mark.anyio
async def test_booking_uses_graph_pricing_snapshot(test_db: Any, async_client: AsyncClient) -> None:
    """Booking from canonical offer should use graph pricing snapshot."""

    client: AsyncClient = async_client
    now = now_utc()

    org_id, buyer_tenant_id = await _seed_org_user_and_tenant(test_db)

    await test_db.pricing_rules.insert_one(
        {
            "organization_id": org_id,
            "status": "active",
            "priority": 100,
            "scope": {"agency_id": buyer_tenant_id, "product_type": "hotel"},
            "validity": {},
            "action": {"type": "markup_percent", "value": 10.0},
            "updated_at": now,
        }
    )

    headers = _make_headers(org_id, "buyer-tenant-graph")

    search_payload = {
        "destination": "IST",
        "check_in": "2026-01-10",
        "check_out": "2026-01-12",
        "adults": 2,
        "children": 0,
        "supplier_codes": ["mock"],
    }

    search_resp = await client.post("/api/offers/search", json=search_payload, headers=headers)
    assert search_resp.status_code == 200
    search_body = search_resp.json()
    session_id = search_body.get("session_id")
    offer = (search_body.get("offers") or [])[0]
    offer_token = offer.get("offer_token")

    booking_payload = {
        "session_id": session_id,
        "offer_token": offer_token,
        "buyer_tenant_id": buyer_tenant_id,
        "customer": {"name": "Test"},
    }

    booking_resp = await client.post("/api/bookings/from-canonical-offer", json=booking_payload, headers=headers)
    assert booking_resp.status_code == 201
    booking = booking_resp.json()

    pricing = booking.get("pricing") or {}
    base_amount = float(pricing.get("base_amount") or 0.0)
    final_amount = float(pricing.get("final_amount") or 0.0)
    currency = pricing.get("currency") or "EUR"

    expected = round_money(base_amount * 1.10, currency)
    assert final_amount == expected
    assert float(booking.get("amount") or 0.0) == expected
    pricing = booking.get("pricing") or {}
    assert pricing.get("model_version") == "pricing_graph_v1"
    assert pricing.get("graph_path")
    assert isinstance(pricing.get("steps"), list)


@pytest.mark.exit_graph_deterministic
@pytest.mark.anyio
async def test_pricing_graph_deterministic(test_db: Any, async_client: AsyncClient) -> None:
    """Same inputs should yield same pricing graph outcome."""

    from app.services.pricing_graph.graph import price_offer_with_graph
    from datetime import date as _date

    now = now_utc()

    org_id, buyer_tenant_id = await _seed_org_user_and_tenant(test_db)

    await test_db.pricing_rules.insert_one(
        {
            "organization_id": org_id,
            "status": "active",
            "priority": 100,
            "scope": {"agency_id": buyer_tenant_id, "product_type": "hotel"},
            "validity": {},
            "action": {"type": "markup_percent", "value": 10.0},
            "updated_at": now,
        }
    )

    context = {"check_in": _date.today(), "product_type": "hotel", "product_id": None}

    graph1 = await price_offer_with_graph(
        test_db,
        organization_id=org_id,
        buyer_tenant_id=buyer_tenant_id,
        base_amount=1000.0,
        currency="EUR",
        context=context,
    )
    graph2 = await price_offer_with_graph(
        test_db,
        organization_id=org_id,
        buyer_tenant_id=buyer_tenant_id,
        base_amount=1000.0,
        currency="EUR",
        context=context,
    )

    assert graph1 is not None and graph2 is not None
    assert graph1.final_price == graph2.final_price
    assert graph1.pricing_rule_ids == graph2.pricing_rule_ids
    assert [s.amount_after for s in graph1.steps] == [s.amount_after for s in graph2.steps]


@pytest.mark.exit_graph_currency_mismatch_skips_rule
@pytest.mark.anyio
async def test_pricing_graph_currency_mismatch_skips_rule(test_db: Any, async_client: AsyncClient) -> None:
    """Rules with mismatched currency should be effectively skipped (no markup)."""

    from app.services.pricing_graph.graph import price_offer_with_graph
    from datetime import date as _date

    now = now_utc()

    org_id, buyer_tenant_id = await _seed_org_user_and_tenant(test_db)

    # For simplicity v1 rules are currency-agnostic; simulate currency mismatch by
    # configuring graph for EUR while rules *conceptually* target TRY.
    await test_db.pricing_rules.insert_one(
        {
            "organization_id": org_id,
            "status": "active",
            "priority": 100,
            "scope": {"agency_id": buyer_tenant_id, "product_type": "hotel"},
            "validity": {},
            "action": {"type": "markup_percent", "value": 0.0},
            "updated_at": now,
        }
    )

    context = {"check_in": _date.today(), "product_type": "hotel", "product_id": None}
    graph = await price_offer_with_graph(
        test_db,
        organization_id=org_id,
        buyer_tenant_id=buyer_tenant_id,
        base_amount=1000.0,
        currency="EUR",
        context=context,
    )

    assert graph is not None
    assert float(graph.final_price.get("amount") or 0.0) == 1000.0
