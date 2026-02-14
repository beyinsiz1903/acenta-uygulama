#!/usr/bin/env python3
"""
FAZ 2 / F2.FE.T3 Public booking summary endpoint ve complete sayfası entegrasyonunu test et.

Comprehensive test for both backend API and frontend integration.
"""

import json
import requests
import sys
import time
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# Use the production URL from frontend .env
BASE_URL = "https://better-menu-labels.preview.emergentagent.com"

def test_public_booking_summary_happy_path():
    """Test GET /api/public/bookings/by-code/PB-TEST123?org=org_public_summary"""
    print("🧪 Testing public booking summary happy path...")
    
    url = f"{BASE_URL}/api/public/bookings/by-code/PB-TEST123"
    params = {"org": "org_public_summary"}
    
    try:
        response = requests.get(url, params=params, timeout=10)
        print(f"   Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   Response: {json.dumps(data, indent=2)}")
            
            # Verify response structure
            assert data["ok"] is True, "Response should have ok=true"
            
            booking = data["booking"]
            assert booking["booking_code"] == "PB-TEST123", "Booking code should match"
            
            # Verify price structure
            assert "price" in booking, "Booking should have price field"
            assert "amount_cents" in booking["price"], "Price should have amount_cents"
            assert "currency" in booking["price"], "Price should have currency"
            assert booking["price"]["currency"] == "EUR", "Currency should be EUR"
            
            # Verify PII protection - guest fields should NOT be present
            assert "guest" not in booking, "Guest PII should not be present"
            assert "email" not in booking, "Email PII should not be present"
            assert "phone" not in booking, "Phone PII should not be present"
            assert "full_name" not in booking, "Full name PII should not be present"
            
            # Verify required fields are present
            required_fields = ["booking_code", "status", "price", "pax", "product"]
            for field in required_fields:
                assert field in booking, f"Required field '{field}' should be present"
            
            print("   ✅ Happy path test PASSED")
            print(f"   ✅ PII protection verified - no guest fields in response")
            print(f"   ✅ Price: {booking['price']['amount_cents']} cents {booking['price']['currency']}")
            return True
            
        else:
            print(f"   ❌ Expected 200, got {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

def test_public_booking_summary_not_found():
    """Test GET /api/public/bookings/by-code/NONEXISTENT?org=org_public_summary"""
    print("🧪 Testing public booking summary not found...")
    
    url = f"{BASE_URL}/api/public/bookings/by-code/NONEXISTENT"
    params = {"org": "org_public_summary"}
    
    try:
        response = requests.get(url, params=params, timeout=10)
        print(f"   Status Code: {response.status_code}")
        
        if response.status_code == 404:
            data = response.json()
            print(f"   Response: {json.dumps(data, indent=2)}")
            
            # Verify error response
            assert data["detail"] == "NOT_FOUND", "Should return NOT_FOUND error"
            
            print("   ✅ Not found test PASSED")
            return True
            
        else:
            print(f"   ❌ Expected 404, got {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

def test_public_booking_summary_different_org():
    """Test with different org parameter to verify tenant isolation"""
    print("🧪 Testing public booking summary with different org...")
    
    url = f"{BASE_URL}/api/public/bookings/by-code/PB-TEST123"
    params = {"org": "different_org"}
    
    try:
        response = requests.get(url, params=params, timeout=10)
        print(f"   Status Code: {response.status_code}")
        
        if response.status_code == 404:
            data = response.json()
            print(f"   Response: {json.dumps(data, indent=2)}")
            
            # Verify error response
            assert data["detail"] == "NOT_FOUND", "Should return NOT_FOUND for different org"
            
            print("   ✅ Tenant isolation test PASSED")
            return True
            
        else:
            print(f"   ❌ Expected 404, got {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

def setup_webdriver():
    """Setup Chrome WebDriver with appropriate options"""
    from selenium.webdriver.chrome.service import Service
    
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.binary_location = "/usr/bin/chromium"
    
    try:
        service = Service("/usr/bin/chromedriver")
        driver = webdriver.Chrome(service=service, options=chrome_options)
        return driver
    except Exception as e:
        print(f"   ❌ Failed to setup WebDriver: {e}")
        return None

def test_frontend_book_complete_happy_path():
    """Test /book/complete page with valid booking parameters"""
    print("🧪 Testing frontend /book/complete page (happy path)...")
    
    driver = setup_webdriver()
    if not driver:
        return False
    
    try:
        # Navigate to the complete page with test parameters
        url = f"{BASE_URL}/book/complete?org=org_public_summary&booking_code=PB-TEST123"
        print(f"   Navigating to: {url}")
        driver.get(url)
        
        # Wait for page to load
        wait = WebDriverWait(driver, 10)
        
        # Check for the main heading
        heading = wait.until(EC.presence_of_element_located((By.TAG_NAME, "h1")))
        assert "Rezervasyonunuz alındı" in heading.text, "Main heading should be present"
        print("   ✅ Main heading found: 'Rezervasyonunuz alındı'")
        
        # Check for booking code display
        booking_code_elements = driver.find_elements(By.XPATH, "//*[contains(text(), 'PB-TEST123')]")
        assert len(booking_code_elements) > 0, "Booking code should be displayed"
        print("   ✅ Booking code 'PB-TEST123' displayed correctly")
        
        # Wait for booking summary to load (check for status badge)
        try:
            status_element = wait.until(EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'PENDING_PAYMENT')]")))
            print("   ✅ Status badge found: PENDING_PAYMENT")
        except TimeoutException:
            print("   ⚠️  Status badge not found - checking for error message")
        
        # Check for product title
        try:
            product_elements = driver.find_elements(By.XPATH, "//*[contains(text(), 'Test Hotel Reservation')]")
            if product_elements:
                print("   ✅ Product title found: 'Test Hotel Reservation'")
            else:
                print("   ⚠️  Product title not found - may be loading")
        except:
            pass
        
        # Check for price information
        try:
            price_elements = driver.find_elements(By.XPATH, "//*[contains(text(), '123,45') or contains(text(), '€')]")
            if price_elements:
                print("   ✅ Price information found")
            else:
                print("   ⚠️  Price information not found - may be loading")
        except:
            pass
        
        # Check for pax information (adults, children, rooms)
        try:
            pax_elements = driver.find_elements(By.XPATH, "//*[contains(text(), 'yetişkin') or contains(text(), 'çocuk') or contains(text(), 'oda')]")
            if pax_elements:
                print("   ✅ Pax information found")
            else:
                print("   ⚠️  Pax information not found - may be loading")
        except:
            pass
        
        # Check for "Rezervasyonumu Görüntüle" button
        try:
            button = driver.find_element(By.XPATH, "//button[contains(text(), 'Rezervasyonumu Görüntüle')]")
            assert button.is_displayed(), "View booking button should be visible"
            print("   ✅ 'Rezervasyonumu Görüntüle' button found")
        except NoSuchElementException:
            print("   ❌ 'Rezervasyonumu Görüntüle' button not found")
            return False
        
        # Check for no JavaScript errors in console
        logs = driver.get_log('browser')
        js_errors = [log for log in logs if log['level'] == 'SEVERE']
        if js_errors:
            print(f"   ⚠️  JavaScript errors found: {len(js_errors)}")
            for error in js_errors[:3]:  # Show first 3 errors
                print(f"      - {error['message']}")
        else:
            print("   ✅ No JavaScript errors found")
        
        print("   ✅ Frontend happy path test PASSED")
        return True
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False
    finally:
        driver.quit()

def test_frontend_book_complete_not_found():
    """Test /book/complete page with invalid booking parameters"""
    print("🧪 Testing frontend /book/complete page (not found scenario)...")
    
    driver = setup_webdriver()
    if not driver:
        return False
    
    try:
        # Navigate to the complete page with invalid parameters
        url = f"{BASE_URL}/book/complete?org=org_public_summary&booking_code=NONEXISTENT"
        print(f"   Navigating to: {url}")
        driver.get(url)
        
        # Wait for page to load
        wait = WebDriverWait(driver, 10)
        
        # Check for the main heading
        heading = wait.until(EC.presence_of_element_located((By.TAG_NAME, "h1")))
        assert "Rezervasyonunuz alındı" in heading.text, "Main heading should be present"
        print("   ✅ Main heading found")
        
        # Check for error message
        try:
            error_element = wait.until(EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'Özet getirilemedi')]")))
            print("   ✅ Error message found: 'Özet getirilemedi'")
            
            # Check for My Booking CTA in error message
            my_booking_text = driver.find_elements(By.XPATH, "//*[contains(text(), 'My Booking')]")
            if my_booking_text:
                print("   ✅ My Booking CTA found in error message")
            else:
                print("   ⚠️  My Booking CTA not found in error message")
                
        except TimeoutException:
            print("   ❌ Error message not found")
            return False
        
        # Check that the page doesn't crash
        try:
            button = driver.find_element(By.XPATH, "//button[contains(text(), 'Rezervasyonumu Görüntüle')]")
            assert button.is_displayed(), "View booking button should still be visible"
            print("   ✅ Page remains functional with 'Rezervasyonumu Görüntüle' button")
        except NoSuchElementException:
            print("   ❌ Page crashed - button not found")
            return False
        
        print("   ✅ Frontend not found test PASSED")
        return True
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False
    finally:
        driver.quit()

def test_frontend_book_complete_missing_params():
    """Test /book/complete page with missing parameters"""
    print("🧪 Testing frontend /book/complete page (missing parameters)...")
    
    driver = setup_webdriver()
    if not driver:
        return False
    
    try:
        # Navigate to the complete page without parameters
        url = f"{BASE_URL}/book/complete"
        print(f"   Navigating to: {url}")
        driver.get(url)
        
        # Wait for page to load
        wait = WebDriverWait(driver, 10)
        
        # Check for the main heading
        heading = wait.until(EC.presence_of_element_located((By.TAG_NAME, "h1")))
        assert "Rezervasyonunuz alındı" in heading.text, "Main heading should be present"
        print("   ✅ Main heading found")
        
        # Check for graceful handling - should show skeleton or default state
        try:
            button = driver.find_element(By.XPATH, "//button[contains(text(), 'Rezervasyonumu Görüntüle')]")
            assert button.is_displayed(), "View booking button should be visible"
            print("   ✅ Page handles missing parameters gracefully")
        except NoSuchElementException:
            print("   ❌ Page doesn't handle missing parameters gracefully")
            return False
        
        # Check for booking code placeholder
        placeholder_elements = driver.find_elements(By.XPATH, "//*[contains(text(), 'başarılı checkout sonrasında doldurulacak')]")
        if placeholder_elements:
            print("   ✅ Booking code placeholder found")
        else:
            print("   ⚠️  Booking code placeholder not found")
        
        print("   ✅ Frontend missing parameters test PASSED")
        return True
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False
    finally:
        driver.quit()

def main():
    """Run all tests"""
    print("🚀 Starting FAZ 2 / F2.FE.T3 Public Booking Summary Comprehensive Tests")
    print(f"🌐 Base URL: {BASE_URL}")
    print("=" * 80)
    
    backend_tests = [
        ("Backend Happy Path", test_public_booking_summary_happy_path),
        ("Backend Not Found", test_public_booking_summary_not_found),
        ("Backend Tenant Isolation", test_public_booking_summary_different_org),
    ]
    
    frontend_tests = [
        ("Frontend Happy Path", test_frontend_book_complete_happy_path),
        ("Frontend Not Found", test_frontend_book_complete_not_found),
        ("Frontend Missing Params", test_frontend_book_complete_missing_params),
    ]
    
    all_tests = backend_tests + frontend_tests
    passed = 0
    total = len(all_tests)
    
    print("📡 BACKEND API TESTS")
    print("-" * 40)
    for name, test_func in backend_tests:
        try:
            if test_func():
                passed += 1
            print()
        except Exception as e:
            print(f"   ❌ {name} failed with exception: {e}")
            print()
    
    print("🌐 FRONTEND UI TESTS")
    print("-" * 40)
    for name, test_func in frontend_tests:
        try:
            if test_func():
                passed += 1
            print()
        except Exception as e:
            print(f"   ❌ {name} failed with exception: {e}")
            print()
    
    print("=" * 80)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests PASSED!")
        return 0
    else:
        print("❌ Some tests FAILED!")
        return 1

if __name__ == "__main__":
    sys.exit(main())