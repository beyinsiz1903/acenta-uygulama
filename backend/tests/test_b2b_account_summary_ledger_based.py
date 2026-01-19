from __future__ import annotations

import pytest

from datetime import datetime


@pytest.mark.anyio
async def test_b2b_account_summary_uses_ledger_when_available(async_client, agency_token, test_db):
    """When finance_accounts + credit_profiles exist, /b2b/account/summary
    should use ledger-based data and expose credit limit + exposure status.

    This is a smoke test to guard against silent regressions in the B2B
    account summary logic.
    """

    db = test_db

    # Decode agency_token to align seeded data with real B2B user context
    import os
    from jose import jwt
    from app.utils_jwt import JWT_SECRET_KEY

    raw_token = agency_token
    payload = jwt.decode(raw_token, JWT_SECRET_KEY, algorithms=["HS256"])
    org_id = payload["org"]
    agency_id = payload["agency_id"]

    # Seed finance data for this org/agency

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

    # Call B2B account summary as agency user (via real auth token)
    resp = await async_client.get(
        "/api/b2b/account/summary",
        headers={"Authorization": f"Bearer {agency_token}"},
    )
    assert resp.status_code == 200, resp.text

    data = resp.json()

    assert data["data_source"] == "ledger_based"
    assert "exposure_eur" in data
    assert data["credit_limit"] == pytest.approx(100.0, rel=1e-6)
    assert data["status"] == "near_limit"
