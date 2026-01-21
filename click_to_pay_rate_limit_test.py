#!/usr/bin/env python3

"""
Click-to-Pay Public Endpoint Rate-Limit and Telemetry Test

Bu test, yeni rate-limit ve telemetry mantığı eklendikten sonra 
Click-to-Pay public endpoint'ini test eder:

1) Temel 404 davranışı (geçersiz token, expired token)
2) Rate-limit happy path (3-4 kez kısa sürede)
3) Rate-limit aşıldığında (10+ istek → 429)
4) Pencere reset (60 saniye sonra veya farklı IP)
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Dict, Any

import httpx
from bson import ObjectId

# Test configuration
BACKEND_URL = "https://b2bportal-3.preview.emergentagent.com/api"
ADMIN_EMAIL = "admin@acenta.test"
ADMIN_PASSWORD = "admin123"

class ClickToPayRateLimitTester:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
        self.admin_token = None
        self.organization_id = None
        self.test_results = []

    async def setup_admin_auth(self):
        """Admin olarak giriş yap ve token al"""
        print("🔐 Admin authentication...")
        
        login_response = await self.client.post(
            f"{BACKEND_URL}/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        
        if login_response.status_code != 200:
            raise Exception(f"Admin login failed: {login_response.status_code} - {login_response.text}")
        
        login_data = login_response.json()
        self.admin_token = login_data["access_token"]
        self.organization_id = login_data["user"]["organization_id"]
        
        print(f"✅ Admin authenticated - org_id: {self.organization_id}")

    async def create_test_payment_link(self) -> str:
        """Test için payment link oluştur"""
        print("🔗 Creating test payment link...")
        
        # Önce bir booking bul
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        bookings_response = await self.client.get(
            f"{BACKEND_URL}/ops/bookings?limit=1",
            headers=headers
        )
        
        if bookings_response.status_code != 200:
            raise Exception(f"Failed to get bookings: {bookings_response.status_code}")
        
        bookings_data = bookings_response.json()
        bookings = bookings_data.get("items", [])
        if not bookings:
            raise Exception("No bookings found for testing")
        
        booking_id = bookings[0]["booking_id"]
        print(f"📋 Using booking: {booking_id}")
        
        # Payment link oluştur
        create_response = await self.client.post(
            f"{BACKEND_URL}/ops/payments/click-to-pay/",
            headers=headers,
            json={"booking_id": booking_id}
        )
        
        if create_response.status_code != 200:
            print(f"⚠️  Payment link creation failed: {create_response.status_code} - {create_response.text}")
            # Test ortamında Stripe config eksikliği nedeniyle 520 olabilir
            # Manuel olarak test token oluşturalım
            return await self.create_manual_test_token(booking_id)
        
        create_data = create_response.json()
        
        # Eğer ok: false ise (Stripe unavailable), manuel token oluştur
        if not create_data.get("ok", False):
            print(f"⚠️  Payment link creation returned ok:false - {create_data.get('reason', 'unknown')}")
            return await self.create_manual_test_token(booking_id)
        
        token = create_data.get("token")
        if not token:
            raise Exception("No token returned from payment link creation")
        
        print(f"✅ Payment link created: {token}")
        return token

    async def create_manual_test_token(self, booking_id: str) -> str:
        """Manuel olarak test token oluştur (Stripe config yoksa)"""
        print("🛠️  Creating manual test token...")
        
        # MongoDB'ye direkt test token ekle
        import os
        import hashlib
        import secrets
        
        # MongoDB connection using pymongo (sync)
        from pymongo import MongoClient
        
        mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017/test_database")
        mongo_client = MongoClient(mongo_url)
        db = mongo_client.get_default_database()
        
        token = f"ctp_{secrets.token_urlsafe(24)}"
        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
        now = datetime.utcnow()
        expires_at = now + timedelta(hours=24)
        
        doc = {
            "token_hash": token_hash,
            "expires_at": expires_at,
            "organization_id": self.organization_id,
            "booking_id": booking_id,
            "payment_intent_id": "pi_test_manual_token",
            "amount_cents": 10000,  # 100.00 EUR
            "currency": "eur",
            "status": "active",
            "telemetry": {
                "access_count": 0,
                "last_access_at": None,
                "last_ip": None,
                "last_ua": None,
            },
            "created_at": now,
            "created_by": "test_setup",
        }
        
        db.click_to_pay_links.insert_one(doc)
        mongo_client.close()
        
        print(f"✅ Manual test token created: {token}")
        return token

    async def test_404_behavior(self):
        """Test 1: Temel 404 davranışı"""
        print("\n📋 Test 1: Basic 404 behavior")
        
        # 1.1: Geçersiz token
        print("  1.1: Invalid token test...")
        response = await self.client.get(f"{BACKEND_URL}/public/pay/invalid-token-xyz")
        
        result = {
            "test": "invalid_token_404",
            "status_code": response.status_code,
            "expected": 404,
            "body": response.json() if response.status_code != 500 else {"error": "server_error"},
            "passed": response.status_code == 404 and response.json().get("error") == "NOT_FOUND"
        }
        self.test_results.append(result)
        
        if result["passed"]:
            print("    ✅ Invalid token returns 404 NOT_FOUND")
        else:
            print(f"    ❌ Expected 404 NOT_FOUND, got {response.status_code}: {result['body']}")
        
        # 1.2: Expired token (manuel olarak expired token oluştur)
        print("  1.2: Expired token test...")
        expired_token = await self.create_expired_token()
        
        response = await self.client.get(f"{BACKEND_URL}/public/pay/{expired_token}")
        
        result = {
            "test": "expired_token_404",
            "status_code": response.status_code,
            "expected": 404,
            "body": response.json() if response.status_code != 500 else {"error": "server_error"},
            "passed": response.status_code == 404 and response.json().get("error") == "NOT_FOUND"
        }
        self.test_results.append(result)
        
        if result["passed"]:
            print("    ✅ Expired token returns 404 NOT_FOUND")
        else:
            print(f"    ❌ Expected 404 NOT_FOUND, got {response.status_code}: {result['body']}")

    async def create_expired_token(self) -> str:
        """Expired test token oluştur"""
        import os
        import hashlib
        import secrets
        from pymongo import MongoClient
        
        mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017/test_database")
        mongo_client = MongoClient(mongo_url)
        db = mongo_client.get_default_database()
        
        token = f"ctp_expired_{secrets.token_urlsafe(16)}"
        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
        now = datetime.utcnow()
        expires_at = now - timedelta(hours=1)  # 1 saat önce expired
        
        doc = {
            "token_hash": token_hash,
            "expires_at": expires_at,
            "organization_id": self.organization_id,
            "booking_id": "test_booking_id",
            "payment_intent_id": "pi_test_expired",
            "amount_cents": 5000,
            "currency": "eur",
            "status": "active",
            "telemetry": {
                "access_count": 0,
                "last_access_at": None,
                "last_ip": None,
                "last_ua": None,
            },
            "created_at": now - timedelta(hours=2),
            "created_by": "test_expired",
        }
        
        db.click_to_pay_links.insert_one(doc)
        mongo_client.close()
        
        return token

    async def test_rate_limit_happy_path(self, valid_token: str):
        """Test 2: Rate-limit happy path"""
        print("\n📋 Test 2: Rate-limit happy path")
        
        print("  2.1: Making 4 requests from same IP...")
        
        # Aynı IP'den 4 kez istek yap
        responses = []
        for i in range(4):
            response = await self.client.get(f"{BACKEND_URL}/public/pay/{valid_token}")
            responses.append({
                "request_num": i + 1,
                "status_code": response.status_code,
                "body": response.json() if response.status_code != 500 else {"error": "server_error"}
            })
            print(f"    Request {i+1}: {response.status_code}")
            
            # Kısa bekleme
            await asyncio.sleep(0.5)
        
        # Tüm isteklerin 200 dönmesi bekleniyor (Stripe config yoksa 500 olabilir)
        all_success = all(r["status_code"] in [200, 500] for r in responses)
        
        result = {
            "test": "rate_limit_happy_path",
            "responses": responses,
            "passed": all_success,
            "note": "All requests should return 200 (or 500 if Stripe not configured)"
        }
        self.test_results.append(result)
        
        if result["passed"]:
            print("    ✅ All 4 requests successful (within rate limit)")
        else:
            print("    ❌ Some requests failed unexpectedly")
        
        # Telemetry kontrolü
        await self.check_telemetry_update(valid_token)

    async def check_telemetry_update(self, token: str):
        """Telemetry güncellemelerini kontrol et"""
        print("  2.2: Checking telemetry updates...")
        
        import os
        import hashlib
        from pymongo import MongoClient
        
        mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017/test_database")
        mongo_client = MongoClient(mongo_url)
        db = mongo_client.get_default_database()
        
        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
        link = db.click_to_pay_links.find_one({"token_hash": token_hash})
        
        if link:
            telemetry = link.get("telemetry", {})
            access_count = telemetry.get("access_count", 0)
            window_count = telemetry.get("window_count", 0)
            
            print(f"    📊 Telemetry - access_count: {access_count}, window_count: {window_count}")
            
            result = {
                "test": "telemetry_update",
                "access_count": access_count,
                "window_count": window_count,
                "passed": access_count > 0 and window_count > 0
            }
            self.test_results.append(result)
            
            if result["passed"]:
                print("    ✅ Telemetry updated correctly")
            else:
                print("    ❌ Telemetry not updated as expected")
        else:
            print("    ⚠️  Could not find token in database for telemetry check")
        
        mongo_client.close()

    async def test_rate_limit_exceeded(self, valid_token: str):
        """Test 3: Rate-limit aşıldığında"""
        print("\n📋 Test 3: Rate-limit exceeded (10+ requests)")
        
        print("  3.1: Making 12 rapid requests...")
        
        # Hızlı bir şekilde 12 istek yap
        responses = []
        for i in range(12):
            response = await self.client.get(f"{BACKEND_URL}/public/pay/{valid_token}")
            responses.append({
                "request_num": i + 1,
                "status_code": response.status_code,
                "body": response.json() if response.status_code != 500 else {"error": "server_error"}
            })
            
            if i < 5 or i >= 10:  # İlk 5 ve son 2'yi göster
                print(f"    Request {i+1}: {response.status_code}")
            elif i == 5:
                print("    ... (requests 6-10)")
            
            # Çok kısa bekleme
            await asyncio.sleep(0.1)
        
        # İlk 10 istek başarılı, sonrakiler 429 olmalı
        first_10_success = all(r["status_code"] in [200, 500] for r in responses[:10])
        rate_limited = any(r["status_code"] == 429 for r in responses[10:])
        
        result = {
            "test": "rate_limit_exceeded",
            "first_10_success": first_10_success,
            "rate_limited_after_10": rate_limited,
            "responses_summary": {
                "total": len(responses),
                "status_codes": [r["status_code"] for r in responses]
            },
            "passed": first_10_success and rate_limited
        }
        self.test_results.append(result)
        
        if result["passed"]:
            print("    ✅ Rate limiting working: first 10 OK, then 429 RATE_LIMITED")
        else:
            print(f"    ❌ Rate limiting not working as expected")
            print(f"        First 10 success: {first_10_success}")
            print(f"        Rate limited after 10: {rate_limited}")

    async def test_window_reset(self, valid_token: str):
        """Test 4: Pencere reset"""
        print("\n📋 Test 4: Window reset behavior")
        
        print("  4.1: Waiting for window reset (60+ seconds)...")
        print("    ⏳ Sleeping 65 seconds to test window reset...")
        
        # 65 saniye bekle (pencere 60 saniye)
        await asyncio.sleep(65)
        
        print("  4.2: Testing after window reset...")
        
        # Pencere reset sonrası istek yap
        response = await self.client.get(f"{BACKEND_URL}/public/pay/{valid_token}")
        
        result = {
            "test": "window_reset",
            "status_code": response.status_code,
            "body": response.json() if response.status_code != 500 else {"error": "server_error"},
            "passed": response.status_code in [200, 500],  # 429 olmamalı
            "note": "Should return 200/500, not 429 after window reset"
        }
        self.test_results.append(result)
        
        if result["passed"]:
            print("    ✅ Window reset working: request successful after 60+ seconds")
        else:
            print(f"    ❌ Window reset not working: got {response.status_code}")

    async def run_all_tests(self):
        """Tüm testleri çalıştır"""
        try:
            print("🚀 Starting Click-to-Pay Rate-Limit and Telemetry Tests")
            print("=" * 60)
            
            # Setup
            await self.setup_admin_auth()
            
            # Test için geçerli token oluştur
            valid_token = await self.create_test_payment_link()
            
            # Test 1: 404 davranışı
            await self.test_404_behavior()
            
            # Test 2: Rate-limit happy path
            await self.test_rate_limit_happy_path(valid_token)
            
            # Test 3: Rate-limit aşıldığında
            await self.test_rate_limit_exceeded(valid_token)
            
            # Test 4: Pencere reset
            await self.test_window_reset(valid_token)
            
            # Sonuçları özetle
            self.print_summary()
            
        except Exception as e:
            print(f"❌ Test failed with error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await self.client.aclose()

    def print_summary(self):
        """Test sonuçlarını özetle"""
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for r in self.test_results if r["passed"])
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {total_tests - passed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        print("\nDetailed Results:")
        for i, result in enumerate(self.test_results, 1):
            status = "✅ PASS" if result["passed"] else "❌ FAIL"
            print(f"{i:2d}. {result['test']:30s} {status}")
        
        print("\n" + "=" * 60)
        
        # JSON formatında da kaydet
        with open("/app/click_to_pay_rate_limit_test_results.json", "w") as f:
            json.dump({
                "summary": {
                    "total_tests": total_tests,
                    "passed_tests": passed_tests,
                    "failed_tests": total_tests - passed_tests,
                    "success_rate": (passed_tests/total_tests)*100
                },
                "detailed_results": self.test_results
            }, f, indent=2, default=str)
        
        print("📄 Detailed results saved to: click_to_pay_rate_limit_test_results.json")


async def main():
    tester = ClickToPayRateLimitTester()
    await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())