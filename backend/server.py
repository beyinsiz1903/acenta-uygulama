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
from datetime import datetime, timezone, timedelta, date
import bcrypt
import jwt
from enum import Enum
import qrcode
import io
import base64
import secrets

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

JWT_SECRET = os.environ.get('JWT_SECRET', 'your-secret-key-change-in-production')
JWT_ALGORITHM = 'HS256'
JWT_EXPIRATION_HOURS = 24

app = FastAPI(title="RoomOps Platform")
api_router = APIRouter(prefix="/api")
security = HTTPBearer()

# ============= ENUMS =============

class UserRole(str, Enum):
    ADMIN = "admin"
    MANAGER = "manager"
    FRONT_DESK = "front_desk"
    HOUSEKEEPING = "housekeeping"
    STAFF = "staff"
    GUEST = "guest"

class RoomStatus(str, Enum):
    AVAILABLE = "available"
    OCCUPIED = "occupied"
    DIRTY = "dirty"
    CLEANING = "cleaning"
    INSPECTED = "inspected"
    MAINTENANCE = "maintenance"
    OUT_OF_ORDER = "out_of_order"

class BookingStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CHECKED_IN = "checked_in"
    CHECKED_OUT = "checked_out"
    NO_SHOW = "no_show"
    CANCELLED = "cancelled"

class PaymentStatus(str, Enum):
    PENDING = "pending"
    PARTIAL = "partial"
    PAID = "paid"
    REFUNDED = "refunded"

class PaymentMethod(str, Enum):
    CASH = "cash"
    CARD = "card"
    BANK_TRANSFER = "bank_transfer"
    ONLINE = "online"

class ChargeType(str, Enum):
    ROOM = "room"
    FOOD = "food"
    BEVERAGE = "beverage"
    LAUNDRY = "laundry"
    MINIBAR = "minibar"
    PHONE = "phone"
    SPA = "spa"
    OTHER = "other"

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

class RoomServiceStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class ChannelType(str, Enum):
    DIRECT = "direct"
    BOOKING_COM = "booking_com"
    EXPEDIA = "expedia"
    AIRBNB = "airbnb"
    AGODA = "agoda"
    OWN_WEBSITE = "own_website"

# ============= MODELS =============

class Tenant(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    property_name: str
    email: EmailStr
    phone: str
    address: str
    subscription_status: str = "active"
    location: Optional[str] = None
    amenities: List[str] = []
    images: List[str] = []
    description: Optional[str] = None
    total_rooms: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class User(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: Optional[str] = None
    email: EmailStr
    name: str
    role: UserRole
    phone: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class TenantRegister(BaseModel):
    property_name: str
    email: EmailStr
    password: str
    name: str
    phone: str
    address: str
    location: Optional[str] = None
    description: Optional[str] = None

class GuestRegister(BaseModel):
    email: EmailStr
    password: str
    name: str
    phone: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: User
    tenant: Optional[Tenant] = None

class NotificationPreferences(BaseModel):
    model_config = ConfigDict(extra="ignore")
    user_id: str
    email_notifications: bool = True
    whatsapp_notifications: bool = False
    in_app_notifications: bool = True
    booking_updates: bool = True
    promotional: bool = True
    room_service_updates: bool = True

# Room Models
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
    current_booking_id: Optional[str] = None
    last_cleaned: Optional[datetime] = None
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class HousekeepingTask(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    room_id: str
    task_type: str  # cleaning, inspection, maintenance
    assigned_to: Optional[str] = None
    status: str = "pending"  # pending, in_progress, completed
    priority: str = "normal"  # low, normal, high, urgent
    notes: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# Guest & Booking Models
class GuestCreate(BaseModel):
    name: str
    email: EmailStr
    phone: str
    id_number: str
    nationality: Optional[str] = None
    address: Optional[str] = None
    vip_status: bool = False

class Guest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    name: str
    email: EmailStr
    phone: str
    id_number: str
    nationality: Optional[str] = None
    address: Optional[str] = None
    vip_status: bool = False
    loyalty_points: int = 0
    total_stays: int = 0
    total_spend: float = 0.0
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class BookingCreate(BaseModel):
    guest_id: str
    room_id: str
    check_in: str
    check_out: str
    guests_count: int
    total_amount: float
    channel: ChannelType = ChannelType.DIRECT
    special_requests: Optional[str] = None
    rate_plan: Optional[str] = None

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
    paid_amount: float = 0.0
    status: BookingStatus = BookingStatus.PENDING
    channel: ChannelType = ChannelType.DIRECT
    rate_plan: Optional[str] = "Standard"
    special_requests: Optional[str] = None
    qr_code: Optional[str] = None
    qr_code_data: Optional[str] = None
    checked_in_at: Optional[datetime] = None
    checked_out_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# Folio & Payment Models
class FolioCharge(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    booking_id: str
    charge_type: ChargeType
    description: str
    amount: float
    quantity: float = 1.0
    total: float
    date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    posted_by: Optional[str] = None

class Payment(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    booking_id: str
    amount: float
    method: PaymentMethod
    status: PaymentStatus = PaymentStatus.PENDING
    reference: Optional[str] = None
    notes: Optional[str] = None
    processed_by: Optional[str] = None
    processed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# Channel Manager Models
class ChannelRate(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    room_type: str
    channel: ChannelType
    date: date
    rate: float
    availability: int
    min_stay: int = 1
    max_stay: Optional[int] = None
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ChannelMapping(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    channel: ChannelType
    room_type: str
    channel_room_id: str
    active: bool = True

# Room Service Models
class RoomServiceCreate(BaseModel):
    booking_id: str
    service_type: str
    description: str
    notes: Optional[str] = None

class RoomService(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    booking_id: str
    guest_id: str
    service_type: str
    description: str
    notes: Optional[str] = None
    status: RoomServiceStatus = RoomServiceStatus.PENDING
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None

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
    due_date: str
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
    transaction_type: str
    description: str

class LoyaltyTransaction(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    guest_id: str
    points: int
    transaction_type: str
    description: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# Marketplace Models
class Product(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    category: str
    description: str
    price: float
    unit: str
    supplier: str
    image_url: Optional[str] = None
    in_stock: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class OrderCreate(BaseModel):
    items: List[Dict[str, Any]]
    total_amount: float
    delivery_address: str

class Order(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    items: List[Dict[str, Any]]
    total_amount: float
    status: str = "pending"
    delivery_address: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

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

# ============= HELPER FUNCTIONS =============

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def create_token(user_id: str, tenant_id: Optional[str] = None) -> str:
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
        
        user_doc = await db.users.find_one({'id': user_id}, {'_id': 0})
        if not user_doc:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
        
        return User(**user_doc)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

def generate_qr_code(data: str) -> str:
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    img_base64 = base64.b64encode(buffer.getvalue()).decode()
    return f"data:image/png;base64,{img_base64}"

def generate_time_based_qr_token(booking_id: str, expiry_hours: int = 72) -> str:
    expiry = datetime.now(timezone.utc) + timedelta(hours=expiry_hours)
    token = secrets.token_urlsafe(32)
    return jwt.encode({
        'booking_id': booking_id,
        'token': token,
        'exp': expiry
    }, JWT_SECRET, algorithm=JWT_ALGORITHM)

# ============= AUTH ENDPOINTS =============

@api_router.post("/auth/register", response_model=TokenResponse)
async def register_tenant(data: TenantRegister):
    existing = await db.users.find_one({'email': data.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    tenant = Tenant(
        name=data.name,
        property_name=data.property_name,
        email=data.email,
        phone=data.phone,
        address=data.address,
        location=data.location,
        description=data.description
    )
    tenant_dict = tenant.model_dump()
    tenant_dict['created_at'] = tenant_dict['created_at'].isoformat()
    await db.tenants.insert_one(tenant_dict)
    
    user = User(
        tenant_id=tenant.id,
        email=data.email,
        name=data.name,
        role=UserRole.ADMIN,
        phone=data.phone
    )
    user_dict = user.model_dump()
    user_dict['password'] = hash_password(data.password)
    user_dict['created_at'] = user_dict['created_at'].isoformat()
    await db.users.insert_one(user_dict)
    
    token = create_token(user.id, tenant.id)
    return TokenResponse(access_token=token, user=user, tenant=tenant)

@api_router.post("/auth/register-guest", response_model=TokenResponse)
async def register_guest(data: GuestRegister):
    existing = await db.users.find_one({'email': data.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    user = User(
        tenant_id=None,
        email=data.email,
        name=data.name,
        role=UserRole.GUEST,
        phone=data.phone
    )
    user_dict = user.model_dump()
    user_dict['password'] = hash_password(data.password)
    user_dict['created_at'] = user_dict['created_at'].isoformat()
    await db.users.insert_one(user_dict)
    
    prefs = NotificationPreferences(user_id=user.id)
    await db.notification_preferences.insert_one(prefs.model_dump())
    
    token = create_token(user.id, None)
    return TokenResponse(access_token=token, user=user, tenant=None)

@api_router.post("/auth/login", response_model=TokenResponse)
async def login(data: UserLogin):
    user_doc = await db.users.find_one({'email': data.email}, {'_id': 0})
    if not user_doc or not verify_password(data.password, user_doc['password']):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    user = User(**{k: v for k, v in user_doc.items() if k != 'password'})
    
    tenant = None
    if user.tenant_id:
        tenant_doc = await db.tenants.find_one({'id': user.tenant_id}, {'_id': 0})
        if tenant_doc:
            tenant = Tenant(**tenant_doc)
    
    token = create_token(user.id, user.tenant_id)
    return TokenResponse(access_token=token, user=user, tenant=tenant)

@api_router.get("/auth/me", response_model=User)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user

# ============= GUEST PORTAL ENDPOINTS =============

@api_router.get("/guest/bookings")
async def get_guest_bookings(current_user: User = Depends(get_current_user)):
    if current_user.role != UserRole.GUEST:
        raise HTTPException(status_code=403, detail="Only guests can access this endpoint")
    
    guest_records = await db.guests.find({'email': current_user.email}, {'_id': 0}).to_list(1000)
    guest_ids = [g['id'] for g in guest_records]
    
    if not guest_ids:
        return {'active_bookings': [], 'past_bookings': []}
    
    all_bookings = await db.bookings.find({'guest_id': {'$in': guest_ids}}, {'_id': 0}).to_list(1000)
    
    now = datetime.now(timezone.utc)
    active_bookings = []
    past_bookings = []
    
    for booking in all_bookings:
        tenant = await db.tenants.find_one({'id': booking['tenant_id']}, {'_id': 0})
        room = await db.rooms.find_one({'id': booking['room_id']}, {'_id': 0})
        
        booking_data = {**booking, 'hotel': tenant, 'room': room}
        
        checkout_date = datetime.fromisoformat(booking['check_out'].replace('Z', '+00:00')) if isinstance(booking['check_out'], str) else booking['check_out']
        
        if checkout_date >= now and booking['status'] not in ['cancelled', 'checked_out']:
            active_bookings.append(booking_data)
        else:
            past_bookings.append(booking_data)
    
    return {'active_bookings': active_bookings, 'past_bookings': past_bookings}

@api_router.get("/guest/loyalty")
async def get_guest_loyalty(current_user: User = Depends(get_current_user)):
    if current_user.role != UserRole.GUEST:
        raise HTTPException(status_code=403, detail="Only guests can access this endpoint")
    
    guest_records = await db.guests.find({'email': current_user.email}, {'_id': 0}).to_list(1000)
    guest_ids = [g['id'] for g in guest_records]
    
    if not guest_ids:
        return {'loyalty_programs': [], 'total_points': 0}
    
    loyalty_programs = await db.loyalty_programs.find({'guest_id': {'$in': guest_ids}}, {'_id': 0}).to_list(1000)
    
    enriched_programs = []
    total_points = 0
    
    for program in loyalty_programs:
        tenant = await db.tenants.find_one({'id': program['tenant_id']}, {'_id': 0})
        enriched_programs.append({**program, 'hotel': tenant})
        total_points += program['points']
    
    return {'loyalty_programs': enriched_programs, 'total_points': total_points}

@api_router.get("/guest/notification-preferences")
async def get_notification_preferences(current_user: User = Depends(get_current_user)):
    prefs = await db.notification_preferences.find_one({'user_id': current_user.id}, {'_id': 0})
    if not prefs:
        prefs = NotificationPreferences(user_id=current_user.id).model_dump()
        await db.notification_preferences.insert_one(prefs)
    return prefs

@api_router.put("/guest/notification-preferences")
async def update_notification_preferences(preferences: Dict[str, bool], current_user: User = Depends(get_current_user)):
    await db.notification_preferences.update_one(
        {'user_id': current_user.id},
        {'$set': preferences},
        upsert=True
    )
    return {'message': 'Preferences updated'}

@api_router.post("/guest/room-service")
async def create_room_service_request(request: RoomServiceCreate, current_user: User = Depends(get_current_user)):
    if current_user.role != UserRole.GUEST:
        raise HTTPException(status_code=403, detail="Only guests can create room service requests")
    
    booking = await db.bookings.find_one({'id': request.booking_id}, {'_id': 0})
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    guest = await db.guests.find_one({'email': current_user.email, 'id': booking['guest_id']}, {'_id': 0})
    if not guest:
        raise HTTPException(status_code=403, detail="This booking does not belong to you")
    
    room_service = RoomService(
        tenant_id=booking['tenant_id'],
        booking_id=request.booking_id,
        guest_id=booking['guest_id'],
        service_type=request.service_type,
        description=request.description,
        notes=request.notes
    )
    
    service_dict = room_service.model_dump()
    service_dict['created_at'] = service_dict['created_at'].isoformat()
    await db.room_services.insert_one(service_dict)
    
    return room_service

@api_router.get("/guest/room-service/{booking_id}")
async def get_room_service_requests(booking_id: str, current_user: User = Depends(get_current_user)):
    services = await db.room_services.find({'booking_id': booking_id}, {'_id': 0}).to_list(1000)
    return services

@api_router.get("/guest/hotels")
async def browse_hotels(current_user: User = Depends(get_current_user)):
    hotels = await db.tenants.find({}, {'_id': 0}).to_list(1000)
    return hotels

# Continue in next message due to length...