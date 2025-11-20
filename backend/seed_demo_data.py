"""
Demo Data Seeder for Hotel Management System
Populates database with realistic test data
"""

import asyncio
import random
from datetime import datetime, timedelta
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv
import uuid

load_dotenv()

# Connect to MongoDB
MONGO_URL = os.getenv('MONGO_URL', 'mongodb://localhost:27017')
client = AsyncIOMotorClient(MONGO_URL)
db = client.roomops

# Helper functions
def random_date(start_days_ago=180, end_days_ago=0):
    """Generate random date within range"""
    days_ago = random.randint(end_days_ago, start_days_ago)
    return datetime.now() - timedelta(days=days_ago)

def random_future_date(start_days=1, end_days=30):
    """Generate random future date"""
    days_ahead = random.randint(start_days, end_days)
    return datetime.now() + timedelta(days=days_ahead)

# Demo data templates
FIRST_NAMES = ["John", "Emma", "Michael", "Sophia", "William", "Olivia", "James", "Ava", 
               "Robert", "Isabella", "David", "Mia", "Richard", "Charlotte", "Joseph", "Amelia",
               "Thomas", "Harper", "Charles", "Evelyn", "Christopher", "Abigail", "Daniel", "Emily"]

LAST_NAMES = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
              "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson",
              "Thomas", "Taylor", "Moore", "Jackson", "Martin", "Lee", "Thompson", "White"]

COUNTRIES = ["USA", "UK", "Germany", "France", "Spain", "Italy", "Canada", "Australia", 
             "Netherlands", "Switzerland", "Japan", "China", "Brazil", "Mexico", "India"]

ROOM_TYPES = [
    {"name": "Standard Single", "price": 80, "capacity": 1, "amenities": ["WiFi", "TV", "AC"]},
    {"name": "Standard Double", "price": 120, "capacity": 2, "amenities": ["WiFi", "TV", "AC", "Mini Bar"]},
    {"name": "Deluxe Double", "price": 180, "capacity": 2, "amenities": ["WiFi", "TV", "AC", "Mini Bar", "City View"]},
    {"name": "Executive Suite", "price": 250, "capacity": 2, "amenities": ["WiFi", "TV", "AC", "Mini Bar", "City View", "Living Room"]},
    {"name": "Family Room", "price": 200, "capacity": 4, "amenities": ["WiFi", "TV", "AC", "Mini Bar", "Kitchenette"]},
    {"name": "Penthouse Suite", "price": 400, "capacity": 4, "amenities": ["WiFi", "TV", "AC", "Mini Bar", "City View", "Living Room", "Kitchen", "Balcony"]},
]

MARKETPLACE_PRODUCTS = [
    {"name": "Luxury Bedding Set", "category": "Equipment", "price": 250, "supplier": "Premium Linens Co", "unit": "Set"},
    {"name": "Industrial Vacuum Cleaner", "category": "Equipment", "price": 450, "supplier": "CleanTech Solutions", "unit": "Piece"},
    {"name": "All-Purpose Cleaner", "category": "Cleaning", "price": 15, "supplier": "CleanSupply Inc", "unit": "Gallon"},
    {"name": "Disinfectant Spray", "category": "Cleaning", "price": 12, "supplier": "CleanSupply Inc", "unit": "Gallon"},
    {"name": "Laundry Detergent", "category": "Cleaning", "price": 25, "supplier": "CleanSupply Inc", "unit": "Gallon"},
    {"name": "Towel Set", "category": "Equipment", "price": 45, "supplier": "Premium Linens Co", "unit": "Set"},
    {"name": "Mini Bar Supplies", "category": "Equipment", "price": 120, "supplier": "Beverage Wholesale", "unit": "Package"},
    {"name": "Room Service Trolley", "category": "Equipment", "price": 380, "supplier": "Hotel Equipment Ltd", "unit": "Piece"},
    {"name": "Floor Mop System", "category": "Cleaning", "price": 75, "supplier": "CleanTech Solutions", "unit": "Set"},
    {"name": "Air Freshener", "category": "Cleaning", "price": 8, "supplier": "CleanSupply Inc", "unit": "Piece"},
]

EXPENSE_CATEGORIES = ["Utilities", "Supplies", "Maintenance", "Marketing", "Staff", "Food & Beverage"]

async def seed_data():
    """Main seeding function"""
    print("🌱 Starting demo data seeding...")
    
    # Get or create default tenant and user
    tenant = await db.tenants.find_one({"property_type": "hotel"})
    if not tenant:
        print("📝 Creating default hotel tenant...")
        tenant_id = str(uuid.uuid4())
        tenant = {
            "id": tenant_id,
            "property_name": "Grand Canyon Hotel",
            "property_type": "hotel",
            "address": "123 Main Street, Phoenix, AZ 85001",
            "contact_email": "admin@grandcanyon.hotel",
            "contact_phone": "+1-602-555-0100",
            "total_rooms": 40,
            "created_at": datetime.now().isoformat()
        }
        await db.tenants.insert_one(tenant)
        print(f"✅ Created tenant: {tenant['property_name']}")
    else:
        tenant_id = tenant['id']
    
    # Get or create admin user
    user = await db.users.find_one({"tenant_id": tenant_id, "role": "admin"})
    if not user:
        print("📝 Creating default admin user...")
        from passlib.context import CryptContext
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        password_hash = pwd_context.hash("admin123")
        
        user_id = str(uuid.uuid4())
        user = {
            "id": user_id,
            "tenant_id": tenant_id,
            "name": "Hotel Administrator",
            "email": "admin@test.com",
            "password": password_hash,
            "role": "admin",
            "created_at": datetime.now().isoformat()
        }
        await db.users.insert_one(user)
        print(f"✅ Created admin user: {user['email']} (password: admin123)")
    else:
        user_id = user['id']
    
    user_name = user['name']
    
    print(f"✅ Using tenant: {tenant['property_name']} (ID: {tenant_id})")
    print(f"✅ Using user: {user_name}")
    
    # Create demo guest user (for Guest Portal login)
    demo_guest = await db.users.find_one({"email": "guest@demo.com", "role": "guest"})
    if not demo_guest:
        print("\n📝 Creating demo guest user account...")
        from passlib.context import CryptContext
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        password_hash = pwd_context.hash("guest123")
        
        demo_guest_id = str(uuid.uuid4())
        demo_guest = {
            "id": demo_guest_id,
            "tenant_id": None,  # Guest users are not tenant-specific
            "name": "Demo Guest",
            "email": "guest@demo.com",
            "password": password_hash,
            "role": "guest",
            "phone": "+1-555-GUEST",
            "created_at": datetime.now().isoformat()
        }
        await db.users.insert_one(demo_guest)
        print(f"✅ Created demo guest user: guest@demo.com (password: guest123)")
    else:
        demo_guest_id = demo_guest['id']
        print(f"✅ Demo guest user already exists: guest@demo.com")
    
    # Clear existing demo data
    print("\n🗑️  Clearing existing demo data...")
    await db.rooms.delete_many({"tenant_id": tenant_id})
    await db.guests.delete_many({"tenant_id": tenant_id})
    await db.bookings.delete_many({"tenant_id": tenant_id})
    await db.accounting_invoices.delete_many({"tenant_id": tenant_id})
    await db.accounting_expenses.delete_many({"tenant_id": tenant_id})
    await db.loyalty_programs.delete_many({"tenant_id": tenant_id})
    await db.marketplace_products.delete_many({"tenant_id": tenant_id})
    await db.marketplace_orders.delete_many({"tenant_id": tenant_id})
    
    # 1. Create Rooms
    print("\n🏨 Creating rooms...")
    rooms = []
    room_number = 101
    for floor in range(1, 6):  # 5 floors
        for room_on_floor in range(1, 9):  # 8 rooms per floor
            room_type = random.choice(ROOM_TYPES)
            room = {
                "id": str(uuid.uuid4()),
                "tenant_id": tenant_id,
                "room_number": str(room_number),
                "room_type": room_type["name"],
                "price_per_night": room_type["price"],
                "capacity": room_type["capacity"],
                "status": "available",
                "amenities": room_type["amenities"],
                "floor": floor,
                "created_at": datetime.now().isoformat()
            }
            rooms.append(room)
            room_number += 1
    
    await db.rooms.insert_many(rooms)
    print(f"✅ Created {len(rooms)} rooms")
    
    # 2. Create Guests
    print("\n👥 Creating guest records...")
    guests = []
    
    # First, create demo guest record linked to demo user
    demo_guest_record = {
        "id": str(uuid.uuid4()),
        "tenant_id": tenant_id,
        "name": "Demo Guest",
        "email": "guest@demo.com",  # Same email as user account
        "phone": "+1-555-GUEST",
        "country": "USA",
        "id_number": "DEMO123456",
        "preferences": "City view, Late checkout, Non-smoking",
        "vip": True,
        "loyalty_points": 2500,  # Give demo guest some points
        "loyalty_tier": "gold",  # Gold tier
        "total_stays": 8,
        "total_spend": 3200.00,
        "created_at": random_date(365, 180).isoformat()
    }
    guests.append(demo_guest_record)
    print(f"✅ Added demo guest record with 2500 loyalty points (Gold tier)")
    
    # Then create other random guests
    for i in range(50):
        first_name = random.choice(FIRST_NAMES)
        last_name = random.choice(LAST_NAMES)
        email = f"{first_name.lower()}.{last_name.lower()}{random.randint(1, 999)}@email.com"
        
        guest = {
            "id": str(uuid.uuid4()),
            "tenant_id": tenant_id,
            "name": f"{first_name} {last_name}",
            "email": email,
            "phone": f"+1{random.randint(2000000000, 9999999999)}",
            "country": random.choice(COUNTRIES),
            "id_number": f"ID{random.randint(100000, 999999)}",
            "preferences": random.choice([
                "Non-smoking, High floor",
                "Near elevator, Quiet room",
                "City view, Late checkout",
                "Early check-in, Airport transfer"
            ]),
            "vip": random.random() > 0.85,
            "loyalty_points": random.randint(0, 1500),
            "loyalty_tier": random.choice(["bronze", "bronze", "silver", "silver", "gold"]),
            "total_stays": random.randint(0, 10),
            "total_spend": round(random.uniform(0, 5000), 2),
            "created_at": random_date(365, 180).isoformat()
        }
        guests.append(guest)
    
    await db.guests.insert_many(guests)
    print(f"✅ Created {len(guests)} guests (including demo guest)")
    
    # 3. Create Bookings (Past, Current, Future)
    print("\n📅 Creating bookings...")
    bookings = []
    
    # Past bookings (completed)
    for i in range(80):
        guest = random.choice(guests)
        room = random.choice(rooms)
        check_in_date = random_date(120, 30)
        nights = random.randint(1, 7)
        check_out_date = check_in_date + timedelta(days=nights)
        
        booking = {
            "id": str(uuid.uuid4()),
            "tenant_id": tenant_id,
            "guest_id": guest["id"],
            "guest_name": guest["name"],
            "guest_email": guest["email"],
            "room_id": room["id"],
            "room_number": room["room_number"],
            "room_type": room["room_type"],
            "check_in": check_in_date.isoformat(),
            "check_out": check_out_date.isoformat(),
            "nights": nights,
            "total_amount": room["price_per_night"] * nights,
            "status": "checked_out",
            "booking_source": random.choice(["direct", "booking.com", "expedia", "airbnb", "walk-in"]),
            "created_at": (check_in_date - timedelta(days=random.randint(7, 30))).isoformat()
        }
        bookings.append(booking)
    
    # Current bookings (checked-in)
    for i in range(15):
        guest = random.choice(guests)
        room = random.choice(rooms)
        check_in_date = datetime.now() - timedelta(days=random.randint(0, 3))
        nights = random.randint(2, 7)
        check_out_date = check_in_date + timedelta(days=nights)
        
        booking = {
            "id": str(uuid.uuid4()),
            "tenant_id": tenant_id,
            "guest_id": guest["id"],
            "guest_name": guest["name"],
            "guest_email": guest["email"],
            "room_id": room["id"],
            "room_number": room["room_number"],
            "room_type": room["room_type"],
            "check_in": check_in_date.isoformat(),
            "check_out": check_out_date.isoformat(),
            "nights": nights,
            "total_amount": room["price_per_night"] * nights,
            "status": "checked_in",
            "booking_source": random.choice(["direct", "booking.com", "expedia", "walk-in"]),
            "created_at": (check_in_date - timedelta(days=random.randint(7, 21))).isoformat()
        }
        bookings.append(booking)
        
        # Update room status
        await db.rooms.update_one(
            {"id": room["id"]},
            {"$set": {"status": "occupied"}}
        )
    
    # Future bookings (confirmed)
    for i in range(25):
        guest = random.choice(guests)
        room = random.choice(rooms)
        check_in_date = random_future_date(1, 30)
        nights = random.randint(1, 5)
        check_out_date = check_in_date + timedelta(days=nights)
        
        booking = {
            "id": str(uuid.uuid4()),
            "tenant_id": tenant_id,
            "guest_id": guest["id"],
            "guest_name": guest["name"],
            "guest_email": guest["email"],
            "room_id": room["id"],
            "room_number": room["room_number"],
            "room_type": room["room_type"],
            "check_in": check_in_date.isoformat(),
            "check_out": check_out_date.isoformat(),
            "nights": nights,
            "total_amount": room["price_per_night"] * nights,
            "status": "confirmed",
            "booking_source": random.choice(["direct", "booking.com", "expedia", "airbnb"]),
            "created_at": datetime.now().isoformat()
        }
        bookings.append(booking)
    
    await db.bookings.insert_many(bookings)
    print(f"✅ Created {len(bookings)} bookings (Past: 80, Current: 15, Future: 25)")
    
    # 4. Create Invoices for bookings
    print("\n💰 Creating invoices...")
    invoices = []
    
    for booking in bookings:
        if booking["status"] in ["checked_out", "checked_in"]:
            # Create invoice for booking
            vat_rate = random.choice([10, 18, 20])
            subtotal = booking["total_amount"]
            vat_amount = subtotal * (vat_rate / 100)
            
            # Sometimes add additional taxes
            additional_taxes = []
            vat_withholding = 0
            total_additional = 0
            
            if random.random() > 0.7:  # 30% chance of additional taxes
                # Add accommodation tax
                if random.random() > 0.5:
                    acc_tax_rate = 2
                    acc_tax_amount = subtotal * (acc_tax_rate / 100)
                    additional_taxes.append({
                        "tax_type": "accommodation",
                        "tax_name": "Konaklama Vergisi",
                        "rate": acc_tax_rate,
                        "is_percentage": True,
                        "calculated_amount": acc_tax_amount
                    })
                    total_additional += acc_tax_amount
                
                # Add withholding tax
                if random.random() > 0.6:
                    withholding_rate = random.choice(["7/10", "5/10", "3/10"])
                    rate_parts = withholding_rate.split('/')
                    rate_percent = (int(rate_parts[0]) / int(rate_parts[1])) * 100
                    withholding_amount = vat_amount * (rate_percent / 100)
                    vat_withholding = withholding_amount
            
            total = subtotal + vat_amount + total_additional - vat_withholding
            
            invoice = {
                "id": str(uuid.uuid4()),
                "tenant_id": tenant_id,
                "invoice_number": f"INV-{datetime.now().year}-{random.randint(1000, 9999)}",
                "invoice_type": "sales",
                "customer_name": booking["guest_name"],
                "customer_email": booking["guest_email"],
                "items": [{
                    "description": f"Room {booking['room_number']} - {booking['room_type']} ({booking['nights']} nights)",
                    "quantity": booking["nights"],
                    "unit_price": booking["total_amount"] / booking["nights"],
                    "vat_rate": vat_rate,
                    "vat_amount": vat_amount,
                    "total": subtotal + vat_amount,
                    "additional_taxes": additional_taxes
                }],
                "subtotal": subtotal,
                "total_vat": vat_amount,
                "vat_withholding": vat_withholding,
                "total_additional_taxes": total_additional,
                "total": total,
                "status": "paid" if booking["status"] == "checked_out" else "pending",
                "issue_date": booking["check_in"],
                "due_date": booking["check_out"],
                "payment_date": booking["check_out"] if booking["status"] == "checked_out" else None,
                "booking_id": booking["id"],
                "created_by": user_name,
                "created_at": booking["check_in"]
            }
            invoices.append(invoice)
    
    await db.accounting_invoices.insert_many(invoices)
    print(f"✅ Created {len(invoices)} invoices")
    
    # 5. Create Expenses
    print("\n📝 Creating expenses...")
    expenses = []
    
    expense_descriptions = {
        "Utilities": ["Electricity Bill", "Water Bill", "Gas Bill", "Internet Service"],
        "Supplies": ["Cleaning Supplies", "Toiletries", "Laundry Detergent", "Office Supplies"],
        "Maintenance": ["HVAC Service", "Plumbing Repair", "Electrical Maintenance", "Painting"],
        "Marketing": ["Google Ads", "Social Media Marketing", "Print Materials", "Website Maintenance"],
        "Staff": ["Salaries", "Training", "Uniforms", "Staff Meals"],
        "Food & Beverage": ["Restaurant Supplies", "Minibar Stock", "Breakfast Items", "Coffee & Tea"]
    }
    
    for i in range(60):
        category = random.choice(EXPENSE_CATEGORIES)
        description = random.choice(expense_descriptions[category])
        amount = random.uniform(50, 2000)
        vat_rate = random.choice([0, 10, 18])
        vat_amount = amount * (vat_rate / 100)
        
        expense = {
            "id": str(uuid.uuid4()),
            "tenant_id": tenant_id,
            "description": description,
            "category": category,
            "amount": amount,
            "vat_rate": vat_rate,
            "vat_amount": vat_amount,
            "total": amount + vat_amount,
            "date": random_date(90, 0).isoformat(),
            "vendor": f"{category} Vendor {random.randint(1, 5)}",
            "payment_method": random.choice(["bank_transfer", "credit_card", "cash", "check"]),
            "created_by": user_name,
            "created_at": random_date(90, 0).isoformat()
        }
        expenses.append(expense)
    
    await db.accounting_expenses.insert_many(expenses)
    print(f"✅ Created {len(expenses)} expenses")
    
    # 6. Create Loyalty Programs
    print("\n🎁 Creating loyalty program members...")
    loyalty_members = []
    
    # Enroll 30 guests in loyalty program
    enrolled_guests = random.sample(guests, 30)
    for guest in enrolled_guests:
        # Get guest's booking history
        guest_bookings = [b for b in bookings if b["guest_id"] == guest["id"]]
        total_stays = len([b for b in guest_bookings if b["status"] == "checked_out"])
        total_spent = sum(b["total_amount"] for b in guest_bookings if b["status"] == "checked_out")
        
        points = total_stays * 100 + int(total_spent / 10)
        tier = "Silver"
        if points > 1000:
            tier = "Gold"
        if points > 2000:
            tier = "Platinum"
        
        member = {
            "id": str(uuid.uuid4()),
            "tenant_id": tenant_id,
            "guest_id": guest["id"],
            "guest_name": guest["name"],
            "guest_email": guest["email"],
            "tier": tier,
            "points": points,
            "total_stays": total_stays,
            "total_spent": total_spent,
            "enrolled_date": random_date(180, 30).isoformat(),
            "last_activity": random_date(30, 0).isoformat() if total_stays > 0 else None
        }
        loyalty_members.append(member)
    
    await db.loyalty_programs.insert_many(loyalty_members)
    print(f"✅ Created {len(loyalty_members)} loyalty program members")
    
    # 7. Create Marketplace Products
    print("\n🛒 Creating marketplace products...")
    products = []
    
    for product_template in MARKETPLACE_PRODUCTS:
        product = {
            "id": str(uuid.uuid4()),
            "tenant_id": tenant_id,
            "name": product_template["name"],
            "category": product_template["category"],
            "price": product_template["price"],
            "supplier": product_template["supplier"],
            "unit": product_template["unit"],
            "quantity": random.randint(5, 50),
            "reorder_level": 10,
            "in_stock": True,
            "created_at": random_date(180, 0).isoformat()
        }
        products.append(product)
    
    await db.marketplace_products.insert_many(products)
    print(f"✅ Created {len(products)} marketplace products")
    
    # 8. Create Marketplace Orders
    print("\n📦 Creating marketplace orders...")
    orders = []
    
    for i in range(15):
        # Random products in order
        order_products = random.sample(products, random.randint(1, 4))
        order_items = []
        order_total = 0
        
        for product in order_products:
            quantity = random.randint(1, 5)
            item_total = product["price"] * quantity
            order_total += item_total
            
            order_items.append({
                "product_id": product["id"],
                "product_name": product["name"],
                "quantity": quantity,
                "unit_price": product["price"],
                "total": item_total
            })
        
        order = {
            "id": str(uuid.uuid4()),
            "tenant_id": tenant_id,
            "order_number": f"ORD-{datetime.now().year}-{random.randint(1000, 9999)}",
            "items": order_items,
            "total": order_total,
            "status": random.choice(["pending", "delivered", "delivered", "delivered"]),  # Most delivered
            "order_date": random_date(60, 0).isoformat(),
            "delivery_date": random_date(50, 0).isoformat(),
            "created_by": user_name,
            "created_at": random_date(60, 0).isoformat()
        }
        orders.append(order)
    
    await db.marketplace_orders.insert_many(orders)
    print(f"✅ Created {len(orders)} marketplace orders")
    
    # 9. Create Bank Accounts
    print("\n🏦 Creating bank accounts...")
    bank_accounts = [
        {
            "id": str(uuid.uuid4()),
            "tenant_id": tenant_id,
            "account_name": "Main Operating Account",
            "account_number": "****1234",
            "bank_name": "First National Bank",
            "account_type": "checking",
            "currency": "USD",
            "balance": 125000 + random.uniform(-10000, 20000),
            "is_active": True,
            "created_at": random_date(365, 0).isoformat()
        },
        {
            "id": str(uuid.uuid4()),
            "tenant_id": tenant_id,
            "account_name": "Savings Account",
            "account_number": "****5678",
            "bank_name": "First National Bank",
            "account_type": "savings",
            "currency": "USD",
            "balance": 50000 + random.uniform(-5000, 15000),
            "is_active": True,
            "created_at": random_date(365, 0).isoformat()
        }
    ]
    
    await db.bank_accounts.insert_many(bank_accounts)
    print(f"✅ Created {len(bank_accounts)} bank accounts")
    
    # Summary
    print("\n" + "="*60)
    print("✅ DEMO DATA SEEDING COMPLETE!")
    print("="*60)
    print(f"🏨 Rooms: {len(rooms)}")
    print(f"👥 Guests: {len(guests)}")
    print(f"📅 Bookings: {len(bookings)} (Past: 80, Current: 15, Future: 25)")
    print(f"💰 Invoices: {len(invoices)}")
    print(f"📝 Expenses: {len(expenses)}")
    print(f"🎁 Loyalty Members: {len(loyalty_members)}")
    print(f"🛒 Products: {len(products)}")
    print(f"📦 Orders: {len(orders)}")
    print(f"🏦 Bank Accounts: {len(bank_accounts)}")
    print("="*60)
    print("\n🎉 Your hotel management system is now fully populated with demo data!")
    print("🚀 You can now test all features including AI predictions!")

if __name__ == "__main__":
    asyncio.run(seed_data())
