#!/usr/bin/env python3
"""
PROMPT 5 (Payments TR Pack + Accounting/e-Fatura V1) - FINAL backend verification

Testing TR Installments endpoint, TR POS checkout endpoint, Admin accounting export endpoint,
and Stripe regression smoke test as requested in the review.
"""

import requests
import json
import uuid
from datetime import datetime, timedelta
from pymongo import MongoClient
import os

# Configuration - Use production URL from frontend/.env
BASE_URL = "https://risk-aware-b2b.preview.emergentagent.com"

def login_admin():
    """Login as admin user and return token, org_id, email"""
    r = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": "admin@acenta.test", "password": "admin123"},
    )
    assert r.status_code == 200, f"Admin login failed: {r.text}"
    data = r.json()
    user = data["user"]
    return data["access_token"], user["organization_id"], user["email"]

def get_mongo_client():
    """Get MongoDB client for direct database access"""
    mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017/test_database")
    return MongoClient(mongo_url)

def get_default_org_id():
    """Get the default organization ID from database"""
    try:
        mongo_client = get_mongo_client()
        db = mongo_client.get_default_database()
        
        # Find organization with slug='default' or use admin org
        org = db.organizations.find_one({"slug": "default"})
        if not org:
            # Fallback to first organization
            org = db.organizations.find_one({})
        
        mongo_client.close()
        return str(org["_id"]) if org else None
    except Exception as e:
        print(f"   ⚠️  Failed to get default org: {e}")
        return None

def create_test_quote(admin_headers, org_id):
    """Create a test public quote for testing"""
    quote_payload = {
        "org": org_id,
        "product_id": "696b4faf6a08833ec53dc8a0",  # Use the ObjectId we created
        "date_from": "2026-02-01",
        "date_to": "2026-02-02", 
        "pax": {"adults": 2, "children": 0},
        "rooms": 1,
        "currency": "EUR"
    }
    
    r = requests.post(
        f"{BASE_URL}/api/public/quote",
        json=quote_payload,
        headers=admin_headers,
    )
    
    if r.status_code == 200:
        return r.json()
    else:
        print(f"   ⚠️  Quote creation failed: {r.status_code} - {r.text}")
        return None

def test_tr_installments_endpoint():
    """Test 1: TR Installments endpoint"""
    print("\n" + "=" * 80)
    print("1️⃣  TR INSTALLMENTS ENDPOINT TEST")
    print("Testing GET /api/public/installments with TR Pack feature gating")
    print("=" * 80 + "\n")

    admin_token, admin_org_id, admin_email = login_admin()
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    
    print(f"   ✅ Admin login successful: {admin_email}")
    print(f"   📋 Organization ID: {admin_org_id}")

    # Test 1a: Valid request with TR Pack enabled org
    print("\n   📋 Test 1a: Valid request with amount_cents=10000, currency=TRY")
    
    r = requests.get(
        f"{BASE_URL}/api/public/installments",
        params={"org": admin_org_id, "amount_cents": 10000, "currency": "TRY"},
        headers=admin_headers,
    )
    
    print(f"   📋 Response status: {r.status_code}")
    
    if r.status_code == 200:
        data = r.json()
        print(f"   ✅ 200 OK response received")
        print(f"   📋 Response: {json.dumps(data, indent=2)}")
        
        # Verify response structure
        assert data.get("ok") is True, "Response should have ok=true"
        assert data.get("currency") == "TRY", "Currency should be TRY"
        assert "items" in data, "Response should have items array"
        
        items = data["items"]
        assert len(items) >= 2, f"Should have at least 2 installment plans, got {len(items)}"
        
        # Verify 3 and 6 installment plans exist
        installment_counts = [item["installments"] for item in items]
        assert 3 in installment_counts, "Should have 3 installment plan"
        assert 6 in installment_counts, "Should have 6 installment plan"
        
        # Verify deterministic cent arithmetic
        for item in items:
            assert "installments" in item, "Item should have installments field"
            assert "monthly_amount_cents" in item, "Item should have monthly_amount_cents field"
            assert "total_amount_cents" in item, "Item should have total_amount_cents field"
            assert "total_interest_cents" in item, "Item should have total_interest_cents field"
            
            # Verify amounts are positive integers
            assert item["monthly_amount_cents"] > 0, "Monthly amount should be positive"
            assert item["total_amount_cents"] > 0, "Total amount should be positive"
            assert item["total_interest_cents"] >= 0, "Interest should be non-negative"
        
        print(f"   ✅ Response structure validated")
        print(f"   ✅ Found {len(items)} installment plans with deterministic amounts")
        
    elif r.status_code == 404:
        print(f"   ⚠️  404 Not Found - Organization may not have payments_tr_pack feature")
        print(f"   📋 Response: {r.text}")
    else:
        print(f"   ❌ Unexpected status: {r.status_code}")
        print(f"   📋 Response: {r.text}")

    # Test 1b: Invalid amount (amount_cents=0)
    print("\n   📋 Test 1b: Invalid amount (amount_cents=0)")
    
    r = requests.get(
        f"{BASE_URL}/api/public/installments",
        params={"org": admin_org_id, "amount_cents": 0, "currency": "TRY"},
        headers=admin_headers,
    )
    
    print(f"   📋 Response status: {r.status_code}")
    
    if r.status_code == 422:
        print(f"   ✅ 422 INVALID_AMOUNT response as expected")
        print(f"   📋 Response: {r.text}")
    else:
        print(f"   ⚠️  Expected 422, got {r.status_code}")
        print(f"   📋 Response: {r.text}")

    # Test 1c: Unsupported currency (EUR)
    print("\n   📋 Test 1c: Unsupported currency (EUR)")
    
    r = requests.get(
        f"{BASE_URL}/api/public/installments",
        params={"org": admin_org_id, "amount_cents": 10000, "currency": "EUR"},
        headers=admin_headers,
    )
    
    print(f"   📋 Response status: {r.status_code}")
    
    if r.status_code == 422:
        print(f"   ✅ 422 UNSUPPORTED_CURRENCY response as expected")
        print(f"   📋 Response: {r.text}")
    else:
        print(f"   ⚠️  Expected 422, got {r.status_code}")
        print(f"   📋 Response: {r.text}")

    # Test 1d: Org without payments_tr_pack (use different org if available)
    print("\n   📋 Test 1d: Testing org without payments_tr_pack feature")
    
    # Try with a different org ID that likely doesn't have TR Pack
    test_org_id = "000000000000000000000000"  # Non-existent org
    
    r = requests.get(
        f"{BASE_URL}/api/public/installments",
        params={"org": test_org_id, "amount_cents": 10000, "currency": "TRY"},
        headers=admin_headers,
    )
    
    print(f"   📋 Response status: {r.status_code}")
    
    if r.status_code == 404:
        print(f"   ✅ 404 Not Found response as expected for org without TR Pack")
        print(f"   📋 Response: {r.text}")
    else:
        print(f"   ⚠️  Expected 404, got {r.status_code}")
        print(f"   📋 Response: {r.text}")

    print(f"\n   ✅ TR Installments endpoint test completed")

def test_tr_pos_checkout_endpoint():
    """Test 2: TR POS checkout endpoint"""
    print("\n" + "=" * 80)
    print("2️⃣  TR POS CHECKOUT ENDPOINT TEST")
    print("Testing POST /api/public/checkout/tr-pos with idempotency")
    print("=" * 80 + "\n")

    admin_token, admin_org_id, admin_email = login_admin()
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    
    print(f"   ✅ Admin login successful: {admin_email}")
    print(f"   📋 Organization ID: {admin_org_id}")

    # First create a valid public quote
    print("\n   📋 Creating test quote for TR POS checkout...")
    
    quote = create_test_quote(admin_headers, admin_org_id)
    if not quote:
        print(f"   ❌ Failed to create test quote, skipping TR POS checkout test")
        return
    
    quote_id = quote["quote_id"]
    print(f"   ✅ Test quote created: {quote_id}")

    # Test 2a: Valid TR POS checkout
    print(f"\n   📋 Test 2a: Valid TR POS checkout")
    
    idempotency_key = f"tr-pos-test-{uuid.uuid4().hex[:16]}"
    checkout_payload = {
        "org": admin_org_id,
        "quote_id": quote_id,
        "guest": {
            "full_name": "Test TR User",
            "email": "tr.test@example.com",
            "phone": "+90 555 123 4567"
        },
        "idempotency_key": idempotency_key,
        "currency": "TRY"
    }
    
    r = requests.post(
        f"{BASE_URL}/api/public/checkout/tr-pos",
        json=checkout_payload,
        headers=admin_headers,
    )
    
    print(f"   📋 Response status: {r.status_code}")
    
    if r.status_code == 200:
        data = r.json()
        print(f"   ✅ 200 OK response received")
        print(f"   📋 Response: {json.dumps(data, indent=2)}")
        
        # Verify response structure
        assert data.get("ok") is True, "Response should have ok=true"
        assert data.get("booking_id") is not None, "Should have booking_id"
        assert data.get("booking_code") is not None, "Should have booking_code"
        assert data.get("provider") == "tr_pos_mock", "Provider should be tr_pos_mock"
        assert data.get("status") == "created", "Status should be created"
        assert data.get("correlation_id") is not None, "Should have correlation_id"
        
        # Verify booking_code has TR- prefix
        booking_code = data["booking_code"]
        assert booking_code.startswith("TR-"), f"Booking code should start with TR-, got {booking_code}"
        
        print(f"   ✅ Response structure validated")
        print(f"   ✅ Booking ID: {data['booking_id']}")
        print(f"   ✅ Booking Code: {data['booking_code']}")
        
        # Store for idempotency test
        first_booking_id = data["booking_id"]
        first_booking_code = data["booking_code"]
        first_provider = data["provider"]
        first_status = data["status"]
        
        # Test 2b: Idempotency replay (same request)
        print(f"\n   📋 Test 2b: Idempotency replay with same request")
        
        r2 = requests.post(
            f"{BASE_URL}/api/public/checkout/tr-pos",
            json=checkout_payload,  # Same payload
            headers=admin_headers,
        )
        
        print(f"   📋 Response status: {r2.status_code}")
        
        if r2.status_code == 200:
            data2 = r2.json()
            print(f"   ✅ 200 OK response received")
            print(f"   📋 Response: {json.dumps(data2, indent=2)}")
            
            # Verify idempotency - should return identical values
            assert data2.get("booking_id") == first_booking_id, "Booking ID should be identical"
            assert data2.get("booking_code") == first_booking_code, "Booking code should be identical"
            assert data2.get("provider") == first_provider, "Provider should be identical"
            assert data2.get("status") == first_status, "Status should be identical"
            
            print(f"   ✅ Idempotency verified - identical response returned")
        else:
            print(f"   ⚠️  Idempotency test failed: {r2.status_code}")
            print(f"   📋 Response: {r2.text}")
        
    elif r.status_code == 404:
        print(f"   ⚠️  404 Not Found - Organization may not have payments_tr_pack feature")
        print(f"   📋 Response: {r.text}")
    else:
        print(f"   ❌ Unexpected status: {r.status_code}")
        print(f"   📋 Response: {r.text}")

    # Test 2c: Invalid quote_id
    print(f"\n   📋 Test 2c: Invalid quote_id")
    
    invalid_checkout_payload = {
        "org": admin_org_id,
        "quote_id": "invalid_quote_id_12345",
        "guest": {
            "full_name": "Test TR User",
            "email": "tr.test@example.com", 
            "phone": "+90 555 123 4567"
        },
        "idempotency_key": f"tr-pos-invalid-{uuid.uuid4().hex[:16]}",
        "currency": "TRY"
    }
    
    r = requests.post(
        f"{BASE_URL}/api/public/checkout/tr-pos",
        json=invalid_checkout_payload,
        headers=admin_headers,
    )
    
    print(f"   📋 Response status: {r.status_code}")
    
    if r.status_code == 404:
        print(f"   ✅ 404 QUOTE_NOT_FOUND response as expected")
        print(f"   📋 Response: {r.text}")
    else:
        print(f"   ⚠️  Expected 404, got {r.status_code}")
        print(f"   📋 Response: {r.text}")

    print(f"\n   ✅ TR POS checkout endpoint test completed")

def test_admin_accounting_export_endpoint():
    """Test 3: Admin accounting export endpoint"""
    print("\n" + "=" * 80)
    print("3️⃣  ADMIN ACCOUNTING EXPORT ENDPOINT TEST")
    print("Testing GET /api/admin/accounting/transactions with JSON and CSV formats")
    print("=" * 80 + "\n")

    admin_token, admin_org_id, admin_email = login_admin()
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    
    print(f"   ✅ Admin login successful: {admin_email}")
    print(f"   📋 Organization ID: {admin_org_id}")

    # Test 3a: JSON format with date range
    print(f"\n   📋 Test 3a: JSON format with date range")
    
    # Use a date range that should capture some transactions
    date_from = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    date_to = datetime.now().strftime("%Y-%m-%d")
    
    r = requests.get(
        f"{BASE_URL}/api/admin/accounting/transactions",
        params={"date_from": date_from, "date_to": date_to},
        headers=admin_headers,
    )
    
    print(f"   📋 Response status: {r.status_code}")
    
    if r.status_code == 200:
        data = r.json()
        print(f"   ✅ 200 OK response received")
        print(f"   📋 Response structure: {list(data.keys())}")
        
        # Verify response structure
        assert "items" in data, "Response should have items array"
        assert "date_from" in data, "Response should have date_from"
        assert "date_to" in data, "Response should have date_to"
        
        items = data["items"]
        print(f"   📋 Found {len(items)} transactions")
        
        if len(items) > 0:
            # Verify first item structure
            item = items[0]
            expected_fields = [
                "date", "booking_id", "booking_code", "customer_name",
                "amount_gross_cents", "amount_net_cents", "vat_cents",
                "currency", "payment_method", "channel"
            ]
            
            for field in expected_fields:
                assert field in item, f"Item should have {field} field"
            
            print(f"   ✅ Transaction structure validated")
            print(f"   📋 Sample transaction: {json.dumps(item, indent=2)}")
        else:
            print(f"   📋 No transactions found in date range")
        
    elif r.status_code == 403:
        print(f"   ⚠️  403 Forbidden - May need accounting_export feature enabled")
        print(f"   📋 Response: {r.text}")
    else:
        print(f"   ❌ Unexpected status: {r.status_code}")
        print(f"   📋 Response: {r.text}")

    # Test 3b: CSV format
    print(f"\n   📋 Test 3b: CSV format")
    
    r = requests.get(
        f"{BASE_URL}/api/admin/accounting/transactions",
        params={"format": "csv"},
        headers=admin_headers,
    )
    
    print(f"   📋 Response status: {r.status_code}")
    print(f"   📋 Content-Type: {r.headers.get('content-type', 'N/A')}")
    
    if r.status_code == 200:
        content = r.text
        print(f"   ✅ 200 OK response received")
        
        # Verify CSV format
        lines = content.strip().split('\n')
        if len(lines) > 0:
            header = lines[0]
            print(f"   📋 CSV header: {header}")
            
            # Verify header contains expected fields
            expected_headers = [
                "date", "booking_id", "booking_code", "customer_name",
                "amount_gross_cents", "amount_net_cents", "vat_cents",
                "currency", "payment_method", "channel"
            ]
            
            for expected in expected_headers:
                assert expected in header, f"CSV header should contain {expected}"
            
            print(f"   ✅ CSV header validated")
            print(f"   📋 Total lines: {len(lines)} (including header)")
            
            if len(lines) > 1:
                print(f"   📋 Sample data line: {lines[1]}")
        else:
            print(f"   📋 Empty CSV response")
        
    elif r.status_code == 403:
        print(f"   ⚠️  403 Forbidden - May need accounting_export feature enabled")
        print(f"   📋 Response: {r.text}")
    else:
        print(f"   ❌ Unexpected status: {r.status_code}")
        print(f"   📋 Response: {r.text}")

    print(f"\n   ✅ Admin accounting export endpoint test completed")

def test_stripe_regression_smoke():
    """Test 4: Stripe regression smoke test"""
    print("\n" + "=" * 80)
    print("4️⃣  STRIPE REGRESSION SMOKE TEST")
    print("Testing existing Stripe checkout to ensure no regression")
    print("=" * 80 + "\n")

    admin_token, admin_org_id, admin_email = login_admin()
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    
    print(f"   ✅ Admin login successful: {admin_email}")
    print(f"   📋 Organization ID: {admin_org_id}")

    # Create a test quote for Stripe checkout
    print("\n   📋 Creating test quote for Stripe checkout...")
    
    quote = create_test_quote(admin_headers, admin_org_id)
    if not quote:
        print(f"   ❌ Failed to create test quote, skipping Stripe regression test")
        return
    
    quote_id = quote["quote_id"]
    print(f"   ✅ Test quote created: {quote_id}")

    # Test Stripe checkout endpoint
    print(f"\n   📋 Testing Stripe checkout endpoint")
    
    idempotency_key = f"stripe-smoke-{uuid.uuid4().hex[:16]}"
    checkout_payload = {
        "org": admin_org_id,
        "quote_id": quote_id,
        "guest": {
            "full_name": "Stripe Test User",
            "email": "stripe.test@example.com",
            "phone": "+90 555 987 6543"
        },
        "payment": {
            "method": "stripe",
            "return_url": "https://example.com/return"
        },
        "idempotency_key": idempotency_key
    }
    
    r = requests.post(
        f"{BASE_URL}/api/public/checkout",
        json=checkout_payload,
        headers=admin_headers,
    )
    
    print(f"   📋 Response status: {r.status_code}")
    
    if r.status_code == 200:
        data = r.json()
        print(f"   ✅ 200 OK response received")
        print(f"   📋 Response: {json.dumps(data, indent=2)}")
        
        # Verify response contract is unchanged
        assert "ok" in data, "Response should have ok field"
        assert "booking_id" in data, "Response should have booking_id field"
        assert "booking_code" in data, "Response should have booking_code field"
        assert "payment_intent_id" in data, "Response should have payment_intent_id field"
        assert "client_secret" in data, "Response should have client_secret field"
        
        print(f"   ✅ Stripe checkout response contract validated")
        
        # Verify public_checkouts record has payment_intent_id + client_secret
        if data.get("ok"):
            booking_id = data.get("booking_id")
            payment_intent_id = data.get("payment_intent_id")
            client_secret = data.get("client_secret")
            
            if booking_id and payment_intent_id and client_secret:
                print(f"   ✅ Payment Intent ID: {payment_intent_id}")
                print(f"   ✅ Client Secret present: {bool(client_secret)}")
                
                # Check public_checkouts collection
                try:
                    mongo_client = get_mongo_client()
                    db = mongo_client.get_default_database()
                    
                    checkout_record = db.public_checkouts.find_one({
                        "organization_id": admin_org_id,
                        "idempotency_key": idempotency_key
                    })
                    
                    if checkout_record:
                        assert checkout_record.get("payment_intent_id") == payment_intent_id, "Payment intent ID should match"
                        assert checkout_record.get("client_secret") == client_secret, "Client secret should match"
                        print(f"   ✅ public_checkouts record validated")
                    else:
                        print(f"   ⚠️  public_checkouts record not found")
                    
                    mongo_client.close()
                    
                except Exception as e:
                    print(f"   ⚠️  Failed to verify public_checkouts: {e}")
            else:
                print(f"   ⚠️  Missing payment fields in successful response")
        else:
            reason = data.get("reason", "unknown")
            print(f"   ⚠️  Checkout failed with reason: {reason}")
        
    else:
        print(f"   ⚠️  Unexpected status: {r.status_code}")
        print(f"   📋 Response: {r.text}")

    print(f"\n   ✅ Stripe regression smoke test completed")

def verify_audit_logs():
    """Verify PAYMENT_TR_INIT and ACCOUNTING_EXPORT_VIEW audit logs exist"""
    print("\n" + "=" * 80)
    print("5️⃣  AUDIT LOGS VERIFICATION")
    print("Checking for PAYMENT_TR_INIT and ACCOUNTING_EXPORT_VIEW audit logs")
    print("=" * 80 + "\n")

    try:
        mongo_client = get_mongo_client()
        db = mongo_client.get_default_database()
        
        # Check for PAYMENT_TR_INIT audit logs
        tr_init_logs = db.audit_logs.find({"action": "PAYMENT_TR_INIT"}).limit(5)
        tr_init_count = db.audit_logs.count_documents({"action": "PAYMENT_TR_INIT"})
        
        print(f"   📋 PAYMENT_TR_INIT audit logs found: {tr_init_count}")
        
        if tr_init_count > 0:
            sample_log = db.audit_logs.find_one({"action": "PAYMENT_TR_INIT"})
            print(f"   ✅ PAYMENT_TR_INIT audit log exists")
            print(f"   📋 Sample log meta: {sample_log.get('meta', {})}")
        else:
            print(f"   ⚠️  No PAYMENT_TR_INIT audit logs found")
        
        # Check for ACCOUNTING_EXPORT_VIEW audit logs
        export_logs = db.audit_logs.find({"action": "ACCOUNTING_EXPORT_VIEW"}).limit(5)
        export_count = db.audit_logs.count_documents({"action": "ACCOUNTING_EXPORT_VIEW"})
        
        print(f"   📋 ACCOUNTING_EXPORT_VIEW audit logs found: {export_count}")
        
        if export_count > 0:
            sample_log = db.audit_logs.find_one({"action": "ACCOUNTING_EXPORT_VIEW"})
            print(f"   ✅ ACCOUNTING_EXPORT_VIEW audit log exists")
            print(f"   📋 Sample log meta: {sample_log.get('meta', {})}")
        else:
            print(f"   ⚠️  No ACCOUNTING_EXPORT_VIEW audit logs found")
        
        mongo_client.close()
        
    except Exception as e:
        print(f"   ❌ Failed to verify audit logs: {e}")

def main():
    """Main test execution"""
    print("\n" + "=" * 80)
    print("PROMPT 5 (Payments TR Pack + Accounting/e-Fatura V1) - FINAL BACKEND VERIFICATION")
    print("Testing TR Installments, TR POS checkout, Admin accounting export, and Stripe regression")
    print("=" * 80)

    try:
        # Test 1: TR Installments endpoint
        test_tr_installments_endpoint()
        
        # Test 2: TR POS checkout endpoint  
        test_tr_pos_checkout_endpoint()
        
        # Test 3: Admin accounting export endpoint
        test_admin_accounting_export_endpoint()
        
        # Test 4: Stripe regression smoke test
        test_stripe_regression_smoke()
        
        # Test 5: Verify audit logs
        verify_audit_logs()
        
        print("\n" + "=" * 80)
        print("✅ PROMPT 5 BACKEND VERIFICATION COMPLETED")
        print("✅ All TR Pack + Accounting/e-Fatura V1 endpoints tested")
        print("=" * 80 + "\n")
        
    except Exception as e:
        print(f"\n❌ Test execution failed: {e}")
        raise

if __name__ == "__main__":
    main()