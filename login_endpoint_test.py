#!/usr/bin/env python3
"""
Login Endpoint Test for Preview Environment
Testing /api/auth/login endpoint with specified user credentials
Base URL: https://mimari-analiz.preview.emergentagent.com/api
"""

import requests
import json
import time
from datetime import datetime

# Base URL for the preview environment
BASE_URL = "https://mimari-analiz.preview.emergentagent.com/api"
LOGIN_ENDPOINT = f"{BASE_URL}/auth/login"

# Test credentials as specified in the request
TEST_CREDENTIALS = [
    {"email": "demo@hotel.com", "password": "demo123"},
    {"email": "muratsutay@hotmail.com", "password": "murat1903"},
    {"email": "test@test.com", "password": "test123"},
    {"email": "demo@demo.com", "password": "demo123"},
    {"email": "patron@hotel.com", "password": "patron123"},
    {"email": "admin@hoteltest.com", "password": "admin123"}
]

def test_login_endpoint():
    """Test login endpoint with all specified credentials"""
    print("🔐 LOGIN ENDPOINT TEST BAŞLADI")
    print(f"📍 Base URL: {BASE_URL}")
    print(f"🎯 Endpoint: {LOGIN_ENDPOINT}")
    print(f"📅 Test Zamanı: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    successful_logins = []
    failed_logins = []
    
    for i, credentials in enumerate(TEST_CREDENTIALS, 1):
        email = credentials["email"]
        password = credentials["password"]
        
        print(f"\n{i}. TEST - {email}")
        print("-" * 50)
        
        try:
            # Prepare request payload
            payload = {
                "email": email,
                "password": password
            }
            
            # Set headers
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
            
            # Record start time
            start_time = time.time()
            
            # Make POST request
            response = requests.post(
                LOGIN_ENDPOINT,
                json=payload,
                headers=headers,
                timeout=30
            )
            
            # Calculate response time
            response_time = round((time.time() - start_time) * 1000, 1)
            
            # Get response details
            status_code = response.status_code
            
            try:
                response_data = response.json()
            except:
                response_data = {"error": "Invalid JSON response", "text": response.text[:500]}
            
            # Print results
            print(f"📊 HTTP Status: {status_code}")
            print(f"⏱️  Response Time: {response_time}ms")
            
            if status_code == 200:
                print("✅ LOGIN BAŞARILI")
                
                # Extract user information
                user_info = response_data.get("user", {})
                user_email = user_info.get("email", "N/A")
                user_role = user_info.get("role", "N/A")
                user_name = user_info.get("name", "N/A")
                
                print(f"👤 User Email: {user_email}")
                print(f"🎭 User Role: {user_role}")
                print(f"📝 User Name: {user_name}")
                
                # Check if token exists
                access_token = response_data.get("access_token")
                if access_token:
                    print(f"🔑 Token: {access_token[:20]}...{access_token[-10:] if len(access_token) > 30 else access_token}")
                else:
                    print("⚠️  Token bulunamadı")
                
                successful_logins.append({
                    "email": email,
                    "status": status_code,
                    "response_time": response_time,
                    "user_email": user_email,
                    "user_role": user_role,
                    "user_name": user_name,
                    "has_token": bool(access_token)
                })
                
            elif status_code == 401:
                print("❌ LOGIN BAŞARISIZ - 401 Invalid Credentials")
                error_detail = response_data.get("detail", "Unknown error")
                print(f"🚫 Error: {error_detail}")
                
                failed_logins.append({
                    "email": email,
                    "status": status_code,
                    "response_time": response_time,
                    "error": error_detail,
                    "is_invalid_credentials": "invalid" in error_detail.lower() or "credential" in error_detail.lower()
                })
                
            else:
                print(f"❌ LOGIN BAŞARISIZ - {status_code}")
                error_detail = response_data.get("detail", response_data.get("message", "Unknown error"))
                print(f"🚫 Error: {error_detail}")
                
                failed_logins.append({
                    "email": email,
                    "status": status_code,
                    "response_time": response_time,
                    "error": error_detail,
                    "is_invalid_credentials": False
                })
            
            # Print response body (truncated)
            print(f"📄 Response Body:")
            response_str = json.dumps(response_data, indent=2, ensure_ascii=False)
            if len(response_str) > 500:
                print(f"{response_str[:500]}...")
            else:
                print(response_str)
                
        except requests.exceptions.Timeout:
            print("❌ TIMEOUT ERROR - Request took longer than 30 seconds")
            failed_logins.append({
                "email": email,
                "status": "TIMEOUT",
                "response_time": "30000+",
                "error": "Request timeout",
                "is_invalid_credentials": False
            })
            
        except requests.exceptions.ConnectionError:
            print("❌ CONNECTION ERROR - Could not connect to server")
            failed_logins.append({
                "email": email,
                "status": "CONNECTION_ERROR",
                "response_time": "N/A",
                "error": "Connection failed",
                "is_invalid_credentials": False
            })
            
        except Exception as e:
            print(f"❌ UNEXPECTED ERROR: {str(e)}")
            failed_logins.append({
                "email": email,
                "status": "ERROR",
                "response_time": "N/A",
                "error": str(e),
                "is_invalid_credentials": False
            })
        
        # Small delay between requests
        time.sleep(0.5)
    
    # Print summary
    print("\n" + "=" * 80)
    print("📊 TEST SONUÇLARI ÖZET")
    print("=" * 80)
    
    print(f"\n✅ BAŞARILI LOGIN'LER ({len(successful_logins)}/{len(TEST_CREDENTIALS)}):")
    if successful_logins:
        for login in successful_logins:
            print(f"  • {login['email']} - {login['user_role']} - {login['user_name']}")
    else:
        print("  Hiç başarılı login yok")
    
    print(f"\n❌ BAŞARISIZ LOGIN'LER ({len(failed_logins)}/{len(TEST_CREDENTIALS)}):")
    if failed_logins:
        for login in failed_logins:
            status_info = f"HTTP {login['status']}" if isinstance(login['status'], int) else login['status']
            print(f"  • {login['email']} - {status_info} - {login['error']}")
    else:
        print("  Hiç başarısız login yok")
    
    # Specific 401 Invalid Credentials check
    invalid_credentials_count = sum(1 for login in failed_logins if login.get('is_invalid_credentials', False))
    print(f"\n🚫 401 Invalid Credentials: {invalid_credentials_count} kullanıcı")
    
    print(f"\n📈 Genel Başarı Oranı: {len(successful_logins)}/{len(TEST_CREDENTIALS)} ({len(successful_logins)/len(TEST_CREDENTIALS)*100:.1f}%)")
    
    return {
        "successful_logins": successful_logins,
        "failed_logins": failed_logins,
        "total_tests": len(TEST_CREDENTIALS),
        "success_rate": len(successful_logins)/len(TEST_CREDENTIALS)*100
    }

if __name__ == "__main__":
    results = test_login_endpoint()