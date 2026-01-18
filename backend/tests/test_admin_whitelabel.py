from __future__ import annotations

from datetime import datetime

import pytest

from app.auth import create_access_token
from app.db import get_db


@pytest.mark.anyio
async def test_admin_whitelabel_feature_disabled(async_client, test_db, anyio_backend):  # type: ignore[override]
    db = test_db
    org_id = "org_no_b2b_pro_whitelabel"
    await db.organizations.insert_one({"_id": org_id, "name": "No B2B PRO", "features": {"b2b_pro": False}})

    email = "admin_whitelabel_nopro@test.local"
    user_doc = {
        "organization_id": org_id,
        "email": email,
        "name": "Admin No PRO",
        "roles": ["admin"],
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    await db.users.insert_one(user_doc)

    token = create_access_token(subject=email, organization_id=org_id, roles=user_doc["roles"])

    resp = await async_client.get(
        "/api/admin/whitelabel",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_admin_whitelabel_upsert_and_get(async_client, test_db, anyio_backend):  # type: ignore[override]
    db = test_db

    org_id = "org_b2b_pro_whitelabel"
    await db.organizations.insert_one({"_id": org_id, "name": "Org B2B PRO", "features": {"b2b_pro": True}})

    email = "admin_whitelabel@test.local"
    user_doc = {
        "organization_id": org_id,
        "email": email,
        "name": "Admin Whitelabel",
        "roles": ["admin"],
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    await db.users.insert_one(user_doc)

    token = create_access_token(subject=email, organization_id=org_id, roles=user_doc["roles"])

    # Initial GET should return synthesized default (no DB doc yet)
    resp_get_initial = await async_client.get(
        "/api/admin/whitelabel",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp_get_initial.status_code == 200
    data_initial = resp_get_initial.json()
    assert data_initial["brand_name"] == ""

    # Upsert new config
    payload = {
        "brand_name": "My B2B Brand",
        "primary_color": "#ff0000",
        "logo_url": "https://example.com/logo.png",
        "favicon_url": "https://example.com/favicon.ico",
        "support_email": "support@example.com",
    }
    resp_put = await async_client.put(
        "/api/admin/whitelabel",
        headers={"Authorization": f"Bearer {token}"},
        json=payload,
    )
    assert resp_put.status_code == 200
    data_put = resp_put.json()
    assert data_put["brand_name"] == payload["brand_name"]
    assert data_put["primary_color"] == payload["primary_color"]

    # Second GET should reflect stored config
    resp_get = await async_client.get(
        "/api/admin/whitelabel",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp_get.status_code == 200
    data = resp_get.json()
    assert data["brand_name"] == payload["brand_name"]
    assert data["primary_color"] == payload["primary_color"]
    assert data["logo_url"] == payload["logo_url"]
    assert data["favicon_url"] == payload["favicon_url"]
    assert data["support_email"] == payload["support_email"]
