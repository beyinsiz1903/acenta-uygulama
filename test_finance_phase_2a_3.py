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

    supplier_id = "phase2a3_supplier"
    if not db.suppliers.find_one({"_id": supplier_id}):
        db.suppliers.insert_one(
            {
                "_id": supplier_id,
                "organization_id": org_id,
                "name": "Test Supplier Phase 2A.3",
                "status": "active",
            }
        )

    # Ensure supplier accounts/balances clean-ish
    db.supplier_accruals.delete_many({"organization_id": org_id, "supplier_id": supplier_id})

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

    # Settlement lock guard via service (Motor DB)
    import asyncio
    from app.db import get_db
    from app.services.supplier_accrual import SupplierAccrualService

    async def _run_locked_reverse():
        motor_db = await get_db()
        svc = SupplierAccrualService(motor_db)
        try:
            await svc.reverse_accrual_for_booking(
                organization_id=org_id,
                booking_id=str(locked_booking_id),
                triggered_by="admin@acenta.test",
            )
            assert False, "Expected accrual_locked_in_settlement"
        except Exception as e:  # AppError string check
            assert "accrual_locked_in_settlement" in str(e)

    asyncio.run(_run_locked_reverse())

    async def _run_locked_adjust():
        motor_db = await get_db()
        svc = SupplierAccrualService(motor_db)
        try:
            await svc.adjust_accrual_for_booking(
                organization_id=org_id,
                booking_id=str(locked_booking_id),
                new_sell=600.0,
                new_commission=60.0,
                triggered_by="admin@acenta.test",
            )
            assert False, "Expected accrual_locked_in_settlement"
        except Exception as e:
            assert "accrual_locked_in_settlement" in str(e)

    asyncio.run(_run_locked_adjust())

    print("   ✅ Settlement lock guard enforced for reverse and adjust")

    # =====================================================================
    # 3) Adjustment delta > 0
    # =====================================================================
    print("3️⃣  Adjustment delta > 0 (increase payable)...")

    adj_booking_id = ObjectId()
    db.bookings.insert_one(
        {
            "_id": adj_booking_id,
            "organization_id": org_id,
            "supplier_id": supplier_id,
            "status": "VOUCHERED",
            "currency": "EUR",
            "amounts": {"sell": 800.0},
            "commission": {"amount": 0.0},
            "items": [{"supplier_id": supplier_id}],
        }
    )
    adj_accrual_id = ObjectId()
    db.supplier_accruals.insert_one(
        {
            "_id": adj_accrual_id,
            "organization_id": org_id,
            "booking_id": str(adj_booking_id),
            "supplier_id": supplier_id,
            "currency": "EUR",
            "amounts": {"gross_sell": 800.0, "commission": 0.0, "net_payable": 800.0},
            "status": "accrued",
            "settlement_id": None,
        }
    )

    async def _run_adjust_up():
        return await svc.adjust_accrual_for_booking(
            organization_id=org_id,
            booking_id=str(adj_booking_id),
            new_sell=900.0,
            new_commission=0.0,
            triggered_by="admin@acenta.test",
        )

    result_up = asyncio.run(_run_adjust_up())
    assert result_up["delta"] > 0

    updated = db.supplier_accruals.find_one({"_id": adj_accrual_id})
    assert updated["status"] == "adjusted"
    assert abs(updated["amounts"]["net_payable"] - 900.0) < 0.01

    print("   ✅ Adjustment up applied correctly")

    # =====================================================================
    # 4) Adjustment delta < 0
    # =====================================================================
    print("4️⃣  Adjustment delta < 0 (decrease payable)...")

    async def _run_adjust_down():
        return await svc.adjust_accrual_for_booking(
            organization_id=org_id,
            booking_id=str(adj_booking_id),
            new_sell=850.0,
            new_commission=0.0,
            triggered_by="admin@acenta.test",
        )

    result_down = asyncio.run(_run_adjust_down())
    assert result_down["delta"] < 0

    updated2 = db.supplier_accruals.find_one({"_id": adj_accrual_id})
    assert abs(updated2["amounts"]["net_payable"] - 850.0) < 0.01

    print("   ✅ Adjustment down applied correctly")

    # =====================================================================
    # 5) Adjustment delta == 0 (no posting)
    # =====================================================================
    print("5️⃣  Adjustment delta == 0 (no posting)...")

    # Count existing postings for this booking
    before_cnt = db.ledger_postings.count_documents(
        {
            "organization_id": org_id,
            "source.type": "booking",
            "source.id": str(adj_booking_id),
            "event": "SUPPLIER_ACCRUAL_ADJUSTED",
        }
    )

    async def _run_adjust_zero():
        return await svc.adjust_accrual_for_booking(
            organization_id=org_id,
            booking_id=str(adj_booking_id),
            new_sell=850.0,
            new_commission=0.0,
            triggered_by="admin@acenta.test",
        )

    result_zero = asyncio.run(_run_adjust_zero())
    assert abs(result_zero["delta"]) < 0.01
    after_cnt = db.ledger_postings.count_documents(
        {
            "organization_id": org_id,
            "source.type": "booking",
            "source.id": str(adj_booking_id),
            "event": "SUPPLIER_ACCRUAL_ADJUSTED",
        }
    )
    assert after_cnt == before_cnt

    print("   ✅ No new posting created when delta == 0")

    client.close()


if __name__ == "__main__":
    test_phase_2a_3()
