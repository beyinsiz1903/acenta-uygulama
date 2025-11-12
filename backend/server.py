from fastapi import FastAPI, APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone, timedelta
import bcrypt
import jwt
from enum import Enum

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# JWT Configuration
JWT_SECRET = os.environ.get('JWT_SECRET', 'your-secret-key-change-in-production')
JWT_ALGORITHM = 'HS256'
JWT_EXPIRATION_HOURS = 24

# Create the main app
app = FastAPI(title="RoomOps Platform")
api_router = APIRouter(prefix="/api")
security = HTTPBearer()

# ============= ENUMS & CONSTANTS =============

class UserRole(str, Enum):
    ADMIN = "admin"
    MANAGER = "manager"
    STAFF = "staff"

class RoomStatus(str, Enum):
    AVAILABLE = "available"
    OCCUPIED = "occupied"
    MAINTENANCE = "maintenance"
    CLEANING = "cleaning"

class BookingStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CHECKED_IN = "checked_in"
    CHECKED_OUT = "checked_out"
    CANCELLED = "cancelled"

class InvoiceStatus(str, Enum):
    DRAFT = "draft"
    SENT = "sent"
    PAID = "paid"
    OVERDUE = "overdue"

class LoyaltyTier(str, Enum):
    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"
    PLATINUM = "platinum"

# ============= PYDANTIC MODELS =============

# Auth & Tenant Models
class Tenant(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    property_name: str
    email: EmailStr
    phone: str
    address: str
    subscription_status: str = "active"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class User(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    email: EmailStr
    name: str
    role: UserRole
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class TenantRegister(BaseModel):
    property_name: str
    email: EmailStr
    password: str
    name: str
    phone: str
    address: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: User
    tenant: Tenant

# PMS Models
class RoomCreate(BaseModel):
    room_number: str
    room_type: str
    floor: int
    capacity: int
    base_price: float
    amenities: List[str] = []

class Room(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    room_number: str
    room_type: str
    floor: int
    capacity: int
    base_price: float
    status: RoomStatus = RoomStatus.AVAILABLE
    amenities: List[str] = []
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class GuestCreate(BaseModel):
    name: str
    email: EmailStr
    phone: str
    id_number: str
    address: Optional[str] = None

class Guest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    name: str
    email: EmailStr
    phone: str
    id_number: str
    address: Optional[str] = None
    loyalty_points: int = 0
    total_stays: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class BookingCreate(BaseModel):
    guest_id: str
    room_id: str
    check_in: str  # ISO format date string
    check_out: str  # ISO format date string
    guests_count: int
    total_amount: float
    channel: str = "direct"
    special_requests: Optional[str] = None

class Booking(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    guest_id: str
    room_id: str
    check_in: datetime
    check_out: datetime
    guests_count: int
    total_amount: float
    status: BookingStatus = BookingStatus.PENDING
    channel: str = "direct"
    special_requests: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# Invoice Models
class InvoiceItem(BaseModel):
    description: str
    quantity: float
    unit_price: float
    total: float

class InvoiceCreate(BaseModel):
    booking_id: Optional[str] = None
    customer_name: str
    customer_email: str
    items: List[InvoiceItem]
    subtotal: float
    tax: float
    total: float
    due_date: str  # ISO format date string
    notes: Optional[str] = None

class Invoice(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    invoice_number: str
    booking_id: Optional[str] = None
    customer_name: str
    customer_email: str
    items: List[InvoiceItem]
    subtotal: float
    tax: float
    total: float
    status: InvoiceStatus = InvoiceStatus.DRAFT
    issue_date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    due_date: datetime
    notes: Optional[str] = None

# RMS Models
class PriceAnalysis(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    room_type: str
    date: datetime
    current_price: float
    suggested_price: float
    occupancy_rate: float
    demand_score: float
    competitor_avg: Optional[float] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# Loyalty Models
class LoyaltyProgramCreate(BaseModel):
    guest_id: str
    tier: LoyaltyTier = LoyaltyTier.BRONZE
    points: int = 0
    lifetime_points: int = 0

class LoyaltyProgram(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    guest_id: str
    tier: LoyaltyTier = LoyaltyTier.BRONZE
    points: int = 0
    lifetime_points: int = 0
    last_activity: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class LoyaltyTransactionCreate(BaseModel):
    guest_id: str
    points: int
    transaction_type: str  # earned, redeemed
    description: str

class LoyaltyTransaction(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    guest_id: str
    points: int
    transaction_type: str  # earned, redeemed
    description: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# Marketplace Models
class Product(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    category: str  # equipment, cleaning, amenities
    description: str
    price: float
    unit: str
    supplier: str
    image_url: Optional[str] = None
    in_stock: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class Order(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    items: List[Dict[str, Any]]
    total_amount: float
    status: str = "pending"
    delivery_address: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# ============= HELPER FUNCTIONS =============

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def create_token(user_id: str, tenant_id: str) -> str:
    payload = {
        'user_id': user_id,
        'tenant_id': tenant_id,
        'exp': datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRATION_HOURS)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        token = credentials.credentials
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = payload.get('user_id')
        tenant_id = payload.get('tenant_id')
        
        user_doc = await db.users.find_one({'id': user_id, 'tenant_id': tenant_id}, {'_id': 0})
        if not user_doc:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
        
        return User(**user_doc)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

# ============= AUTH ENDPOINTS =============

@api_router.post("/auth/register", response_model=TokenResponse)
async def register_tenant(data: TenantRegister):
    # Check if email exists
    existing = await db.users.find_one({'email': data.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create tenant
    tenant = Tenant(
        name=data.name,
        property_name=data.property_name,
        email=data.email,
        phone=data.phone,
        address=data.address
    )
    tenant_dict = tenant.model_dump()
    tenant_dict['created_at'] = tenant_dict['created_at'].isoformat()
    await db.tenants.insert_one(tenant_dict)
    
    # Create admin user
    user = User(
        tenant_id=tenant.id,
        email=data.email,
        name=data.name,
        role=UserRole.ADMIN
    )
    user_dict = user.model_dump()
    user_dict['password'] = hash_password(data.password)
    user_dict['created_at'] = user_dict['created_at'].isoformat()
    await db.users.insert_one(user_dict)
    
    # Create token
    token = create_token(user.id, tenant.id)
    
    return TokenResponse(access_token=token, user=user, tenant=tenant)

@api_router.post("/auth/login", response_model=TokenResponse)
async def login(data: UserLogin):
    user_doc = await db.users.find_one({'email': data.email}, {'_id': 0})
    if not user_doc or not verify_password(data.password, user_doc['password']):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    tenant_doc = await db.tenants.find_one({'id': user_doc['tenant_id']}, {'_id': 0})
    if not tenant_doc:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    user = User(**{k: v for k, v in user_doc.items() if k != 'password'})
    tenant = Tenant(**tenant_doc)
    token = create_token(user.id, tenant.id)
    
    return TokenResponse(access_token=token, user=user, tenant=tenant)

@api_router.get("/auth/me", response_model=User)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user

# ============= PMS ENDPOINTS =============

# Rooms
@api_router.post("/pms/rooms", response_model=Room)
async def create_room(room: Room, current_user: User = Depends(get_current_user)):
    room.tenant_id = current_user.tenant_id
    room_dict = room.model_dump()
    room_dict['created_at'] = room_dict['created_at'].isoformat()
    await db.rooms.insert_one(room_dict)
    return room

@api_router.get("/pms/rooms", response_model=List[Room])
async def get_rooms(current_user: User = Depends(get_current_user)):
    rooms = await db.rooms.find({'tenant_id': current_user.tenant_id}, {'_id': 0}).to_list(1000)
    return rooms

@api_router.put("/pms/rooms/{room_id}", response_model=Room)
async def update_room(room_id: str, updates: Dict[str, Any], current_user: User = Depends(get_current_user)):
    await db.rooms.update_one(
        {'id': room_id, 'tenant_id': current_user.tenant_id},
        {'$set': updates}
    )
    room_doc = await db.rooms.find_one({'id': room_id}, {'_id': 0})
    return Room(**room_doc)

# Guests
@api_router.post("/pms/guests", response_model=Guest)
async def create_guest(guest: Guest, current_user: User = Depends(get_current_user)):
    guest.tenant_id = current_user.tenant_id
    guest_dict = guest.model_dump()
    guest_dict['created_at'] = guest_dict['created_at'].isoformat()
    await db.guests.insert_one(guest_dict)
    return guest

@api_router.get("/pms/guests", response_model=List[Guest])
async def get_guests(current_user: User = Depends(get_current_user)):
    guests = await db.guests.find({'tenant_id': current_user.tenant_id}, {'_id': 0}).to_list(1000)
    return guests

# Bookings
@api_router.post("/pms/bookings", response_model=Booking)
async def create_booking(booking: Booking, current_user: User = Depends(get_current_user)):
    booking.tenant_id = current_user.tenant_id
    booking_dict = booking.model_dump()
    booking_dict['check_in'] = booking_dict['check_in'].isoformat()
    booking_dict['check_out'] = booking_dict['check_out'].isoformat()
    booking_dict['created_at'] = booking_dict['created_at'].isoformat()
    await db.bookings.insert_one(booking_dict)
    
    # Update room status
    await db.rooms.update_one(
        {'id': booking.room_id},
        {'$set': {'status': RoomStatus.OCCUPIED}}
    )
    
    return booking

@api_router.get("/pms/bookings", response_model=List[Booking])
async def get_bookings(current_user: User = Depends(get_current_user)):
    bookings = await db.bookings.find({'tenant_id': current_user.tenant_id}, {'_id': 0}).to_list(1000)
    return bookings

@api_router.get("/pms/dashboard")
async def get_pms_dashboard(current_user: User = Depends(get_current_user)):
    total_rooms = await db.rooms.count_documents({'tenant_id': current_user.tenant_id})
    occupied_rooms = await db.rooms.count_documents({'tenant_id': current_user.tenant_id, 'status': 'occupied'})
    today_checkins = await db.bookings.count_documents({
        'tenant_id': current_user.tenant_id,
        'check_in': {'$gte': datetime.now(timezone.utc).replace(hour=0, minute=0).isoformat()}
    })
    total_guests = await db.guests.count_documents({'tenant_id': current_user.tenant_id})
    
    return {
        'total_rooms': total_rooms,
        'occupied_rooms': occupied_rooms,
        'available_rooms': total_rooms - occupied_rooms,
        'occupancy_rate': (occupied_rooms / total_rooms * 100) if total_rooms > 0 else 0,
        'today_checkins': today_checkins,
        'total_guests': total_guests
    }

# ============= INVOICE ENDPOINTS =============

@api_router.post("/invoices", response_model=Invoice)
async def create_invoice(invoice: Invoice, current_user: User = Depends(get_current_user)):
    invoice.tenant_id = current_user.tenant_id
    # Generate invoice number
    count = await db.invoices.count_documents({'tenant_id': current_user.tenant_id})
    invoice.invoice_number = f"INV-{count + 1:05d}"
    
    invoice_dict = invoice.model_dump()
    invoice_dict['issue_date'] = invoice_dict['issue_date'].isoformat()
    invoice_dict['due_date'] = invoice_dict['due_date'].isoformat()
    await db.invoices.insert_one(invoice_dict)
    return invoice

@api_router.get("/invoices", response_model=List[Invoice])
async def get_invoices(current_user: User = Depends(get_current_user)):
    invoices = await db.invoices.find({'tenant_id': current_user.tenant_id}, {'_id': 0}).to_list(1000)
    return invoices

@api_router.put("/invoices/{invoice_id}", response_model=Invoice)
async def update_invoice(invoice_id: str, updates: Dict[str, Any], current_user: User = Depends(get_current_user)):
    await db.invoices.update_one(
        {'id': invoice_id, 'tenant_id': current_user.tenant_id},
        {'$set': updates}
    )
    invoice_doc = await db.invoices.find_one({'id': invoice_id}, {'_id': 0})
    return Invoice(**invoice_doc)

@api_router.get("/invoices/stats")
async def get_invoice_stats(current_user: User = Depends(get_current_user)):
    invoices = await db.invoices.find({'tenant_id': current_user.tenant_id}, {'_id': 0}).to_list(1000)
    
    total_revenue = sum(inv['total'] for inv in invoices if inv['status'] == 'paid')
    pending_amount = sum(inv['total'] for inv in invoices if inv['status'] in ['draft', 'sent'])
    overdue_amount = sum(inv['total'] for inv in invoices if inv['status'] == 'overdue')
    
    return {
        'total_invoices': len(invoices),
        'total_revenue': total_revenue,
        'pending_amount': pending_amount,
        'overdue_amount': overdue_amount
    }

# ============= RMS ENDPOINTS =============

@api_router.post("/rms/analysis", response_model=PriceAnalysis)
async def create_price_analysis(analysis: PriceAnalysis, current_user: User = Depends(get_current_user)):
    analysis.tenant_id = current_user.tenant_id
    analysis_dict = analysis.model_dump()
    analysis_dict['date'] = analysis_dict['date'].isoformat()
    analysis_dict['created_at'] = analysis_dict['created_at'].isoformat()
    await db.price_analysis.insert_one(analysis_dict)
    return analysis

@api_router.get("/rms/analysis", response_model=List[PriceAnalysis])
async def get_price_analysis(current_user: User = Depends(get_current_user)):
    analyses = await db.price_analysis.find({'tenant_id': current_user.tenant_id}, {'_id': 0}).to_list(1000)
    return analyses

@api_router.get("/rms/suggestions")
async def get_price_suggestions(current_user: User = Depends(get_current_user)):
    # Get all rooms
    rooms = await db.rooms.find({'tenant_id': current_user.tenant_id}, {'_id': 0}).to_list(1000)
    
    suggestions = []
    for room in rooms:
        # Calculate occupancy rate
        total_bookings = await db.bookings.count_documents({
            'tenant_id': current_user.tenant_id,
            'room_id': room['id']
        })
        
        occupancy_rate = min(total_bookings * 10, 100)  # Simplified calculation
        demand_score = occupancy_rate / 100
        
        # Simple pricing logic
        suggested_price = room['base_price']
        if occupancy_rate > 80:
            suggested_price *= 1.2
        elif occupancy_rate < 50:
            suggested_price *= 0.9
        
        suggestions.append({
            'room_type': room['room_type'],
            'room_number': room['room_number'],
            'current_price': room['base_price'],
            'suggested_price': round(suggested_price, 2),
            'occupancy_rate': occupancy_rate,
            'demand_score': demand_score
        })
    
    return suggestions

# ============= LOYALTY ENDPOINTS =============

@api_router.post("/loyalty/programs", response_model=LoyaltyProgram)
async def create_loyalty_program(program: LoyaltyProgram, current_user: User = Depends(get_current_user)):
    program.tenant_id = current_user.tenant_id
    program_dict = program.model_dump()
    program_dict['last_activity'] = program_dict['last_activity'].isoformat()
    await db.loyalty_programs.insert_one(program_dict)
    return program

@api_router.get("/loyalty/programs", response_model=List[LoyaltyProgram])
async def get_loyalty_programs(current_user: User = Depends(get_current_user)):
    programs = await db.loyalty_programs.find({'tenant_id': current_user.tenant_id}, {'_id': 0}).to_list(1000)
    return programs

@api_router.post("/loyalty/transactions", response_model=LoyaltyTransaction)
async def create_loyalty_transaction(transaction: LoyaltyTransaction, current_user: User = Depends(get_current_user)):
    transaction.tenant_id = current_user.tenant_id
    transaction_dict = transaction.model_dump()
    transaction_dict['created_at'] = transaction_dict['created_at'].isoformat()
    await db.loyalty_transactions.insert_one(transaction_dict)
    
    # Update loyalty program points
    if transaction.transaction_type == 'earned':
        await db.loyalty_programs.update_one(
            {'guest_id': transaction.guest_id, 'tenant_id': current_user.tenant_id},
            {'$inc': {'points': transaction.points, 'lifetime_points': transaction.points}}
        )
    else:
        await db.loyalty_programs.update_one(
            {'guest_id': transaction.guest_id, 'tenant_id': current_user.tenant_id},
            {'$inc': {'points': -transaction.points}}
        )
    
    return transaction

@api_router.get("/loyalty/guest/{guest_id}")
async def get_guest_loyalty(guest_id: str, current_user: User = Depends(get_current_user)):
    program = await db.loyalty_programs.find_one(
        {'guest_id': guest_id, 'tenant_id': current_user.tenant_id},
        {'_id': 0}
    )
    
    transactions = await db.loyalty_transactions.find(
        {'guest_id': guest_id, 'tenant_id': current_user.tenant_id},
        {'_id': 0}
    ).to_list(1000)
    
    return {
        'program': program,
        'transactions': transactions
    }

# ============= MARKETPLACE ENDPOINTS =============

@api_router.get("/marketplace/products", response_model=List[Product])
async def get_products():
    products = await db.products.find({}, {'_id': 0}).to_list(1000)
    return products

@api_router.post("/marketplace/orders", response_model=Order)
async def create_order(order: Order, current_user: User = Depends(get_current_user)):
    order.tenant_id = current_user.tenant_id
    order_dict = order.model_dump()
    order_dict['created_at'] = order_dict['created_at'].isoformat()
    await db.orders.insert_one(order_dict)
    return order

@api_router.get("/marketplace/orders", response_model=List[Order])
async def get_orders(current_user: User = Depends(get_current_user)):
    orders = await db.orders.find({'tenant_id': current_user.tenant_id}, {'_id': 0}).to_list(1000)
    return orders

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
