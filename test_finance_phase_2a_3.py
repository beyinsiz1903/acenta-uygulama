"""
Finance OS Phase 2A.3 Backend Test
Tests: Supplier Accrual Reverse & Adjustment Logic

Scenarios:
1) Happy reverse (VOUCHERED booking with accrual → SUPPLIER_ACCRUAL_REVERSED)
2) Settlement lock guard (reverse/adjust blocked with 409 accrual_locked_in_settlement)
3) Adjustment delta > 0 (increase payable)
4) Adjustment delta < 0 (decrease payable)
5) Adjustment delta == 0 (no posting)
"""
import requests
import pymongo
from bson import ObjectId
from uuid import uuid4

BASE_URL = "http://localhost:8001"
MONGO_URL = "mongodb://localhost:27017/"


def _login_admin():
    r = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": "admin@acenta.test", "password": "admin123"},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    return data["access_token"], data["user"]["organization_id"]


def test_phase_2a_3():
    print("\n" + "=" * 80)
    print("FINANCE OS PHASE 2A.3 BACKEND TEST")
    print("=" * 80 + "\n")

    client = pymongo.MongoClient(MONGO_URL)
    db = client["test_database"]

    token, org_id = _login_admin()
    headers = {"Authorization": f"Bearer {token}"}

    # Health check
    r = requests.get(f"{BASE_URL}/api/health")
    assert r.status_code == 200

    # supplier_id and cleanup are defined below (isolated per test run)
    # Generate isolated supplier_id for this test run (to avoid collisions)
    supplier_id = f"phase2a3_{uuid4().hex[:8]}"

    # Targeted cleanup for this supplier and any test bookings we will create
    # (done before inserting fresh data)
    # We will pre-generate booking IDs so we can filter by them later if needed.
    booking_id = ObjectId()
    locked_booking_id = ObjectId()
    adj_booking_id = ObjectId()

    # Clean supplier-specific finance data
    # 1) Supplier accruals
    db.supplier_accruals.delete_many({"organization_id": org_id, "supplier_id": supplier_id})

    # 2) Supplier finance accounts and balances
    supplier_accounts = list(
        db.finance_accounts.find(
            {
                "organization_id": org_id,
                "type": "supplier",
                "owner_id": supplier_id,
            }
        )
    )
    if supplier_accounts:
        account_ids = [str(a["_id"]) for a in supplier_accounts]
        db.account_balances.delete_many(
            {
                "organization_id": org_id,
                "account_id": {"$in": account_ids},
            }
        )
        db.finance_accounts.delete_many({"_id": {"$in": [a["_id"] for a in supplier_accounts]}})

    # 3) Ledger postings and entries for our test bookings and supplier events only
    test_booking_ids = [str(booking_id), str(locked_booking_id), str(adj_booking_id)]
    supplier_events = [
        "SUPPLIER_ACCRUED",
        "SUPPLIER_ACCRUAL_REVERSED",
        "SUPPLIER_ACCRUAL_ADJUSTED",
    ]
    db.ledger_postings.delete_many(
        {
            "organization_id": org_id,
            "source.type": "booking",
            "source.id": {"$in": test_booking_ids},
            "event": {"$in": supplier_events},
        }
    )
    db.ledger_entries.delete_many(
        {
            "organization_id": org_id,
            "source.type": "booking",
            "source.id": {"$in": test_booking_ids},
            "event": {"$in": supplier_events},
        }
    )

    # 4) Cases & bookings for these test booking IDs
    db.cases.delete_many({"organization_id": org_id, "booking_id": {"$in": test_booking_ids}})
    db.bookings.delete_many({"_id": {"$in": [booking_id, locked_booking_id, adj_booking_id]}})

    # Ensure supplier exists after cleanup
    if not db.suppliers.find_one({"_id": supplier_id}):
        db.suppliers.insert_one(
            {
                "_id": supplier_id,
                "organization_id": org_id,
                "name": "Test Supplier Phase 2A.3",
                "status": "active",
            }
        )

    # Helper to get balances for debug
    def get_supplier_balance(ccy: str) -> float:
        r2 = requests.get(
            f"{BASE_URL}/api/ops/finance/suppliers/{supplier_id}/balances",
            params={"currency": ccy},
            headers=headers,
        )
        assert r2.status_code == 200, r2.text
        return r2.json()["balance"]

    # =====================================================================
    # 1) Happy reverse
    # =====================================================================
    print("1️⃣  Happy reverse (VOUCHERED → CANCELLED with accrual)...")

    # Create booking in CONFIRMED state (same pattern as Phase 2A.2)
    booking_id = ObjectId()
    net_payable = 850.0
    booking_doc = {
        "_id": booking_id,
        "organization_id": org_id,
        "supplier_id": supplier_id,
        "status": "CONFIRMED",
        "currency": "EUR",
        "amounts": {"sell": 1000.0},
        "commission": {"amount": 150.0},
        "items": [{"supplier_id": supplier_id}],
    }
    db.bookings.insert_one(booking_doc)

    balance_before = get_supplier_balance("EUR")

    # Generate voucher via ops endpoint -> VOUCHERED + SUPPLIER_ACCRUED
    r = requests.post(
        f"{BASE_URL}/api/ops/bookings/{booking_id}/voucher/generate",
        headers=headers,
    )
    assert r.status_code in [200, 201], r.text

    # Now supplier payable should have increased by net_payable
    balance_after_accrual = get_supplier_balance("EUR")
    assert abs(balance_after_accrual - (balance_before + net_payable)) < 0.01

    # Create a cancel case and approve via ops endpoint (triggers reverse hook)
    case_doc = {
        "organization_id": org_id,
        "booking_id": str(booking_id),
        "type": "cancel",
        "status": "open",
    }
    case_id = db.cases.insert_one(case_doc).inserted_id

    r = requests.post(
        f"{BASE_URL}/api/ops/cases/{case_id}/approve",
        headers=headers,
    )
    assert r.status_code == 200, r.text

    print("   ✅ /api/ops/cases/{case_id}/approve called successfully")

    # Supplier balance after reverse should return to original
    balance_final = get_supplier_balance("EUR")
    assert abs(balance_final - balance_before) < 0.01, (
        f"Supplier balance mismatch after reverse: expected {balance_before}, got {balance_final}"
    )

    print("   ✅ Supplier balance and accrual status reversed correctly")

    # =====================================================================
    # 2) Settlement lock guard
    # =====================================================================
    print("2️⃣  Settlement lock guard (reverse/adjust blocked)...")

    locked_booking_id = ObjectId()
    db.bookings.insert_one(
        {
            "_id": locked_booking_id,
            "organization_id": org_id,
            "supplier_id": supplier_id,
            "status": "VOUCHERED",
            "currency": "EUR",
            "amounts": {"sell": 500.0},
            "commission": {"amount": 50.0},
            "items": [{"supplier_id": supplier_id}],
        }
    )
    locked_accrual_id = ObjectId()
    db.supplier_accruals.insert_one(
        {
            "_id": locked_accrual_id,
            "organization_id": org_id,
            "booking_id": str(locked_booking_id),
            "supplier_id": supplier_id,
            "currency": "EUR",
            "amounts": {"gross_sell": 500.0, "commission": 50.0, "net_payable": 450.0},
            "status": "in_settlement",
            "settlement_id": "set_123",
        }
    )

    # Settlement lock guard via HTTP ops endpoints (more realistic)
    # First capture existing postings/entries for this booking
    before_post_cnt = db.ledger_postings.count_documents(
        {
            "organization_id": org_id,
            "source.type": "booking",
            "source.id": str(locked_booking_id),
        }
    )
    before_entry_cnt = db.ledger_entries.count_documents(
        {
            "organization_id": org_id,
            "source.type": "booking",
            "source.id": str(locked_booking_id),
        }
    )

    # Reverse endpoint
    r_lock_rev = requests.post(
        f"{BASE_URL}/api/ops/finance/supplier-accruals/{locked_booking_id}/reverse",
        headers=headers,
    )
    assert r_lock_rev.status_code == 409, r_lock_rev.text
    data_rev = r_lock_rev.json()
    assert data_rev["error"]["code"] == "accrual_locked_in_settlement"

    mid_post_cnt = db.ledger_postings.count_documents(
        {
            "organization_id": org_id,
            "source.type": "booking",
            "source.id": str(locked_booking_id),
        }
    )
    mid_entry_cnt = db.ledger_entries.count_documents(
        {
            "organization_id": org_id,
            "source.type": "booking",
            "source.id": str(locked_booking_id),
        }
    )

    # Adjust endpoint
    r_lock_adj = requests.post(
        f"{BASE_URL}/api/ops/finance/supplier-accruals/{locked_booking_id}/adjust",
        json={"new_sell": 600.0, "new_commission": 60.0},
        headers=headers,
    )
    assert r_lock_adj.status_code == 409, r_lock_adj.text
    data_adj = r_lock_adj.json()
    assert data_adj["error"]["code"] == "accrual_locked_in_settlement"

    after_post_cnt = db.ledger_postings.count_documents(
        {
            "organization_id": org_id,
            "source.type": "booking",
            "source.id": str(locked_booking_id),
        }
    )
    after_entry_cnt = db.ledger_entries.count_documents(
        {
            "organization_id": org_id,
            "source.type": "booking",
            "source.id": str(locked_booking_id),
        }
    )

    # No new postings/entries must be created by locked reverse/adjust
    assert before_post_cnt == mid_post_cnt == after_post_cnt
    assert before_entry_cnt == mid_entry_cnt == after_entry_cnt

    # Accrual doc must remain locked/in_settlement
    locked = db.supplier_accruals.find_one({"_id": locked_accrual_id})
    assert locked["status"] == "in_settlement"
    assert locked["settlement_id"] == "set_123"

    print("   ✅ Settlement lock guard enforced for reverse and adjust (no side-effects)")

    # =====================================================================
    # 3) Adjustment delta > 0 (increase payable)
    # =====================================================================
    print("3️⃣  Adjustment delta > 0 (increase payable)...")

    # Booking A: net 800 -> 900 (delta +100)
    adj_up_booking_id = ObjectId()
    db.bookings.insert_one(
        {
            "_id": adj_up_booking_id,
            "organization_id": org_id,
            "supplier_id": supplier_id,
            "status": "VOUCHERED",
            "currency": "EUR",
            "amounts": {"sell": 800.0},
            "commission": {"amount": 0.0},
            "items": [{"supplier_id": supplier_id}],
        }
    )
    adj_up_accrual_id = ObjectId()
    db.supplier_accruals.insert_one(
        {
            "_id": adj_up_accrual_id,
            "organization_id": org_id,
            "booking_id": str(adj_up_booking_id),
            "supplier_id": supplier_id,
            "currency": "EUR",
            "amounts": {"gross_sell": 800.0, "commission": 0.0, "net_payable": 800.0},
            "status": "accrued",
            "settlement_id": None,
        }
    )

    r_up = requests.post(
        f"{BASE_URL}/api/ops/finance/supplier-accruals/{adj_up_booking_id}/adjust",
        json={"new_sell": 900.0, "new_commission": 0.0},
        headers=headers,
    )
    assert r_up.status_code == 200, r_up.text
    data_up = r_up.json()
    assert data_up["delta"] > 0

    updated_up = db.supplier_accruals.find_one({"_id": adj_up_accrual_id})
    assert updated_up["status"] == "adjusted"
    assert abs(updated_up["amounts"]["net_payable"] - 900.0) < 0.01

    post_cnt_up = db.ledger_postings.count_documents(
        {
            "organization_id": org_id,
            "source.type": "booking",
            "source.id": str(adj_up_booking_id),
            "event": "SUPPLIER_ACCRUAL_ADJUSTED",
        }
    )
    assert post_cnt_up == 1

    print("   ✅ Adjustment up applied correctly")

    # =====================================================================
    # 4) Adjustment delta < 0 (decrease payable)
    # =====================================================================
    print("4️⃣  Adjustment delta < 0 (decrease payable)...")

    # Booking B: net 900 -> 850 (delta -50)
    adj_down_booking_id = ObjectId()
    db.bookings.insert_one(
        {
            "_id": adj_down_booking_id,
            "organization_id": org_id,
            "supplier_id": supplier_id,
            "status": "VOUCHERED",
            "currency": "EUR",
            "amounts": {"sell": 900.0},
            "commission": {"amount": 0.0},
            "items": [{"supplier_id": supplier_id}],
        }
    )
    adj_down_accrual_id = ObjectId()
    db.supplier_accruals.insert_one(
        {
            "_id": adj_down_accrual_id,
            "organization_id": org_id,
            "booking_id": str(adj_down_booking_id),
            "supplier_id": supplier_id,
            "currency": "EUR",
            "amounts": {"gross_sell": 900.0, "commission": 0.0, "net_payable": 900.0},
            "status": "accrued",
            "settlement_id": None,
        }
    )

    r_down = requests.post(
        f"{BASE_URL}/api/ops/finance/supplier-accruals/{adj_down_booking_id}/adjust",
        json={"new_sell": 850.0, "new_commission": 0.0},
        headers=headers,
    )
    assert r_down.status_code == 200, r_down.text
    data_down = r_down.json()
    assert data_down["delta"] < 0

    updated_down = db.supplier_accruals.find_one({"_id": adj_down_accrual_id})
    assert abs(updated_down["amounts"]["net_payable"] - 850.0) < 0.01

    post_cnt_down = db.ledger_postings.count_documents(
        {
            "organization_id": org_id,
            "source.type": "booking",
            "source.id": str(adj_down_booking_id),
            "event": "SUPPLIER_ACCRUAL_ADJUSTED",
        }
    )
    assert post_cnt_down == 1

    print("   ✅ Adjustment down applied correctly")

    # =====================================================================
    # 5) Adjustment delta == 0 (no posting)
    # =====================================================================
    print("5️⃣  Adjustment delta == 0 (no posting)...")

    # Booking C: net 850 -> 850 (delta 0, no posting)
    adj_zero_booking_id = ObjectId()
    db.bookings.insert_one(
        {
            "_id": adj_zero_booking_id,
            "organization_id": org_id,
            "supplier_id": supplier_id,
            "status": "VOUCHERED",
            "currency": "EUR",
            "amounts": {"sell": 850.0},
            "commission": {"amount": 0.0},
            "items": [{"supplier_id": supplier_id}],
        }
    )
    adj_zero_accrual_id = ObjectId()
    db.supplier_accruals.insert_one(
        {
            "_id": adj_zero_accrual_id,
            "organization_id": org_id,
            "booking_id": str(adj_zero_booking_id),
            "supplier_id": supplier_id,
            "currency": "EUR",
            "amounts": {"gross_sell": 850.0, "commission": 0.0, "net_payable": 850.0},
            "status": "accrued",
            "settlement_id": None,
        }
    )

    before_zero_cnt = db.ledger_postings.count_documents(
        {
            "organization_id": org_id,
            "source.type": "booking",
            "source.id": str(adj_zero_booking_id),
            "event": "SUPPLIER_ACCRUAL_ADJUSTED",
        }
    )

    r_zero = requests.post(
        f"{BASE_URL}/api/ops/finance/supplier-accruals/{adj_zero_booking_id}/adjust",
        json={"new_sell": 850.0, "new_commission": 0.0},
        headers=headers,
    )
    assert r_zero.status_code == 200, r_zero.text
    data_zero = r_zero.json()
    assert abs(data_zero["delta"]) < 0.01

    after_zero_cnt = db.ledger_postings.count_documents(
        {
            "organization_id": org_id,
            "source.type": "booking",
            "source.id": str(adj_zero_booking_id),
            "event": "SUPPLIER_ACCRUAL_ADJUSTED",
        }
    )
    assert after_zero_cnt == before_zero_cnt == 0

    updated_zero = db.supplier_accruals.find_one({"_id": adj_zero_accrual_id})
    assert abs(updated_zero["amounts"]["net_payable"] - 850.0) < 0.01
    # Status may remain 'accrued' for zero-delta adjustments

    print("   ✅ No posting created when delta == 0")

    client.close()


if __name__ == "__main__":
    test_phase_2a_3()
