"""
Finance OS Phase 1.4 Backend Test
Tests: Statement & Exposure APIs + Manual Payment
"""
import requests
import json
import pymongo
from datetime import datetime, timedelta

BASE_URL = "http://localhost:8001"
MONGO_URL = "mongodb://localhost:27017/"


def test_phase_1_4():
    """Phase 1.4: Statement & Exposure APIs"""
    
    print("\n" + "="*80)
    print("FINANCE OS PHASE 1.4 BACKEND TEST")
    print("="*80 + "\n")
    
    # Setup MongoDB connection
    client = pymongo.MongoClient(MONGO_URL)
    db = client["test_database"]
    
    # Test 1: Health check
    print("1️⃣  Testing backend health...")
    r = requests.get(f"{BASE_URL}/api/health")
    assert r.status_code == 200
    print("   ✅ Backend is healthy\n")
    
    # Test 2: Admin login
    print("2️⃣  Testing admin authentication...")
    r = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": "admin@acenta.test", "password": "admin123"}
    )
    assert r.status_code == 200
    data = r.json()
    token = data["access_token"]
    org_id = data["user"]["organization_id"]
    headers = {"Authorization": f"Bearer {token}"}
    print(f"   ✅ Admin login successful\n")
    
    # Get test accounts
    print("3️⃣  Setting up test accounts...")
    r = requests.get(f"{BASE_URL}/api/ops/finance/accounts", headers=headers)
    accounts = r.json()["items"]
    
    agency_account = next((a for a in accounts if a["type"] == "agency"), None)
    assert agency_account is not None
    
    agency_account_id = agency_account["account_id"]
    print(f"   ✅ Agency account: {agency_account_id}\n")
    
    # ========================================================================
    # TEST 4: STATEMENT - Full list (no date filters)
    # ========================================================================
    print("4️⃣  Testing STATEMENT: Full list (no date filters)...")
    
    r = requests.get(
        f"{BASE_URL}/api/ops/finance/accounts/{agency_account_id}/statement",
        headers=headers,
    )
    assert r.status_code == 200, f"Statement failed: {r.status_code} - {r.text}"
    statement = r.json()
    
    print(f"   ✅ Statement retrieved")
    print(f"      Account: {statement['account_id']}")
    print(f"      Currency: {statement['currency']}")
    print(f"      Opening balance: {statement['opening_balance']} {statement['currency']}")
    print(f"      Closing balance: {statement['closing_balance']} {statement['currency']}")
    print(f"      Items: {len(statement['items'])}")
    
    # Verify structure
    assert "opening_balance" in statement
    assert "closing_balance" in statement
    assert "items" in statement
    
    if statement["items"]:
        first_item = statement["items"][0]
        assert "posted_at" in first_item
        assert "direction" in first_item
        assert "amount" in first_item
        assert "event" in first_item
        assert "source" in first_item
        print(f"   📋 First item: {first_item['event']} {first_item['direction']} {first_item['amount']} {statement['currency']}")
    
    print()
    
    # ========================================================================
    # TEST 5: STATEMENT with from date
    # ========================================================================
    print("5️⃣  Testing STATEMENT: With from date filter...")
    
    # Use current time as from date (should show recent entries only)
    from_date = (datetime.utcnow() - timedelta(hours=1)).isoformat() + "Z"
    
    r = requests.get(
        f"{BASE_URL}/api/ops/finance/accounts/{agency_account_id}/statement",
        params={"from": from_date, "limit": 100},
        headers=headers,
    )
    assert r.status_code == 200
    statement_filtered = r.json()
    
    print(f"   ✅ Statement with from filter retrieved")
    print(f"      From: {from_date}")
    print(f"      Opening balance: {statement_filtered['opening_balance']} EUR")
    print(f"      Closing balance: {statement_filtered['closing_balance']} EUR")
    print(f"      Items: {len(statement_filtered['items'])}")
    print()
    
    # ========================================================================
    # TEST 6: EXPOSURE DASHBOARD
    # ========================================================================
    print("6️⃣  Testing EXPOSURE DASHBOARD...")
    
    r = requests.get(f"{BASE_URL}/api/ops/finance/exposure", headers=headers)
    assert r.status_code == 200, f"Exposure failed: {r.status_code} - {r.text}"
    exposure_data = r.json()
    
    assert "items" in exposure_data
    print(f"   ✅ Exposure dashboard retrieved")
    print(f"      Agencies: {len(exposure_data['items'])}")
    
    if exposure_data["items"]:
        for i, item in enumerate(exposure_data["items"][:3], 1):
            print(f"   📊 Agency {i}: {item['agency_name']}")
            print(f"      Exposure: {item['exposure']} {item['currency']}")
            print(f"      Credit limit: {item['credit_limit']} {item['currency']}")
            if item.get("soft_limit"):
                print(f"      Soft limit: {item['soft_limit']} {item['currency']}")
            print(f"      Payment terms: {item['payment_terms']}")
            print(f"      Status: {item['status']}")
            
            # Verify status calculation
            if item["exposure"] >= item["credit_limit"]:
                assert item["status"] == "over_limit", f"Status should be over_limit, got {item['status']}"
            elif item.get("soft_limit") and item["exposure"] >= item["soft_limit"]:
                assert item["status"] == "near_limit", f"Status should be near_limit, got {item['status']}"
            else:
                assert item["status"] == "ok", f"Status should be ok, got {item['status']}"
            
            print(f"      ✅ Status calculation correct")
    
    print()
    
    # ========================================================================
    # TEST 7: MANUAL PAYMENT
    # ========================================================================
    print("7️⃣  Testing MANUAL PAYMENT: Payment entry + balance update...")
    
    # Get balance before payment
    before_balance = db.account_balances.find_one({
        "account_id": agency_account_id,
        "currency": "EUR"
    })
    balance_before = before_balance["balance"] if before_balance else 0.0
    print(f"   📊 Balance before payment: {balance_before} EUR")
    
    # Create payment
    payment_payload = {
        "account_id": agency_account_id,
        "amount": 200.0,
        "currency": "EUR",
        "method": "bank_transfer",
        "reference": "TEST-PAYMENT-001",
    }
    
    r = requests.post(
        f"{BASE_URL}/api/ops/finance/payments",
        json=payment_payload,
        headers=headers,
    )
    assert r.status_code == 201, f"Payment failed: {r.status_code} - {r.text}"
    payment = r.json()
    
    print(f"   ✅ Payment created: {payment['payment_id']}")
    print(f"      Amount: {payment['amount']} {payment['currency']}")
    print(f"      Method: {payment['method']}")
    print(f"      Reference: {payment['reference']}")
    
    # Verify balance decreased
    after_balance = db.account_balances.find_one({
        "account_id": agency_account_id,
        "currency": "EUR"
    })
    balance_after = after_balance["balance"]
    
    expected_balance = balance_before - 200.0
    assert abs(balance_after - expected_balance) < 0.01, \
        f"Balance mismatch: expected {expected_balance}, got {balance_after}"
    
    print(f"   📊 Balance after payment: {balance_after} EUR (Δ -200.0)")
    print(f"   ✅ Balance updated correctly\n")
    
    # ========================================================================
    # TEST 8: PAYMENT appears in STATEMENT
    # ========================================================================
    print("8️⃣  Testing PAYMENT appears in STATEMENT...")
    
    r = requests.get(
        f"{BASE_URL}/api/ops/finance/accounts/{agency_account_id}/statement",
        params={"limit": 10},
        headers=headers,
    )
    assert r.status_code == 200
    statement = r.json()
    
    # Find PAYMENT_RECEIVED event
    payment_entries = [
        item for item in statement["items"]
        if item["event"] == "PAYMENT_RECEIVED" and item["source"]["id"] == payment["payment_id"]
    ]
    
    assert len(payment_entries) > 0, "Payment not found in statement"
    payment_entry = payment_entries[0]
    
    print(f"   ✅ Payment found in statement")
    print(f"      Event: {payment_entry['event']}")
    print(f"      Direction: {payment_entry['direction']}")
    print(f"      Amount: {payment_entry['amount']} EUR")
    print(f"      Source: {payment_entry['source']['type']}/{payment_entry['source']['id']}")
    print()
    
    # ========================================================================
    # TEST 9: NEGATIVE CASES
    # ========================================================================
    print("9️⃣  Testing NEGATIVE CASES...")
    
    # Invalid account ID
    r = requests.get(
        f"{BASE_URL}/api/ops/finance/accounts/invalid_account/statement",
        headers=headers,
    )
    assert r.status_code == 404, f"Expected 404 for invalid account, got {r.status_code}"
    error = r.json()
    assert error["error"]["code"] == "account_not_found"
    print(f"   ✅ Invalid account → 404 account_not_found")
    
    # Amount <= 0
    r = requests.post(
        f"{BASE_URL}/api/ops/finance/payments",
        json={
            "account_id": agency_account_id,
            "amount": -100.0,
            "currency": "EUR",
            "method": "bank_transfer",
            "reference": "INVALID",
        },
        headers=headers,
    )
    assert r.status_code == 422, f"Expected 422 for amount <= 0, got {r.status_code}"
    error = r.json()
    assert error["error"]["code"] == "validation_error"
    print(f"   ✅ Amount <= 0 → 422 validation_error")
    print()
    
    print("="*80)
    print("✅ PHASE 1.4 TEST COMPLETE - ALL CHECKS PASSED")
    print("="*80)
    print("\n📊 Summary:")
    print("   - Statement full list ✅")
    print("   - Statement with from date ✅")
    print("   - Exposure dashboard ✅")
    print("   - Manual payment ✅")
    print("   - Payment in statement ✅")
    print("   - Negative cases (404, 422) ✅")
    print("\n🎯 Phase 1.4 deliverables:")
    print("   ✅ Statement API (opening/closing balance)")
    print("   ✅ Exposure dashboard (risk monitoring)")
    print("   ✅ Manual payment (ops entry)")
    print("   ✅ Payment → ledger integration")
    print("\n📈 Statement Example:")
    print(f"   Opening: {statement['opening_balance']} EUR")
    print(f"   Closing: {statement['closing_balance']} EUR")
    print(f"   Items: {len(statement['items'])}")
    print("\n🚨 Exposure Status Examples:")
    if exposure_data["items"]:
        for item in exposure_data["items"][:2]:
            print(f"   {item['agency_name']}: {item['status']} (exposure={item['exposure']} EUR)")
    print("\n💰 Payment Snapshot:")
    print(f"   Before: {balance_before} EUR")
    print(f"   Payment: -200.0 EUR")
    print(f"   After: {balance_after} EUR")
    print("\n🚀 Ready for Phase 1.5: Booking Integration\n")
    
    # Cleanup
    client.close()


if __name__ == "__main__":
    test_phase_1_4()
