"""
Finance OS Phase 1.4 - P0 Bug Fix Verification
Tests: Soft limit validation + Payment traceability
"""
import requests
import json

BASE_URL = "http://localhost:8001"


def test_p0_fixes():
    """P0 Bug Fixes: Soft limit validation + Payment traceability"""
    
    print("\n" + "="*80)
    print("FINANCE OS PHASE 1.4 - P0 BUG FIX VERIFICATION")
    print("="*80 + "\n")
    
    # Admin login
    r = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": "admin@acenta.test", "password": "admin123"}
    )
    assert r.status_code == 200
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # Get test agency
    r = requests.get(f"{BASE_URL}/api/ops/finance/credit-profiles", headers=headers)
    profiles = r.json()["items"]
    test_agency_id = profiles[0]["agency_id"] if profiles else None
    assert test_agency_id is not None
    
    # ========================================================================
    # EK KANIT A: Credit Profile Invariant (soft_limit <= limit)
    # ========================================================================
    print("🔴 EK KANIT A: Credit Profile Invariant (soft_limit <= limit)")
    print("-" * 80)
    
    # Test A1: soft_limit > limit → 422 (MUST FAIL)
    print("\n   Test A1: soft_limit > limit → 422 validation_error")
    r = requests.put(
        f"{BASE_URL}/api/ops/finance/credit-profiles/{test_agency_id}",
        json={
            "limit": 10000.0,
            "soft_limit": 11000.0,  # INVALID: > limit
            "payment_terms": "NET14",
            "status": "active"
        },
        headers=headers,
    )
    
    assert r.status_code == 422, f"Expected 422, got {r.status_code}"
    error = r.json()
    assert error["error"]["code"] == "validation_error", f"Wrong error code: {error['error']['code']}"
    assert "soft_limit must be <= limit" in error["error"]["message"], "Wrong error message"
    
    print(f"   ✅ PASS: soft_limit > limit rejected with 422")
    print(f"      Error code: {error['error']['code']}")
    print(f"      Message: {error['error']['message']}")
    
    # Test A2: soft_limit <= limit → 200 (MUST SUCCEED)
    print("\n   Test A2: soft_limit <= limit → 200 OK")
    r = requests.put(
        f"{BASE_URL}/api/ops/finance/credit-profiles/{test_agency_id}",
        json={
            "limit": 10000.0,
            "soft_limit": 9000.0,  # VALID: <= limit (90% threshold)
            "payment_terms": "NET14",
            "status": "active"
        },
        headers=headers,
    )
    
    assert r.status_code == 200, f"Expected 200, got {r.status_code} - {r.text}"
    profile = r.json()
    assert profile["limit"] == 10000.0, "Limit mismatch"
    assert profile["soft_limit"] == 9000.0, "Soft limit mismatch"
    
    print(f"   ✅ PASS: soft_limit <= limit accepted")
    print(f"      Limit: {profile['limit']} EUR")
    print(f"      Soft limit: {profile['soft_limit']} EUR (90% threshold)")
    
    # Test A3: soft_limit = limit → 200 (edge case, MUST SUCCEED)
    print("\n   Test A3: soft_limit = limit → 200 OK (edge case)")
    r = requests.put(
        f"{BASE_URL}/api/ops/finance/credit-profiles/{test_agency_id}",
        json={
            "limit": 10000.0,
            "soft_limit": 10000.0,  # VALID: = limit
            "payment_terms": "NET14",
            "status": "active"
        },
        headers=headers,
    )
    
    assert r.status_code == 200, f"Expected 200, got {r.status_code}"
    profile = r.json()
    assert profile["soft_limit"] == 10000.0, "Soft limit mismatch"
    
    print(f"   ✅ PASS: soft_limit = limit accepted (edge case)")
    print(f"      Soft limit: {profile['soft_limit']} EUR")
    
    print("\n   ✅ KANIT A COMPLETE: Credit profile invariant enforced")
    print("      Rule: soft_limit <= limit ✅")
    print("      Invalid case rejected: soft_limit > limit → 422 ✅")
    print("      Valid case accepted: soft_limit <= limit → 200 ✅")
    
    # ========================================================================
    # EK KANIT B: Payment Traceability
    # ========================================================================
    print("\n" + "="*80)
    print("🔴 EK KANIT B: Payment Traceability")
    print("-" * 80)
    
    # Get agency account
    r = requests.get(f"{BASE_URL}/api/ops/finance/accounts?type=agency", headers=headers)
    accounts = r.json()["items"]
    agency_account = accounts[0] if accounts else None
    assert agency_account is not None
    agency_account_id = agency_account["account_id"]
    
    # Test B1: POST /payments returns payment_id
    print("\n   Test B1: POST /payments returns payment_id")
    r = requests.post(
        f"{BASE_URL}/api/ops/finance/payments",
        json={
            "account_id": agency_account_id,
            "amount": 300.0,
            "currency": "EUR",
            "method": "bank_transfer",
            "reference": "P0-TEST-TRACE-001",
        },
        headers=headers,
    )
    
    assert r.status_code == 201, f"Payment failed: {r.status_code} - {r.text}"
    payment = r.json()
    
    assert "payment_id" in payment, "Missing payment_id"
    assert payment["payment_id"].startswith("pay_"), f"Invalid payment_id format: {payment['payment_id']}"
    assert payment["reference"] == "P0-TEST-TRACE-001", "Reference mismatch"
    
    payment_id = payment["payment_id"]
    
    print(f"   ✅ PASS: Payment created with payment_id")
    print(f"      Payment ID: {payment_id}")
    print(f"      Amount: {payment['amount']} {payment['currency']}")
    print(f"      Reference: {payment['reference']}")
    
    # Test B2: Statement contains source.id = payment_id
    print("\n   Test B2: Statement contains payment with source.id = payment_id")
    r = requests.get(
        f"{BASE_URL}/api/ops/finance/accounts/{agency_account_id}/statement",
        params={"limit": 20},
        headers=headers,
    )
    
    assert r.status_code == 200, f"Statement failed: {r.status_code}"
    statement = r.json()
    
    # Find payment entry
    payment_entries = [
        item for item in statement["items"]
        if item["source"]["type"] == "payment" and item["source"]["id"] == payment_id
    ]
    
    assert len(payment_entries) > 0, f"Payment {payment_id} not found in statement"
    payment_entry = payment_entries[0]
    
    assert payment_entry["event"] == "PAYMENT_RECEIVED", f"Wrong event: {payment_entry['event']}"
    assert payment_entry["direction"] == "credit", f"Wrong direction: {payment_entry['direction']}"
    assert payment_entry["amount"] == 300.0, f"Wrong amount: {payment_entry['amount']}"
    assert payment_entry["source"]["id"] == payment_id, "Source ID mismatch"
    
    print(f"   ✅ PASS: Payment found in statement")
    print(f"      Event: {payment_entry['event']}")
    print(f"      Direction: {payment_entry['direction']}")
    print(f"      Amount: {payment_entry['amount']} EUR")
    print(f"      Source: {payment_entry['source']['type']}/{payment_entry['source']['id']}")
    print(f"      Memo: {payment_entry.get('memo', 'N/A')}")
    
    print("\n   ✅ KANIT B COMPLETE: Payment traceability verified")
    print("      Payment ID returned: ✅")
    print("      Statement source.id matches payment_id: ✅")
    print("      Event = PAYMENT_RECEIVED: ✅")
    print("      Direction = credit: ✅")
    
    # ========================================================================
    # SUMMARY
    # ========================================================================
    print("\n" + "="*80)
    print("✅ P0 BUG FIX VERIFICATION COMPLETE")
    print("="*80)
    print("\n🐛 Bug #1 FIXED: Soft limit validation")
    print("   Old rule: soft_limit >= limit (WRONG)")
    print("   New rule: soft_limit <= limit (CORRECT)")
    print("   Status: ✅ Enforced with 422 validation_error")
    print("\n🐛 Bug #2 VERIFIED: Payment traceability")
    print("   Payment ID: ✅ Returned in response")
    print("   Statement: ✅ Contains source.id = payment_id")
    print("   Event: ✅ PAYMENT_RECEIVED")
    print("   Direction: ✅ credit")
    print("\n🚀 READY FOR PHASE 1.5: Booking Integration")
    print("   Credit check logic will use correct thresholds:")
    print("   - near_limit: exposure >= soft_limit (9000 EUR)")
    print("   - over_limit: exposure >= limit (10000 EUR)")
    print()


if __name__ == "__main__":
    test_p0_fixes()
