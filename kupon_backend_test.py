#!/usr/bin/env python3
"""
B2C Public Checkout Kupon Entegrasyonu Backend Testleri

Bu test dosyası aşağıdaki senaryoları test eder:
1. Başarılı kupon uygulaması (APPLIED) - Kupon değerlendirme mantığı
2. Geçersiz kupon (NOT_FOUND) - Kupon değerlendirme mantığı  
3. Per-customer limit aşımı (LIMIT_PER_CUSTOMER) - Kupon değerlendirme mantığı

NOT: Stripe entegrasyonu mevcut olmadığından, kupon mantığını doğrudan test ediyoruz.
"""

import requests
import json
import uuid
import hashlib
from datetime import datetime, timedelta
from pymongo import MongoClient
import os
import time

# Configuration - Use production URL from frontend/.env
BASE_URL = "https://syroce-acenta.preview.emergentagent.com"

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

def find_test_org_and_product():
    """Find a suitable org and product for testing"""
    mongo_client = get_mongo_client()
    db = mongo_client.get_default_database()
    
    # Look for existing test organizations
    test_orgs = ["org_public_checkout", "org_public_A", "org_A"]
    
    for org_id in test_orgs:
        org = db.organizations.find_one({"_id": org_id})
        if org:
            # Find a product for this org
            product = db.products.find_one({"organization_id": org_id})
            if product:
                product_id = product.get("_id") or product.get("id")
                mongo_client.close()
                return org_id, str(product_id)
    
    # If no test org found, use the first available org with products
    orgs = list(db.organizations.find({}).limit(10))
    for org in orgs:
        org_id = org.get("_id") or org.get("id")
        if org_id:
            product = db.products.find_one({"organization_id": org_id})
            if product:
                product_id = product.get("_id") or product.get("id")
                mongo_client.close()
                return str(org_id), str(product_id)
    
    mongo_client.close()
    raise Exception("No suitable org/product pair found for testing")

def create_public_quote(org, product_id):
    """Create a public quote for testing"""
    from datetime import date
    
    # Use dates in the future
    date_from = date.today() + timedelta(days=30)
    date_to = date.today() + timedelta(days=33)
    
    payload = {
        "org": org,
        "product_id": product_id,
        "date_from": date_from.isoformat(),
        "date_to": date_to.isoformat(),
        "pax": {
            "adults": 2,
            "children": 0
        },
        "rooms": 1,
        "currency": "EUR"
    }
    
    print(f"   📋 Creating quote with payload: {payload}")
    
    r = requests.post(f"{BASE_URL}/api/public/quote", json=payload)
    
    print(f"   📋 Quote response status: {r.status_code}")
    if r.status_code != 200:
        print(f"   📋 Quote response text: {r.text}")
        
    assert r.status_code == 200, f"Quote creation failed: {r.status_code} - {r.text}"
    
    data = r.json()
    assert data.get("ok") is True, f"Quote response not ok: {data}"
    
    return data["quote_id"], data["amount_cents"], data["currency"]

def create_test_coupon(admin_headers, admin_org_id, code_suffix=None):
    """Create a test coupon"""
    if code_suffix is None:
        code_suffix = str(uuid.uuid4())[:8].upper()
    
    coupon_code = f"PUB10_{code_suffix}"
    
    # Create coupon with dates in the future
    valid_from = datetime.utcnow()
    valid_to = datetime.utcnow() + timedelta(days=1)
    
    payload = {
        "code": coupon_code,
        "discount_type": "PERCENT",
        "value": 10,
        "scope": "B2C",
        "min_total": 0,
        "usage_limit": 10,
        "per_customer_limit": 2,
        "valid_from": valid_from.isoformat(),
        "valid_to": valid_to.isoformat(),
        "active": True
    }
    
    print(f"   📋 Creating coupon with payload: {payload}")
    
    r = requests.post(f"{BASE_URL}/api/admin/coupons", json=payload, headers=admin_headers)
    
    print(f"   📋 Coupon response status: {r.status_code}")
    if r.status_code != 200:
        print(f"   📋 Coupon response text: {r.text}")
        
    assert r.status_code == 200, f"Coupon creation failed: {r.status_code} - {r.text}"
    
    data = r.json()
    return data["id"], coupon_code

def test_coupon_evaluation_directly(org, quote_id, coupon_code, guest_email, expected_status):
    """Test coupon evaluation logic directly via database"""
    print(f"   📋 Testing coupon evaluation: {coupon_code} -> expected: {expected_status}")
    
    mongo_client = get_mongo_client()
    db = mongo_client.get_default_database()
    
    # Get the quote from database
    quote = db.public_quotes.find_one({"quote_id": quote_id, "organization_id": org})
    assert quote is not None, f"Quote {quote_id} not found"
    
    print(f"   📋 Quote found: amount_cents={quote.get('amount_cents')}, currency={quote.get('currency')}")
    
    # Simulate the coupon evaluation using the same logic as the backend
    from app.services.coupons import CouponService
    import asyncio
    
    async def evaluate_coupon():
        coupons = CouponService(db)
        coupon_doc, coupon_eval = await coupons.evaluate_for_public_quote(
            organization_id=org,
            quote=quote,
            code=coupon_code,
            customer_key=guest_email,
        )
        return coupon_doc, coupon_eval
    
    # Run the async coupon evaluation
    coupon_doc, coupon_eval = asyncio.run(evaluate_coupon())
    
    print(f"   📋 Coupon evaluation result: {coupon_eval}")
    print(f"   📋 Coupon document found: {coupon_doc is not None}")
    
    # Verify the expected status
    actual_status = coupon_eval.get("status")
    assert actual_status == expected_status, f"Expected status {expected_status}, got {actual_status}"
    
    # Return results for further testing
    mongo_client.close()
    return coupon_doc, coupon_eval

def simulate_coupon_usage_increment(coupon_doc, guest_email):
    """Simulate coupon usage increment"""
    if not coupon_doc:
        return
    
    mongo_client = get_mongo_client()
    db = mongo_client.get_default_database()
    
    from app.services.coupons import CouponService
    import asyncio
    
    async def increment_usage():
        coupons = CouponService(db)
        await coupons.increment_usage_for_customer(coupon_doc.get("_id"), customer_key=guest_email)
    
    asyncio.run(increment_usage())
    mongo_client.close()

def verify_coupon_usage(coupon_id, expected_usage_count, expected_customer_usage=None, customer_email=None):
    """Verify coupon usage counters in database"""
    mongo_client = get_mongo_client()
    db = mongo_client.get_default_database()
    
    from bson import ObjectId
    coupon = db.coupons.find_one({"_id": ObjectId(coupon_id)})
    
    assert coupon is not None, f"Coupon {coupon_id} not found in database"
    
    print(f"   📋 Coupon usage_count: {coupon.get('usage_count')}")
    print(f"   📋 Coupon usage_per_customer: {coupon.get('usage_per_customer')}")
    
    assert coupon.get("usage_count") == expected_usage_count, f"Expected usage_count {expected_usage_count}, got {coupon.get('usage_count')}"
    
    if expected_customer_usage is not None and customer_email:
        usage_per_customer = coupon.get("usage_per_customer", {})
        # Email is normalized: lowercase, dots/spaces replaced with underscores
        safe_email = customer_email.strip().lower().replace(" ", "_").replace(".", "_").replace("$", "_")
        customer_usage = usage_per_customer.get(safe_email, 0)
        assert customer_usage == expected_customer_usage, f"Expected customer usage {expected_customer_usage}, got {customer_usage}"
    
    mongo_client.close()
    return coupon

def test_scenario_1_successful_coupon():
    """Senaryo 1: Başarılı kupon uygulaması (APPLIED)"""
    print("\n" + "=" * 80)
    print("SENARYO 1: BAŞARILI KUPON UYGULAMASI (APPLIED)")
    print("=" * 80)
    
    # 1. Login as admin
    print("\n1️⃣  Admin login...")
    admin_token, admin_org_id, admin_email = login_admin()
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    print(f"   ✅ Admin login successful: {admin_email}")
    
    # 2. Find test org and product
    print("\n2️⃣  Finding test org and product...")
    org, product_id = find_test_org_and_product()
    print(f"   ✅ Using org: {org}, product: {product_id}")
    
    # 3. Create public quote
    print("\n3️⃣  Creating public quote...")
    quote_id, amount_cents, currency = create_public_quote(org, product_id)
    print(f"   ✅ Quote created: {quote_id}, amount: {amount_cents} {currency}")
    
    # 4. Create test coupon
    print("\n4️⃣  Creating test coupon...")
    coupon_id, coupon_code = create_test_coupon(admin_headers, admin_org_id)
    print(f"   ✅ Coupon created: {coupon_id}, code: {coupon_code}")
    
    # 5. Test coupon evaluation directly
    print("\n5️⃣  Testing coupon evaluation...")
    guest_email = "test.customer@example.com"
    coupon_doc, coupon_eval = test_coupon_evaluation_directly(org, quote_id, coupon_code, guest_email, "APPLIED")
    print(f"   ✅ Coupon evaluation successful: APPLIED status")
    
    # 6. Verify discount calculation
    print("\n6️⃣  Verifying discount calculation...")
    discount_cents = coupon_eval.get("amount_cents", 0)
    expected_discount = int(amount_cents * 0.1)  # 10% discount
    assert abs(discount_cents - expected_discount) <= 1, f"Expected discount ~{expected_discount}, got {discount_cents}"
    print(f"   ✅ Discount calculation correct: {discount_cents} cents ({discount_cents/100:.2f} EUR)")
    
    # 7. Simulate usage increment
    print("\n7️⃣  Simulating coupon usage increment...")
    simulate_coupon_usage_increment(coupon_doc, guest_email)
    coupon = verify_coupon_usage(coupon_id, 1, 1, guest_email)
    print(f"   ✅ Coupon usage incremented: global=1, customer=1")
    
    print(f"\n✅ SENARYO 1 BAŞARILI: Kupon değerlendirme mantığı çalışıyor ve %10 indirim hesaplanıyor")
    return org, product_id, coupon_id, coupon_code, guest_email

def test_scenario_2_invalid_coupon(org, product_id):
    """Senaryo 2: Geçersiz kupon (NOT_FOUND)"""
    print("\n" + "=" * 80)
    print("SENARYO 2: GEÇERSİZ KUPON (NOT_FOUND)")
    print("=" * 80)
    
    # 1. Create new quote
    print("\n1️⃣  Creating new public quote...")
    quote_id, amount_cents, currency = create_public_quote(org, product_id)
    print(f"   ✅ Quote created: {quote_id}, amount: {amount_cents} {currency}")
    
    # 2. Test invalid coupon evaluation
    print("\n2️⃣  Testing invalid coupon evaluation...")
    invalid_coupon = "YANLIS_KOD"
    guest_email = "test.customer2@example.com"
    coupon_doc, coupon_eval = test_coupon_evaluation_directly(org, quote_id, invalid_coupon, guest_email, "NOT_FOUND")
    print(f"   ✅ Invalid coupon correctly identified: NOT_FOUND status")
    
    # 3. Verify no discount
    print("\n3️⃣  Verifying no discount applied...")
    discount_cents = coupon_eval.get("amount_cents", 0)
    assert discount_cents == 0, f"Expected no discount, got {discount_cents}"
    print(f"   ✅ No discount applied for invalid coupon")
    
    print(f"\n✅ SENARYO 2 BAŞARILI: Geçersiz kupon doğru şekilde tespit edildi")

def test_scenario_3_per_customer_limit(org, product_id, coupon_id, coupon_code, guest_email):
    """Senaryo 3: Per-customer limit aşımı (LIMIT_PER_CUSTOMER)"""
    print("\n" + "=" * 80)
    print("SENARYO 3: PER-CUSTOMER LIMIT AŞIMI (LIMIT_PER_CUSTOMER)")
    print("=" * 80)
    
    # The coupon was created with per_customer_limit=2, and we already used it once in scenario 1
    
    # 1. Second usage (should work)
    print("\n1️⃣  Second usage of same coupon with same email...")
    quote_id2, amount_cents2, currency2 = create_public_quote(org, product_id)
    coupon_doc2, coupon_eval2 = test_coupon_evaluation_directly(org, quote_id2, coupon_code, guest_email, "APPLIED")
    print(f"   ✅ Second usage successful: APPLIED status")
    
    # Simulate second usage increment
    simulate_coupon_usage_increment(coupon_doc2, guest_email)
    coupon = verify_coupon_usage(coupon_id, 2, 2, guest_email)
    print(f"   ✅ Coupon usage after second use: global=2, customer=2")
    
    # 2. Third usage (should fail with LIMIT_PER_CUSTOMER)
    print("\n2️⃣  Third usage of same coupon with same email (should hit limit)...")
    quote_id3, amount_cents3, currency3 = create_public_quote(org, product_id)
    coupon_doc3, coupon_eval3 = test_coupon_evaluation_directly(org, quote_id3, coupon_code, guest_email, "LIMIT_PER_CUSTOMER")
    print(f"   ✅ Third usage correctly blocked: LIMIT_PER_CUSTOMER status")
    
    # 3. Verify no discount for third attempt
    print("\n3️⃣  Verifying no discount for limit exceeded...")
    discount_cents = coupon_eval3.get("amount_cents", 0)
    assert discount_cents == 0, f"Expected no discount for limit exceeded, got {discount_cents}"
    print(f"   ✅ No discount applied when per-customer limit exceeded")
    
    # 4. Verify usage counters remain unchanged for failed attempt
    print("\n4️⃣  Verifying usage counters after failed attempt...")
    coupon = verify_coupon_usage(coupon_id, 2, 2, guest_email)  # Should remain 2, 2
    print(f"   ✅ Usage counters unchanged after failed attempt: global=2, customer=2")
    
    print(f"\n✅ SENARYO 3 BAŞARILI: Per-customer limit aşımı doğru şekilde tespit edildi")

def test_kupon_backend_integration():
    """Main test function for B2C public checkout coupon integration"""
    print("\n" + "=" * 100)
    print("B2C PUBLIC CHECKOUT KUPON ENTEGRASYONU BACKEND TESTLERİ")
    print("=" * 100)
    print("Bu test aşağıdaki senaryoları kapsar:")
    print("1. Başarılı kupon uygulaması (APPLIED) - Kupon değerlendirme mantığı")
    print("2. Geçersiz kupon (NOT_FOUND) - Kupon değerlendirme mantığı")
    print("3. Per-customer limit aşımı (LIMIT_PER_CUSTOMER) - Kupon değerlendirme mantığı")
    print("")
    print("NOT: Stripe entegrasyonu mevcut olmadığından, kupon mantığını doğrudan test ediyoruz.")
    print("=" * 100)
    
    try:
        # Run scenario 1
        org, product_id, coupon_id, coupon_code, guest_email = test_scenario_1_successful_coupon()
        
        # Run scenario 2
        test_scenario_2_invalid_coupon(org, product_id)
        
        # Run scenario 3
        test_scenario_3_per_customer_limit(org, product_id, coupon_id, coupon_code, guest_email)
        
        print("\n" + "=" * 100)
        print("✅ TÜM KUPON ENTEGRASYONU TESTLERİ BAŞARILI")
        print("✅ Senaryo 1: Başarılı kupon uygulaması ✓")
        print("✅ Senaryo 2: Geçersiz kupon işleme ✓")
        print("✅ Senaryo 3: Per-customer limit kontrolü ✓")
        print("")
        print("📋 Test edilen özellikler:")
        print("   - POST /api/public/quote endpoint'i")
        print("   - POST /api/admin/coupons endpoint'i")
        print("   - CouponService.evaluate_for_public_quote() mantığı")
        print("   - Kupon değerlendirme algoritması (scope, limits, discount calculation)")
        print("   - Kupon kullanım sayaçları (global ve per-customer)")
        print("   - İndirim hesaplama (PERCENT type, 10% discount)")
        print("   - Per-customer limit kontrolü")
        print("")
        print("⚠️  NOT: Stripe entegrasyonu test edilmedi (provider_unavailable)")
        print("   Ancak kupon mantığı Stripe'dan bağımsız olarak çalışıyor.")
        print("=" * 100)
        
    except Exception as e:
        print(f"\n❌ TEST BAŞARISIZ: {e}")
        import traceback
        traceback.print_exc()
        raise

if __name__ == "__main__":
    test_kupon_backend_integration()