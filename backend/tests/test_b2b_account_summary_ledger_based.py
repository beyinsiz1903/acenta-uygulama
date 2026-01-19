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

    # Resolve org/agency from /api/auth/me using the real agency_token
    headers = {"Authorization": f"Bearer {agency_token}"}
    me_resp = await async_client.get("/api/auth/me", headers=headers)
    assert me_resp.status_code == 200, f"/api/auth/me failed: {me_resp.text}"
    me = me_resp.json()
    org_id = me.get("organization_id")
    agency_id = me.get("agency_id")

    assert org_id, "organization_id must be present in /api/auth/me response"
    assert agency_id, "agency_id must be present in /api/auth/me response"

    # Idempotent seed of minimal finance data for this org/agency
    account_filter = {
        "organization_id": org_id,
        "type": "agency",
        "owner_id": agency_id,
        "currency": "EUR",
    }
    account_doc = {
        **account_filter,
        "code": "AGENCY_AR_TEST",
        "name": "Agency Receivable Test",
        "status": "active",
        "updated_at": datetime.utcnow(),
    }
    await db.finance_accounts.update_one(account_filter, {"$set": account_doc}, upsert=True)
    account = await db.finance_accounts.find_one(account_filter)
    assert account is not None

    balance_filter = {
        "organization_id": org_id,
        "account_id": account["_id"],
        "currency": "EUR",
    }
    balance_doc = {
        **balance_filter,
        "balance": 80.0,
        "updated_at": datetime.utcnow(),
        "created_at": datetime.utcnow(),
    }
    await db.account_balances.update_one(balance_filter, {"$set": balance_doc}, upsert=True)

    credit_filter = {"organization_id": org_id, "agency_id": agency_id}
    credit_doc = {
        **credit_filter,
        "limit": 100.0,
        "soft_limit": 70.0,
        "payment_terms": "30d",
        "updated_at": datetime.utcnow(),
        "created_at": datetime.utcnow(),
    }
    await db.credit_profiles.update_one(credit_filter, {"$set": credit_doc}, upsert=True)

    # Call B2B account summary as agency user (via real auth token)
    resp = await async_client.get(
        "/api/b2b/account/summary",
        headers=headers,
    )
    assert resp.status_code == 200, resp.text

    data = resp.json()

    assert data["data_source"] == "ledger_based"
    assert "exposure_eur" in data
    assert data["credit_limit"] == pytest.approx(100.0, rel=1e-6)
    assert data["status"] == "near_limit"
    # Aging B2B summary'de hesaplanmıyor; contract olarak None bekliyoruz
    assert data.get("aging") is None
