from __future__ import annotations

import pytest

from app.utils import now_utc


@pytest.mark.anyio
async def test_exposure_dashboard_returns_aging_buckets(async_client, test_db, admin_token):
    """Exposure dashboard should include basic aging buckets for agency accounts.

    We seed a single agency finance account with a few ledger entries spread
    over time and verify that age_0_30, age_31_60, age_61_plus are populated.
    """

    db = test_db

    # Align org_id with the admin user's organization so auth + data match
    admin_doc = await db.users.find_one({"email": "admin@acenta.test"})
    assert admin_doc is not None
    org_id = admin_doc["organization_id"]

    agency_id = "agency_exposure_1"

    # Seed agency document
    await db.agencies.insert_one(
        {
            "_id": agency_id,
            "organization_id": org_id,
            "name": "Exposure Test Agency",
            "status": "active",
        }
    )

    # Seed finance account for agency
    account_id = "acct_exposure_1"
    now = now_utc()
    await db.finance_accounts.insert_one(
        {
            "_id": account_id,
            "organization_id": org_id,
            "type": "agency",
            "owner_id": agency_id,
            "code": "AGENCY_EXPOSURE_TEST",
            "name": "Agency Exposure Test Account",
            "currency": "EUR",
            "status": "active",
            "created_at": now,
            "updated_at": now,
        }
    )

    # Seed credit profile so exposure endpoint does not skip this agency
    await db.credit_profiles.insert_one(
        {
            "_id": f"cred_{agency_id}",
            "organization_id": org_id,
            "agency_id": agency_id,
            "currency": "EUR",
            "limit": 10000.0,
            "soft_limit": 7000.0,
            "payment_terms": "NET30",
            "status": "active",
            "created_at": now,
            "updated_at": now,
        }
    )

    # Helper to backdate days
    from datetime import timedelta

    def days_ago(d: int):
        return now - timedelta(days=d)

    # Seed ledger entries: each entry is 100 EUR debit at different ages
    entries = [
        # 10 days ago -> 0-30 bucket
        {
            "_id": "le_0_10",
            "organization_id": org_id,
            "posting_id": "post_0_10",
            "account_id": account_id,
            "currency": "EUR",
            "direction": "debit",
            "amount": 100.0,
            "occurred_at": days_ago(10),
            "posted_at": days_ago(10),
            "source": {"type": "booking", "id": "bk_0_10"},
            "event": "BOOKING_CONFIRMED",
            "memo": "0-30 debit",
            "meta": {},
        },
        # 40 days ago -> 31-60 bucket
        {
            "_id": "le_31_40",
            "organization_id": org_id,
            "posting_id": "post_31_40",
            "account_id": account_id,
            "currency": "EUR",
            "direction": "debit",
            "amount": 200.0,
            "occurred_at": days_ago(40),
            "posted_at": days_ago(40),
            "source": {"type": "booking", "id": "bk_31_40"},
            "event": "BOOKING_CONFIRMED",
            "memo": "31-60 debit",
            "meta": {},
        },
        # 80 days ago -> 61+ bucket
        {
            "_id": "le_61_80",
            "organization_id": org_id,
            "posting_id": "post_61_80",
            "account_id": account_id,
            "currency": "EUR",
            "direction": "debit",
            "amount": 300.0,
            "occurred_at": days_ago(80),
            "posted_at": days_ago(80),
            "source": {"type": "booking", "id": "bk_61_80"},
            "event": "BOOKING_CONFIRMED",
            "memo": "61+ debit",
            "meta": {},
        },
    ]
    await db.ledger_entries.insert_many(entries)

    # Keep account_balances in sync with total exposure (100 + 200 + 300)
    await db.account_balances.insert_one(
        {
            "_id": f"bal_{account_id}_eur",
            "organization_id": org_id,
            "account_id": account_id,
            "currency": "EUR",
            "balance": 600.0,
            "as_of": now,
            "updated_at": now,
        }
    )

    # Call exposure dashboard as admin user using real JWT auth
    headers = {"Authorization": f"Bearer {admin_token}"}
    # NOTE: Router has its own "/api/ops/finance" prefix and is mounted without
    # extra API_PREFIX in server.py, bu yüzden efektif path "/api/ops/finance/exposure".
    resp = await async_client.get("/api/ops/finance/exposure", headers=headers)
    assert resp.status_code == 200
    data = resp.json()

    items = data.get("items") or []
    assert len(items) >= 1

    # Find our agency item
    item = next(i for i in items if i["agency_id"] == agency_id)

    assert item["currency"] == "EUR"
    # Exposure should be close to 600
    assert abs(item["exposure"] - 600.0) < 0.01

    # Aging buckets should reflect our seeded entries
    assert abs(item["age_0_30"] - 100.0) < 0.01
    assert abs(item["age_31_60"] - 200.0) < 0.01
    assert abs(item["age_61_plus"] - 300.0) < 0.01
