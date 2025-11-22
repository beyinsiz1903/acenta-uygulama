"""
Automatic Database Seeding for Hotel PMS
Runs on startup to create test data
"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from passlib.context import CryptContext
import uuid
from datetime import datetime, timezone, timedelta
import random

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class HotelSeeder:
    def __init__(self):
        self.client = AsyncIOMotorClient('mongodb://localhost:27017')
        self.db = self.client.hotel_pms
        self.tenant_id = "hotel-demo-tenant"
        
    async def clear_database(self):
        """Clear all collections"""
        collections = await self.db.list_collection_names()
        for collection in collections:
            await self.db[collection].delete_many({})
        print("✓ Database cleared")
    
    async def create_users(self):
        """Create admin and staff users"""
        users = [
            {
                'id': str(uuid.uuid4()),
                'email': 'admin@hotel.com',
                'name': 'Hotel Admin',
                'role': 'admin',
                'hashed_password': pwd_context.hash("admin123"),
                'tenant_id': None,
                'created_at': datetime.now(timezone.utc).isoformat(),
                'is_active': True
            },
            {
                'id': str(uuid.uuid4()),
                'email': 'frontdesk@hotel.com',
                'name': 'Ayşe Yılmaz',
                'role': 'front_desk',
                'hashed_password': pwd_context.hash("frontdesk123"),
                'tenant_id': None,
                'created_at': datetime.now(timezone.utc).isoformat(),
                'is_active': True
            },
            {
                'id': str(uuid.uuid4()),
                'email': 'housekeeping@hotel.com',
                'name': 'Fatma Demir',
                'role': 'housekeeping',
                'hashed_password': pwd_context.hash("housekeeping123"),
                'tenant_id': None,
                'created_at': datetime.now(timezone.utc).isoformat(),
                'is_active': True
            },
            {
                'id': str(uuid.uuid4()),
                'email': 'finance@hotel.com',
                'name': 'Mehmet Kaya',
                'role': 'finance',
                'hashed_password': pwd_context.hash("finance123"),
                'tenant_id': None,
                'created_at': datetime.now(timezone.utc).isoformat(),
                'is_active': True
            }
        ]
        await self.db.users.insert_many(users)
        print(f"✓ Created {len(users)} users")
        return users
    
    async def create_rooms(self):
        """Create hotel rooms"""
        rooms = []
        room_types = [
            {'type': 'Standard', 'rate': 100.0, 'count': 10},
            {'type': 'Deluxe', 'rate': 150.0, 'count': 8},
            {'type': 'Suite', 'rate': 250.0, 'count': 4},
            {'type': 'Presidential', 'rate': 500.0, 'count': 2}
        ]
        
        room_counter = 101
        for room_type_info in room_types:
            for _ in range(room_type_info['count']):
                floor = int(str(room_counter)[0])
                rooms.append({
                    'id': str(uuid.uuid4()),
                    'tenant_id': self.tenant_id,
                    'room_number': str(room_counter),
                    'room_type': room_type_info['type'],
                    'status': random.choice(['available', 'occupied', 'dirty', 'cleaning', 'inspected']),
                    'floor': floor,
                    'capacity': 2 if room_type_info['type'] in ['Standard', 'Deluxe'] else 4,
                    'bed_type': random.choice(['single', 'double', 'king', 'twin']),
                    'max_occupancy': 2 if room_type_info['type'] in ['Standard', 'Deluxe'] else 4,
                    'base_price': room_type_info['rate'],
                    'current_booking_id': None,
                    'is_active': True,
                    'amenities': ['TV', 'WiFi', 'Air Conditioning', 'Mini Bar'],
                    'created_at': datetime.now(timezone.utc).isoformat()
                })
                room_counter += 1
        
        await self.db.rooms.insert_many(rooms)
        print(f"✓ Created {len(rooms)} rooms")
        return rooms
    
    async def create_guests(self):
        """Create guest profiles"""
        turkish_names = [
            ('Ahmet', 'Yılmaz'), ('Mehmet', 'Demir'), ('Ayşe', 'Çelik'),
            ('Fatma', 'Şahin'), ('Ali', 'Öztürk'), ('Zeynep', 'Kaya'),
            ('Mustafa', 'Aydın'), ('Elif', 'Arslan'), ('Hasan', 'Yıldız'),
            ('Emine', 'Koç'), ('Can', 'Kurt'), ('Selin', 'Özdemir'),
            ('Burak', 'Aksoy'), ('Deniz', 'Çetin'), ('Ece', 'Karataş')
        ]
        
        guests = []
        for first_name, last_name in turkish_names:
            email = f"{first_name.lower()}.{last_name.lower()}@email.com"
            guests.append({
                'id': str(uuid.uuid4()),
                'tenant_id': self.tenant_id,
                'name': f"{first_name} {last_name}",
                'first_name': first_name,
                'last_name': last_name,
                'email': email,
                'phone': f"+90 5{random.randint(10, 99)} {random.randint(100, 999)} {random.randint(10, 99)} {random.randint(10, 99)}",
                'id_number': f'TR{random.randint(100000, 999999)}',
                'nationality': 'TR',
                'passport_number': f'TR{random.randint(100000, 999999)}',
                'date_of_birth': (datetime.now() - timedelta(days=random.randint(8000, 20000))).date().isoformat(),
                'address': f'İstanbul, Türkiye',
                'total_stays': random.randint(1, 10),
                'total_spend': round(random.uniform(500, 5000), 2),
                'vip_status': random.choice([True, False]),
                'preferences': {
                    'pillow_type': random.choice(['soft', 'firm']),
                    'floor_preference': random.choice(['low', 'high', 'any']),
                    'smoking': False
                },
                'created_at': datetime.now(timezone.utc).isoformat()
            })
        
        await self.db.guests.insert_many(guests)
        print(f"✓ Created {len(guests)} guests")
        return guests
    
    async def create_bookings(self, rooms, guests):
        """Create bookings (past, current, future)"""
        bookings = []
        now = datetime.now(timezone.utc)
        
        # Past bookings (checked out)
        for i in range(10):
            guest = random.choice(guests)
            room = random.choice(rooms)
            check_in = now - timedelta(days=random.randint(10, 60))
            check_out = check_in + timedelta(days=random.randint(1, 7))
            nights = (check_out - check_in).days
            
            bookings.append({
                'id': str(uuid.uuid4()),
                'tenant_id': self.tenant_id,
                'booking_number': f'BK{now.year}{random.randint(1000, 9999)}',
                'guest_id': guest['id'],
                'room_id': room['id'],
                'check_in': check_in.date().isoformat(),
                'check_out': check_out.date().isoformat(),
                'status': 'checked_out',
                'adults': random.randint(1, 2),
                'children': random.randint(0, 2),
                'guests_count': random.randint(1, 3),
                'total_amount': room['base_price'] * nights,
                'paid_amount': room['base_price'] * nights,
                'rate_code': 'BAR',
                'source': random.choice(['Direct', 'Booking.com', 'Expedia', 'Walk-in']),
                'special_requests': '',
                'created_at': (check_in - timedelta(days=random.randint(5, 30))).isoformat()
            })
        
        # Current bookings (checked in)
        for i in range(8):
            guest = random.choice(guests)
            room = random.choice([r for r in rooms if r['status'] == 'occupied'])
            check_in = now - timedelta(days=random.randint(0, 3))
            check_out = now + timedelta(days=random.randint(1, 5))
            nights = (check_out - check_in).days
            
            booking_id = str(uuid.uuid4())
            bookings.append({
                'id': booking_id,
                'tenant_id': self.tenant_id,
                'booking_number': f'BK{now.year}{random.randint(1000, 9999)}',
                'guest_id': guest['id'],
                'room_id': room['id'],
                'check_in': check_in.date().isoformat(),
                'check_out': check_out.date().isoformat(),
                'status': 'checked_in',
                'adults': random.randint(1, 2),
                'children': random.randint(0, 2),
                'guests_count': random.randint(1, 3),
                'total_amount': room['base_price'] * nights,
                'paid_amount': round(room['base_price'] * nights * random.uniform(0, 0.5), 2),
                'rate_code': 'BAR',
                'source': random.choice(['Direct', 'Booking.com', 'Expedia']),
                'special_requests': random.choice(['', 'High floor', 'Late check-out', 'Extra pillows']),
                'created_at': (check_in - timedelta(days=random.randint(5, 30))).isoformat()
            })
            
            # Update room with current booking
            await self.db.rooms.update_one(
                {'id': room['id']},
                {'$set': {'current_booking_id': booking_id, 'status': 'occupied'}}
            )
        
        # Future bookings (confirmed)
        for i in range(12):
            guest = random.choice(guests)
            room = random.choice(rooms)
            check_in = now + timedelta(days=random.randint(1, 30))
            check_out = check_in + timedelta(days=random.randint(1, 7))
            nights = (check_out - check_in).days
            
            bookings.append({
                'id': str(uuid.uuid4()),
                'tenant_id': self.tenant_id,
                'booking_number': f'BK{now.year}{random.randint(1000, 9999)}',
                'guest_id': guest['id'],
                'room_id': room['id'],
                'check_in': check_in.date().isoformat(),
                'check_out': check_out.date().isoformat(),
                'status': random.choice(['confirmed', 'guaranteed']),
                'adults': random.randint(1, 2),
                'children': random.randint(0, 2),
                'guests_count': random.randint(1, 3),
                'total_amount': room['base_price'] * nights,
                'paid_amount': 0.0,
                'rate_code': random.choice(['BAR', 'ADVANCE', 'CORPORATE']),
                'source': random.choice(['Direct', 'Booking.com', 'Expedia', 'Phone']),
                'special_requests': random.choice(['', 'Honeymoon', 'Anniversary', 'Birthday']),
                'created_at': (now - timedelta(days=random.randint(1, 10))).isoformat()
            })
        
        await self.db.bookings.insert_many(bookings)
        print(f"✓ Created {len(bookings)} bookings")
        return bookings
    
    async def create_folios(self, bookings):
        """Create folios for checked-in bookings"""
        folios = []
        folio_charges = []
        
        checked_in_bookings = [b for b in bookings if b['status'] == 'checked_in']
        
        for booking in checked_in_bookings:
            # Create guest folio
            folio_id = str(uuid.uuid4())
            folio_number = f"F-{datetime.now().year}-{random.randint(10000, 99999)}"
            
            folios.append({
                'id': folio_id,
                'folio_number': folio_number,
                'booking_id': booking['id'],
                'guest_id': booking['guest_id'],
                'folio_type': 'guest',
                'status': 'open',
                'balance': round(random.uniform(100, 500), 2),
                'created_at': datetime.now(timezone.utc).isoformat(),
                'closed_at': None
            })
            
            # Add room charges
            check_in_date = datetime.fromisoformat(booking['check_in']).date() if isinstance(booking['check_in'], str) else booking['check_in']
            nights_stayed = (datetime.now().date() - check_in_date).days
            for night in range(max(1, nights_stayed)):
                folio_charges.append({
                    'id': str(uuid.uuid4()),
                    'folio_id': folio_id,
                    'charge_date': (datetime.now() - timedelta(days=nights_stayed - night)).date().isoformat(),
                    'charge_category': 'room',
                    'description': f"Room Charge - Night {night + 1}",
                    'quantity': 1,
                    'unit_price': booking['total_amount'] / max(1, (datetime.fromisoformat(booking['check_out']).date() - datetime.fromisoformat(booking['check_in']).date()).days),
                    'amount': booking['total_amount'] / max(1, (datetime.fromisoformat(booking['check_out']).date() - datetime.fromisoformat(booking['check_in']).date()).days),
                    'tax_percentage': 18.0,
                    'tax_amount': 0.0,
                    'total': 0.0,
                    'voided': False,
                    'posted_by': 'System',
                    'created_at': datetime.now(timezone.utc).isoformat()
                })
            
            # Add F&B charges
            if random.random() > 0.5:
                folio_charges.append({
                    'id': str(uuid.uuid4()),
                    'folio_id': folio_id,
                    'charge_date': datetime.now().date().isoformat(),
                    'charge_category': 'food',
                    'description': 'Restaurant - Breakfast',
                    'quantity': 2,
                    'unit_price': 25.0,
                    'amount': 50.0,
                    'tax_percentage': 18.0,
                    'tax_amount': 9.0,
                    'total': 59.0,
                    'voided': False,
                    'posted_by': 'POS System',
                    'created_at': datetime.now(timezone.utc).isoformat()
                })
            
            # Add minibar charges
            if random.random() > 0.6:
                folio_charges.append({
                    'id': str(uuid.uuid4()),
                    'folio_id': folio_id,
                    'charge_date': datetime.now().date().isoformat(),
                    'charge_category': 'minibar',
                    'description': 'Minibar - Beverages',
                    'quantity': 1,
                    'unit_price': 35.0,
                    'amount': 35.0,
                    'tax_percentage': 18.0,
                    'tax_amount': 6.3,
                    'total': 41.3,
                    'voided': False,
                    'posted_by': 'Housekeeping',
                    'created_at': datetime.now(timezone.utc).isoformat()
                })
        
        if folios:
            await self.db.folios.insert_many(folios)
            print(f"✓ Created {len(folios)} folios")
        
        if folio_charges:
            await self.db.folio_charges.insert_many(folio_charges)
            print(f"✓ Created {len(folio_charges)} folio charges")
        
        return folios
    
    async def create_housekeeping_tasks(self, rooms):
        """Create housekeeping tasks"""
        tasks = []
        staff_names = ['Fatma', 'Ayşe', 'Zeynep', 'Elif', 'Emine']
        
        dirty_rooms = [r for r in rooms if r['status'] in ['dirty', 'cleaning']]
        
        for room in dirty_rooms[:15]:
            tasks.append({
                'id': str(uuid.uuid4()),
                'room_id': room['id'],
                'room_number': room['room_number'],
                'task_type': 'cleaning',
                'status': random.choice(['pending', 'in_progress', 'completed']),
                'priority': random.choice(['low', 'normal', 'high']),
                'assigned_to': random.choice(staff_names),
                'assigned_at': (datetime.now() - timedelta(hours=random.randint(0, 8))).isoformat(),
                'started_at': (datetime.now() - timedelta(hours=random.randint(0, 4))).isoformat() if random.random() > 0.5 else None,
                'completed_at': None,
                'notes': random.choice(['', 'Extra cleaning required', 'Guest requested deep clean']),
                'created_at': datetime.now(timezone.utc).isoformat()
            })
        
        if tasks:
            await self.db.housekeeping_tasks.insert_many(tasks)
            print(f"✓ Created {len(tasks)} housekeeping tasks")
        
        return tasks
    
    async def create_pos_data(self):
        """Create POS menu items and orders"""
        menu_items = [
            {'name': 'Türk Kahvesi', 'category': 'beverage', 'price': 25.0},
            {'name': 'Cappuccino', 'category': 'beverage', 'price': 30.0},
            {'name': 'Çay', 'category': 'beverage', 'price': 15.0},
            {'name': 'Menemen', 'category': 'food', 'price': 45.0},
            {'name': 'Serpme Kahvaltı', 'category': 'food', 'price': 120.0},
            {'name': 'İzgara Köfte', 'category': 'food', 'price': 85.0},
            {'name': 'Karışık Izgara', 'category': 'food', 'price': 150.0},
            {'name': 'Salata', 'category': 'food', 'price': 35.0},
            {'name': 'Baklava', 'category': 'dessert', 'price': 40.0},
            {'name': 'Künefe', 'category': 'dessert', 'price': 50.0},
            {'name': 'Rakı', 'category': 'alcohol', 'price': 180.0},
            {'name': 'Şarap (Şişe)', 'category': 'alcohol', 'price': 250.0}
        ]
        
        items = []
        for item_data in menu_items:
            items.append({
                'id': str(uuid.uuid4()),
                'name': item_data['name'],
                'category': item_data['category'],
                'price': item_data['price'],
                'cost': round(item_data['price'] * 0.4, 2),
                'is_active': True,
                'description': '',
                'created_at': datetime.now(timezone.utc).isoformat()
            })
        
        await self.db.menu_items.insert_many(items)
        print(f"✓ Created {len(items)} menu items")
        return items
    
    async def create_feedback(self, guests):
        """Create guest feedback and reviews"""
        feedback_list = []
        comments_positive = [
            'Harika bir konaklama deneyimi yaşadık!',
            'Personel çok ilgili ve yardımcı.',
            'Odalar tertemiz ve konforlu.',
            'Kahvaltı muhteşemdi!',
            'Kesinlikle tekrar geleceğiz.'
        ]
        comments_negative = [
            'WiFi biraz yavaştı.',
            'Odada klima gürültülüydü.',
            'Kahvaltı çeşitliliği artırılabilir.',
            'Check-in süreci biraz uzun sürdü.'
        ]
        
        for guest in random.sample(guests, min(20, len(guests))):
            is_positive = random.random() > 0.3
            rating = random.randint(4, 5) if is_positive else random.randint(2, 3)
            
            feedback_list.append({
                'id': str(uuid.uuid4()),
                'guest_id': guest['id'],
                'rating': rating,
                'comment': random.choice(comments_positive if is_positive else comments_negative),
                'sentiment': 'positive' if is_positive else 'negative',
                'category': random.choice(['overall', 'cleanliness', 'service', 'food']),
                'source': random.choice(['Direct', 'Google', 'TripAdvisor', 'Booking.com']),
                'created_at': (datetime.now() - timedelta(days=random.randint(0, 30))).isoformat()
            })
        
        if feedback_list:
            await self.db.feedback.insert_many(feedback_list)
            print(f"✓ Created {len(feedback_list)} feedback entries")
        
        return feedback_list
    
    async def seed_all(self):
        """Seed all data"""
        print("\n🌱 Starting Hotel PMS Database Seeding...")
        print("=" * 50)
        
        try:
            # Clear existing data
            await self.clear_database()
            
            # Create data in order
            users = await self.create_users()
            rooms = await self.create_rooms()
            guests = await self.create_guests()
            bookings = await self.create_bookings(rooms, guests)
            folios = await self.create_folios(bookings)
            tasks = await self.create_housekeeping_tasks(rooms)
            menu_items = await self.create_pos_data()
            feedback = await self.create_feedback(guests)
            
            print("=" * 50)
            print("✅ Database seeding completed successfully!")
            print(f"\n📊 Summary:")
            print(f"  - Users: {len(users)}")
            print(f"  - Rooms: {len(rooms)}")
            print(f"  - Guests: {len(guests)}")
            print(f"  - Bookings: {len(bookings)}")
            print(f"  - Folios: {len(folios)}")
            print(f"  - Housekeeping Tasks: {len(tasks)}")
            print(f"  - Menu Items: {len(menu_items)}")
            print(f"  - Feedback: {len(feedback)}")
            print(f"\n🔐 Login Credentials:")
            print(f"  Admin: admin@hotel.com / admin123")
            print(f"  Front Desk: frontdesk@hotel.com / frontdesk123")
            print(f"  Housekeeping: housekeeping@hotel.com / housekeeping123")
            print(f"  Finance: finance@hotel.com / finance123")
            print("\n")
            
        except Exception as e:
            print(f"❌ Error during seeding: {str(e)}")
            raise
        finally:
            self.client.close()

async def main():
    seeder = HotelSeeder()
    await seeder.seed_all()

if __name__ == '__main__':
    asyncio.run(main())
