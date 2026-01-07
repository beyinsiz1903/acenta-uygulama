#!/usr/bin/env python3
"""
Finance OS Phase 2B.4 Booking Financials Backend Test
Focused regression test for refund approval and booking_financials integration
"""

import requests
import pymongo
from bson import ObjectId
from datetime import datetime
import json

# Configuration
BASE_URL = "http://localhost:8001"
MONGO_URL = "mongodb://localhost:27017/"
DATABASE_NAME = "test_database"

def login_admin():
    """Login as admin and return token, org_id, email"""
    r = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": "admin@acenta.test", "password": "admin123"},
    )
    assert r.status_code == 200, f"Login failed: {r.text}"
    data = r.json()
    return data["access_token"], data["user"]["organization_id"], data["user"]["email"]

def test_refund_approval_booking_financials():
    """Test refund approval via /api/ops/finance/refunds/{case_id}/approve updates booking_financials"""
    print("\n" + "=" * 80)
    print("FINANCE OS PHASE 2B.4 FOCUSED BACKEND REGRESSION TEST")
    print("Testing refund approval and booking_financials integration")
    print("=" * 80 + "\n")

    # Setup
    client = pymongo.MongoClient(MONGO_URL)
    db = client[DATABASE_NAME]
    token, org_id, admin_email = login_admin()
    headers = {"Authorization": f"Bearer {token}"}

    print(f"✅ Admin login successful: {admin_email}")
    print(f"✅ Organization ID: {org_id}")
    print(f"✅ Database: {DATABASE_NAME}")

    # ------------------------------------------------------------------
    # Test 1: Verify refund approval updates booking_financials
    # ------------------------------------------------------------------
    print("\n1️⃣  Testing refund approval updates booking_financials...")

    # Create test booking
    booking_id = ObjectId()
    agency_id = f"test_agency_{ObjectId()}"
    
    # Create agency first
    db.agencies.insert_one({
        "_id": agency_id,
        "organization_id": org_id,
        "name": "Test Agency for Refund",
        "status": "active"
    })

    # Create booking
    db.bookings.insert_one({
        "_id": booking_id,
        "organization_id": org_id,
        "agency_id": agency_id,
        "status": "CONFIRMED",
        "currency": "EUR",
        "amounts": {"sell": 1000.0},
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    })

    # Create refund case
    from app.services.refund_calculator import RefundCalculatorService
    calc = RefundCalculatorService(currency="EUR")
    booking = db.bookings.find_one({"_id": booking_id})
    comp = calc.compute_refund(
        booking,
        datetime.utcnow(),
        mode="policy_first",
        manual_requested_amount=400.0,
    )

    case_id = ObjectId()
    now = datetime.utcnow()
    db.refund_cases.insert_one({
        "_id": case_id,
        "organization_id": org_id,
        "type": "refund",
        "booking_id": str(booking_id),
        "agency_id": agency_id,
        "status": "open",
        "reason": "customer_request",
        "currency": "EUR",
        "requested": {"amount": 400.0, "message": "Test refund"},
        "computed": {
            "gross_sell": comp.gross_sell,
            "penalty": comp.penalty,
            "refundable": comp.refundable,
            "basis": comp.basis,
            "policy_ref": comp.policy_ref,
        },
        "decision": None,
        "approved": {"amount": None},
        "ledger_posting_id": None,
        "booking_financials_id": None,
        "created_at": now,
        "updated_at": now,
        "decision_by_email": None,
        "decision_at": None,
    })

    # Get initial booking_financials state
    r_initial = requests.get(
        f"{BASE_URL}/api/ops/finance/bookings/{booking_id}/financials",
        headers=headers,
    )
    assert r_initial.status_code == 200, f"Failed to get initial financials: {r_initial.text}"
    initial_financials = r_initial.json()
    
    print(f"   📊 Initial booking_financials:")
    print(f"      sell_total: {initial_financials['sell_total']}")
    print(f"      refunded_total: {initial_financials['refunded_total']}")
    print(f"      penalty_total: {initial_financials['penalty_total']}")
    print(f"      refunds_applied: {len(initial_financials['refunds_applied'])}")

    # Approve refund
    r_approve = requests.post(
        f"{BASE_URL}/api/ops/finance/refunds/{case_id}/approve",
        json={"approved_amount": 400.0},
        headers=headers,
    )
    assert r_approve.status_code == 200, f"Refund approval failed: {r_approve.text}"
    approve_response = r_approve.json()
    
    print(f"   ✅ Refund approval successful")

    # Verify booking_financials updated
    r_updated = requests.get(
        f"{BASE_URL}/api/ops/finance/bookings/{booking_id}/financials",
        headers=headers,
    )
    assert r_updated.status_code == 200, f"Failed to get updated financials: {r_updated.text}"
    updated_financials = r_updated.json()
    
    print(f"   📊 Updated booking_financials:")
    print(f"      sell_total: {updated_financials['sell_total']}")
    print(f"      refunded_total: {updated_financials['refunded_total']}")
    print(f"      penalty_total: {updated_financials['penalty_total']}")
    print(f"      refunds_applied: {len(updated_financials['refunds_applied'])}")

    # Verify the updates
    assert abs(updated_financials["sell_total"] - 1000.0) < 0.01, "sell_total should remain 1000.0"
    assert abs(updated_financials["refunded_total"] - 400.0) < 0.01, "refunded_total should be 400.0"
    assert abs(updated_financials["penalty_total"] - 600.0) < 0.01, "penalty_total should be 600.0"
    assert len(updated_financials["refunds_applied"]) == 1, "Should have 1 refund applied"
    
    refund_applied = updated_financials["refunds_applied"][0]
    assert refund_applied["refund_case_id"] == str(case_id), "refund_case_id should match"
    assert abs(refund_applied["amount"] - 400.0) < 0.01, "Applied amount should be 400.0"
    
    print("   ✅ booking_financials correctly updated after refund approval")

    # ------------------------------------------------------------------
    # Test 2: Verify idempotency - repeated approve returns 409
    # ------------------------------------------------------------------
    print("\n2️⃣  Testing idempotency: repeated approve on same refund case...")

    # Store current state
    before_retry = updated_financials.copy()

    # Try to approve the same case again
    r_retry = requests.post(
        f"{BASE_URL}/api/ops/finance/refunds/{case_id}/approve",
        json={"approved_amount": 400.0},
        headers=headers,
    )
    
    print(f"   📋 Retry response status: {r_retry.status_code}")
    
    # Should return 409 invalid_case_state
    assert r_retry.status_code == 409, f"Expected 409, got {r_retry.status_code}: {r_retry.text}"
    retry_response = r_retry.json()
    assert retry_response.get("error", {}).get("code") == "invalid_case_state", "Should return invalid_case_state error"
    
    print("   ✅ Repeated approve correctly returns 409 invalid_case_state")

    # Verify booking_financials unchanged
    r_after_retry = requests.get(
        f"{BASE_URL}/api/ops/finance/bookings/{booking_id}/financials",
        headers=headers,
    )
    assert r_after_retry.status_code == 200, f"Failed to get financials after retry: {r_after_retry.text}"
    after_retry_financials = r_after_retry.json()
    
    # Compare all key fields
    assert abs(after_retry_financials["refunded_total"] - before_retry["refunded_total"]) < 0.01, "refunded_total should be unchanged"
    assert abs(after_retry_financials["penalty_total"] - before_retry["penalty_total"]) < 0.01, "penalty_total should be unchanged"
    assert len(after_retry_financials["refunds_applied"]) == len(before_retry["refunds_applied"]), "refunds_applied count should be unchanged"
    
    print("   ✅ booking_financials unchanged after retry (idempotent)")

    # ------------------------------------------------------------------
    # Test 3: Verify direct apply_refund_approved idempotency
    # ------------------------------------------------------------------
    print("\n3️⃣  Testing direct apply_refund_approved idempotency...")

    # Test direct service call with same refund_case_id
    import anyio
    from app.services.booking_financials import BookingFinancialsService
    from app.db import get_db

    async def test_direct_idempotency():
        db_async = await get_db()
        svc = BookingFinancialsService(db_async)
        
        # Call apply_refund_approved with same refund_case_id
        result = await svc.apply_refund_approved(
            organization_id=org_id,
            booking_id=str(booking_id),
            refund_case_id=str(case_id),  # Same case_id as before
            ledger_posting_id="test_posting_id",
            approved_amount=400.0,
            applied_at=datetime.utcnow(),
        )
        return result

    # This should be a no-op since the refund_case_id already exists
    direct_result = anyio.run(test_direct_idempotency)
    
    # Verify still only 1 refund applied
    r_final = requests.get(
        f"{BASE_URL}/api/ops/finance/bookings/{booking_id}/financials",
        headers=headers,
    )
    assert r_final.status_code == 200, f"Failed to get final financials: {r_final.text}"
    final_financials = r_final.json()
    
    assert len(final_financials["refunds_applied"]) == 1, "Should still have only 1 refund applied"
    assert abs(final_financials["refunded_total"] - 400.0) < 0.01, "refunded_total should still be 400.0"
    
    print("   ✅ Direct apply_refund_approved with same refund_case_id is no-op (idempotent)")

    # ------------------------------------------------------------------
    # Test 4: Test multiple different refunds accumulate correctly
    # ------------------------------------------------------------------
    print("\n4️⃣  Testing multiple different refunds accumulate correctly...")

    # Create second refund case for same booking
    case2_id = ObjectId()
    comp2 = calc.compute_refund(
        booking,
        datetime.utcnow(),
        mode="policy_first",
        manual_requested_amount=200.0,
    )

    db.refund_cases.insert_one({
        "_id": case2_id,
        "organization_id": org_id,
        "type": "refund",
        "booking_id": str(booking_id),
        "agency_id": agency_id,
        "status": "open",
        "reason": "customer_request",
        "currency": "EUR",
        "requested": {"amount": 200.0, "message": "Second refund"},
        "computed": {
            "gross_sell": comp2.gross_sell,
            "penalty": comp2.penalty,
            "refundable": comp2.refundable,
            "basis": comp2.basis,
            "policy_ref": comp2.policy_ref,
        },
        "decision": None,
        "approved": {"amount": None},
        "ledger_posting_id": None,
        "booking_financials_id": None,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        "decision_by_email": None,
        "decision_at": None,
    })

    # Approve second refund
    r_approve2 = requests.post(
        f"{BASE_URL}/api/ops/finance/refunds/{case2_id}/approve",
        json={"approved_amount": 200.0},
        headers=headers,
    )
    assert r_approve2.status_code == 200, f"Second refund approval failed: {r_approve2.text}"

    # Verify accumulation
    r_accumulated = requests.get(
        f"{BASE_URL}/api/ops/finance/bookings/{booking_id}/financials",
        headers=headers,
    )
    assert r_accumulated.status_code == 200, f"Failed to get accumulated financials: {r_accumulated.text}"
    accumulated_financials = r_accumulated.json()
    
    print(f"   📊 Accumulated booking_financials:")
    print(f"      sell_total: {accumulated_financials['sell_total']}")
    print(f"      refunded_total: {accumulated_financials['refunded_total']}")
    print(f"      penalty_total: {accumulated_financials['penalty_total']}")
    print(f"      refunds_applied: {len(accumulated_financials['refunds_applied'])}")

    # Verify accumulation
    assert abs(accumulated_financials["sell_total"] - 1000.0) < 0.01, "sell_total should remain 1000.0"
    assert abs(accumulated_financials["refunded_total"] - 600.0) < 0.01, "refunded_total should be 600.0 (400+200)"
    assert abs(accumulated_financials["penalty_total"] - 400.0) < 0.01, "penalty_total should be 400.0 (1000-600)"
    assert len(accumulated_financials["refunds_applied"]) == 2, "Should have 2 refunds applied"
    
    print("   ✅ Multiple refunds correctly accumulated")

    # Cleanup
    client.close()
    
    print("\n" + "=" * 80)
    print("✅ ALL TESTS PASSED - Finance OS Phase 2B.4 booking_financials working correctly")
    print("✅ Refund approval via /api/ops/finance/refunds/{case_id}/approve updates booking_financials")
    print("✅ Idempotency verified: repeated approve returns 409 and doesn't change booking_financials")
    print("✅ Direct apply_refund_approved with same refund_case_id is no-op")
    print("✅ Multiple refunds accumulate correctly")
    print("=" * 80 + "\n")

if __name__ == "__main__":
    test_refund_approval_booking_financials()