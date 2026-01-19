from __future__ import annotations

import pytest

from datetime import datetime

import jwt

JWT_SECRET_KEY = "test-secret-key"
JWT_ALGORITHM = "HS256"


@pytest.mark.anyio
async def test_b2b_account_summary_uses_ledger_when_available(async_client, test_db):
    """When finance_accounts + credit_profiles exist, /b2b/account/summary
    should use ledger-based data and expose credit limit + exposure status.

    This is a smoke test to guard against silent regressions in the B2B
    account summary logic.
    """

    db = test_db

    # Seed minimal org + agency + finance data in isolation for this test
    org_doc = {"name": "Test Org", "created_at": datetime.utcnow(), "updated_at": datetime.utcnow()}
    org_res = await db.organizations.insert_one(org_doc)
    org_id = str(org_res.inserted_id)

    agency_doc = {
        "organization_id": org_id,
        "name": "Ledger Test Agency",
        "settings": {"selling_currency": "EUR"},
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    agency_res = await db.agencies.insert_one(agency_doc)
    agency_id = str(agency_res.inserted_id)

    account_doc = {
        "organization_id": org_id,
        "type": "agency",
        "owner_id": agency_id,
        "currency": "EUR",
        "code": "AGENCY_AR_TEST",
        "name": "Agency Receivable Test",
        "status": "active",
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    acc_res = await db.finance_accounts.insert_one(account_doc)

    await db.account_balances.insert_one(
        {
            "organization_id": org_id,
            "account_id": acc_res.inserted_id,
            "currency": "EUR",
            "balance": 80.0,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
    )

    await db.credit_profiles.insert_one(
        {
            "organization_id": org_id,
            "agency_id": agency_id,
            "limit": 100.0,
            "soft_limit": 70.0,
            "payment_terms": "30d",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
    )

    # Build JWT for this agency user (bypassing full auth flow)
    payload = {
        "sub": "test-b2b-user",
        "org": org_id,
        "agency_id": agency_id,
        "roles": ["agency_admin"],
    }
    token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)

    # Call B2B account summary as agency user
    resp = await async_client.get(
        "/api/b2b/account/summary",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text

    data = resp.json()

    assert data["data_source"] == "ledger_based"
    assert "exposure_eur" in data
    assert data["credit_limit"] == pytest.approx(100.0, rel=1e-6)
    assert data["status"] == "near_limit"
