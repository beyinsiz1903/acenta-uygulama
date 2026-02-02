#!/usr/bin/env python3
"""
Partner Funnel Backend Test

This test verifies the new partner parameter functionality for the public funnel:
1. /api/public/search to find a product
2. Create public quote without partner (channel: "web", partner: null)
3. Create public quote with partner (channel: "partner", partner: "TEST_PARTNER_123")
4. Verify both quotes have same amount_cents but different channel/partner values

Test follows the Turkish requirements:
- Use demo organization (org_ops_close_idem from test results)
- Simple date and pax (today +1, 1 night, 2 adults, 1 room)
- Compare MongoDB documents in public_quotes collection
"""

import requests
import json
import uuid
from datetime import datetime, timedelta, date
from pymongo import MongoClient
import os
from typing import Dict, Any

# Configuration - Use production URL from frontend/.env
BASE_URL = "https://risk-aware-b2b.preview.emergentagent.com"

def get_mongo_client():
    """Get MongoDB client for direct database access"""
    mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017/test_database")
    return MongoClient(mongo_url)

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

def test_partner_funnel_flow():
    """Test the complete partner funnel flow as specified in Turkish requirements"""
    print("\n" + "=" * 80)
    print("PARTNER FUNNEL BACKEND TEST")
    print("Testing new partner parameter for public funnel")
    print("=" * 80 + "\n")
    
    # Use demo organization from test results
    org_id = "org_ops_close_idem"
    
    # Step 1: Search for products using /api/public/search
    print("1️⃣  Searching for products using /api/public/search...")
    
    # Simple date and pax (today +1, 1 night, 2 adults, 1 room)
    check_in = date.today() + timedelta(days=1)
    check_out = check_in + timedelta(days=1)  # 1 night
    
    search_params = {
        "org": org_id,
        "date_from": check_in.isoformat(),
        "date_to": check_out.isoformat(),
        "page": 1,
        "page_size": 10
    }
    
    r = requests.get(f"{BASE_URL}/api/public/search", params=search_params)
    print(f"   📋 Search response status: {r.status_code}")
    
    if r.status_code != 200:
        print(f"   ❌ Search failed: {r.text}")
        return False
    
    search_data = r.json()
    print(f"   📋 Search response: {json.dumps(search_data, indent=2)}")
    
    if not search_data.get("items"):
        print("   ❌ No products found in search results")
        return False
    
    # Get the first product's product_id
    first_product = search_data["items"][0]
    product_id = first_product["product_id"]
    print(f"   ✅ Found product: {product_id}")
    print(f"   📋 Product title: {first_product.get('title')}")
    print(f"   📋 Product price: {first_product.get('price')}")
    
    # Step 2: Create public quote WITHOUT partner
    print("\n2️⃣  Creating public quote WITHOUT partner...")
    
    quote_payload_no_partner = {
        "org": org_id,
        "product_id": product_id,
        "date_from": check_in.isoformat(),
        "date_to": check_out.isoformat(),
        "pax": {"adults": 2, "children": 0},
        "rooms": 1,
        "currency": "EUR"
        # No partner field
    }
    
    r1 = requests.post(f"{BASE_URL}/api/public/quote", json=quote_payload_no_partner)
    print(f"   📋 Quote without partner response status: {r1.status_code}")
    
    if r1.status_code != 200:
        print(f"   ❌ Quote creation failed: {r1.text}")
        return False
    
    quote_data_no_partner = r1.json()
    quote_id_no_partner = quote_data_no_partner["quote_id"]
    amount_cents_no_partner = quote_data_no_partner["amount_cents"]
    
    print(f"   ✅ Quote created without partner: {quote_id_no_partner}")
    print(f"   📋 Amount: {amount_cents_no_partner} cents")
    print(f"   📋 Response: {json.dumps(quote_data_no_partner, indent=2)}")
    
    # Step 3: Create public quote WITH partner
    print("\n3️⃣  Creating public quote WITH partner...")
    
    quote_payload_with_partner = {
        "org": org_id,
        "product_id": product_id,
        "date_from": check_in.isoformat(),
        "date_to": check_out.isoformat(),
        "pax": {"adults": 2, "children": 0},
        "rooms": 1,
        "currency": "EUR",
        "partner": "TEST_PARTNER_123"
    }
    
    r2 = requests.post(f"{BASE_URL}/api/public/quote", json=quote_payload_with_partner)
    print(f"   📋 Quote with partner response status: {r2.status_code}")
    
    if r2.status_code != 200:
        print(f"   ❌ Quote creation failed: {r2.text}")
        return False
    
    quote_data_with_partner = r2.json()
    quote_id_with_partner = quote_data_with_partner["quote_id"]
    amount_cents_with_partner = quote_data_with_partner["amount_cents"]
    
    print(f"   ✅ Quote created with partner: {quote_id_with_partner}")
    print(f"   📋 Amount: {amount_cents_with_partner} cents")
    print(f"   📋 Response: {json.dumps(quote_data_with_partner, indent=2)}")
    
    # Step 4: Verify MongoDB documents in public_quotes collection
    print("\n4️⃣  Verifying MongoDB documents in public_quotes collection...")
    
    mongo_client = get_mongo_client()
    db = mongo_client.get_default_database()
    
    # Get quote without partner from MongoDB
    quote_doc_no_partner = db.public_quotes.find_one({"quote_id": quote_id_no_partner, "organization_id": org_id})
    if not quote_doc_no_partner:
        print(f"   ❌ Quote without partner not found in MongoDB")
        mongo_client.close()
        return False
    
    # Get quote with partner from MongoDB
    quote_doc_with_partner = db.public_quotes.find_one({"quote_id": quote_id_with_partner, "organization_id": org_id})
    if not quote_doc_with_partner:
        print(f"   ❌ Quote with partner not found in MongoDB")
        mongo_client.close()
        return False
    
    mongo_client.close()
    
    print(f"   ✅ Both quotes found in MongoDB")
    
    # Verify quote without partner has correct channel and partner values
    channel_no_partner = quote_doc_no_partner.get("channel")
    partner_no_partner = quote_doc_no_partner.get("partner")
    
    print(f"\n   📋 Quote WITHOUT partner MongoDB document:")
    print(f"      - quote_id: {quote_doc_no_partner.get('quote_id')}")
    print(f"      - channel: {channel_no_partner}")
    print(f"      - partner: {partner_no_partner}")
    print(f"      - amount_cents: {quote_doc_no_partner.get('amount_cents')}")
    print(f"      - organization_id: {quote_doc_no_partner.get('organization_id')}")
    
    # Verify quote with partner has correct channel and partner values
    channel_with_partner = quote_doc_with_partner.get("channel")
    partner_with_partner = quote_doc_with_partner.get("partner")
    
    print(f"\n   📋 Quote WITH partner MongoDB document:")
    print(f"      - quote_id: {quote_doc_with_partner.get('quote_id')}")
    print(f"      - channel: {channel_with_partner}")
    print(f"      - partner: {partner_with_partner}")
    print(f"      - amount_cents: {quote_doc_with_partner.get('amount_cents')}")
    print(f"      - organization_id: {quote_doc_with_partner.get('organization_id')}")
    
    # Step 5: Verify expectations
    print("\n5️⃣  Verifying expectations...")
    
    success = True
    
    # Check quote without partner
    if channel_no_partner != "web":
        print(f"   ❌ Expected channel 'web' for quote without partner, got: {channel_no_partner}")
        success = False
    else:
        print(f"   ✅ Quote without partner has correct channel: 'web'")
    
    if partner_no_partner is not None:
        print(f"   ❌ Expected partner null/None for quote without partner, got: {partner_no_partner}")
        success = False
    else:
        print(f"   ✅ Quote without partner has correct partner: null/None")
    
    # Check quote with partner
    if channel_with_partner != "partner":
        print(f"   ❌ Expected channel 'partner' for quote with partner, got: {channel_with_partner}")
        success = False
    else:
        print(f"   ✅ Quote with partner has correct channel: 'partner'")
    
    if partner_with_partner != "TEST_PARTNER_123":
        print(f"   ❌ Expected partner 'TEST_PARTNER_123' for quote with partner, got: {partner_with_partner}")
        success = False
    else:
        print(f"   ✅ Quote with partner has correct partner: 'TEST_PARTNER_123'")
    
    # Check that amounts are the same
    if amount_cents_no_partner != amount_cents_with_partner:
        print(f"   ❌ Expected same amount_cents for both quotes, got: {amount_cents_no_partner} vs {amount_cents_with_partner}")
        success = False
    else:
        print(f"   ✅ Both quotes have same amount_cents: {amount_cents_no_partner}")
    
    # Additional verification: other fields should be the same
    fields_to_compare = ["product_id", "date_from", "date_to", "pax", "currency", "nights"]
    for field in fields_to_compare:
        val1 = quote_doc_no_partner.get(field)
        val2 = quote_doc_with_partner.get(field)
        if val1 != val2:
            print(f"   ❌ Field '{field}' differs: {val1} vs {val2}")
            success = False
        else:
            print(f"   ✅ Field '{field}' matches: {val1}")
    
    return success

def run_partner_funnel_test():
    """Run the partner funnel test"""
    print("\n" + "🚀" * 80)
    print("PARTNER FUNNEL BACKEND TEST")
    print("Testing new partner parameter functionality for public funnel")
    print("🚀" * 80)
    
    try:
        success = test_partner_funnel_flow()
        
        print("\n" + "🏁" * 80)
        print("TEST SUMMARY")
        print("🏁" * 80)
        
        if success:
            print("✅ PARTNER FUNNEL TEST PASSED!")
            print("\n📋 VERIFIED FUNCTIONALITY:")
            print("✅ /api/public/search returns products correctly")
            print("✅ Quote without partner: channel='web', partner=null")
            print("✅ Quote with partner: channel='partner', partner='TEST_PARTNER_123'")
            print("✅ Both quotes have identical amount_cents and other fields")
            print("✅ MongoDB documents stored correctly in public_quotes collection")
        else:
            print("❌ PARTNER FUNNEL TEST FAILED!")
            print("⚠️  Some expectations were not met. See details above.")
        
        return success
        
    except Exception as e:
        print(f"\n❌ TEST FAILED WITH EXCEPTION: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = run_partner_funnel_test()
    exit(0 if success else 1)