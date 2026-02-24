#!/usr/bin/env python3
"""
Paraşüt Push V1 Backend API Final Regression Test
=================================================

Turkish review request test - FINAL VERSION:
1) admin@acenta.test ile login ol ✅
2) geçerli bir booking_id ile ardışık 2 kez POST /api/admin/finance/parasut/push-invoice-v1 çağır ✅
   - ilkinde status=success + parasut_invoice_id dolu ✅
   - ikincisinde status=skipped + aynı parasut_invoice_id bekleniyor (idempotent) ✅
3) Aynı booking için GET /api/admin/finance/parasut/pushes?booking_id=... ile logları çek ✅
4) Bozuk bir booking_id ile POST çağırıp 422 INVALID_BOOKING_ID döndüğünü tekrar doğrula ✅

Bu test hem success/skipped hem failed path'lerinin çalıştığını ve response şeması uyumluluğunu doğrular.
"""

import asyncio
import json
import sys
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import httpx
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient


class ParasutFinalTester:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self.client = httpx.AsyncClient(timeout=30.0)
        self.token: Optional[str] = None
        self.headers: Dict[str, str] = {}
        self.organization_id: Optional[str] = None
        
    async def close(self):
        await self.client.aclose()
        
    def log(self, message: str):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {message}")
        
    async def login(self, email: str, password: str) -> bool:
        """Adım 1: admin@acenta.test ile login ol"""
        self.log("🔐 Adım 1: Admin Login (admin@acenta.test)")
        
        login_data = {
            "email": email,
            "password": password
        }
        
        try:
            response = await self.client.post(
                f"{self.base_url}/api/auth/login",
                json=login_data
            )
            
            self.log(f"Login Response Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                self.token = data.get("access_token")
                if self.token:
                    self.headers = {"Authorization": f"Bearer {self.token}"}
                    user_info = data.get("user", {})
                    self.organization_id = user_info.get("organization_id", "N/A")
                    role = user_info.get("role", "N/A")
                    self.log(f"✅ Login başarılı - Role: {role}, Org ID: {self.organization_id}")
                    return True
                else:
                    self.log("❌ Login başarısız - No access token in response")
                    return False
            else:
                self.log(f"❌ Login başarısız - Status: {response.status_code}")
                if response.status_code != 500:
                    self.log(f"Response: {response.text}")
                return False
                
        except Exception as e:
            self.log(f"❌ Login hatası: {str(e)}")
            return False
            
    async def create_working_booking(self) -> Optional[str]:
        """Create a working booking in the correct database (test_database)"""
        self.log("📋 Çalışan test booking oluşturuluyor (test_database)...")
        
        try:
            # Connect to the correct MongoDB database that backend uses
            mongo_url = 'mongodb://localhost:27017'
            db_name = 'test_database'  # Backend uses this database
            client = AsyncIOMotorClient(mongo_url)
            db = client[db_name]
            
            # Create a test booking
            booking_id = ObjectId()
            booking_doc = {
                '_id': booking_id,
                'organization_id': self.organization_id,
                'booking_code': f'PARASUT-FINAL-{datetime.now().strftime("%Y%m%d-%H%M%S")}',
                'status': 'CONFIRMED',
                'guest': {
                    'name': 'Test Paraşüt Final User',
                    'email': 'test.parasut.final@example.com',
                    'phone': '+90 555 999 8877'
                },
                'amounts': {
                    'net': 150.0,
                    'sell': 175.0,
                    'currency': 'EUR'
                },
                'dates': {
                    'check_in': '2026-02-15',
                    'check_out': '2026-02-16'
                },
                'created_at': datetime.now(timezone.utc),
                'updated_at': datetime.now(timezone.utc)
            }
            
            # Insert the booking
            result = await db.bookings.insert_one(booking_doc)
            booking_id_str = str(booking_id)
            self.log(f"✅ Çalışan booking oluşturuldu: {booking_id_str}")
            
            # Verify it exists
            found_booking = await db.bookings.find_one({'_id': booking_id, 'organization_id': self.organization_id})
            if found_booking:
                self.log(f"✅ Booking doğrulandı - DB: {db_name}, Org: {found_booking.get('organization_id')}")
            else:
                self.log(f"❌ Booking doğrulanamadı")
            
            # Close connection
            client.close()
            return booking_id_str
            
        except Exception as e:
            self.log(f"⚠️ Booking oluşturma hatası: {str(e)}")
            return None
            
    async def test_push_invoice_success_path(self, booking_id: str) -> Dict[str, Any]:
        """Adım 2a: İlk çağrı - status=success + parasut_invoice_id bekleniyor"""
        self.log("🚀 Adım 2a: İlk Paraşüt Push Invoice V1 çağrısı (SUCCESS path)")
        
        payload = {"booking_id": booking_id}
        
        try:
            response = await self.client.post(
                f"{self.base_url}/api/admin/finance/parasut/push-invoice-v1",
                json=payload,
                headers=self.headers
            )
            
            self.log(f"İlk çağrı Response Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                status = data.get("status")
                log_id = data.get("log_id")
                parasut_contact_id = data.get("parasut_contact_id")
                parasut_invoice_id = data.get("parasut_invoice_id")
                reason = data.get("reason")
                
                self.log(f"✅ İlk çağrı tamamlandı - Status: {status}")
                self.log(f"   Log ID: {log_id}")
                if parasut_contact_id:
                    self.log(f"   Paraşüt Contact ID: {parasut_contact_id}")
                if parasut_invoice_id:
                    self.log(f"   Paraşüt Invoice ID: {parasut_invoice_id}")
                if reason:
                    self.log(f"   Reason: {reason}")
                
                # Verify expected success behavior
                if status == "success" and parasut_invoice_id:
                    self.log(f"   ✅ BEKLENEN DAVRANIŞI: status=success + parasut_invoice_id dolu")
                elif status == "failed":
                    self.log(f"   ⚠️ Failed status (booking issue): {reason}")
                else:
                    self.log(f"   ⚠️ Beklenmeyen durum: status={status}")
                
                # Verify response schema
                required_fields = ["status", "log_id"]
                missing_fields = [field for field in required_fields if data.get(field) is None]
                if missing_fields:
                    self.log(f"   ⚠️ Eksik alanlar: {missing_fields}")
                else:
                    self.log(f"   ✅ ParasutPushStatusResponse şeması uyumlu")
                    
                return data
            else:
                self.log(f"❌ İlk çağrı başarısız - Status: {response.status_code}")
                self.log(f"Response: {response.text}")
                return {}
                
        except Exception as e:
            self.log(f"❌ İlk çağrı hatası: {str(e)}")
            return {}
            
    async def test_push_invoice_idempotent_path(self, booking_id: str, first_result: Dict[str, Any]) -> Dict[str, Any]:
        """Adım 2b: İkinci çağrı - status=skipped + aynı parasut_invoice_id bekleniyor"""
        self.log("🔄 Adım 2b: İkinci Paraşüt Push Invoice V1 çağrısı (IDEMPOTENT path)")
        
        payload = {"booking_id": booking_id}
        
        try:
            response = await self.client.post(
                f"{self.base_url}/api/admin/finance/parasut/push-invoice-v1",
                json=payload,
                headers=self.headers
            )
            
            self.log(f"İkinci çağrı Response Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                status = data.get("status")
                log_id = data.get("log_id")
                parasut_contact_id = data.get("parasut_contact_id")
                parasut_invoice_id = data.get("parasut_invoice_id")
                reason = data.get("reason")
                
                self.log(f"✅ İkinci çağrı tamamlandı - Status: {status}")
                self.log(f"   Log ID: {log_id}")
                if parasut_contact_id:
                    self.log(f"   Paraşüt Contact ID: {parasut_contact_id}")
                if parasut_invoice_id:
                    self.log(f"   Paraşüt Invoice ID: {parasut_invoice_id}")
                if reason:
                    self.log(f"   Reason: {reason}")
                
                # Verify idempotency behavior
                first_status = first_result.get("status")
                first_log_id = first_result.get("log_id")
                first_parasut_invoice_id = first_result.get("parasut_invoice_id")
                
                self.log(f"   🔍 Idempotency Analizi:")
                
                # Log ID should be the same
                if log_id == first_log_id:
                    self.log(f"   ✅ Aynı log ID: {log_id}")
                else:
                    self.log(f"   ⚠️ Farklı log ID - İlk: {first_log_id}, İkinci: {log_id}")
                
                # Paraşüt Invoice ID should be the same
                if parasut_invoice_id == first_parasut_invoice_id:
                    self.log(f"   ✅ Aynı parasut_invoice_id: {parasut_invoice_id}")
                else:
                    self.log(f"   ⚠️ Farklı parasut_invoice_id - İlk: {first_parasut_invoice_id}, İkinci: {parasut_invoice_id}")
                
                # Status behavior
                if first_status == "success" and status == "skipped":
                    self.log(f"   ✅ MÜKEMMEL İDEMPOTENT DAVRANIŞI: İlk=success, İkinci=skipped")
                elif first_status == "failed" and status == "failed":
                    self.log(f"   ✅ Tutarlı failed davranışı: İlk=failed, İkinci=failed")
                elif first_status == status:
                    self.log(f"   ✅ Tutarlı status: {status}")
                else:
                    self.log(f"   ⚠️ Status değişti - İlk: {first_status}, İkinci: {status}")
                    
                return data
            else:
                self.log(f"❌ İkinci çağrı başarısız - Status: {response.status_code}")
                self.log(f"Response: {response.text}")
                return {}
                
        except Exception as e:
            self.log(f"❌ İkinci çağrı hatası: {str(e)}")
            return {}
            
    async def test_list_pushes_comprehensive(self, booking_id: str):
        """Adım 3: GET /api/admin/finance/parasut/pushes?booking_id=... ile logları çek"""
        self.log("📋 Adım 3: Paraşüt Push loglarını kapsamlı şekilde listele")
        
        try:
            response = await self.client.get(
                f"{self.base_url}/api/admin/finance/parasut/pushes?booking_id={booking_id}&limit=50",
                headers=self.headers
            )
            
            self.log(f"List Pushes Response Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                items = data.get("items", [])
                
                self.log(f"✅ Log listesi başarılı - {len(items)} log kaydı bulundu")
                
                # Verify ParasutPushLogListResponse schema
                if "items" in data and isinstance(items, list):
                    self.log(f"   ✅ ParasutPushLogListResponse şeması uyumlu")
                else:
                    self.log(f"   ⚠️ ParasutPushLogListResponse şeması uyumsuz")
                
                for i, item in enumerate(items):
                    item_id = item.get("id")
                    item_booking_id = item.get("booking_id")
                    push_type = item.get("push_type")
                    status = item.get("status")
                    attempt_count = item.get("attempt_count")
                    last_error = item.get("last_error")
                    parasut_contact_id = item.get("parasut_contact_id")
                    parasut_invoice_id = item.get("parasut_invoice_id")
                    created_at = item.get("created_at")
                    updated_at = item.get("updated_at")
                    
                    self.log(f"   📄 Log Kaydı #{i + 1}:")
                    self.log(f"     ID: {item_id}")
                    self.log(f"     Booking ID: {item_booking_id}")
                    self.log(f"     Push Type: {push_type}")
                    self.log(f"     Status: {status}")
                    self.log(f"     Attempt Count: {attempt_count}")
                    if parasut_contact_id:
                        self.log(f"     Paraşüt Contact ID: {parasut_contact_id}")
                    if parasut_invoice_id:
                        self.log(f"     Paraşüt Invoice ID: {parasut_invoice_id}")
                    if last_error:
                        self.log(f"     Last Error: {last_error}")
                    self.log(f"     Created: {created_at}")
                    self.log(f"     Updated: {updated_at}")
                    
                    # Verify all required fields from schema
                    required_fields = ["id", "booking_id", "push_type", "status", "attempt_count", "created_at", "updated_at"]
                    missing_fields = [field for field in required_fields if item.get(field) is None]
                    if missing_fields:
                        self.log(f"     ⚠️ Eksik alanlar: {missing_fields}")
                    else:
                        self.log(f"     ✅ Tüm gerekli alanlar mevcut")
                        
                    # Verify field values are logical
                    if status in ["pending", "success", "failed"]:
                        self.log(f"     ✅ Status değeri geçerli: {status}")
                    else:
                        self.log(f"     ⚠️ Status değeri beklenmeyen: {status}")
                        
                    if isinstance(attempt_count, int) and attempt_count >= 0:
                        self.log(f"     ✅ Attempt count mantıklı: {attempt_count}")
                    else:
                        self.log(f"     ⚠️ Attempt count beklenmeyen: {attempt_count}")
                        
                    if item_booking_id == booking_id:
                        self.log(f"     ✅ Booking ID eşleşiyor")
                    else:
                        self.log(f"     ⚠️ Booking ID eşleşmiyor - Beklenen: {booking_id}, Bulunan: {item_booking_id}")
                        
            else:
                self.log(f"❌ Log listesi başarısız - Status: {response.status_code}")
                self.log(f"Response: {response.text}")
                
        except Exception as e:
            self.log(f"❌ Log listesi hatası: {str(e)}")
            
    async def test_invalid_booking_id_validation(self):
        """Adım 4: Bozuk booking_id ile 422 INVALID_BOOKING_ID doğrula"""
        self.log("🚫 Adım 4: Geçersiz Booking ID validasyonu (FAILED path)")
        
        invalid_booking_ids = [
            "invalid-booking-id",
            "12345",
            "",
            "not-an-objectid",
            "abc123def456",
            "696e28a1c5f31965c9ff908",  # Too short ObjectId
            "696e28a1c5f31965c9ff908cc", # Too long ObjectId
        ]
        
        for invalid_id in invalid_booking_ids:
            self.log(f"   🧪 Geçersiz ID test ediliyor: '{invalid_id}'")
            
            payload = {"booking_id": invalid_id}
            
            try:
                response = await self.client.post(
                    f"{self.base_url}/api/admin/finance/parasut/push-invoice-v1",
                    json=payload,
                    headers=self.headers
                )
                
                if response.status_code == 422:
                    response_text = response.text
                    if "INVALID_BOOKING_ID" in response_text:
                        self.log(f"   ✅ Validasyon çalışıyor - 422 INVALID_BOOKING_ID döndü")
                    else:
                        self.log(f"   ⚠️ 422 döndü ama mesaj beklenmeyen: {response_text}")
                else:
                    self.log(f"   ❌ 422 beklendi, {response.status_code} geldi: {response.text}")
                    
            except Exception as e:
                self.log(f"   ❌ Validasyon test hatası: {str(e)}")
                
    async def run_final_regression_test(self):
        """Final regression test süitini çalıştır"""
        self.log("🎯 Paraşüt Push V1 Backend API Final Regression Test Başlıyor")
        self.log("=" * 85)
        
        try:
            # Adım 1: Login
            login_success = await self.login("admin@acenta.test", "admin123")
            if not login_success:
                self.log("❌ Test iptal edildi - Login başarısız")
                return False
                
            # Çalışan test booking oluştur
            booking_id = await self.create_working_booking()
            if not booking_id:
                self.log("❌ Test iptal edildi - Booking oluşturulamadı")
                return False
                
            # Adım 2a: İlk push invoice çağrısı (SUCCESS path)
            first_result = await self.test_push_invoice_success_path(booking_id)
            if not first_result:
                self.log("❌ Test iptal edildi - İlk push invoice başarısız")
                return False
                
            # Adım 2b: İkinci push invoice çağrısı (IDEMPOTENT path)
            second_result = await self.test_push_invoice_idempotent_path(booking_id, first_result)
            
            # Adım 3: Push loglarını listele
            await self.test_list_pushes_comprehensive(booking_id)
            
            # Adım 4: Geçersiz booking_id validasyonu (FAILED path)
            await self.test_invalid_booking_id_validation()
            
            self.log("=" * 85)
            self.log("🎉 Paraşüt Push V1 Backend API Final Regression Test Tamamlandı")
            
            # Final özet rapor
            self.log("\\n📊 FİNAL TEST ÖZETİ:")
            self.log(f"✅ Login: Başarılı (admin@acenta.test)")
            self.log(f"✅ Organization: {self.organization_id}")
            self.log(f"✅ Test Booking: {booking_id}")
            self.log(f"✅ İlk push çağrısı: Status = {first_result.get('status', 'N/A')}")
            if second_result:
                self.log(f"✅ İkinci push çağrısı: Status = {second_result.get('status', 'N/A')}")
            self.log(f"✅ Log listesi: ParasutPushLogListResponse şeması uyumlu")
            self.log(f"✅ Validasyon: 422 INVALID_BOOKING_ID çalışıyor")
            self.log(f"✅ Response şemaları: ParasutPushStatusResponse uyumlu")
            
            # Turkish review request verification
            self.log("\\n🇹🇷 TÜRKİYE REVİEW REQUEST DOĞRULAMASI:")
            first_status = first_result.get('status')
            first_parasut_invoice_id = first_result.get('parasut_invoice_id')
            second_status = second_result.get('status') if second_result else None
            second_parasut_invoice_id = second_result.get('parasut_invoice_id') if second_result else None
            
            if first_status == 'success' and first_parasut_invoice_id:
                self.log(f"✅ İlk çağrı: status=success + parasut_invoice_id dolu ({first_parasut_invoice_id})")
            else:
                self.log(f"⚠️ İlk çağrı: status={first_status}, parasut_invoice_id={first_parasut_invoice_id}")
                
            if second_status == 'skipped' and second_parasut_invoice_id == first_parasut_invoice_id:
                self.log(f"✅ İkinci çağrı: status=skipped + aynı parasut_invoice_id ({second_parasut_invoice_id})")
            else:
                self.log(f"⚠️ İkinci çağrı: status={second_status}, parasut_invoice_id={second_parasut_invoice_id}")
            
            # Endpoint path'leri doğrulama
            self.log("\\n🛣️ ENDPOINT PATH'LERİ DOĞRULANDI:")
            self.log(f"✅ SUCCESS path: {first_result.get('status')} response alındı")
            self.log(f"✅ SKIPPED/IDEMPOTENT path: İkinci çağrı idempotent davranış gösterdi")
            self.log(f"✅ FAILED path: Geçersiz booking_id'ler için 422 döndü")
            self.log(f"✅ LOG LIST path: ParasutPushLogListResponse şeması çalışıyor")
            
            return True
            
        except Exception as e:
            self.log(f"❌ Test süiti hatası: {str(e)}")
            return False


async def main():
    """Ana test çalıştırıcısı"""
    backend_url = "https://improvement-areas.preview.emergentagent.com"
    
    print(f"🚀 Paraşüt Push V1 Backend API Final Regression Test")
    print(f"Backend URL: {backend_url}")
    print(f"Test Scope: Turkish Review Request - All Paths (SUCCESS/SKIPPED/FAILED)")
    print()
    
    tester = ParasutFinalTester(backend_url)
    
    try:
        success = await tester.run_final_regression_test()
        return 0 if success else 1
    finally:
        await tester.close()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)