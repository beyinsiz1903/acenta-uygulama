#!/usr/bin/env python3
"""
Final comprehensive Syroce backend validation - Fixed version
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
    
    if not admin_token or not agency_token:
        print("❌ Login failed")
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
    admin_results = []
    
    for endpoint in admin_endpoints:
        response = requests.get(f"{BASE_URL}{endpoint}", headers=headers, timeout=30)
        success = response.status_code == 200
        admin_results.append(success)
        print(f"{'✅' if success else '❌'} {endpoint}: {response.status_code}")
    
    print()
    
    # Test sync endpoint with real hotel ID
    print("🔄 SHEETS SYNC ENDPOINT (Google credential yokken)")
    response = requests.get(f"{BASE_URL}/admin/sheets/available-hotels", headers=headers, timeout=30)
    sync_graceful = False
    
    if response.status_code == 200:
        hotels = response.json()
        if len(hotels) > 0:
            # Extract hotel ID safely
            hotel = hotels[0]
            hotel_id = hotel.get('id') or hotel.get('hotel_id') or hotel.get('_id') or list(hotel.values())[0]
            
            if hotel_id:
                sync_response = requests.post(f"{BASE_URL}/admin/sheets/sync/{hotel_id}", headers=headers, timeout=30)
                
                if sync_response.status_code == 200:
                    sync_data = sync_response.json()
                    if (sync_data.get('status') == 'not_configured' or 
                        'yapilandirilmamis' in sync_data.get('message', '').lower() or
                        'not_configured' in str(sync_data).lower()):
                        print(f"✅ POST /admin/sheets/sync/{hotel_id}: Graceful not_configured")
                        sync_graceful = True
                    else:
                        print(f"⚠️ Unexpected sync response: {sync_data}")
                else:
                    print(f"❌ Sync failed: {sync_response.status_code} - {sync_response.text}")
            else:
                print("❌ Could not extract hotel ID")
        else:
            print("❌ No hotels available")
    else:
        print("❌ Could not get available hotels")
    
    print()
    
    # Test agency hotels endpoint for sheet-related fields
    print("🏨 AGENCY HOTELS ENDPOINT")
    headers = {"Authorization": f"Bearer {agency_token}"}
    response = requests.get(f"{BASE_URL}/agency/hotels", headers=headers, timeout=30)
    
    sheet_fields_found = False
    
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
                    sheet_fields_found = True
                else:
                    print(f"❌ No sheet-related fields found")
                    print(f"Available fields: {list(sample_hotel.keys())}")
            else:
                print("❌ No hotels in response")
        
        except Exception as e:
            print(f"❌ Could not parse agency hotels response: {e}")
    else:
        print(f"❌ GET /agency/hotels failed: {response.status_code}")
    
    print()
    print("=" * 70)
    print("📊 TURKISH REVIEW VALIDATION SUMMARY")
    print("=" * 70)
    
    all_admin_passed = all(admin_results)
    
    print(f"1. Admin sheets endpoints: {'✅ PASS' if all_admin_passed else '❌ FAIL'}")
    print(f"   - GET /admin/sheets/config: {'✅' if admin_results[0] else '❌'}")
    print(f"   - GET /admin/sheets/connections: {'✅' if admin_results[1] else '❌'}")
    print(f"   - GET /admin/sheets/status: {'✅' if admin_results[2] else '❌'}")
    print(f"   - GET /admin/sheets/templates: {'✅' if admin_results[3] else '❌'}")
    print(f"   - GET /admin/sheets/writeback/stats: {'✅' if admin_results[4] else '❌'}")
    print(f"   - GET /admin/sheets/runs: {'✅' if admin_results[5] else '❌'}")
    print(f"   - GET /admin/sheets/available-hotels: {'✅' if admin_results[6] else '❌'}")
    
    print(f"2. Sync graceful handling: {'✅ PASS' if sync_graceful else '❌ FAIL'}")
    print(f"   - POST /admin/sheets/sync/{{hotel_id}}: {'✅ Graceful not_configured' if sync_graceful else '❌ Not graceful'}")
    
    print(f"3. Agency hotels sheet fields: {'✅ PASS' if sheet_fields_found else '❌ FAIL'}")
    print(f"   - GET /agency/hotels: {'✅ Contains sheet fields' if sheet_fields_found else '❌ Missing sheet fields'}")
    
    # Overall assessment
    total_checks = 3
    passed_checks = sum([all_admin_passed, sync_graceful, sheet_fields_found])
    
    print()
    print("🎯 AMACIN DOĞRULAMA:")
    print(f"   ✅ Google credential yokken backend'in kırılmadan çalışması: {'PASS' if all_admin_passed else 'FAIL'}")
    print(f"   ✅ Düzgün payload dönmesi: {'PASS' if sync_graceful else 'FAIL'}")
    print(f"   ✅ Agency hotels payload'ında sheet-related alanlar: {'PASS' if sheet_fields_found else 'FAIL'}")
    
    print()
    if passed_checks == total_checks:
        print("🎉 BAŞARI: Tüm validasyon geçti - issue YOK")
    else:
        print(f"⚠️ ISSUE VAR: {total_checks - passed_checks}/{total_checks} validation başarısız")
    
    return passed_checks == total_checks

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)