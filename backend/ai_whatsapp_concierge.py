"""
AI WhatsApp Concierge - GPT-4 Powered Guest Assistant
24/7 Otomatik misafir hizmeti WhatsApp üzerinden
"""
import json
from datetime import datetime, timezone
from typing import Optional, Dict, List

class AIWhatsAppConcierge:
    """AI-powered WhatsApp concierge service"""
    
    def __init__(self, db):
        self.db = db
        self.conversation_history = {}
    
    async def process_guest_message(self, phone: str, message: str, tenant_id: str) -> dict:
        """Misafir mesajını işle ve AI yanıtı oluştur"""
        # Find guest by phone
        guest = await self.db.guests.find_one({'phone': phone, 'tenant_id': tenant_id}, {'_id': 0})
        
        if not guest:
            return {
                'response': 'Merhaba! Size yardımcı olmak için telefon numaranızı sistemimizde bulamadım. Lütfen resepsiyonla iletişime geçin.',
                'action': None
            }
        
        # Get active booking
        booking = await self.db.bookings.find_one({
            'guest_id': guest['id'],
            'tenant_id': tenant_id,
            'status': 'checked_in'
        }, {'_id': 0})
        
        # Analyze intent using keywords (gerçekte GPT-4 kullanılır)
        message_lower = message.lower()
        
        # Intent: Room Service
        if any(word in message_lower for word in ['havlu', 'towel', 'şampuan', 'shampoo', 'room service']):
            return await self.handle_room_service(guest, booking, message)
        
        # Intent: Restaurant Reservation
        elif any(word in message_lower for word in ['restoran', 'restaurant', 'yemek', 'dinner', 'masa', 'table']):
            return await self.handle_restaurant_reservation(guest, booking, message)
        
        # Intent: Late Checkout
        elif any(word in message_lower for word in ['late checkout', 'geç çıkış', 'check-out']):
            return await self.handle_late_checkout(guest, booking, message)
        
        # Intent: Spa Booking
        elif any(word in message_lower for word in ['spa', 'masaj', 'massage']):
            return await self.handle_spa_booking(guest, booking, message)
        
        # Intent: Complaint
        elif any(word in message_lower for word in ['sorun', 'problem', 'şikayet', 'complaint']):
            return await self.handle_complaint(guest, booking, message)
        
        # General inquiry
        else:
            return {
                'response': f'''Merhaba {guest['name']}! Size nasıl yardımcı olabilirim?

Şunları yapabilirim:
🛎️ Room service siparişi
🍽️ Restoran rezervasyonu
💆 Spa randevusu
⏰ Late checkout talebi
🔧 Teknik destek

Lütfen isteğinizi yazın!''',
                'action': None
            }
    
    async def handle_room_service(self, guest: dict, booking: dict, message: str) -> dict:
        """Room service talebi"""
        if not booking:
            return {
                'response': 'Aktif rezervasyonunuz bulunamadı. Lütfen resepsiyonla iletişime geçin.',
                'action': None
            }
        
        # Create housekeeping task
        task = {
            'id': str(__import__('uuid').uuid4()),
            'tenant_id': booking['tenant_id'],
            'room_id': booking['room_id'],
            'task_type': 'room_service',
            'description': f'WhatsApp talebi: {message}',
            'priority': 'high',
            'status': 'pending',
            'requested_by': guest['id'],
            'created_at': datetime.now(timezone.utc).isoformat()
        }
        
        await self.db.housekeeping_tasks.insert_one(task)
        
        return {
            'response': f'''✅ Talebiniz alındı, {guest['name']}!

{message}

⏱️ 10-15 dakika içinde odanıza ulaştırılacak.

İyi günler! 🌟''',
            'action': 'housekeeping_task_created',
            'task_id': task['id']
        }
    
    async def handle_restaurant_reservation(self, guest: dict, booking: dict, message: str) -> dict:
        """Restoran rezervasyonu"""
        # Extract time (basit - gerçekte GPT-4 kullanılır)
        import re
        time_match = re.search(r'(\d{1,2})[:.](\d{2})|saat (\d{1,2})', message)
        
        if time_match:
            hour = time_match.group(1) or time_match.group(3)
            minute = time_match.group(2) or '00'
            time_str = f"{hour}:{minute}"
        else:
            time_str = '19:00'  # Default
        
        # Create restaurant reservation
        reservation = {
            'id': str(__import__('uuid').uuid4()),
            'tenant_id': booking['tenant_id'] if booking else guest.get('tenant_id'),
            'guest_id': guest['id'],
            'reservation_date': datetime.now(timezone.utc).date().isoformat(),
            'reservation_time': time_str,
            'party_size': 2,
            'status': 'confirmed',
            'source': 'whatsapp_ai',
            'created_at': datetime.now(timezone.utc).isoformat()
        }
        
        await self.db.restaurant_reservations.insert_one(reservation)
        
        return {
            'response': f'''✅ Rezervasyon oluşturuldu!

🍽️ Restoran: Hotel Restaurant
⏰ Saat: {time_str}
👥 Kişi sayısı: 2
📅 Tarih: Bugün

Rezervasyon No: {reservation['id'][:8].upper()}

Afiyet olsun! 🥂''',
            'action': 'restaurant_reservation_created',
            'reservation_id': reservation['id']
        }
    
    async def handle_late_checkout(self, guest: dict, booking: dict, message: str) -> dict:
        """Late checkout talebi"""
        if not booking:
            return {
                'response': 'Aktif rezervasyonunuz bulunamadı.',
                'action': None
            }
        
        # Check availability (simplified)
        # Gerçekte: Next booking check, room availability
        late_checkout_available = True
        
        if late_checkout_available:
            # Update booking
            await self.db.bookings.update_one(
                {'id': booking['id']},
                {'$set': {
                    'late_checkout_approved': True,
                    'checkout_time': '16:00'
                }}
            )
            
            # Add charge to folio
            charge = {
                'id': str(__import__('uuid').uuid4()),
                'tenant_id': booking['tenant_id'],
                'booking_id': booking['id'],
                'charge_category': 'late_checkout',
                'description': 'Late Checkout (16:00)',
                'amount': 35.0,
                'posted_at': datetime.now(timezone.utc).isoformat()
            }
            
            # Find folio
            folio = await self.db.folios.find_one({
                'booking_id': booking['id'],
                'folio_type': 'guest'
            }, {'_id': 0})
            
            if folio:
                charge['folio_id'] = folio['id']
                await self.db.folio_charges.insert_one(charge)
            
            return {
                'response': f'''✅ Late checkout onaylandı!

⏰ Yeni check-out saatiniz: 16:00
💰 Ücret: €35 (folio'nuza eklendi)

İyi günler! 🌟''',
                'action': 'late_checkout_approved',
                'charge_id': charge['id']
            }
        else:
            return {
                'response': 'Üzgünüz, bugün late checkout mümkün değil. Lütfen resepsiyonla görüşün.',
                'action': 'late_checkout_denied'
            }
    
    async def handle_spa_booking(self, guest: dict, booking: dict, message: str) -> dict:
        """Spa randevusu"""
        # Simplified - gerçekte GPT-4 ile treatment seçimi
        appointment = {
            'id': str(__import__('uuid').uuid4()),
            'tenant_id': booking['tenant_id'] if booking else guest.get('tenant_id'),
            'guest_id': guest['id'],
            'treatment_id': 'massage_60',
            'appointment_date': datetime.now(timezone.utc).isoformat(),
            'duration_minutes': 60,
            'price': 75.0,
            'charge_to_room': True,
            'status': 'confirmed',
            'source': 'whatsapp_ai',
            'created_at': datetime.now(timezone.utc).isoformat()
        }
        
        await self.db.spa_appointments.insert_one(appointment)
        
        return {
            'response': f'''✅ Spa randevunuz oluşturuldu!

💆 Treatment: Swedish Massage (60 dk)
💰 Fiyat: €75 (oda hesabınıza eklenecek)
⏰ Saat: En yakın müsait

Spa ekibimiz sizi arayacak.

Keyifli bir seans! 🧖''',
            'action': 'spa_appointment_created',
            'appointment_id': appointment['id']
        }
    
    async def handle_complaint(self, guest: dict, booking: dict, message: str) -> dict:
        """Şikayet yönetimi"""
        # Create service complaint
        complaint = {
            'id': str(__import__('uuid').uuid4()),
            'tenant_id': booking['tenant_id'] if booking else guest.get('tenant_id'),
            'guest_id': guest['id'],
            'booking_id': booking['id'] if booking else None,
            'category': 'service',  # Simplified
            'severity': 'medium',
            'description': message,
            'status': 'open',
            'source': 'whatsapp',
            'created_at': datetime.now(timezone.utc).isoformat()
        }
        
        await self.db.service_complaints.insert_one(complaint)
        
        # Alert MOD
        print(f"🚨 ALERT: Guest complaint via WhatsApp - {complaint['id']}")
        
        return {
            'response': f'''Üzgünüz {guest['name']}, yaşadığınız sorunu duyduğumuza çok üzüldük. 😔

Şikayetiniz kaydedildi ve yönetimimiz derhal haberdar edildi.

📞 Manager on Duty size 15 dakika içinde ulaşacak.

Anlayışınız için teşekkürler.''',
            'action': 'complaint_created',
            'complaint_id': complaint['id']
        }

# Global instance
ai_concierge = None

def get_ai_concierge(db):
    global ai_concierge
    if ai_concierge is None:
        ai_concierge = AIWhatsAppConcierge(db)
    return ai_concierge
