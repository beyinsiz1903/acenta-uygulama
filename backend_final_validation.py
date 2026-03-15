#!/usr/bin/env python3
"""
Final comprehensive Syroce backend validation
"""

import requests
import json

BASE_URL = "https://frontend-standardize.preview.emergentagent.com/api"
ADMIN_CREDENTIALS = {"email": "admin@acenta.test", "password": "admin123"}
AGENCY_CREDENTIALS = {"email": "agent@acenta.test", "password": "agent123"}

def login(credentials):
    response = requests.post(f"{BASE_URL}/auth/login", json=credentials, timeout=30)
    if response.status_code == 200:
        return response.json().get('access_token')
    return None

def main():
    print("🇹🇷 SYROCE BACKEND SMOKE VALIDATION - FINAL REPORT")
    print("=" * 70)
    
    # Login
    admin_token = login(ADMIN_CREDENTIALS)
    agency_token = login(AGENCY_CREDENTIALS)
    
    test_results = []
    
    if not admin_token:
        print("❌ Admin login failed")
        return
    if not agency_token:
        print("❌ Agency login failed")
        return
    
    print("✅ Admin login successful")
    print("✅ Agency login successful")
    print()
    
    # Test all admin sheets endpoints
    print("📋 ADMIN SHEETS ENDPOINTS VALIDATION")
    admin_endpoints = [
        "/admin/sheets/config",
        "/admin/sheets/connections", 
        "/admin/sheets/status",
        "/admin/sheets/templates",
        "/admin/sheets/writeback/stats",
        "/admin/sheets/runs",
        "/admin/sheets/available-hotels"
    ]
    
    headers = {"Authorization": f"Bearer {admin_token}"}
    all_admin_passed = True
    
    for endpoint in admin_endpoints:
        response = requests.get(f"{BASE_URL}{endpoint}", headers=headers, timeout=30)
        if response.status_code == 200:
            print(f"✅ {endpoint}: 200 OK")
        else:
            print(f"❌ {endpoint}: {response.status_code}")
            all_admin_passed = False
    
    print()
    
    # Test sync endpoint with real hotel ID
    print("🔄 SHEETS SYNC ENDPOINT (Google credential yokken)")
    # Get a real hotel ID first
    response = requests.get(f"{BASE_URL}/admin/sheets/available-hotels", headers=headers, timeout=30)
    if response.status_code == 200:
        hotels = response.json()
        if len(hotels) > 0:
            hotel_id = hotels[0]['hotel_id']
            sync_response = requests.post(f"{BASE_URL}/admin/sheets/sync/{hotel_id}", headers=headers, timeout=30)
            
            if sync_response.status_code == 200:
                sync_data = sync_response.json()
                if sync_data.get('status') == 'not_configured' and 'yapilandirilmamis' in sync_data.get('message', '').lower():
                    print(f"✅ POST /admin/sheets/sync/{hotel_id}: Graceful not_configured response")
                    test_results.append(("Sheets Sync Graceful", True))
                else:
                    print(f"❌ Unexpected sync response: {sync_data}")
                    test_results.append(("Sheets Sync Graceful", False))
            else:
                print(f"❌ Sync failed: {sync_response.status_code}")
                test_results.append(("Sheets Sync Graceful", False))
        else:
            print("❌ No hotels available for sync test")
            test_results.append(("Sheets Sync Graceful", False))
    else:
        print("❌ Could not get available hotels")
        test_results.append(("Sheets Sync Graceful", False))
    
    print()
    
    # Test agency hotels endpoint for sheet-related fields
    print("🏨 AGENCY HOTELS ENDPOINT")
    headers = {"Authorization": f"Bearer {agency_token}"}
    response = requests.get(f"{BASE_URL}/agency/hotels", headers=headers, timeout=30)
    
    if response.status_code == 200:
        print("✅ GET /agency/hotels: 200 OK")
        
        try:
            data = response.json()
            hotels = data.get('items', [])
            
            if len(hotels) > 0:
                sample_hotel = hotels[0]
                
                # Check for sheet-related fields
                sheet_fields = [
                    'sheet_managed_inventory', 'sheet_inventory_date', 'sheet_last_sync_at', 
                    'sheet_last_sync_status', 'sheet_reservations_imported', 'cm_status'
                ]
                
                found_fields = [field for field in sheet_fields if field in sample_hotel]
                
                if found_fields:
                    print(f"✅ Agency hotels payload contains sheet-related fields:")
                    for field in found_fields:
                        print(f"   - {field}: {sample_hotel.get(field)}")
                    test_results.append(("Agency Hotels Sheet Fields", True))
                else:
                    print(f"❌ No sheet-related fields found")
                    print(f"Available fields: {list(sample_hotel.keys())}")
                    test_results.append(("Agency Hotels Sheet Fields", False))
            else:
                print("❌ No hotels in response")
                test_results.append(("Agency Hotels Sheet Fields", False))
        
        except Exception as e:
            print(f"❌ Could not parse agency hotels response: {e}")
            test_results.append(("Agency Hotels Sheet Fields", False))
    else:
        print(f"❌ GET /agency/hotels failed: {response.status_code}")
        test_results.append(("Agency Hotels Sheet Fields", False))
    
    print()
    print("=" * 70)
    print("📊 FINAL SUMMARY")
    print("=" * 70)
    
    if all_admin_passed:
        print("✅ ALL admin sheets endpoints working (200 OK)")
    else:
        print("❌ Some admin sheets endpoints failed")
    
    sync_graceful = any(result[0] == "Sheets Sync Graceful" and result[1] for result in test_results)
    if sync_graceful:
        print("✅ POST /admin/sheets/sync graceful not_configured response working")
    else:
        print("❌ POST /admin/sheets/sync graceful handling failed")
    
    sheet_fields = any(result[0] == "Agency Hotels Sheet Fields" and result[1] for result in test_results)
    if sheet_fields:
        print("✅ GET /agency/hotels contains sheet-related fields")
    else:
        print("❌ GET /agency/hotels missing sheet-related fields")
    
    # Overall assessment
    total_checks = 3  # admin endpoints, sync graceful, agency sheet fields
    passed_checks = sum([all_admin_passed, sync_graceful, sheet_fields])
    
    print()
    if passed_checks == total_checks:
        print("🎉 SUCCESS: Syroce backend doğrulaması tamam - tüm endpoint'ler çalışıyor")
        print("   ✅ Google credential yokken backend kırılmıyor")  
        print("   ✅ Düzgün payload dönüyor")
        print("   ✅ Agency hotels sheet alanları mevcut")
    else:
        print(f"⚠️ ISSUES: {total_checks - passed_checks} validation(s) failed")
        print("   Some endpoints or functionality needs attention")

if __name__ == "__main__":
    main()