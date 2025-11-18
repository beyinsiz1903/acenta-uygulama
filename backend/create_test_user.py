"""
Create test user for the test hotel
"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from datetime import datetime, timezone
import uuid
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def create_test_user():
    # Connect to MongoDB
    mongo_url = os.getenv('MONGO_URL', 'mongodb://localhost:27017')
    client = AsyncIOMotorClient(mongo_url)
    db = client['pms_db']
    
    tenant_id = "test-hotel-001"
    
    # Create test user
    test_user = {
        'id': str(uuid.uuid4()),
        'tenant_id': tenant_id,
        'username': 'testuser',
        'password': pwd_context.hash('test123'),  # Password: test123
        'email': 'testuser@grandemerald.com',
        'name': 'Test Manager',
        'role': 'manager',
        'permissions': ['all'],
        'active': True,
        'created_at': datetime.now(timezone.utc).isoformat()
    }
    
    # Check if user exists
    existing = await db.users.find_one({'username': 'testuser', 'tenant_id': tenant_id})
    if existing:
        print("⚠️  Test user already exists, updating...")
        await db.users.replace_one({'username': 'testuser', 'tenant_id': tenant_id}, test_user)
    else:
        await db.users.insert_one(test_user)
    
    print("\n" + "="*60)
    print("✅ TEST USER CREATED!")
    print("="*60)
    print(f"\n🔐 Login Credentials:")
    print(f"   Username: testuser")
    print(f"   Password: test123")
    print(f"   Tenant ID: {tenant_id}")
    print(f"   Role: Manager (Full Access)")
    print(f"\n🏨 Hotel: Grand Emerald Hotel")
    print(f"📧 Email: testuser@grandemerald.com")
    print("\n" + "="*60)
    print("\n✨ You can now login and test all features!")
    print("   • Guest 360° Profile")
    print("   • AI Upsell Center")
    print("   • Messaging Center")
    print("   • Housekeeping Management")
    print("   • Room Blocks")
    print("   • Reservation Calendar")
    print("   • Enterprise & AI Modes")
    print("   • Deluxe+ Features")
    print("\n" + "="*60)

if __name__ == "__main__":
    asyncio.run(create_test_user())
