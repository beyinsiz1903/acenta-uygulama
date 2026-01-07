"""
Finance OS Phase 2A.4 Backend Test
Settlement Run Engine: Supplier settlement_runs over supplier_accruals

Scenarios:
1) Create settlement run (draft)
2) Prevent multiple open runs (same supplier+currency)
3) Add eligible accrual locks
4) Cannot add ineligible accrual
5) Remove items from draft (unlock)
6) Approve snapshots and totals
7) Approve makes immutable (add/remove -> 409)
8) Cancel unlocks (draft + approved), paid cannot cancel
9) Mark paid only from approved

HTTP + DB mix, similar style to Phase 2A.3 tests.
"""

import requests
import pymongo
from bson import ObjectId
from datetime import datetime

BASE_URL = "http://localhost:8001"
MONGO_URL = "mongodb://localhost:27017/"


def _login_admin():
    r = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": "admin@acenta.test", "password": "admin123"},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    return data["access_token"], data["user"]["organization_id"], data["user"]["email"]


def test_phase_2a_4():
    print("\n" + "=" * 80)
    print("FINANCE OS PHASE 2A.4 BACKEND TEST - SETTLEMENT RUN ENGINE")
    print("=" * 80 + "\n")

    client = pymongo.MongoClient(MONGO_URL)
    db = client["test_database"]

    token, org_id, admin_email = _login_admin()
    headers = {"Authorization": f"Bearer {token}"}

    # Health check
    r = requests.get(f"{BASE_URL}/api/health")
    assert r.status_code == 200

    # Isolated supplier & cleanup
    supplier_id = f"phase2a4_sup_{ObjectId()}"

    # Clean any existing data for this supplier
    db.supplier_accruals.delete_many({"organization_id": org_id, "supplier_id": supplier_id})
    db.settlement_runs.delete_many({"organization_id": org_id, "supplier_id": supplier_id})

    # Ensure supplier
    db.suppliers.insert_one(
        {
            "_id": supplier_id,
            "organization_id": org_id,
            "name": "Phase 2A.4 Test Supplier",
            "status": "active",
        }
    )

    # ------------------------------------------------------------------
    # 1) Create settlement run -> draft
    # ------------------------------------------------------------------
    print("1️⃣  Create settlement run (draft)...")

    # Ensure platform cash account for EUR (needed for Phase 2A.5 mark-paid)
    platform_cash_code = "PLATFORM_CASH_EUR"
    existing_cash = db.finance_accounts.find_one(
        {
            "organization_id": org_id,
            "type": "platform",
            "code": platform_cash_code,
            "currency": "EUR",
        }
    )
    if not existing_cash:
        cash_id = ObjectId()
        now_seed = datetime.utcnow()
        db.finance_accounts.insert_one(
            {
                "_id": cash_id,
                "organization_id": org_id,
                "type": "platform",
                "owner_id": "platform",
                "code": platform_cash_code,
                "name": "Platform Cash EUR",
                "currency": "EUR",
                "status": "active",
                "created_at": now_seed,
                "updated_at": now_seed,
            }
        )

    payload = {
        "supplier_id": supplier_id,
        "currency": "EUR",
        "period": {"from": "2026-01-01", "to": "2026-01-31"},
    }
    r = requests.post(f"{BASE_URL}/api/ops/finance/settlements", json=payload, headers=headers)
    assert r.status_code == 200, r.text
    run = r.json()

    settlement_id = run["settlement_id"]
    assert run["status"] == "draft"
    assert run["totals"]["total_items"] == 0
    assert abs(run["totals"]["total_net_payable"] - 0.0) < 0.01

    print("   ✅ Draft settlement created", settlement_id)

    # ------------------------------------------------------------------
    # 2) Prevent multiple open runs
    # ------------------------------------------------------------------
    print("2️⃣  Prevent multiple open runs (same supplier+currency)...")

    r2 = requests.post(f"{BASE_URL}/api/ops/finance/settlements", json=payload, headers=headers)
    assert r2.status_code == 409, r2.text
    data2 = r2.json()
    assert data2["error"]["code"] == "open_settlement_exists"

    print("   ✅ open_settlement_exists enforced")

    # ------------------------------------------------------------------
    # Seed accruals for tests
    # ------------------------------------------------------------------
    print("Seeding accruals for settlement tests...")

    accrual_ok_id = ObjectId()
    accrual_ineligible_id = ObjectId()

    now = datetime.utcnow()

    # Eligible accrual (accrued, no settlement_id)
    db.supplier_accruals.insert_one(
        {
            "_id": accrual_ok_id,
            "organization_id": org_id,
            "supplier_id": supplier_id,
            "currency": "EUR",
            "booking_id": str(ObjectId()),
            "amounts": {"net_payable": 500.0},
            "status": "accrued",
            "settlement_id": None,
            "accrued_at": now,
        }
    )

    # Ineligible accrual (reversed)
    db.supplier_accruals.insert_one(
        {
            "_id": accrual_ineligible_id,
            "organization_id": org_id,
            "supplier_id": supplier_id,
            "currency": "EUR",
            "booking_id": str(ObjectId()),
            "amounts": {"net_payable": 300.0},
            "status": "reversed",
            "settlement_id": None,
            "accrued_at": now,
        }
    )

    # ------------------------------------------------------------------
    # 3) Add eligible accrual locks
    # ------------------------------------------------------------------
    print("3️⃣  Add eligible accrual to settlement (lock accrual)...")

    r3 = requests.post(
        f"{BASE_URL}/api/ops/finance/settlements/{settlement_id}/items:add",
        json=[str(accrual_ok_id)],
        headers=headers,
    )
    assert r3.status_code == 200, r3.text
    data3 = r3.json()
    assert data3["added"] == 1
    assert data3["totals"]["total_items"] == 1
    assert abs(data3["totals"]["total_net_payable"] - 500.0) < 0.01

    accrual_ok = db.supplier_accruals.find_one({"_id": accrual_ok_id})
    assert accrual_ok["status"] == "in_settlement"
    assert str(accrual_ok["settlement_id"]) == settlement_id

    print("   ✅ Eligible accrual locked into settlement")

    # ------------------------------------------------------------------
    # 4) Cannot add ineligible accrual
    # ------------------------------------------------------------------
    print("4️⃣  Cannot add ineligible accrual (status=reversed)...")

    r4 = requests.post(
        f"{BASE_URL}/api/ops/finance/settlements/{settlement_id}/items:add",
        json=[str(accrual_ineligible_id)],
        headers=headers,
    )
    assert r4.status_code == 409, r4.text
    data4 = r4.json()
    assert data4["error"]["code"] == "accrual_not_eligible"

    # Side-effect: ineligible accrual unchanged
    accrual_inel = db.supplier_accruals.find_one({"_id": accrual_ineligible_id})
    assert accrual_inel["status"] == "reversed"
    assert accrual_inel.get("settlement_id") is None

    print("   ✅ Ineligible accrual rejected without side-effects")

    # ------------------------------------------------------------------
    # 5) Remove items from draft (unlock)
    # ------------------------------------------------------------------
    print("5️⃣  Remove accrual from draft settlement (unlock)...")

    r5 = requests.post(
        f"{BASE_URL}/api/ops/finance/settlements/{settlement_id}/items:remove",
        json=[str(accrual_ok_id)],
        headers=headers,
    )
    assert r5.status_code == 200, r5.text

    # After removal, accrual should be unlocked
    accrual_ok2 = db.supplier_accruals.find_one({"_id": accrual_ok_id})
    assert accrual_ok2["settlement_id"] is None
    # We fallback prev status to accrued
    assert accrual_ok2["status"] in {"accrued", "adjusted"}

    print("   ✅ Draft remove unlocks accrual")

    # Re-add eligible accrual so we can approve a non-empty settlement
    r5b = requests.post(
        f"{BASE_URL}/api/ops/finance/settlements/{settlement_id}/items:add",
        json=[str(accrual_ok_id)],
        headers=headers,
    )
    assert r5b.status_code == 200, r5b.text

    # ------------------------------------------------------------------
    # 6) Approve snapshots and totals
    # ------------------------------------------------------------------
    print("6️⃣  Approve settlement (snapshot line_items + totals)...")

    r6 = requests.post(
        f"{BASE_URL}/api/ops/finance/settlements/{settlement_id}/approve",
        headers=headers,
    )
    assert r6.status_code == 200, r6.text
    data6 = r6.json()
    assert data6["status"] == "approved"
    assert data6["totals"]["total_items"] == 1
    assert abs(data6["totals"]["total_net_payable"] - 500.0) < 0.01

    # Fetch detail to inspect snapshot
    r6d = requests.get(
        f"{BASE_URL}/api/ops/finance/settlements/{settlement_id}", headers=headers
    )
    assert r6d.status_code == 200, r6d.text
    detail = r6d.json()

    assert detail["status"] == "approved"
    assert len(detail["line_items"]) == 1
    li = detail["line_items"][0]
    assert li["accrual_id"] == str(accrual_ok_id)
    assert abs(li["net_payable"] - 500.0) < 0.01

    print("   ✅ Approval snapshot immutable line_items captured")

    # ------------------------------------------------------------------
    # 7) Approve makes immutable (no add/remove)
    # ------------------------------------------------------------------
    print("7️⃣  Approved settlement is immutable (add/remove -> 409)...")

    r7a = requests.post(
        f"{BASE_URL}/api/ops/finance/settlements/{settlement_id}/items:add",
        json=[str(accrual_ok_id)],
        headers=headers,
    )
    assert r7a.status_code == 409, r7a.text
    assert r7a.json()["error"]["code"] == "settlement_not_draft"

    r7b = requests.post(
        f"{BASE_URL}/api/ops/finance/settlements/{settlement_id}/items:remove",
        json=[str(accrual_ok_id)],
        headers=headers,
    )
    assert r7b.status_code == 409, r7b.text
    assert r7b.json()["error"]["code"] == "settlement_not_draft"

    print("   ✅ Approved settlement is immutable")

    # ------------------------------------------------------------------
    # 8) Cancel unlocks (draft + approved), paid cannot cancel
    # ------------------------------------------------------------------
    print("8️⃣  Cancel behaviour (draft/approved unlock, paid forbidden)...")

    # New draft settlement + accrual for cancel tests (can reuse EUR; previous run was cancelled)
    payload2 = {
        "supplier_id": supplier_id,
        "currency": "EUR",
        "period": None,
    }
    r8 = requests.post(f"{BASE_URL}/api/ops/finance/settlements", json=payload2, headers=headers)
    assert r8.status_code == 200, r8.text
    run2 = r8.json()
    settlement2_id = run2["settlement_id"]

    accrual_cancel_id = ObjectId()
    db.supplier_accruals.insert_one(
        {
            "_id": accrual_cancel_id,
            "organization_id": org_id,
            "supplier_id": supplier_id,
            "currency": "EUR",
            "booking_id": str(ObjectId()),
            "amounts": {"net_payable": 100.0},
            "status": "accrued",
            "settlement_id": None,
            "accrued_at": now,
        }
    )

    # Add to settlement2
    r8a = requests.post(
        f"{BASE_URL}/api/ops/finance/settlements/{settlement2_id}/items:add",
        json=[str(accrual_cancel_id)],
        headers=headers,
    )
    assert r8a.status_code == 200, r8a.text

    # Cancel draft
    r8c = requests.post(
        f"{BASE_URL}/api/ops/finance/settlements/{settlement2_id}/cancel",
        json={"reason": "ops_draft_cancel"},
        headers=headers,
    )
    assert r8c.status_code == 200, r8c.text
    data8c = r8c.json()
    assert data8c["status"] == "cancelled"

    # Accrual unlocked
    accrual_cancel = db.supplier_accruals.find_one({"_id": accrual_cancel_id})
    assert accrual_cancel["settlement_id"] is None

    print("   ✅ Draft cancel unlocks accrual and marks settlement cancelled")

    # Approved cancel (reuse first settlement: settlement_id)
    r8c2 = requests.post(
        f"{BASE_URL}/api/ops/finance/settlements/{settlement_id}/cancel",
        json={"reason": "ops_approved_cancel"},
        headers=headers,
    )
    assert r8c2.status_code == 200, r8c2.text
    data8c2 = r8c2.json()
    assert data8c2["status"] == "cancelled"

    print("   ✅ Approved cancel works (though no accrual unlocks here as they were already snapshot-only)")

    # ------------------------------------------------------------------
    # 9) Mark paid only from approved
    # ------------------------------------------------------------------
    print("9️⃣  Mark paid only from approved (enforce state)...")

    # New run3: draft -> approved -> paid (reuse USD to avoid open-settlement clash)
    r9 = requests.post(f"{BASE_URL}/api/ops/finance/settlements", json=payload2, headers=headers)
    assert r9.status_code == 200, r9.text
    run3 = r9.json()
    settlement3_id = run3["settlement_id"]

    # Approve empty settlement should fail
    r9a = requests.post(
        f"{BASE_URL}/api/ops/finance/settlements/{settlement3_id}/approve",
        headers=headers,
    )
    assert r9a.status_code == 409, r9a.text
    assert r9a.json()["error"]["code"] == "settlement_empty"

    # Mark-paid on draft should fail
    r9b = requests.post(
        f"{BASE_URL}/api/ops/finance/settlements/{settlement3_id}/mark-paid",
        json={"payment_reference": "BANK-REF-123"},
        headers=headers,
    )
    assert r9b.status_code == 409, r9b.text
    assert r9b.json()["error"]["code"] == "settlement_not_approved"

    # Seed one accrual and approve
    accrual_paid_id = ObjectId()
    db.supplier_accruals.insert_one(
        {
            "_id": accrual_paid_id,
            "organization_id": org_id,
            "supplier_id": supplier_id,
            "currency": "EUR",
            "booking_id": str(ObjectId()),
            "amounts": {"net_payable": 200.0},
            "status": "accrued",
            "settlement_id": None,
            "accrued_at": now,
        }
    )

    r9c = requests.post(
        f"{BASE_URL}/api/ops/finance/settlements/{settlement3_id}/items:add",
        json=[str(accrual_paid_id)],
        headers=headers,
    )
    assert r9c.status_code == 200, r9c.text

    r9d = requests.post(
        f"{BASE_URL}/api/ops/finance/settlements/{settlement3_id}/approve",
        headers=headers,
    )
    assert r9d.status_code == 200, r9d.text

    # Now mark-paid should succeed
    r9e = requests.post(
        f"{BASE_URL}/api/ops/finance/settlements/{settlement3_id}/mark-paid",
        json={"payment_reference": "BANK-REF-999"},
        headers=headers,
    )
    assert r9e.status_code == 200, r9e.text
    data9e = r9e.json()
    assert data9e["status"] == "paid"
    assert data9e["payment_posting_id"] is not None

    # Cancel on paid must fail
    r9f = requests.post(
        f"{BASE_URL}/api/ops/finance/settlements/{settlement3_id}/cancel",
        json={"reason": "should_not_cancel_paid"},
        headers=headers,
    )
    assert r9f.status_code == 409, r9f.text
    assert r9f.json()["error"]["code"] == "settlement_already_paid"

    print("   ✅ Mark-paid + paid immutability enforced")

    client.close()


if __name__ == "__main__":
    test_phase_2a_4()
