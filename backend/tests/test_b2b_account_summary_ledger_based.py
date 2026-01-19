from __future__ import annotations

import pytest

from app.db import get_db


@pytest.mark.anyio
async def test_b2b_account_summary_uses_ledger_when_available(async_client, agency_token, test_db):
    """When finance_accounts + credit_profiles exist, /b2b/account/summary
    should use ledger-based data and expose credit limit + exposure status.

    This is a smoke test to guard against silent regressions in the B2B
    account summary logic.
    """

    db = test_db

    # Ensure credit profile and finance account/balance are present (minimal_finance_seed
    # already creates them for default org + demo agency)
    org = await db.organizations.find_one({})
    assert org is not None
    org_id = str(org["_id"])

    agency = await db.agencies.find_one({"organization_id": org_id, "name": "Demo Agency"})
    assert agency is not None
    agency_id = str(agency["_id"])

    credit = await db.credit_profiles.find_one({"organization_id": org_id, "agency_id": agency_id})
    assert credit is not None

    account = await db.finance_accounts.find_one(
        {"organization_id": org_id, "type": "agency", "owner_id": agency_id}
    )
    assert account is not None

    balance = await db.account_balances.find_one(
        {"organization_id": org_id, "account_id": account["_id"], "currency": account["currency"]}
    )
    assert balance is not None

    # Call B2B account summary as agency user
    resp = await async_client.get(
        "/api/b2b/account/summary",
        headers={"Authorization": f"Bearer {agency_token}"},
    )
    assert resp.status_code == 200, resp.text

    data = resp.json()

    assert data["data_source"] == "ledger_based"
    assert "exposure_eur" in data
    assert data["credit_limit"] == pytest.approx(float(credit["limit"]), rel=1e-6)
    assert data["status"] in {"ok", "near_limit", "over_limit"}
