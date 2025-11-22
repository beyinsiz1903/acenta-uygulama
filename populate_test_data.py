#!/usr/bin/env python3
"""
Comprehensive Test Data Population Script
Creates realistic hotel data for testing all features
"""

import pymongo
from pymongo import MongoClient
import os
import random
from datetime import datetime, timedelta
import uuid
from faker import Faker

fake = Faker(['tr_TR', 'en_US'])

# MongoDB connection
mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
client = MongoClient(mongo_url)
db = client['hotel_pms']

print("🏨 Hotel PMS - Comprehensive Test Data Population")
print("=" * 60)

# Get test tenant
test_user = db.users.find_one({'email': 'test@test.com'})
if not test_user:
    print("❌ Test user not found! Please create test@test.com first")
    exit(1)

tenant_id = test_user['tenant_id']
print(f"✅ Using tenant: {tenant_id}")

# Clear existing data for this tenant
print("\n🧹 Cleaning existing data...")
collections_to_clear = [
    'rooms', 'guests', 'bookings', 'folio_charges', 'payments',
    'expenses', 'reviews', 'pos_orders', 'budgets', 'folios'
]

for collection_name in collections_to_clear:
    result = db[collection_name].delete_many({'tenant_id': tenant_id})
    print(f"   Deleted {result.deleted_count} records from {collection_name}")

# Room Types Configuration
room_types = [
    {'type': 'Standard Single', 'capacity': 1, 'base_rate': 150, 'count': 20},
    {'type': 'Standard Double', 'capacity': 2, 'base_rate': 200, 'count': 30},
    {'type': 'Deluxe Double', 'capacity': 2, 'base_rate': 280, 'count': 15},
    {'type': 'Suite', 'capacity': 3, 'base_rate': 400, 'count': 10},
    {'type': 'Family Room', 'capacity': 4, 'base_rate': 350, 'count': 8},
    {'type': 'Presidential Suite', 'capacity': 4, 'base_rate': 800, 'count': 2}
]

# Create Rooms
print("\n🛏️  Creating Rooms...")
rooms = []
floor = 1
room_number = 101

for room_type in room_types:
    for i in range(room_type['count']):
        room = {
            'id': str(uuid.uuid4()),
            'tenant_id': tenant_id,
            'room_number': str(room_number),
            'room_type': room_type['type'],
            'floor': floor,
            'status': 'available',
            'capacity': room_type['capacity'],
            'base_rate': room_type['base_rate'],
            'amenities': ['wifi', 'tv', 'minibar', 'ac'],
            'created_at': datetime.now().isoformat()
        }
        rooms.append(room)
        room_number += 1
        if room_number % 100 >= 50:
            floor += 1
            room_number = floor * 100 + 1

db.rooms.insert_many(rooms)
print(f"   Created {len(rooms)} rooms across {len(room_types)} room types")

# Create Guests
print("\n👥 Creating Guests...")
guests = []
nationalities = ['Turkish', 'American', 'German', 'British', 'French', 'Italian', 'Spanish', 'Russian']
guest_types = ['leisure', 'business', 'group']

for i in range(500):  # 500 unique guests
    guest = {
        'id': str(uuid.uuid4()),
        'tenant_id': tenant_id,
        'name': fake.name(),
        'surname': fake.last_name(),
        'email': fake.email(),
        'phone': fake.phone_number(),
        'nationality': random.choice(nationalities),
        'id_number': fake.passport_number(),
        'guest_type': random.choice(guest_types),
        'total_stays': random.randint(1, 10),
        'vip_status': random.choice([True, False]) if random.random() > 0.8 else False,
        'blacklist_status': False,
        'preferences': {
            'pillow_type': random.choice(['soft', 'medium', 'firm']),
            'floor_preference': random.choice(['low', 'high', 'any']),
            'room_temperature': random.randint(20, 24)
        },
        'created_at': (datetime.now() - timedelta(days=random.randint(1, 730))).isoformat()
    }
    guests.append(guest)

db.guests.insert_many(guests)
print(f"   Created {len(guests)} guests")

# Create Bookings and Financial Data
print("\n📅 Creating Bookings (Last 2 Years)...")

market_segments = ['corporate', 'leisure', 'group', 'mice', 'government', 'wholesale']
booking_sources = ['direct', 'ota', 'corporate', 'walk_in', 'agent']
ota_channels = ['Booking.com', 'Expedia', 'Hotels.com', 'Agoda', 'Airbnb']
booking_statuses_for_past = ['checked_out', 'cancelled', 'no_show']
booking_statuses_for_future = ['confirmed', 'guaranteed']

bookings = []
folio_charges = []
payments = []
expenses = []
reviews = []
pos_orders = []
folios_list = []

# Generate data for last 2 years + next 3 months
start_date = datetime.now() - timedelta(days=730)
end_date = datetime.now() + timedelta(days=90)

current_date = start_date
booking_count = 0
total_revenue = 0

print("   Generating bookings month by month...")

while current_date < end_date:
    # Determine occupancy based on season
    month = current_date.month
    if month in [6, 7, 8]:  # Summer - high season
        daily_occupancy_target = 0.85
    elif month in [12, 1]:  # Winter holidays
        daily_occupancy_target = 0.75
    elif month in [4, 5, 9, 10]:  # Shoulder season
        daily_occupancy_target = 0.65
    else:  # Low season
        daily_occupancy_target = 0.50
    
    # Random variation
    daily_occupancy = daily_occupancy_target + random.uniform(-0.15, 0.15)
    daily_occupancy = max(0.3, min(0.95, daily_occupancy))  # Keep between 30-95%
    
    rooms_to_book = int(len(rooms) * daily_occupancy)
    
    for _ in range(rooms_to_book):
        guest = random.choice(guests)
        room = random.choice(rooms)
        
        # Booking duration
        nights = random.randint(1, 7) if random.random() > 0.1 else random.randint(8, 21)
        check_in = current_date
        check_out = check_in + timedelta(days=nights)
        
        # Determine status based on date
        if check_out < datetime.now():
            # Past booking
            status_pool = ['checked_out'] * 85 + ['cancelled'] * 12 + ['no_show'] * 3
            status = random.choice(status_pool)
        elif check_in < datetime.now() < check_out:
            # Currently checked in
            status = 'checked_in'
        else:
            # Future booking
            status = random.choice(booking_statuses_for_future)
        
        # Market segment and source
        segment = random.choice(market_segments)
        source = random.choice(booking_sources)
        
        # Rate calculation
        base_rate = room['base_rate']
        rate_variation = random.uniform(0.8, 1.3)  # +/- 30% variation
        rate_per_night = round(base_rate * rate_variation, 2)
        
        # Commission for OTA bookings
        commission_pct = 0
        ota_channel = None
        if source == 'ota':
            commission_pct = random.uniform(15, 25)
            ota_channel = random.choice(ota_channels)
        
        booking_id = str(uuid.uuid4())
        created_at = (check_in - timedelta(days=random.randint(1, 90))).isoformat()
        
        booking = {
            'id': booking_id,
            'tenant_id': tenant_id,
            'guest_id': guest['id'],
            'room_id': room['id'],
            'room_number': room['room_number'],
            'room_type': room['room_type'],
            'check_in': check_in.isoformat(),
            'check_out': check_out.isoformat(),
            'status': status,
            'guests_count': random.randint(1, room['capacity']),
            'rate_per_night': rate_per_night,
            'total_amount': round(rate_per_night * nights, 2),
            'market_segment': segment,
            'source': source,
            'ota_channel': ota_channel,
            'commission_pct': commission_pct,
            'special_requests': fake.text(max_nb_chars=100) if random.random() > 0.7 else '',
            'created_at': created_at,
            'updated_at': created_at
        }
        
        # Add cancellation details if cancelled
        if status == 'cancelled':
            booking['cancelled_at'] = (check_in - timedelta(days=random.randint(0, 30))).isoformat()
        
        bookings.append(booking)
        booking_count += 1
        
        # Create Folio and Charges for completed/checked-in bookings
        if status in ['checked_out', 'checked_in']:
            # Create folio
            folio_id = str(uuid.uuid4())
            folio_number = f"F-{current_date.year}-{len(folios_list) + 1:05d}"
            
            folio = {
                'id': folio_id,
                'tenant_id': tenant_id,
                'booking_id': booking_id,
                'guest_id': guest['id'],
                'folio_number': folio_number,
                'folio_type': 'guest',
                'status': 'closed' if status == 'checked_out' else 'open',
                'balance': 0,
                'created_at': check_in.isoformat(),
                'closed_at': check_out.isoformat() if status == 'checked_out' else None
            }
            folios_list.append(folio)
            
            # Room charges
            for night in range(nights):
                charge_date = check_in + timedelta(days=night)
                if charge_date < datetime.now():  # Only create charges for past dates
                    charge = {
                        'id': str(uuid.uuid4()),
                        'tenant_id': tenant_id,
                        'folio_id': folio_id,
                        'booking_id': booking_id,
                        'charge_type': 'Room Charge',
                        'charge_category': 'room',
                        'description': f"Room {room['room_number']} - Night {night + 1}",
                        'quantity': 1,
                        'unit_price': rate_per_night,
                        'amount': rate_per_night,
                        'tax_amount': round(rate_per_night * 0.08, 2),  # 8% VAT
                        'total': round(rate_per_night * 1.08, 2),
                        'voided': False,
                        'date': charge_date.isoformat(),
                        'created_at': charge_date.isoformat()
                    }
                    folio_charges.append(charge)
                    total_revenue += charge['total']
            
            # Additional charges (F&B, minibar, etc.)
            if random.random() > 0.3:  # 70% chance of additional charges
                num_additional_charges = random.randint(1, 5)
                
                for _ in range(num_additional_charges):
                    charge_types = [
                        ('Restaurant', 'food', 25, 150),
                        ('Bar', 'beverage', 10, 80),
                        ('Minibar', 'minibar', 5, 30),
                        ('Room Service', 'food', 20, 100),
                        ('Spa', 'spa', 50, 200),
                        ('Laundry', 'laundry', 15, 60)
                    ]
                    
                    charge_info = random.choice(charge_types)
                    charge_amount = round(random.uniform(charge_info[2], charge_info[3]), 2)
                    charge_date = check_in + timedelta(days=random.randint(0, nights - 1))
                    
                    if charge_date < datetime.now():
                        charge = {
                            'id': str(uuid.uuid4()),
                            'tenant_id': tenant_id,
                            'folio_id': folio_id,
                            'booking_id': booking_id,
                            'charge_type': charge_info[0],
                            'charge_category': charge_info[1],
                            'description': f"{charge_info[0]} Service",
                            'quantity': 1,
                            'unit_price': charge_amount,
                            'amount': charge_amount,
                            'tax_amount': round(charge_amount * 0.08, 2),
                            'total': round(charge_amount * 1.08, 2),
                            'voided': False,
                            'date': charge_date.isoformat(),
                            'created_at': charge_date.isoformat()
                        }
                        folio_charges.append(charge)
                        total_revenue += charge['total']
                        
                        # Create POS order for F&B items
                        if charge_info[1] in ['food', 'beverage']:
                            menu_items = [
                                {'name': 'Steak', 'category': 'food', 'price': 45},
                                {'name': 'Pasta', 'category': 'food', 'price': 28},
                                {'name': 'Salad', 'category': 'food', 'price': 18},
                                {'name': 'Wine', 'category': 'beverage', 'price': 35},
                                {'name': 'Beer', 'category': 'beverage', 'price': 12},
                                {'name': 'Coffee', 'category': 'beverage', 'price': 8},
                                {'name': 'Dessert', 'category': 'food', 'price': 15}
                            ]
                            
                            num_items = random.randint(1, 4)
                            order_items = []
                            order_total = 0
                            
                            for _ in range(num_items):
                                item = random.choice(menu_items)
                                quantity = random.randint(1, 3)
                                item_total = item['price'] * quantity
                                order_total += item_total
                                
                                order_items.append({
                                    'item_name': item['name'],
                                    'quantity': quantity,
                                    'price': item['price'],
                                    'category': item['category']
                                })
                            
                            pos_order = {
                                'id': str(uuid.uuid4()),
                                'tenant_id': tenant_id,
                                'booking_id': booking_id,
                                'guest_id': guest['id'],
                                'table_number': str(random.randint(1, 30)),
                                'items': order_items,
                                'subtotal': round(order_total, 2),
                                'tax': round(order_total * 0.08, 2),
                                'total': round(order_total * 1.08, 2),
                                'status': 'completed',
                                'created_at': charge_date.isoformat()
                            }
                            pos_orders.append(pos_order)
            
            # Create payments for checked-out bookings
            if status == 'checked_out':
                total_folio_charges = sum(c['total'] for c in folio_charges if c['folio_id'] == folio_id)
                
                # Payment methods distribution
                payment_methods = ['card', 'cash', 'bank_transfer']
                payment_method = random.choice(payment_methods)
                
                payment = {
                    'id': str(uuid.uuid4()),
                    'tenant_id': tenant_id,
                    'folio_id': folio_id,
                    'booking_id': booking_id,
                    'amount': total_folio_charges,
                    'payment_method': payment_method,
                    'payment_type': 'final',
                    'status': 'completed',
                    'date': check_out.isoformat(),
                    'created_at': check_out.isoformat()
                }
                payments.append(payment)
                
                # Update folio balance
                folio['balance'] = 0
            
            # Create review for checked-out bookings
            if status == 'checked_out' and random.random() > 0.4:  # 60% review rate
                rating = random.choices([3, 4, 5, 4, 5, 5], weights=[5, 15, 30, 20, 20, 10])[0]
                
                positive_comments = [
                    "Harika bir deneyimdi! Kesinlikle tekrar geleceğim.",
                    "Personel çok ilgili, odalar temizdi.",
                    "Mükemmel konum, her şeye yakın.",
                    "Great stay! Highly recommended.",
                    "Perfect location and service."
                ]
                
                negative_comments = [
                    "Oda biraz küçüktü.",
                    "Kahvaltı daha iyi olabilirdi.",
                    "Gürültülü bir kat.",
                    "Room could be cleaner.",
                    "Service was slow."
                ]
                
                if rating >= 4:
                    comment = random.choice(positive_comments)
                else:
                    comment = random.choice(negative_comments)
                
                review = {
                    'id': str(uuid.uuid4()),
                    'tenant_id': tenant_id,
                    'booking_id': booking_id,
                    'guest_id': guest['id'],
                    'rating': rating,
                    'comment': comment,
                    'source': random.choice(['Google', 'TripAdvisor', 'Booking.com', 'Direct']),
                    'created_at': (check_out + timedelta(days=random.randint(1, 7))).isoformat()
                }
                reviews.append(review)
    
    # Monthly expenses
    if current_date.day == 1 and current_date < datetime.now():
        # Payroll
        payroll = round(random.uniform(45000, 55000), 2)
        expenses.append({
            'id': str(uuid.uuid4()),
            'tenant_id': tenant_id,
            'category': 'payroll',
            'description': 'Monthly Payroll',
            'amount': payroll,
            'date': current_date.isoformat(),
            'created_at': current_date.isoformat()
        })
        
        # Utilities
        utilities = round(random.uniform(8000, 12000), 2)
        expenses.append({
            'id': str(uuid.uuid4()),
            'tenant_id': tenant_id,
            'category': 'utilities',
            'description': 'Electricity, Water, Gas',
            'amount': utilities,
            'date': current_date.isoformat(),
            'created_at': current_date.isoformat()
        })
        
        # Supplies
        supplies = round(random.uniform(5000, 8000), 2)
        expenses.append({
            'id': str(uuid.uuid4()),
            'tenant_id': tenant_id,
            'category': 'supplies',
            'description': 'Cleaning & Room Supplies',
            'amount': supplies,
            'date': current_date.isoformat(),
            'created_at': current_date.isoformat()
        })
        
        # Maintenance
        maintenance = round(random.uniform(3000, 7000), 2)
        expenses.append({
            'id': str(uuid.uuid4()),
            'tenant_id': tenant_id,
            'category': 'maintenance',
            'description': 'Maintenance & Repairs',
            'amount': maintenance,
            'date': current_date.isoformat(),
            'created_at': current_date.isoformat()
        })
        
        # Marketing
        marketing = round(random.uniform(4000, 8000), 2)
        expenses.append({
            'id': str(uuid.uuid4()),
            'tenant_id': tenant_id,
            'category': 'marketing',
            'description': 'Marketing & Advertising',
            'amount': marketing,
            'date': current_date.isoformat(),
            'created_at': current_date.isoformat()
        })
    
    current_date += timedelta(days=1)
    
    # Progress indicator
    if current_date.day == 1:
        print(f"   ✓ {current_date.strftime('%B %Y')} - {booking_count} bookings created")

# Insert all data
print("\n💾 Inserting data into database...")

if bookings:
    db.bookings.insert_many(bookings)
    print(f"   ✅ {len(bookings)} bookings")

if folios_list:
    db.folios.insert_many(folios_list)
    print(f"   ✅ {len(folios_list)} folios")

if folio_charges:
    db.folio_charges.insert_many(folio_charges)
    print(f"   ✅ {len(folio_charges)} folio charges")

if payments:
    db.payments.insert_many(payments)
    print(f"   ✅ {len(payments)} payments")

if expenses:
    db.expenses.insert_many(expenses)
    print(f"   ✅ {len(expenses)} expenses")

if reviews:
    db.reviews.insert_many(reviews)
    print(f"   ✅ {len(reviews)} reviews")

if pos_orders:
    db.pos_orders.insert_many(pos_orders)
    print(f"   ✅ {len(pos_orders)} POS orders")

# Create budgets for last 12 months
print("\n💰 Creating monthly budgets...")
budgets = []
current_month = datetime.now().replace(day=1)

for i in range(12):
    budget_month = current_month - timedelta(days=30 * i)
    month_str = budget_month.strftime('%Y-%m')
    
    budget = {
        'id': str(uuid.uuid4()),
        'tenant_id': tenant_id,
        'month': month_str,
        'revenue_budget': round(random.uniform(180000, 220000), 2),
        'expense_budget': round(random.uniform(120000, 150000), 2),
        'occupancy_budget': round(random.uniform(70, 85), 2),
        'adr_budget': round(random.uniform(180, 220), 2),
        'created_at': budget_month.isoformat()
    }
    budgets.append(budget)

if budgets:
    db.budgets.insert_many(budgets)
    print(f"   ✅ {len(budgets)} monthly budgets")

# Summary Statistics
print("\n" + "=" * 60)
print("📊 DATA POPULATION SUMMARY")
print("=" * 60)
print(f"🛏️  Rooms: {len(rooms)}")
print(f"👥 Guests: {len(guests)}")
print(f"📅 Bookings: {len(bookings)}")
print(f"📄 Folios: {len(folios_list)}")
print(f"💳 Charges: {len(folio_charges)}")
print(f"💰 Payments: {len(payments)}")
print(f"💸 Expenses: {len(expenses)}")
print(f"⭐ Reviews: {len(reviews)}")
print(f"🍽️  POS Orders: {len(pos_orders)}")
print(f"📊 Budgets: {len(budgets)}")
print(f"\n💵 Total Revenue Generated: ${total_revenue:,.2f}")
print(f"📆 Date Range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
print("=" * 60)
print("\n✅ Test data population completed successfully!")
print("\n🎯 You can now test all features with realistic data:")
print("   - Revenue dashboards and reports")
print("   - F&B analytics")
print("   - Occupancy trends")
print("   - Budget vs actual")
print("   - Guest reviews and ratings")
print("   - Financial statements")
