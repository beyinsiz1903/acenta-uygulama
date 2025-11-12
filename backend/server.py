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
# ============= PMS - ROOMS MANAGEMENT =============

@api_router.post("/pms/rooms", response_model=Room)
async def create_room(room_data: RoomCreate, current_user: User = Depends(get_current_user)):
    room = Room(tenant_id=current_user.tenant_id, **room_data.model_dump())
    room_dict = room.model_dump()
    room_dict['created_at'] = room_dict['created_at'].isoformat()
    await db.rooms.insert_one(room_dict)
    return room

@api_router.get("/pms/rooms", response_model=List[Room])
async def get_rooms(current_user: User = Depends(get_current_user)):
    rooms = await db.rooms.find({'tenant_id': current_user.tenant_id}, {'_id': 0}).to_list(1000)
    return rooms

@api_router.put("/pms/rooms/{room_id}")
async def update_room(room_id: str, updates: Dict[str, Any], current_user: User = Depends(get_current_user)):
    await db.rooms.update_one({'id': room_id, 'tenant_id': current_user.tenant_id}, {'$set': updates})
    room_doc = await db.rooms.find_one({'id': room_id}, {'_id': 0})
    return room_doc

# ============= PMS - GUESTS MANAGEMENT =============

@api_router.post("/pms/guests", response_model=Guest)
async def create_guest(guest_data: GuestCreate, current_user: User = Depends(get_current_user)):
    guest = Guest(tenant_id=current_user.tenant_id, **guest_data.model_dump())
    guest_dict = guest.model_dump()
    guest_dict['created_at'] = guest_dict['created_at'].isoformat()
    await db.guests.insert_one(guest_dict)
    return guest

@api_router.get("/pms/guests", response_model=List[Guest])
async def get_guests(current_user: User = Depends(get_current_user)):
    guests = await db.guests.find({'tenant_id': current_user.tenant_id}, {'_id': 0}).to_list(1000)
    return guests

# ============= PMS - BOOKINGS MANAGEMENT =============

@api_router.post("/pms/bookings", response_model=Booking)
async def create_booking(booking_data: BookingCreate, current_user: User = Depends(get_current_user)):
    check_in_dt = datetime.fromisoformat(booking_data.check_in.replace('Z', '+00:00'))
    check_out_dt = datetime.fromisoformat(booking_data.check_out.replace('Z', '+00:00'))
    
    booking = Booking(
        tenant_id=current_user.tenant_id,
        guest_id=booking_data.guest_id,
        room_id=booking_data.room_id,
        check_in=check_in_dt,
        check_out=check_out_dt,
        guests_count=booking_data.guests_count,
        total_amount=booking_data.total_amount,
        channel=booking_data.channel,
        rate_plan=booking_data.rate_plan,
        special_requests=booking_data.special_requests
    )
    
    qr_token = generate_time_based_qr_token(booking.id, expiry_hours=72)
    qr_data = f"booking:{booking.id}:token:{qr_token}"
    qr_code = generate_qr_code(qr_data)
    
    booking.qr_code = qr_code
    booking.qr_code_data = qr_token
    
    booking_dict = booking.model_dump()
    booking_dict['check_in'] = booking_dict['check_in'].isoformat()
    booking_dict['check_out'] = booking_dict['check_out'].isoformat()
    booking_dict['created_at'] = booking_dict['created_at'].isoformat()
    await db.bookings.insert_one(booking_dict)
    
    await db.rooms.update_one({'id': booking.room_id}, {'$set': {'status': 'occupied'}})
    
    return booking

@api_router.get("/pms/bookings", response_model=List[Booking])
async def get_bookings(current_user: User = Depends(get_current_user)):
    bookings = await db.bookings.find({'tenant_id': current_user.tenant_id}, {'_id': 0}).to_list(1000)
    return bookings

@api_router.get("/pms/dashboard")
async def get_pms_dashboard(current_user: User = Depends(get_current_user)):
    total_rooms = await db.rooms.count_documents({'tenant_id': current_user.tenant_id})
    occupied_rooms = await db.rooms.count_documents({'tenant_id': current_user.tenant_id, 'status': 'occupied'})
    today = datetime.now(timezone.utc).replace(hour=0, minute=0).isoformat()
    today_checkins = await db.bookings.count_documents({'tenant_id': current_user.tenant_id, 'check_in': {'$gte': today}})
    total_guests = await db.guests.count_documents({'tenant_id': current_user.tenant_id})
    
    return {
        'total_rooms': total_rooms,
        'occupied_rooms': occupied_rooms,
        'available_rooms': total_rooms - occupied_rooms,
        'occupancy_rate': (occupied_rooms / total_rooms * 100) if total_rooms > 0 else 0,
        'today_checkins': today_checkins,
        'total_guests': total_guests
    }

@api_router.get("/pms/room-services")
async def get_hotel_room_services(current_user: User = Depends(get_current_user)):
    services = await db.room_services.find({'tenant_id': current_user.tenant_id}, {'_id': 0}).to_list(1000)
    return services

@api_router.put("/pms/room-services/{service_id}")
async def update_room_service(service_id: str, updates: Dict[str, Any], current_user: User = Depends(get_current_user)):
    if 'status' in updates and updates['status'] == 'completed':
        updates['completed_at'] = datetime.now(timezone.utc).isoformat()
    await db.room_services.update_one({'id': service_id, 'tenant_id': current_user.tenant_id}, {'$set': updates})
    service = await db.room_services.find_one({'id': service_id}, {'_id': 0})
    return service

# ============= INVOICES =============

@api_router.post("/invoices", response_model=Invoice)
async def create_invoice(invoice_data: InvoiceCreate, current_user: User = Depends(get_current_user)):
    count = await db.invoices.count_documents({'tenant_id': current_user.tenant_id})
    invoice_number = f"INV-{count + 1:05d}"
    due_date_dt = datetime.fromisoformat(invoice_data.due_date.replace('Z', '+00:00'))
    invoice = Invoice(tenant_id=current_user.tenant_id, invoice_number=invoice_number, due_date=due_date_dt,
                     **{k: v for k, v in invoice_data.model_dump().items() if k != 'due_date'})
    invoice_dict = invoice.model_dump()
    invoice_dict['issue_date'] = invoice_dict['issue_date'].isoformat()
    invoice_dict['due_date'] = invoice_dict['due_date'].isoformat()
    await db.invoices.insert_one(invoice_dict)
    return invoice

@api_router.get("/invoices", response_model=List[Invoice])
async def get_invoices(current_user: User = Depends(get_current_user)):
    invoices = await db.invoices.find({'tenant_id': current_user.tenant_id}, {'_id': 0}).to_list(1000)
    return invoices

@api_router.put("/invoices/{invoice_id}")
async def update_invoice(invoice_id: str, updates: Dict[str, Any], current_user: User = Depends(get_current_user)):
    await db.invoices.update_one({'id': invoice_id, 'tenant_id': current_user.tenant_id}, {'$set': updates})
    invoice_doc = await db.invoices.find_one({'id': invoice_id}, {'_id': 0})
    return invoice_doc

@api_router.get("/invoices/stats")
async def get_invoice_stats(current_user: User = Depends(get_current_user)):
    invoices = await db.invoices.find({'tenant_id': current_user.tenant_id}, {'_id': 0}).to_list(1000)
    total_revenue = sum(inv['total'] for inv in invoices if inv['status'] == 'paid')
    pending_amount = sum(inv['total'] for inv in invoices if inv['status'] in ['draft', 'sent'])
    overdue_amount = sum(inv['total'] for inv in invoices if inv['status'] == 'overdue')
    return {'total_invoices': len(invoices), 'total_revenue': total_revenue, 'pending_amount': pending_amount, 'overdue_amount': overdue_amount}

# ============= RMS =============

@api_router.get("/rms/suggestions")
async def get_price_suggestions(current_user: User = Depends(get_current_user)):
    rooms = await db.rooms.find({'tenant_id': current_user.tenant_id}, {'_id': 0}).to_list(1000)
    suggestions = []
    for room in rooms:
        total_bookings = await db.bookings.count_documents({'tenant_id': current_user.tenant_id, 'room_id': room['id']})
        occupancy_rate = min(total_bookings * 10, 100)
        suggested_price = room['base_price'] * (1.2 if occupancy_rate > 80 else 0.9 if occupancy_rate < 50 else 1.0)
        suggestions.append({'room_type': room['room_type'], 'room_number': room['room_number'], 'current_price': room['base_price'],
                          'suggested_price': round(suggested_price, 2), 'occupancy_rate': occupancy_rate, 'demand_score': occupancy_rate/100})
    return suggestions

# ============= LOYALTY =============

@api_router.post("/loyalty/programs", response_model=LoyaltyProgram)
async def create_loyalty_program(program_data: LoyaltyProgramCreate, current_user: User = Depends(get_current_user)):
    program = LoyaltyProgram(tenant_id=current_user.tenant_id, **program_data.model_dump())
    program_dict = program.model_dump()
    program_dict['last_activity'] = program_dict['last_activity'].isoformat()
    await db.loyalty_programs.insert_one(program_dict)
    return program

@api_router.get("/loyalty/programs", response_model=List[LoyaltyProgram])
async def get_loyalty_programs(current_user: User = Depends(get_current_user)):
    programs = await db.loyalty_programs.find({'tenant_id': current_user.tenant_id}, {'_id': 0}).to_list(1000)
    return programs

@api_router.post("/loyalty/transactions", response_model=LoyaltyTransaction)
async def create_loyalty_transaction(transaction_data: LoyaltyTransactionCreate, current_user: User = Depends(get_current_user)):
    transaction = LoyaltyTransaction(tenant_id=current_user.tenant_id, **transaction_data.model_dump())
    transaction_dict = transaction.model_dump()
    transaction_dict['created_at'] = transaction_dict['created_at'].isoformat()
    await db.loyalty_transactions.insert_one(transaction_dict)
    
    if transaction.transaction_type == 'earned':
        await db.loyalty_programs.update_one({'guest_id': transaction.guest_id, 'tenant_id': current_user.tenant_id},
                                            {'$inc': {'points': transaction.points, 'lifetime_points': transaction.points}})
    else:
        await db.loyalty_programs.update_one({'guest_id': transaction.guest_id, 'tenant_id': current_user.tenant_id},
                                            {'$inc': {'points': -transaction.points}})
    return transaction

# ============= MARKETPLACE =============

@api_router.post("/marketplace/products", response_model=Product)
async def create_product(product: Product):
    product_dict = product.model_dump()
    product_dict['created_at'] = product_dict['created_at'].isoformat()
    await db.products.insert_one(product_dict)
    return product

@api_router.get("/marketplace/products", response_model=List[Product])
async def get_products():
    products = await db.products.find({}, {'_id': 0}).to_list(1000)
    return products

@api_router.post("/marketplace/orders", response_model=Order)
async def create_order(order_data: OrderCreate, current_user: User = Depends(get_current_user)):
    order = Order(tenant_id=current_user.tenant_id, **order_data.model_dump())
    order_dict = order.model_dump()
    order_dict['created_at'] = order_dict['created_at'].isoformat()
    await db.orders.insert_one(order_dict)
    return order

@api_router.get("/marketplace/orders", response_model=List[Order])
async def get_orders(current_user: User = Depends(get_current_user)):
    orders = await db.orders.find({'tenant_id': current_user.tenant_id}, {'_id': 0}).to_list(1000)
    return orders

# Include router
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
