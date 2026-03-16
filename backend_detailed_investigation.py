#!/usr/bin/env python3
"""
Detailed investigation of the failing tests
"""

import requests
import json

BASE_URL = "https://error-trends-dash.preview.emergentagent.com/api"
ADMIN_CREDENTIALS = {"email": "admin@acenta.test", "password": "admin123"}
AGENCY_CREDENTIALS = {"email": "agent@acenta.test", "password": "agent123"}

def login(credentials):
    response = requests.post(f"{BASE_URL}/auth/login", json=credentials, timeout=30)
    if response.status_code == 200:
        return response.json().get('access_token')
    return None

def main():
    print("🔍 DETAILED INVESTIGATION OF FAILING TESTS")
    print("=" * 60)
    
    # Login
    admin_token = login(ADMIN_CREDENTIALS)
    agency_token = login(AGENCY_CREDENTIALS)
    
    if not admin_token or not agency_token:
        print("❌ Could not get tokens")
        return
    
    # 1. Check agency hotels response structure
    print("\n1️⃣ INVESTIGATING AGENCY HOTELS RESPONSE")
    headers = {"Authorization": f"Bearer {agency_token}"}
    response = requests.get(f"{BASE_URL}/agency/hotels", headers=headers, timeout=30)
    
    print(f"Status Code: {response.status_code}")
    print(f"Response Headers: {dict(response.headers)}")
    print(f"Response Length: {len(response.text)} chars")
    print(f"Response Preview: {response.text[:500]}...")
    
    # Try to parse as JSON
    try:
        data = response.json()
        print(f"✅ JSON parsing successful")
        print(f"Response Type: {type(data)}")
        if isinstance(data, list):
            print(f"Hotels Count: {len(data)}")
            if len(data) > 0:
                print(f"Sample Hotel Fields: {list(data[0].keys())}")
                # Check for sheet-related fields
                sheet_fields = ['sheet_id', 'sheet_url', 'sync_status', 'writeback_tab', 'validation_status', 'sheet_connection']
                found_fields = [field for field in sheet_fields if field in data[0]]
                if found_fields:
                    print(f"✅ Sheet-related fields found: {found_fields}")
                else:
                    print(f"⚠️ No sheet-related fields found in: {list(data[0].keys())}")
        elif isinstance(data, dict):
            print(f"Response Keys: {list(data.keys())}")
    except Exception as e:
        print(f"❌ JSON parsing failed: {e}")
        print(f"Raw response: {response.text}")
    
    # 2. Check available hotels to get valid hotel_id
    print("\n2️⃣ INVESTIGATING AVAILABLE HOTELS FOR SYNC TEST")
    headers = {"Authorization": f"Bearer {admin_token}"}
    response = requests.get(f"{BASE_URL}/admin/sheets/available-hotels", headers=headers, timeout=30)
    
    if response.status_code == 200:
        try:
            hotels = response.json()
            print(f"✅ Available hotels: {len(hotels) if isinstance(hotels, list) else 'Not a list'}")
            if isinstance(hotels, list) and len(hotels) > 0:
                hotel_id = hotels[0].get('id') or hotels[0].get('hotel_id') or hotels[0].get('_id')
                print(f"First hotel ID: {hotel_id}")
                
                if hotel_id:
                    # Test sync with real hotel ID
                    print(f"\n3️⃣ TESTING SYNC WITH REAL HOTEL ID: {hotel_id}")
                    sync_response = requests.post(f"{BASE_URL}/admin/sheets/sync/{hotel_id}", headers=headers, timeout=30)
                    print(f"Sync Status: {sync_response.status_code}")
                    print(f"Sync Response: {sync_response.text}")
                    
                    # Analyze if this is graceful handling of no credentials
                    if sync_response.status_code in [400, 422]:
                        try:
                            sync_data = sync_response.json()
                            if 'not_configured' in sync_response.text.lower() or 'yapilandirilmamis' in sync_response.text.lower():
                                print("✅ Graceful not_configured response detected")
                            else:
                                print(f"Response content: {sync_data}")
                        except:
                            print(f"Could not parse sync response as JSON")
                else:
                    print("❌ Could not extract hotel ID from available hotels")
            else:
                print(f"❌ No hotels available or unexpected format: {hotels}")
        except Exception as e:
            print(f"❌ Could not parse available hotels: {e}")
    else:
        print(f"❌ Could not get available hotels: {response.status_code}")
    
    print("\n" + "=" * 60)
    print("INVESTIGATION COMPLETE")

if __name__ == "__main__":
    main()