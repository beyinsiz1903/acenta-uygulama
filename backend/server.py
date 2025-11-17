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
import sys

# Add current directory to path for accounting models
sys.path.append(os.path.dirname(__file__))

# Import accounting models
try:
    from accounting_models import (
        AccountingInvoice, AccountingInvoiceItem, AdditionalTax,
        Supplier, BankAccount, Expense, InventoryItem, StockMovement, CashFlow,
        AccountType, TransactionType, ExpenseCategory, IncomeCategory,
        PaymentStatus, InvoiceType, VATRate, AdditionalTaxType, WithholdingRate
    )
    print("✅ Accounting models imported successfully")
except ImportError as e:
    print(f"❌ Failed to import accounting models: {e}")
    raise e  # Don't continue if accounting models can't be imported

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
    GUARANTEED = "guaranteed"
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

class ContractedRateType(str, Enum):
    CORP_STD = "corp_std"  # Standard Corporate
    CORP_PREF = "corp_pref"  # Preferred Corporate
    GOV = "gov"  # Government Rate
    TA = "ta"  # Travel Agent Rate
    CREW = "crew"  # Airline Crew Rate
    MICE = "mice"  # Event/Conference Rate
    LTS = "lts"  # Long Stay/Project Rate
    TOU = "tou"  # Tour Operator/Series Group Rate

class RateType(str, Enum):
    BAR = "bar"  # Best Available Rate / Rack Rate
    CORPORATE = "corporate"
    GOVERNMENT = "government"
    WHOLESALE = "wholesale"
    PACKAGE = "package"
    PROMOTIONAL = "promotional"
    NON_REFUNDABLE = "non_refundable"
    LONG_STAY = "long_stay"
    DAY_USE = "day_use"

class MarketSegment(str, Enum):
    CORPORATE = "corporate"
    LEISURE = "leisure"
    GROUP = "group"
    MICE = "mice"
    GOVERNMENT = "government"
    CREW = "crew"
    WHOLESALE = "wholesale"
    LONG_STAY = "long_stay"
    COMPLIMENTARY = "complimentary"
    OTHER = "other"

class CancellationPolicyType(str, Enum):
    SAME_DAY = "same_day"  # Free cancellation until 18:00
    H24 = "h24"  # 24 hours before check-in
    H48 = "h48"  # 48 hours before check-in
    H72 = "h72"  # 72 hours before check-in
    D7 = "d7"  # 7 days before check-in
    D14 = "d14"  # 14 days before check-in
    NON_REFUNDABLE = "non_refundable"
    FLEXIBLE = "flexible"
    SPECIAL_EVENT = "special_event"

class CompanyStatus(str, Enum):
    ACTIVE = "active"
    PENDING = "pending"  # Quick-created from booking form
    INACTIVE = "inactive"

class FolioType(str, Enum):
    GUEST = "guest"
    COMPANY = "company"
    AGENCY = "agency"

class FolioStatus(str, Enum):
    OPEN = "open"
    CLOSED = "closed"
    TRANSFERRED = "transferred"
    VOIDED = "voided"

class ChargeCategory(str, Enum):
    ROOM = "room"
    FOOD = "food"
    BEVERAGE = "beverage"
    MINIBAR = "minibar"
    SPA = "spa"
    LAUNDRY = "laundry"
    PHONE = "phone"
    INTERNET = "internet"
    PARKING = "parking"
    CITY_TAX = "city_tax"
    SERVICE_CHARGE = "service_charge"
    OTHER = "other"

class FolioOperationType(str, Enum):
    TRANSFER = "transfer"
    SPLIT = "split"
    MERGE = "merge"
    VOID = "void"
    REFUND = "refund"

class PaymentType(str, Enum):
    PREPAYMENT = "prepayment"
    DEPOSIT = "deposit"
    INTERIM = "interim"
    FINAL = "final"
    REFUND = "refund"

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

# Company Models
class CompanyCreate(BaseModel):
    name: str
    corporate_code: Optional[str] = None
    tax_number: Optional[str] = None
    billing_address: Optional[str] = None
    contact_person: Optional[str] = None
    contact_email: Optional[EmailStr] = None
    contact_phone: Optional[str] = None
    contracted_rate: Optional[ContractedRateType] = None
    default_rate_type: Optional[RateType] = None
    default_market_segment: Optional[MarketSegment] = None
    default_cancellation_policy: Optional[CancellationPolicyType] = None
    payment_terms: Optional[str] = None
    status: CompanyStatus = CompanyStatus.PENDING

class Company(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    name: str
    corporate_code: Optional[str] = None
    tax_number: Optional[str] = None
    billing_address: Optional[str] = None
    contact_person: Optional[str] = None
    contact_email: Optional[EmailStr] = None
    contact_phone: Optional[str] = None
    contracted_rate: Optional[ContractedRateType] = None
    default_rate_type: Optional[RateType] = None
    default_market_segment: Optional[MarketSegment] = None
    default_cancellation_policy: Optional[CancellationPolicyType] = None
    payment_terms: Optional[str] = None
    status: CompanyStatus = CompanyStatus.ACTIVE
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

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
    adults: int = 1
    children: int = 0
    children_ages: List[int] = []
    guests_count: int  # Total: adults + children
    total_amount: float
    base_rate: Optional[float] = None  # For override tracking
    channel: ChannelType = ChannelType.DIRECT
    special_requests: Optional[str] = None
    rate_plan: Optional[str] = None
    # New fields for corporate/contracted bookings
    company_id: Optional[str] = None
    contracted_rate: Optional[ContractedRateType] = None
    rate_type: Optional[RateType] = None
    market_segment: Optional[MarketSegment] = None
    cancellation_policy: Optional[CancellationPolicyType] = None
    billing_address: Optional[str] = None
    billing_tax_number: Optional[str] = None
    billing_contact_person: Optional[str] = None
    # Override tracking
    override_reason: Optional[str] = None

class Booking(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    guest_id: str
    room_id: str
    check_in: datetime
    check_out: datetime
    adults: int = 1
    children: int = 0
    children_ages: List[int] = []
    guests_count: int
    total_amount: float
    base_rate: Optional[float] = None
    paid_amount: float = 0.0
    status: BookingStatus = BookingStatus.PENDING
    channel: ChannelType = ChannelType.DIRECT
    rate_plan: Optional[str] = "Standard"
    special_requests: Optional[str] = None
    # Corporate/contracted booking fields
    company_id: Optional[str] = None
    contracted_rate: Optional[ContractedRateType] = None
    rate_type: Optional[RateType] = None
    market_segment: Optional[MarketSegment] = None
    cancellation_policy: Optional[CancellationPolicyType] = None
    billing_address: Optional[str] = None
    billing_tax_number: Optional[str] = None
    billing_contact_person: Optional[str] = None
    # System fields
    qr_code: Optional[str] = None
    qr_code_data: Optional[str] = None
    checked_in_at: Optional[datetime] = None
    checked_out_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# Folio & Payment Models
class FolioCreate(BaseModel):
    booking_id: str
    folio_type: FolioType
    guest_id: Optional[str] = None
    company_id: Optional[str] = None
    notes: Optional[str] = None

class Folio(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    booking_id: str
    folio_number: str  # e.g., "F-2024-0001"
    folio_type: FolioType
    status: FolioStatus = FolioStatus.OPEN
    guest_id: Optional[str] = None
    company_id: Optional[str] = None
    balance: float = 0.0  # Total charges - Total payments
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    closed_at: Optional[datetime] = None

class ChargeCreate(BaseModel):
    charge_category: ChargeCategory
    description: str
    amount: float
    quantity: float = 1.0
    auto_calculate_tax: bool = False

class FolioCharge(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    folio_id: str
    booking_id: str
    charge_category: ChargeCategory
    description: str
    unit_price: float
    quantity: float = 1.0
    amount: float  # unit_price * quantity
    tax_amount: float = 0.0
    total: float  # amount + tax_amount
    date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    posted_by: Optional[str] = None
    voided: bool = False
    void_reason: Optional[str] = None
    voided_by: Optional[str] = None
    voided_at: Optional[datetime] = None

class PaymentCreate(BaseModel):
    amount: float
    method: PaymentMethod
    payment_type: PaymentType
    reference: Optional[str] = None
    notes: Optional[str] = None

class Payment(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    folio_id: str
    booking_id: str
    amount: float
    method: PaymentMethod
    payment_type: PaymentType
    status: PaymentStatus = PaymentStatus.PAID
    reference: Optional[str] = None
    notes: Optional[str] = None
    processed_by: Optional[str] = None
    processed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class FolioOperationCreate(BaseModel):
    operation_type: FolioOperationType
    from_folio_id: str
    to_folio_id: Optional[str] = None
    charge_ids: List[str] = []  # For transfer operations
    amount: Optional[float] = None
    reason: str

class FolioOperation(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    operation_type: FolioOperationType
    from_folio_id: str
    to_folio_id: Optional[str] = None
    charge_ids: List[str] = []
    amount: Optional[float] = None
    reason: str
    performed_by: str
    performed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class CityTaxRule(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    name: str
    tax_percentage: float
    flat_amount: Optional[float] = None  # If not percentage-based
    per_night: bool = True
    exempt_market_segments: List[MarketSegment] = []
    min_nights: Optional[int] = None
    max_nights: Optional[int] = None
    active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# Rate Override Log Model
class RateOverrideLog(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    booking_id: str
    user_id: str
    user_name: Optional[str] = None
    base_rate: float
    new_rate: float
    override_reason: str
    ip_address: Optional[str] = None
    terminal: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

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
    except Exception:
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
    if not user_doc or not verify_password(data.password, user_doc.get('password', '')):
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

# ============= COMPANY MANAGEMENT =============

@api_router.post("/companies", response_model=Company)
async def create_company(company_data: CompanyCreate, current_user: User = Depends(get_current_user)):
    """Create a new company. Status is 'pending' by default for quick-created companies from booking form."""
    company = Company(
        tenant_id=current_user.tenant_id,
        **company_data.model_dump()
    )
    company_dict = company.model_dump()
    company_dict['created_at'] = company_dict['created_at'].isoformat()
    company_dict['updated_at'] = company_dict['updated_at'].isoformat()
    await db.companies.insert_one(company_dict)
    return company

@api_router.get("/companies", response_model=List[Company])
async def get_companies(
    search: Optional[str] = None,
    status: Optional[CompanyStatus] = None,
    current_user: User = Depends(get_current_user)
):
    """Get all companies with optional search and status filter."""
    query = {'tenant_id': current_user.tenant_id}
    
    if status:
        query['status'] = status
    
    if search:
        query['$or'] = [
            {'name': {'$regex': search, '$options': 'i'}},
            {'corporate_code': {'$regex': search, '$options': 'i'}}
        ]
    
    companies = await db.companies.find(query, {'_id': 0}).to_list(1000)
    return companies

@api_router.get("/companies/{company_id}", response_model=Company)
async def get_company(company_id: str, current_user: User = Depends(get_current_user)):
    """Get a specific company by ID."""
    company = await db.companies.find_one({
        'id': company_id,
        'tenant_id': current_user.tenant_id
    }, {'_id': 0})
    
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    return company

@api_router.put("/companies/{company_id}", response_model=Company)
async def update_company(
    company_id: str,
    company_data: CompanyCreate,
    current_user: User = Depends(get_current_user)
):
    """Update company information. Used by sales team to complete pending company profiles."""
    company = await db.companies.find_one({
        'id': company_id,
        'tenant_id': current_user.tenant_id
    })
    
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    update_data = company_data.model_dump()
    update_data['updated_at'] = datetime.now(timezone.utc).isoformat()
    
    await db.companies.update_one(
        {'id': company_id, 'tenant_id': current_user.tenant_id},
        {'$set': update_data}
    )
    
    updated_company = await db.companies.find_one({
        'id': company_id,
        'tenant_id': current_user.tenant_id
    }, {'_id': 0})
    
    return updated_company

# ============= FOLIO & BILLING ENGINE =============

async def generate_folio_number(tenant_id: str) -> str:
    """Generate unique folio number"""
    year = datetime.now(timezone.utc).year
    count = await db.folios.count_documents({'tenant_id': tenant_id}) + 1
    return f"F-{year}-{count:05d}"

async def calculate_folio_balance(folio_id: str, tenant_id: str) -> float:
    """Calculate folio balance (charges - payments)"""
    charges = await db.folio_charges.find({
        'folio_id': folio_id,
        'tenant_id': tenant_id,
        'voided': False
    }).to_list(1000)
    
    payments = await db.payments.find({
        'folio_id': folio_id,
        'tenant_id': tenant_id,
        'status': 'paid'
    }).to_list(1000)
    
    total_charges = sum(c['total'] for c in charges)
    total_payments = sum(p['amount'] for p in payments)
    
    return total_charges - total_payments

@api_router.post("/folio/create", response_model=Folio)
async def create_folio(folio_data: FolioCreate, current_user: User = Depends(get_current_user)):
    """Create a new folio for a booking"""
    # Verify booking exists
    booking = await db.bookings.find_one({
        'id': folio_data.booking_id,
        'tenant_id': current_user.tenant_id
    })
    
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    folio_number = await generate_folio_number(current_user.tenant_id)
    
    folio = Folio(
        tenant_id=current_user.tenant_id,
        folio_number=folio_number,
        **folio_data.model_dump()
    )
    
    folio_dict = folio.model_dump()
    folio_dict['created_at'] = folio_dict['created_at'].isoformat()
    await db.folios.insert_one(folio_dict)
    
    return folio

@api_router.get("/folio/booking/{booking_id}", response_model=List[Folio])
async def get_booking_folios(booking_id: str, current_user: User = Depends(get_current_user)):
    """Get all folios for a booking"""
    folios = await db.folios.find({
        'booking_id': booking_id,
        'tenant_id': current_user.tenant_id
    }, {'_id': 0}).to_list(1000)
    
    # Calculate current balance for each folio
    for folio in folios:
        folio['balance'] = await calculate_folio_balance(folio['id'], current_user.tenant_id)
    
    return folios

@api_router.get("/folio/{folio_id}", response_model=Dict[str, Any])
async def get_folio_details(folio_id: str, current_user: User = Depends(get_current_user)):
    """Get folio with charges and payments"""
    folio = await db.folios.find_one({
        'id': folio_id,
        'tenant_id': current_user.tenant_id
    }, {'_id': 0})
    
    if not folio:
        raise HTTPException(status_code=404, detail="Folio not found")
    
    charges = await db.folio_charges.find({
        'folio_id': folio_id,
        'tenant_id': current_user.tenant_id
    }, {'_id': 0}).to_list(1000)
    
    payments = await db.payments.find({
        'folio_id': folio_id,
        'tenant_id': current_user.tenant_id
    }, {'_id': 0}).to_list(1000)
    
    balance = await calculate_folio_balance(folio_id, current_user.tenant_id)
    folio['balance'] = balance
    
    return {
        'folio': folio,
        'charges': charges,
        'payments': payments,
        'balance': balance
    }

@api_router.post("/folio/{folio_id}/charge", response_model=FolioCharge)
async def post_charge_to_folio(
    folio_id: str,
    charge_data: ChargeCreate,
    current_user: User = Depends(get_current_user)
):
    """Post a charge to folio"""
    folio = await db.folios.find_one({
        'id': folio_id,
        'tenant_id': current_user.tenant_id,
        'status': 'open'
    })
    
    if not folio:
        raise HTTPException(status_code=404, detail="Folio not found or closed")
    
    # Calculate amounts
    amount = charge_data.amount * charge_data.quantity
    tax_amount = 0.0
    
    # Auto-calculate city tax if requested
    if charge_data.auto_calculate_tax and charge_data.charge_category == ChargeCategory.ROOM:
        # Get city tax rule
        tax_rule = await db.city_tax_rules.find_one({
            'tenant_id': current_user.tenant_id,
            'active': True
        })
        if tax_rule:
            if tax_rule.get('flat_amount'):
                tax_amount = tax_rule['flat_amount']
            else:
                tax_amount = amount * (tax_rule['tax_percentage'] / 100)
    
    total = amount + tax_amount
    
    charge = FolioCharge(
        tenant_id=current_user.tenant_id,
        folio_id=folio_id,
        booking_id=folio['booking_id'],
        charge_category=charge_data.charge_category,
        description=charge_data.description,
        unit_price=charge_data.amount,
        quantity=charge_data.quantity,
        amount=amount,
        tax_amount=tax_amount,
        total=total,
        posted_by=current_user.id
    )
    
    charge_dict = charge.model_dump()
    charge_dict['date'] = charge_dict['date'].isoformat()
    await db.folio_charges.insert_one(charge_dict)
    
    # Update folio balance
    balance = await calculate_folio_balance(folio_id, current_user.tenant_id)
    await db.folios.update_one(
        {'id': folio_id},
        {'$set': {'balance': balance}}
    )
    
    return charge

@api_router.post("/folio/{folio_id}/payment", response_model=Payment)
async def post_payment_to_folio(
    folio_id: str,
    payment_data: PaymentCreate,
    current_user: User = Depends(get_current_user)
):
    """Post a payment to folio"""
    folio = await db.folios.find_one({
        'id': folio_id,
        'tenant_id': current_user.tenant_id
    })
    
    if not folio:
        raise HTTPException(status_code=404, detail="Folio not found")
    
    payment = Payment(
        tenant_id=current_user.tenant_id,
        folio_id=folio_id,
        booking_id=folio['booking_id'],
        processed_by=current_user.id,
        **payment_data.model_dump()
    )
    
    payment_dict = payment.model_dump()
    payment_dict['processed_at'] = payment_dict['processed_at'].isoformat()
    await db.payments.insert_one(payment_dict)
    
    # Update folio balance
    balance = await calculate_folio_balance(folio_id, current_user.tenant_id)
    await db.folios.update_one(
        {'id': folio_id},
        {'$set': {'balance': balance}}
    )
    
    return payment

@api_router.post("/folio/transfer", response_model=FolioOperation)
async def transfer_charges(
    operation_data: FolioOperationCreate,
    current_user: User = Depends(get_current_user)
):
    """Transfer charges from one folio to another"""
    if operation_data.operation_type != FolioOperationType.TRANSFER:
        raise HTTPException(status_code=400, detail="Invalid operation type")
    
    if not operation_data.to_folio_id:
        raise HTTPException(status_code=400, detail="Destination folio required for transfer")
    
    # Verify both folios exist
    from_folio = await db.folios.find_one({
        'id': operation_data.from_folio_id,
        'tenant_id': current_user.tenant_id
    })
    
    to_folio = await db.folios.find_one({
        'id': operation_data.to_folio_id,
        'tenant_id': current_user.tenant_id,
        'status': 'open'
    })
    
    if not from_folio or not to_folio:
        raise HTTPException(status_code=404, detail="Folio not found")
    
    # Transfer specified charges
    for charge_id in operation_data.charge_ids:
        await db.folio_charges.update_one(
            {'id': charge_id, 'folio_id': operation_data.from_folio_id},
            {'$set': {'folio_id': operation_data.to_folio_id}}
        )
    
    # Create operation record
    operation = FolioOperation(
        tenant_id=current_user.tenant_id,
        performed_by=current_user.id,
        **operation_data.model_dump()
    )
    
    operation_dict = operation.model_dump()
    operation_dict['performed_at'] = operation_dict['performed_at'].isoformat()
    await db.folio_operations.insert_one(operation_dict)
    
    # Update balances
    from_balance = await calculate_folio_balance(operation_data.from_folio_id, current_user.tenant_id)
    to_balance = await calculate_folio_balance(operation_data.to_folio_id, current_user.tenant_id)
    
    await db.folios.update_one(
        {'id': operation_data.from_folio_id},
        {'$set': {'balance': from_balance}}
    )
    await db.folios.update_one(
        {'id': operation_data.to_folio_id},
        {'$set': {'balance': to_balance}}
    )
    
    return operation

@api_router.post("/folio/{folio_id}/void-charge/{charge_id}")
async def void_charge(
    folio_id: str,
    charge_id: str,
    void_reason: str,
    current_user: User = Depends(get_current_user)
):
    """Void a charge"""
    charge = await db.folio_charges.find_one({
        'id': charge_id,
        'folio_id': folio_id,
        'tenant_id': current_user.tenant_id,
        'voided': False
    })
    
    if not charge:
        raise HTTPException(status_code=404, detail="Charge not found or already voided")
    
    await db.folio_charges.update_one(
        {'id': charge_id},
        {'$set': {
            'voided': True,
            'void_reason': void_reason,
            'voided_by': current_user.id,
            'voided_at': datetime.now(timezone.utc).isoformat()
        }}
    )
    
    # Update folio balance
    balance = await calculate_folio_balance(folio_id, current_user.tenant_id)
    await db.folios.update_one(
        {'id': folio_id},
        {'$set': {'balance': balance}}
    )
    
    # Create operation record
    operation = FolioOperation(
        tenant_id=current_user.tenant_id,
        operation_type=FolioOperationType.VOID,
        from_folio_id=folio_id,
        charge_ids=[charge_id],
        amount=charge['total'],
        reason=void_reason,
        performed_by=current_user.id
    )
    
    operation_dict = operation.model_dump()
    operation_dict['performed_at'] = operation_dict['performed_at'].isoformat()
    await db.folio_operations.insert_one(operation_dict)
    
    return {"message": "Charge voided successfully"}

@api_router.post("/folio/{folio_id}/close")
async def close_folio(
    folio_id: str,
    current_user: User = Depends(get_current_user)
):
    """Close a folio"""
    folio = await db.folios.find_one({
        'id': folio_id,
        'tenant_id': current_user.tenant_id,
        'status': 'open'
    })
    
    if not folio:
        raise HTTPException(status_code=404, detail="Folio not found or already closed")
    
    # Check balance
    balance = await calculate_folio_balance(folio_id, current_user.tenant_id)
    
    if balance > 0.01:  # Allow small rounding differences
        raise HTTPException(
            status_code=400,
            detail=f"Cannot close folio with outstanding balance: {balance}"
        )
    
    await db.folios.update_one(
        {'id': folio_id},
        {'$set': {
            'status': 'closed',
            'balance': 0.0,
            'closed_at': datetime.now(timezone.utc).isoformat()
        }}
    )
    
    return {"message": "Folio closed successfully"}

@api_router.post("/night-audit/post-room-charges")
async def post_room_charges(current_user: User = Depends(get_current_user)):
    """Night audit: Post room charges to all active bookings"""
    # Get all checked-in bookings
    bookings = await db.bookings.find({
        'tenant_id': current_user.tenant_id,
        'status': 'checked_in'
    }).to_list(1000)
    
    charges_posted = 0
    
    for booking in bookings:
        # Get guest folio for this booking
        folio = await db.folios.find_one({
            'booking_id': booking['id'],
            'folio_type': 'guest',
            'status': 'open'
        })
        
        if folio:
            # Post room charge
            charge = FolioCharge(
                tenant_id=current_user.tenant_id,
                folio_id=folio['id'],
                booking_id=booking['id'],
                charge_category=ChargeCategory.ROOM,
                description=f"Room {booking.get('room_id', 'N/A')} - Night Charge",
                unit_price=booking.get('base_rate', booking.get('total_amount', 0)),
                quantity=1.0,
                amount=booking.get('base_rate', booking.get('total_amount', 0)),
                tax_amount=0.0,
                total=booking.get('base_rate', booking.get('total_amount', 0)),
                posted_by="SYSTEM"
            )
            
            charge_dict = charge.model_dump()
            charge_dict['date'] = charge_dict['date'].isoformat()
            await db.folio_charges.insert_one(charge_dict)
            
            # Update folio balance
            balance = await calculate_folio_balance(folio['id'], current_user.tenant_id)
            await db.folios.update_one(
                {'id': folio['id']},
                {'$set': {'balance': balance}}
            )
            
            charges_posted += 1
    
    return {
        "message": "Night audit completed",
        "charges_posted": charges_posted,
        "bookings_processed": len(bookings)
    }

# ============= GUEST MANAGEMENT =============

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
        adults=booking_data.adults,
        children=booking_data.children,
        children_ages=booking_data.children_ages,
        guests_count=booking_data.guests_count,
        total_amount=booking_data.total_amount,
        base_rate=booking_data.base_rate,
        channel=booking_data.channel,
        rate_plan=booking_data.rate_plan,
        special_requests=booking_data.special_requests,
        company_id=booking_data.company_id,
        contracted_rate=booking_data.contracted_rate,
        rate_type=booking_data.rate_type,
        market_segment=booking_data.market_segment,
        cancellation_policy=booking_data.cancellation_policy,
        billing_address=booking_data.billing_address,
        billing_tax_number=booking_data.billing_tax_number,
        billing_contact_person=booking_data.billing_contact_person
    )
    
    # Check for rate override and log it
    if booking_data.base_rate and booking_data.base_rate != booking_data.total_amount:
        if booking_data.override_reason:
            override_log = RateOverrideLog(
                tenant_id=current_user.tenant_id,
                booking_id=booking.id,
                user_id=current_user.id,
                user_name=current_user.name,
                base_rate=booking_data.base_rate,
                new_rate=booking_data.total_amount,
                override_reason=booking_data.override_reason
            )
            override_dict = override_log.model_dump()
            override_dict['timestamp'] = override_dict['timestamp'].isoformat()
            await db.rate_override_logs.insert_one(override_dict)
    
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

@api_router.get("/bookings/{booking_id}/override-logs", response_model=List[RateOverrideLog])
async def get_booking_override_logs(booking_id: str, current_user: User = Depends(get_current_user)):
    """Get all rate override logs for a specific booking."""
    logs = await db.rate_override_logs.find({
        'booking_id': booking_id,
        'tenant_id': current_user.tenant_id
    }, {'_id': 0}).sort('timestamp', -1).to_list(100)
    return logs

@api_router.post("/bookings/{booking_id}/override")
async def create_rate_override(
    booking_id: str,
    new_rate: float,
    override_reason: str,
    current_user: User = Depends(get_current_user)
):
    """Create a rate override log for an existing booking."""
    booking = await db.bookings.find_one({
        'id': booking_id,
        'tenant_id': current_user.tenant_id
    })
    
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    base_rate = booking.get('base_rate') or booking.get('total_amount')
    
    override_log = RateOverrideLog(
        tenant_id=current_user.tenant_id,
        booking_id=booking_id,
        user_id=current_user.id,
        user_name=current_user.name,
        base_rate=base_rate,
        new_rate=new_rate,
        override_reason=override_reason
    )
    
    override_dict = override_log.model_dump()
    override_dict['timestamp'] = override_dict['timestamp'].isoformat()
    await db.rate_override_logs.insert_one(override_dict)
    
    # Update booking with new rate
    await db.bookings.update_one(
        {'id': booking_id, 'tenant_id': current_user.tenant_id},
        {'$set': {'total_amount': new_rate}}
    )
    
    return {"message": "Rate override logged successfully", "log": override_log}

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

@api_router.get("/loyalty/guest/{guest_id}")
async def get_guest_loyalty_by_id(guest_id: str, current_user: User = Depends(get_current_user)):
    program = await db.loyalty_programs.find_one({'guest_id': guest_id, 'tenant_id': current_user.tenant_id}, {'_id': 0})
    transactions = await db.loyalty_transactions.find({'guest_id': guest_id, 'tenant_id': current_user.tenant_id}, {'_id': 0}).to_list(1000)
    return {'program': program, 'transactions': transactions}

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

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# ============= FRONT DESK OPERATIONS =============

@api_router.post("/frontdesk/checkin/{booking_id}")
async def check_in_guest(booking_id: str, create_folio: bool = True, current_user: User = Depends(get_current_user)):
    """Check-in guest with validations and auto-folio creation"""
    booking = await db.bookings.find_one({'id': booking_id, 'tenant_id': current_user.tenant_id}, {'_id': 0})
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    if booking['status'] == 'checked_in':
        raise HTTPException(status_code=400, detail="Guest already checked in")
    
    # Validate room is available/clean
    room = await db.rooms.find_one({'id': booking['room_id']}, {'_id': 0})
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    if room['status'] not in ['available', 'inspected']:
        raise HTTPException(
            status_code=400,
            detail=f"Room not ready for check-in. Current status: {room['status']}"
        )
    
    # Create guest folio if requested and doesn't exist
    if create_folio:
        existing_folio = await db.folios.find_one({
            'booking_id': booking_id,
            'folio_type': 'guest'
        })
        
        if not existing_folio:
            folio_number = await generate_folio_number(current_user.tenant_id)
            folio = Folio(
                tenant_id=current_user.tenant_id,
                booking_id=booking_id,
                folio_number=folio_number,
                folio_type=FolioType.GUEST,
                guest_id=booking['guest_id']
            )
            folio_dict = folio.model_dump()
            folio_dict['created_at'] = folio_dict['created_at'].isoformat()
            await db.folios.insert_one(folio_dict)
    
    # Update booking and room status
    checked_in_time = datetime.now(timezone.utc)
    await db.bookings.update_one(
        {'id': booking_id},
        {'$set': {
            'status': 'checked_in',
            'checked_in_at': checked_in_time.isoformat()
        }}
    )
    await db.rooms.update_one(
        {'id': booking['room_id']},
        {'$set': {
            'status': 'occupied',
            'current_booking_id': booking_id
        }}
    )
    
    # Update guest total stays
    await db.guests.update_one({'id': booking['guest_id']}, {'$inc': {'total_stays': 1}})
    
    return {
        'message': 'Check-in completed successfully',
        'checked_in_at': checked_in_time.isoformat(),
        'room_number': room['room_number']
    }

@api_router.post("/frontdesk/checkout/{booking_id}")
async def check_out_guest(
    booking_id: str,
    force: bool = False,
    auto_close_folios: bool = True,
    current_user: User = Depends(get_current_user)
):
    """Check-out guest with balance validation and folio closure"""
    booking = await db.bookings.find_one({'id': booking_id, 'tenant_id': current_user.tenant_id}, {'_id': 0})
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    if booking['status'] == 'checked_out':
        raise HTTPException(status_code=400, detail="Guest already checked out")
    
    # Get all folios for this booking
    folios = await db.folios.find({
        'booking_id': booking_id,
        'tenant_id': current_user.tenant_id,
        'status': 'open'
    }).to_list(100)
    
    # Calculate total balance across all folios
    total_balance = 0.0
    folio_details = []
    
    for folio in folios:
        balance = await calculate_folio_balance(folio['id'], current_user.tenant_id)
        total_balance += balance
        folio_details.append({
            'folio_number': folio['folio_number'],
            'folio_type': folio['folio_type'],
            'balance': balance
        })
    
    # Check for outstanding balance
    if total_balance > 0.01 and not force:
        raise HTTPException(
            status_code=400,
            detail=f"Outstanding balance: ${total_balance:.2f}. Folios: {folio_details}"
        )
    
    # Close all open folios if requested
    if auto_close_folios and total_balance <= 0.01:
        for folio in folios:
            await db.folios.update_one(
                {'id': folio['id']},
                {'$set': {
                    'status': 'closed',
                    'balance': 0.0,
                    'closed_at': datetime.now(timezone.utc).isoformat()
                }}
            )
    
    # Update booking and room status
    checked_out_time = datetime.now(timezone.utc)
    await db.bookings.update_one(
        {'id': booking_id},
        {'$set': {
            'status': 'checked_out',
            'checked_out_at': checked_out_time.isoformat()
        }}
    )
    
    # Update room to dirty and create housekeeping task
    await db.rooms.update_one(
        {'id': booking['room_id']},
        {'$set': {
            'status': 'dirty',
            'current_booking_id': None
        }}
    )
    
    task = HousekeepingTask(
        tenant_id=current_user.tenant_id,
        room_id=booking['room_id'],
        task_type='cleaning',
        priority='high',
        notes='Guest checked out - departure clean required'
    )
    task_dict = task.model_dump()
    task_dict['created_at'] = task_dict['created_at'].isoformat()
    await db.housekeeping_tasks.insert_one(task_dict)
    
    return {
        'message': 'Check-out completed successfully',
        'checked_out_at': checked_out_time.isoformat(),
        'total_balance': total_balance,
        'folios_closed': len(folios) if auto_close_folios else 0,
        'folio_details': folio_details
    }

@api_router.post("/frontdesk/folio/{booking_id}/charge")
async def add_folio_charge(booking_id: str, charge_type: str, description: str, amount: float, quantity: float = 1.0, current_user: User = Depends(get_current_user)):
    folio_charge = FolioCharge(tenant_id=current_user.tenant_id, booking_id=booking_id, charge_type=charge_type, description=description,
                               amount=amount, quantity=quantity, total=amount * quantity, posted_by=current_user.name)
    charge_dict = folio_charge.model_dump()
    charge_dict['date'] = charge_dict['date'].isoformat()
    await db.folio_charges.insert_one(charge_dict)
    return folio_charge

@api_router.get("/frontdesk/folio/{booking_id}")
async def get_folio(booking_id: str, current_user: User = Depends(get_current_user)):
    charges = await db.folio_charges.find({'booking_id': booking_id, 'tenant_id': current_user.tenant_id}, {'_id': 0}).to_list(1000)
    payments = await db.payments.find({'booking_id': booking_id, 'tenant_id': current_user.tenant_id}, {'_id': 0}).to_list(1000)
    total_charges = sum(c['total'] for c in charges)
    total_paid = sum(p['amount'] for p in payments if p['status'] == 'paid')
    return {'charges': charges, 'payments': payments, 'total_charges': total_charges, 'total_paid': total_paid, 'balance': total_charges - total_paid}

@api_router.post("/frontdesk/payment/{booking_id}")
async def process_payment(booking_id: str, amount: float, method: str, reference: Optional[str] = None, notes: Optional[str] = None, current_user: User = Depends(get_current_user)):
    payment = Payment(tenant_id=current_user.tenant_id, booking_id=booking_id, amount=amount, method=method, status='paid',
                     reference=reference, notes=notes, processed_by=current_user.name)
    payment_dict = payment.model_dump()
    payment_dict['processed_at'] = payment_dict['processed_at'].isoformat()
    await db.payments.insert_one(payment_dict)
    await db.bookings.update_one({'id': booking_id}, {'$inc': {'paid_amount': amount}})
    return payment

@api_router.get("/frontdesk/arrivals")
async def get_arrivals(date: Optional[str] = None, current_user: User = Depends(get_current_user)):
    target_date = datetime.fromisoformat(date).date() if date else datetime.now(timezone.utc).date()
    start_of_day = datetime.combine(target_date, datetime.min.time())
    end_of_day = datetime.combine(target_date, datetime.max.time())
    bookings = await db.bookings.find({'tenant_id': current_user.tenant_id, 'status': {'$in': ['confirmed', 'checked_in']},
                                       'check_in': {'$gte': start_of_day.isoformat(), '$lte': end_of_day.isoformat()}}, {'_id': 0}).to_list(1000)
    enriched = []
    for booking in bookings:
        guest = await db.guests.find_one({'id': booking['guest_id']}, {'_id': 0})
        room = await db.rooms.find_one({'id': booking['room_id']}, {'_id': 0})
        enriched.append({**booking, 'guest': guest, 'room': room})
    return enriched

@api_router.get("/frontdesk/departures")
async def get_departures(date: Optional[str] = None, current_user: User = Depends(get_current_user)):
    target_date = datetime.fromisoformat(date).date() if date else datetime.now(timezone.utc).date()
    start_of_day = datetime.combine(target_date, datetime.min.time())
    end_of_day = datetime.combine(target_date, datetime.max.time())
    bookings = await db.bookings.find({'tenant_id': current_user.tenant_id, 'status': 'checked_in',
                                       'check_out': {'$gte': start_of_day.isoformat(), '$lte': end_of_day.isoformat()}}, {'_id': 0}).to_list(1000)
    enriched = []
    for booking in bookings:
        guest = await db.guests.find_one({'id': booking['guest_id']}, {'_id': 0})
        room = await db.rooms.find_one({'id': booking['room_id']}, {'_id': 0})
        charges = await db.folio_charges.find({'booking_id': booking['id']}, {'_id': 0}).to_list(1000)
        payments = await db.payments.find({'booking_id': booking['id']}, {'_id': 0}).to_list(1000)
        balance = sum(c['total'] for c in charges) - sum(p['amount'] for p in payments if p['status'] == 'paid')
        enriched.append({**booking, 'guest': guest, 'room': room, 'balance': balance})
    return enriched

@api_router.get("/frontdesk/inhouse")
async def get_inhouse_guests(current_user: User = Depends(get_current_user)):
    bookings = await db.bookings.find({'tenant_id': current_user.tenant_id, 'status': 'checked_in'}, {'_id': 0}).to_list(1000)
    enriched = []
    for booking in bookings:
        guest = await db.guests.find_one({'id': booking['guest_id']}, {'_id': 0})
        room = await db.rooms.find_one({'id': booking['room_id']}, {'_id': 0})
        enriched.append({**booking, 'guest': guest, 'room': room})
    return enriched

# ============= HOUSEKEEPING =============

@api_router.get("/housekeeping/tasks")
async def get_housekeeping_tasks(status: Optional[str] = None, current_user: User = Depends(get_current_user)):
    query = {'tenant_id': current_user.tenant_id}
    if status:
        query['status'] = status
    tasks = await db.housekeeping_tasks.find(query, {'_id': 0}).to_list(1000)
    enriched = []
    for task in tasks:
        room = await db.rooms.find_one({'id': task['room_id']}, {'_id': 0})
        enriched.append({**task, 'room': room})
    return enriched

@api_router.post("/housekeeping/tasks")
async def create_housekeeping_task(room_id: str, task_type: str, priority: str = "normal", notes: Optional[str] = None, current_user: User = Depends(get_current_user)):
    task = HousekeepingTask(tenant_id=current_user.tenant_id, room_id=room_id, task_type=task_type, priority=priority, notes=notes)
    task_dict = task.model_dump()
    task_dict['created_at'] = task_dict['created_at'].isoformat()
    await db.housekeeping_tasks.insert_one(task_dict)
    return task

@api_router.put("/housekeeping/tasks/{task_id}")
async def update_housekeeping_task(task_id: str, status: Optional[str] = None, assigned_to: Optional[str] = None, current_user: User = Depends(get_current_user)):
    updates = {}
    if status:
        updates['status'] = status
        if status == 'in_progress':
            updates['started_at'] = datetime.now(timezone.utc).isoformat()
        elif status == 'completed':
            updates['completed_at'] = datetime.now(timezone.utc).isoformat()
            task = await db.housekeeping_tasks.find_one({'id': task_id}, {'_id': 0})
            if task and task['task_type'] == 'cleaning':
                await db.rooms.update_one({'id': task['room_id']}, {'$set': {'status': 'inspected', 'last_cleaned': datetime.now(timezone.utc).isoformat()}})
    if assigned_to:
        updates['assigned_to'] = assigned_to
    await db.housekeeping_tasks.update_one({'id': task_id, 'tenant_id': current_user.tenant_id}, {'$set': updates})
    task = await db.housekeeping_tasks.find_one({'id': task_id}, {'_id': 0})
    return task

@api_router.get("/housekeeping/room-status")
async def get_room_status_board(current_user: User = Depends(get_current_user)):
    """Get comprehensive room status board"""
    rooms = await db.rooms.find({'tenant_id': current_user.tenant_id}, {'_id': 0}).to_list(1000)
    status_counts = {s: 0 for s in ['available', 'occupied', 'dirty', 'cleaning', 'inspected', 'maintenance', 'out_of_order']}
    for room in rooms:
        status_counts[room['status']] += 1
    return {'rooms': rooms, 'status_counts': status_counts, 'total_rooms': len(rooms)}

@api_router.get("/housekeeping/due-out")
async def get_due_out_rooms(current_user: User = Depends(get_current_user)):
    """Get rooms with guests checking out today"""
    today = datetime.now(timezone.utc).date()
    tomorrow = today + timedelta(days=1)
    
    # Find bookings checking out today
    bookings = await db.bookings.find({
        'tenant_id': current_user.tenant_id,
        'status': 'checked_in'
    }).to_list(1000)
    
    due_out_rooms = []
    for booking in bookings:
        checkout_date = datetime.fromisoformat(booking['check_out']).date()
        if checkout_date == today or checkout_date == tomorrow:
            room = await db.rooms.find_one({'id': booking['room_id']}, {'_id': 0})
            guest = await db.guests.find_one({'id': booking['guest_id']}, {'_id': 0})
            
            due_out_rooms.append({
                'room_number': room['room_number'] if room else 'N/A',
                'room_type': room['room_type'] if room else 'N/A',
                'guest_name': guest['name'] if guest else 'N/A',
                'checkout_date': booking['check_out'],
                'booking_id': booking['id'],
                'is_today': checkout_date == today
            })
    
    return {
        'due_out_rooms': due_out_rooms,
        'count': len(due_out_rooms)
    }

@api_router.get("/housekeeping/stayovers")
async def get_stayover_rooms(current_user: User = Depends(get_current_user)):
    """Get rooms with guests staying beyond today"""
    today = datetime.now(timezone.utc).date()
    
    # Find checked-in bookings not checking out today
    bookings = await db.bookings.find({
        'tenant_id': current_user.tenant_id,
        'status': 'checked_in'
    }).to_list(1000)
    
    stayover_rooms = []
    for booking in bookings:
        checkout_date = datetime.fromisoformat(booking['check_out']).date()
        if checkout_date > today:
            room = await db.rooms.find_one({'id': booking['room_id']}, {'_id': 0})
            guest = await db.guests.find_one({'id': booking['guest_id']}, {'_id': 0})
            
            nights_remaining = (checkout_date - today).days
            
            stayover_rooms.append({
                'room_number': room['room_number'] if room else 'N/A',
                'room_type': room['room_type'] if room else 'N/A',
                'guest_name': guest['name'] if guest else 'N/A',
                'checkout_date': booking['check_out'],
                'nights_remaining': nights_remaining,
                'booking_id': booking['id']
            })
    
    return {
        'stayover_rooms': stayover_rooms,
        'count': len(stayover_rooms)
    }

@api_router.get("/housekeeping/arrivals")
async def get_arrival_rooms(current_user: User = Depends(get_current_user)):
    """Get rooms with guests arriving today"""
    today = datetime.now(timezone.utc).date()
    
    # Find bookings checking in today
    bookings = await db.bookings.find({
        'tenant_id': current_user.tenant_id,
        'status': {'$in': ['confirmed', 'guaranteed', 'pending']}
    }).to_list(1000)
    
    arrival_rooms = []
    for booking in bookings:
        checkin_date = datetime.fromisoformat(booking['check_in']).date()
        if checkin_date == today:
            room = await db.rooms.find_one({'id': booking['room_id']}, {'_id': 0})
            guest = await db.guests.find_one({'id': booking['guest_id']}, {'_id': 0})
            
            arrival_rooms.append({
                'room_number': room['room_number'] if room else 'N/A',
                'room_type': room['room_type'] if room else 'N/A',
                'room_status': room['status'] if room else 'unknown',
                'guest_name': guest['name'] if guest else 'N/A',
                'checkin_time': booking.get('check_in'),
                'booking_id': booking['id'],
                'booking_status': booking['status'],
                'ready': room['status'] in ['available', 'inspected'] if room else False
            })
    
    return {
        'arrival_rooms': arrival_rooms,
        'count': len(arrival_rooms),
        'ready_count': sum(1 for r in arrival_rooms if r['ready'])
    }

@api_router.put("/housekeeping/room/{room_id}/status")
async def update_room_status_hk(
    room_id: str,
    new_status: str,
    notes: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Quick room status update from housekeeping"""
    valid_statuses = ['available', 'occupied', 'dirty', 'cleaning', 'inspected', 'maintenance', 'out_of_order']
    
    if new_status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {valid_statuses}")
    
    room = await db.rooms.find_one({
        'id': room_id,
        'tenant_id': current_user.tenant_id
    })
    
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    update_data = {
        'status': new_status,
        'updated_at': datetime.now(timezone.utc).isoformat()
    }
    
    if notes:
        update_data['hk_notes'] = notes
    
    await db.rooms.update_one(
        {'id': room_id},
        {'$set': update_data}
    )
    
    return {
        'message': f'Room {room["room_number"]} status updated to {new_status}',
        'room_number': room['room_number'],
        'new_status': new_status
    }

@api_router.post("/housekeeping/assign")
async def assign_housekeeping_task(
    room_id: str,
    assigned_to: str,
    task_type: str = 'cleaning',
    priority: str = 'normal',
    notes: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Assign housekeeping task to staff"""
    room = await db.rooms.find_one({
        'id': room_id,
        'tenant_id': current_user.tenant_id
    })
    
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    task = HousekeepingTask(
        tenant_id=current_user.tenant_id,
        room_id=room_id,
        assigned_to=assigned_to,
        task_type=task_type,
        priority=priority,
        notes=notes or f"{task_type.title()} for Room {room['room_number']}"
    )
    
    task_dict = task.model_dump()
    task_dict['created_at'] = task_dict['created_at'].isoformat()
    await db.housekeeping_tasks.insert_one(task_dict)
    
    return {
        'message': f'Task assigned to {assigned_to}',
        'task': task
    }

# ============= CHANNEL MANAGER =============

@api_router.post("/channel/rates")
async def update_channel_rates(room_type: str, channel: str, start_date: str, end_date: str, rate: float, availability: int, current_user: User = Depends(get_current_user)):
    start = datetime.fromisoformat(start_date).date()
    end = datetime.fromisoformat(end_date).date()
    current_date = start
    while current_date <= end:
        channel_rate = ChannelRate(tenant_id=current_user.tenant_id, room_type=room_type, channel=channel, date=current_date, rate=rate, availability=availability)
        await db.channel_rates.update_one({'tenant_id': current_user.tenant_id, 'room_type': room_type, 'channel': channel, 'date': current_date.isoformat()},
                                          {'$set': channel_rate.model_dump()}, upsert=True)
        current_date += timedelta(days=1)
    return {'message': f'Rates updated for {(end - start).days + 1} days'}

@api_router.get("/channel/rates")
async def get_channel_rates(room_type: Optional[str] = None, channel: Optional[str] = None, start_date: Optional[str] = None, current_user: User = Depends(get_current_user)):
    query = {'tenant_id': current_user.tenant_id}
    if room_type:
        query['room_type'] = room_type
    if channel:
        query['channel'] = channel
    if start_date:
        query['date'] = {'$gte': start_date}
    rates = await db.channel_rates.find(query, {'_id': 0}).to_list(1000)
    return rates

@api_router.get("/channel/performance")
async def get_channel_performance(start_date: Optional[str] = None, end_date: Optional[str] = None, current_user: User = Depends(get_current_user)):
    query = {'tenant_id': current_user.tenant_id}
    if start_date and end_date:
        query['check_in'] = {'$gte': start_date, '$lte': end_date}
    bookings = await db.bookings.find(query, {'_id': 0}).to_list(1000)
    channel_stats = {}
    for booking in bookings:
        channel = booking['channel']
        if channel not in channel_stats:
            channel_stats[channel] = {'bookings': 0, 'revenue': 0.0, 'avg_rate': 0.0}
        channel_stats[channel]['bookings'] += 1
        channel_stats[channel]['revenue'] += booking['total_amount']
    for channel in channel_stats:
        if channel_stats[channel]['bookings'] > 0:
            channel_stats[channel]['avg_rate'] = channel_stats[channel]['revenue'] / channel_stats[channel]['bookings']
    return channel_stats

# ============= REPORTING =============

@api_router.get("/reports/occupancy")
async def get_occupancy_report(start_date: str, end_date: str, current_user: User = Depends(get_current_user)):
    start = datetime.fromisoformat(start_date)
    end = datetime.fromisoformat(end_date)
    total_rooms = await db.rooms.count_documents({'tenant_id': current_user.tenant_id})
    bookings = await db.bookings.find({'tenant_id': current_user.tenant_id, 'status': {'$in': ['confirmed', 'checked_in', 'checked_out']},
                                       '$or': [{'check_in': {'$gte': start.isoformat(), '$lte': end.isoformat()}},
                                              {'check_out': {'$gte': start.isoformat(), '$lte': end.isoformat()}},
                                              {'check_in': {'$lte': start.isoformat()}, 'check_out': {'$gte': end.isoformat()}}]}, {'_id': 0}).to_list(1000)
    days = (end - start).days + 1
    total_room_nights = total_rooms * days
    occupied_room_nights = 0
    for booking in bookings:
        check_in = datetime.fromisoformat(booking['check_in'])
        check_out = datetime.fromisoformat(booking['check_out'])
        overlap_start = max(start, check_in)
        overlap_end = min(end, check_out)
        if overlap_start < overlap_end:
            occupied_room_nights += (overlap_end - overlap_start).days
    occupancy_rate = (occupied_room_nights / total_room_nights * 100) if total_room_nights > 0 else 0
    return {'start_date': start_date, 'end_date': end_date, 'total_rooms': total_rooms, 'total_room_nights': total_room_nights,
            'occupied_room_nights': occupied_room_nights, 'occupancy_rate': round(occupancy_rate, 2)}

@api_router.get("/reports/revenue")
async def get_revenue_report(start_date: str, end_date: str, current_user: User = Depends(get_current_user)):
    start = datetime.fromisoformat(start_date)
    end = datetime.fromisoformat(end_date)
    bookings = await db.bookings.find({'tenant_id': current_user.tenant_id, 'status': {'$in': ['checked_in', 'checked_out']},
                                       'check_in': {'$gte': start.isoformat(), '$lte': end.isoformat()}}, {'_id': 0}).to_list(1000)
    total_revenue = sum(b['total_amount'] for b in bookings)
    total_room_nights = sum((datetime.fromisoformat(b['check_out']) - datetime.fromisoformat(b['check_in'])).days for b in bookings)
    adr = (total_revenue / total_room_nights) if total_room_nights > 0 else 0
    total_rooms = await db.rooms.count_documents({'tenant_id': current_user.tenant_id})
    days = (end - start).days + 1
    total_available_room_nights = total_rooms * days
    rev_par = (total_revenue / total_available_room_nights) if total_available_room_nights > 0 else 0
    folio_charges = await db.folio_charges.find({'tenant_id': current_user.tenant_id, 'date': {'$gte': start.isoformat(), '$lte': end.isoformat()}}, {'_id': 0}).to_list(1000)
    revenue_by_type = {}
    for charge in folio_charges:
        charge_type = charge['charge_type']
        revenue_by_type[charge_type] = revenue_by_type.get(charge_type, 0.0) + charge['total']
    return {'start_date': start_date, 'end_date': end_date, 'total_revenue': round(total_revenue, 2), 'room_nights_sold': total_room_nights,
            'adr': round(adr, 2), 'rev_par': round(rev_par, 2), 'revenue_by_type': revenue_by_type, 'bookings_count': len(bookings)}

@api_router.get("/reports/daily-summary")
async def get_daily_summary(date_str: Optional[str] = None, current_user: User = Depends(get_current_user)):
    target_date = datetime.fromisoformat(date_str).date() if date_str else datetime.now(timezone.utc).date()
    start_of_day = datetime.combine(target_date, datetime.min.time())
    end_of_day = datetime.combine(target_date, datetime.max.time())
    arrivals = await db.bookings.count_documents({'tenant_id': current_user.tenant_id, 'check_in': {'$gte': start_of_day.isoformat(), '$lte': end_of_day.isoformat()}})
    departures = await db.bookings.count_documents({'tenant_id': current_user.tenant_id, 'check_out': {'$gte': start_of_day.isoformat(), '$lte': end_of_day.isoformat()}})
    inhouse = await db.bookings.count_documents({'tenant_id': current_user.tenant_id, 'status': 'checked_in'})
    total_rooms = await db.rooms.count_documents({'tenant_id': current_user.tenant_id})
    payments = await db.payments.find({'tenant_id': current_user.tenant_id, 'status': 'paid',
                                       'processed_at': {'$gte': start_of_day.isoformat(), '$lte': end_of_day.isoformat()}}, {'_id': 0}).to_list(1000)
    daily_revenue = sum(p['amount'] for p in payments)
    return {'date': target_date.isoformat(), 'arrivals': arrivals, 'departures': departures, 'inhouse': inhouse, 'total_rooms': total_rooms,
            'occupancy_rate': round((inhouse / total_rooms * 100) if total_rooms > 0 else 0, 2), 'daily_revenue': round(daily_revenue, 2)}

@api_router.get("/reports/forecast")
async def get_forecast(days: int = 30, current_user: User = Depends(get_current_user)):
    today = datetime.now(timezone.utc).date()
    forecast_data = []
    for i in range(days):
        forecast_date = today + timedelta(days=i)
        start_of_day = datetime.combine(forecast_date, datetime.min.time())
        end_of_day = datetime.combine(forecast_date, datetime.max.time())
        bookings = await db.bookings.count_documents({'tenant_id': current_user.tenant_id, 'status': {'$in': ['confirmed', 'checked_in']},
                                                       'check_in': {'$lte': end_of_day.isoformat()}, 'check_out': {'$gte': start_of_day.isoformat()}})
        total_rooms = await db.rooms.count_documents({'tenant_id': current_user.tenant_id})
        occupancy = round((bookings / total_rooms * 100) if total_rooms > 0 else 0, 2)
        forecast_data.append({'date': forecast_date.isoformat(), 'bookings': bookings, 'total_rooms': total_rooms, 'occupancy_rate': occupancy})
    return forecast_data

# Router will be included at the very end after ALL endpoints are defined

logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import List, Optional
from datetime import datetime
from enum import Enum

# ============= ACCOUNTING ENUMS =============

class AccountType(str, Enum):
    ASSET = "asset"
    LIABILITY = "liability"
    EQUITY = "equity"
    REVENUE = "revenue"
    EXPENSE = "expense"

class TransactionType(str, Enum):
    INCOME = "income"
    EXPENSE = "expense"
    TRANSFER = "transfer"

class ExpenseCategory(str, Enum):
    SALARIES = "salaries"
    UTILITIES = "utilities"
    SUPPLIES = "supplies"
    MAINTENANCE = "maintenance"
    MARKETING = "marketing"
    RENT = "rent"
    INSURANCE = "insurance"
    TAXES = "taxes"
    OTHER = "other"

class IncomeCategory(str, Enum):
    ROOM_REVENUE = "room_revenue"
    FOOD_BEVERAGE = "food_beverage"
    SPA = "spa"
    EVENTS = "events"
    LAUNDRY = "laundry"
    OTHER_SERVICES = "other_services"

class PaymentStatus(str, Enum):
    PENDING = "pending"
    PAID = "paid"
    PARTIAL = "partial"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"

class InvoiceType(str, Enum):
    SALES = "sales"  # Satış faturası
    PURCHASE = "purchase"  # Alış faturası
    PROFORMA = "proforma"  # Proforma
    E_INVOICE = "e_invoice"  # E-Fatura
    E_ARCHIVE = "e_archive"  # E-Arşiv

class VATRate(str, Enum):
    RATE_1 = "1"
    RATE_8 = "8"
    RATE_18 = "18"
    RATE_20 = "20"
    EXEMPT = "0"

# ============= ACCOUNTING MODELS =============

class Supplier(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    name: str
    tax_office: Optional[str] = None
    tax_number: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    account_balance: float = 0.0
    category: str = "general"
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class BankAccount(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    name: str
    bank_name: str
    account_number: str
    iban: Optional[str] = None
    currency: str = "USD"
    balance: float = 0.0
    is_active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class Expense(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    expense_number: str
    supplier_id: Optional[str] = None
    category: ExpenseCategory
    description: str
    amount: float
    vat_rate: float = 18.0
    vat_amount: float = 0.0
    total_amount: float
    date: datetime
    payment_status: PaymentStatus = PaymentStatus.PENDING
    payment_method: Optional[str] = None
    receipt_url: Optional[str] = None
    notes: Optional[str] = None
    created_by: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class InventoryItem(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    name: str
    sku: Optional[str] = None
    category: str
    unit: str
    quantity: float = 0.0
    unit_cost: float = 0.0
    reorder_level: float = 0.0
    supplier_id: Optional[str] = None
    location: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class StockMovement(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    item_id: str
    movement_type: str  # in, out, adjustment
    quantity: float
    unit_cost: float
    reference: Optional[str] = None
    notes: Optional[str] = None
    created_by: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# Accounting models are imported from accounting_models.py at the top of the file
# Accounting Endpoints to be integrated into server.py

# These endpoints will be added to server.py

# ============= SUPPLIER MANAGEMENT =============


@api_router.post("/accounting/suppliers")
async def create_supplier(
    name: str,
    tax_office: Optional[str] = None,
    tax_number: Optional[str] = None,
    email: Optional[str] = None,
    phone: Optional[str] = None,
    address: Optional[str] = None,
    category: str = "general",
    current_user: User = Depends(get_current_user)
):
    # Supplier model imported at top
    supplier = Supplier(
        tenant_id=current_user.tenant_id,
        name=name,
        tax_office=tax_office,
        tax_number=tax_number,
        email=email,
        phone=phone,
        address=address,
        category=category
    )
    supplier_dict = supplier.model_dump()
    supplier_dict['created_at'] = supplier_dict['created_at'].isoformat()
    await db.suppliers.insert_one(supplier_dict)
    return supplier


@api_router.get("/accounting/suppliers")
async def get_suppliers(current_user: User = Depends(get_current_user)):
    suppliers = await db.suppliers.find({'tenant_id': current_user.tenant_id}, {'_id': 0}).to_list(1000)
    return suppliers


@api_router.put("/accounting/suppliers/{supplier_id}")
async def update_supplier(supplier_id: str, updates: Dict[str, Any], current_user: User = Depends(get_current_user)):
    await db.suppliers.update_one({'id': supplier_id, 'tenant_id': current_user.tenant_id}, {'$set': updates})
    supplier = await db.suppliers.find_one({'id': supplier_id}, {'_id': 0})
    return supplier

# ============= BANK ACCOUNTS =============


@api_router.post("/accounting/bank-accounts")
async def create_bank_account(
    name: str,
    bank_name: str,
    account_number: str,
    iban: Optional[str] = None,
    currency: str = "USD",
    balance: float = 0.0,
    current_user: User = Depends(get_current_user)
):
    # BankAccount model imported at top
    bank_account = BankAccount(
        tenant_id=current_user.tenant_id,
        name=name,
        bank_name=bank_name,
        account_number=account_number,
        iban=iban,
        currency=currency,
        balance=balance
    )
    account_dict = bank_account.model_dump()
    account_dict['created_at'] = account_dict['created_at'].isoformat()
    await db.bank_accounts.insert_one(account_dict)
    return bank_account


@api_router.get("/accounting/bank-accounts")
async def get_bank_accounts(current_user: User = Depends(get_current_user)):
    accounts = await db.bank_accounts.find({'tenant_id': current_user.tenant_id}, {'_id': 0}).to_list(1000)
    return accounts


@api_router.put("/accounting/bank-accounts/{account_id}")
async def update_bank_account(account_id: str, updates: Dict[str, Any], current_user: User = Depends(get_current_user)):
    await db.bank_accounts.update_one({'id': account_id, 'tenant_id': current_user.tenant_id}, {'$set': updates})
    account = await db.bank_accounts.find_one({'id': account_id}, {'_id': 0})
    return account

# ============= EXPENSE MANAGEMENT =============


@api_router.post("/accounting/expenses")
async def create_expense(
    category: str,
    description: str,
    amount: float,
    vat_rate: float,
    date: str,
    supplier_id: Optional[str] = None,
    payment_method: Optional[str] = None,
    receipt_url: Optional[str] = None,
    notes: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    # Expense model imported at top
    
    count = await db.expenses.count_documents({'tenant_id': current_user.tenant_id})
    expense_number = f"EXP-{count + 1:05d}"
    
    vat_amount = amount * (vat_rate / 100)
    total_amount = amount + vat_amount
    
    expense = Expense(
        tenant_id=current_user.tenant_id,
        expense_number=expense_number,
        supplier_id=supplier_id,
        category=category,
        description=description,
        amount=amount,
        vat_rate=vat_rate,
        vat_amount=vat_amount,
        total_amount=total_amount,
        date=datetime.fromisoformat(date),
        payment_method=payment_method,
        receipt_url=receipt_url,
        notes=notes,
        created_by=current_user.name
    )
    
    expense_dict = expense.model_dump()
    expense_dict['date'] = expense_dict['date'].isoformat()
    expense_dict['created_at'] = expense_dict['created_at'].isoformat()
    await db.expenses.insert_one(expense_dict)
    
    # Update supplier balance if applicable
    if supplier_id:
        await db.suppliers.update_one(
            {'id': supplier_id},
            {'$inc': {'account_balance': total_amount}}
        )
    
    # Create cash flow entry
    # CashFlow model imported at top
    cash_flow = CashFlow(
        tenant_id=current_user.tenant_id,
        transaction_type='expense',
        category=category,
        amount=total_amount,
        description=description,
        reference_id=expense.id,
        reference_type='expense',
        date=datetime.fromisoformat(date),
        created_by=current_user.name
    )
    cf_dict = cash_flow.model_dump()
    cf_dict['date'] = cf_dict['date'].isoformat()
    cf_dict['created_at'] = cf_dict['created_at'].isoformat()
    await db.cash_flow.insert_one(cf_dict)
    
    return expense


@api_router.get("/accounting/expenses")
async def get_expenses(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    category: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    query = {'tenant_id': current_user.tenant_id}
    if start_date and end_date:
        query['date'] = {'$gte': start_date, '$lte': end_date}
    if category:
        query['category'] = category
    
    expenses = await db.expenses.find(query, {'_id': 0}).sort('date', -1).to_list(1000)
    return expenses


@api_router.put("/accounting/expenses/{expense_id}")
async def update_expense(expense_id: str, updates: Dict[str, Any], current_user: User = Depends(get_current_user)):
    await db.expenses.update_one({'id': expense_id, 'tenant_id': current_user.tenant_id}, {'$set': updates})
    expense = await db.expenses.find_one({'id': expense_id}, {'_id': 0})
    return expense

# ============= INVENTORY MANAGEMENT =============


@api_router.post("/accounting/inventory")
async def create_inventory_item(
    name: str,
    category: str,
    unit: str,
    quantity: float = 0.0,
    unit_cost: float = 0.0,
    reorder_level: float = 0.0,
    sku: Optional[str] = None,
    supplier_id: Optional[str] = None,
    location: Optional[str] = None,
    notes: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    # InventoryItem model imported at top
    item = InventoryItem(
        tenant_id=current_user.tenant_id,
        name=name,
        sku=sku,
        category=category,
        unit=unit,
        quantity=quantity,
        unit_cost=unit_cost,
        reorder_level=reorder_level,
        supplier_id=supplier_id,
        location=location,
        notes=notes
    )
    item_dict = item.model_dump()
    item_dict['created_at'] = item_dict['created_at'].isoformat()
    await db.inventory_items.insert_one(item_dict)
    return item


@api_router.get("/accounting/inventory")
async def get_inventory(current_user: User = Depends(get_current_user)):
    items = await db.inventory_items.find({'tenant_id': current_user.tenant_id}, {'_id': 0}).to_list(1000)
    
    # Get low stock items
    low_stock = [item for item in items if item['quantity'] <= item['reorder_level']]
    
    return {
        'items': items,
        'low_stock_count': len(low_stock),
        'total_value': sum(item['quantity'] * item['unit_cost'] for item in items)
    }


@api_router.post("/accounting/inventory/movement")
async def create_stock_movement(
    item_id: str,
    movement_type: str,
    quantity: float,
    unit_cost: float,
    reference: Optional[str] = None,
    notes: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    # StockMovement model imported at top
    
    movement = StockMovement(
        tenant_id=current_user.tenant_id,
        item_id=item_id,
        movement_type=movement_type,
        quantity=quantity,
        unit_cost=unit_cost,
        reference=reference,
        notes=notes,
        created_by=current_user.name
    )
    
    movement_dict = movement.model_dump()
    movement_dict['created_at'] = movement_dict['created_at'].isoformat()
    await db.stock_movements.insert_one(movement_dict)
    
    # Update inventory quantity
    if movement_type == 'in':
        await db.inventory_items.update_one(
            {'id': item_id},
            {'$inc': {'quantity': quantity}}
        )
    elif movement_type == 'out':
        await db.inventory_items.update_one(
            {'id': item_id},
            {'$inc': {'quantity': -quantity}}
        )
    else:  # adjustment
        await db.inventory_items.update_one(
            {'id': item_id},
            {'$set': {'quantity': quantity}}
        )
    
    return movement

# ============= ADVANCED INVOICING =============


class AccountingInvoiceCreateRequest(BaseModel):
    invoice_type: str
    customer_name: str
    customer_email: Optional[str] = None
    customer_tax_office: Optional[str] = None
    customer_tax_number: Optional[str] = None
    customer_address: Optional[str] = None
    items: List[Dict[str, Any]] = []
    due_date: str
    booking_id: Optional[str] = None
    notes: Optional[str] = None

@api_router.post("/accounting/invoices")
async def create_accounting_invoice(
    request: AccountingInvoiceCreateRequest,
    current_user: User = Depends(get_current_user)
):
    # Models are now imported at the top of the file
    
    count = await db.accounting_invoices.count_documents({'tenant_id': current_user.tenant_id})
    invoice_number = f"INV-{datetime.now().year}-{count + 1:05d}"
    
    invoice_items = []
    subtotal = 0.0
    total_vat = 0.0
    vat_withholding = 0.0
    total_additional_taxes = 0.0
    
    for item_data in request.items:
        # Handle additional_taxes parsing
        additional_taxes = []
        if 'additional_taxes' in item_data and item_data['additional_taxes']:
            for tax_data in item_data['additional_taxes']:
                additional_taxes.append(AdditionalTax(**tax_data))
        
        # Create item with parsed additional taxes
        item_dict = {k: v for k, v in item_data.items() if k != 'additional_taxes'}
        item_dict['additional_taxes'] = additional_taxes
        
        item = AccountingInvoiceItem(**item_dict)
        
        invoice_items.append(item)
        subtotal += item.quantity * item.unit_price
        total_vat += item.vat_amount
        
        # Calculate additional taxes if present
        if item.additional_taxes:
            for tax in item.additional_taxes:
                if tax.tax_type == 'withholding':
                    # Withholding tax is deducted from VAT
                    # Calculate based on withholding rate (e.g., "7/10" = 70%)
                    if tax.withholding_rate:
                        rate_parts = tax.withholding_rate.split('/')
                        if len(rate_parts) == 2:
                            rate_percent = (int(rate_parts[0]) / int(rate_parts[1])) * 100
                            withholding_amount = item.vat_amount * (rate_percent / 100)
                            vat_withholding += withholding_amount
                            tax.calculated_amount = withholding_amount
                else:
                    # Other taxes (ÖTV, accommodation, etc.)
                    if tax.is_percentage and tax.rate:
                        tax_amount = (item.quantity * item.unit_price) * (tax.rate / 100)
                        total_additional_taxes += tax_amount
                        tax.calculated_amount = tax_amount
                    elif tax.amount:
                        total_additional_taxes += tax.amount
                        tax.calculated_amount = tax.amount
    
    total = subtotal + total_vat + total_additional_taxes - vat_withholding
    
    invoice = AccountingInvoice(
        tenant_id=current_user.tenant_id,
        invoice_number=invoice_number,
        invoice_type=request.invoice_type,
        customer_name=request.customer_name,
        customer_email=request.customer_email,
        customer_tax_office=request.customer_tax_office,
        customer_tax_number=request.customer_tax_number,
        customer_address=request.customer_address,
        items=invoice_items,
        subtotal=subtotal,
        total_vat=total_vat,
        vat_withholding=vat_withholding,
        total_additional_taxes=total_additional_taxes,
        total=total,
        due_date=datetime.fromisoformat(request.due_date),
        booking_id=request.booking_id,
        notes=request.notes,
        created_by=current_user.name
    )
    
    invoice_dict = invoice.model_dump()
    invoice_dict['issue_date'] = invoice_dict['issue_date'].isoformat()
    invoice_dict['due_date'] = invoice_dict['due_date'].isoformat()
    invoice_dict['created_at'] = invoice_dict['created_at'].isoformat()
    await db.accounting_invoices.insert_one(invoice_dict)
    
    # Create cash flow entry
    # CashFlow model imported at top
    cash_flow = CashFlow(
        tenant_id=current_user.tenant_id,
        transaction_type='income',
        category='room_revenue' if request.booking_id else 'other_services',
        amount=total,
        description=f"Invoice {invoice_number}",
        reference_id=invoice.id,
        reference_type='invoice',
        date=datetime.now(timezone.utc),
        created_by=current_user.name
    )
    cf_dict = cash_flow.model_dump()
    cf_dict['date'] = cf_dict['date'].isoformat()
    cf_dict['created_at'] = cf_dict['created_at'].isoformat()
    await db.cash_flow.insert_one(cf_dict)
    
    return invoice


@api_router.get("/accounting/invoices")
async def get_accounting_invoices(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    invoice_type: Optional[str] = None,
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    query = {'tenant_id': current_user.tenant_id}
    if start_date and end_date:
        query['issue_date'] = {'$gte': start_date, '$lte': end_date}
    if invoice_type:
        query['invoice_type'] = invoice_type
    if status:
        query['status'] = status
    
    invoices = await db.accounting_invoices.find(query, {'_id': 0}).sort('issue_date', -1).to_list(1000)
    return invoices


@api_router.put("/accounting/invoices/{invoice_id}")
async def update_accounting_invoice(invoice_id: str, updates: Dict[str, Any], current_user: User = Depends(get_current_user)):
    if 'status' in updates and updates['status'] == 'paid' and 'payment_date' not in updates:
        updates['payment_date'] = datetime.now(timezone.utc).isoformat()
    
    await db.accounting_invoices.update_one({'id': invoice_id, 'tenant_id': current_user.tenant_id}, {'$set': updates})
    invoice = await db.accounting_invoices.find_one({'id': invoice_id}, {'_id': 0})
    return invoice

# ============= CASH FLOW =============


@api_router.get("/accounting/cash-flow")
async def get_cash_flow(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    transaction_type: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    query = {'tenant_id': current_user.tenant_id}
    if start_date and end_date:
        query['date'] = {'$gte': start_date, '$lte': end_date}
    if transaction_type:
        query['transaction_type'] = transaction_type
    
    flows = await db.cash_flow.find(query, {'_id': 0}).sort('date', -1).to_list(1000)
    
    total_income = sum(f['amount'] for f in flows if f['transaction_type'] == 'income')
    total_expense = sum(f['amount'] for f in flows if f['transaction_type'] == 'expense')
    net_cash_flow = total_income - total_expense
    
    return {
        'transactions': flows,
        'total_income': total_income,
        'total_expense': total_expense,
        'net_cash_flow': net_cash_flow
    }

# ============= FINANCIAL REPORTS =============


@api_router.get("/accounting/reports/profit-loss")
async def get_profit_loss_report(
    start_date: str,
    end_date: str,
    current_user: User = Depends(get_current_user)
):
    # Get all income
    invoices = await db.accounting_invoices.find({
        'tenant_id': current_user.tenant_id,
        'status': 'paid',
        'issue_date': {'$gte': start_date, '$lte': end_date}
    }, {'_id': 0}).to_list(1000)
    
    # Get all expenses
    expenses = await db.expenses.find({
        'tenant_id': current_user.tenant_id,
        'date': {'$gte': start_date, '$lte': end_date}
    }, {'_id': 0}).to_list(1000)
    
    total_revenue = sum(inv['total'] for inv in invoices)
    total_expenses = sum(exp['total_amount'] for exp in expenses)
    gross_profit = total_revenue - total_expenses
    profit_margin = (gross_profit / total_revenue * 100) if total_revenue > 0 else 0
    
    # Revenue breakdown
    revenue_by_category = {}
    for inv in invoices:
        for item in inv['items']:
            desc = item['description']
            revenue_by_category[desc] = revenue_by_category.get(desc, 0) + item['total']
    
    # Expense breakdown
    expense_by_category = {}
    for exp in expenses:
        cat = exp['category']
        expense_by_category[cat] = expense_by_category.get(cat, 0) + exp['total_amount']
    
    return {
        'period': {'start': start_date, 'end': end_date},
        'total_revenue': round(total_revenue, 2),
        'total_expenses': round(total_expenses, 2),
        'gross_profit': round(gross_profit, 2),
        'profit_margin': round(profit_margin, 2),
        'revenue_breakdown': revenue_by_category,
        'expense_breakdown': expense_by_category
    }


@api_router.get("/accounting/reports/vat-report")
async def get_vat_report(
    start_date: str,
    end_date: str,
    current_user: User = Depends(get_current_user)
):
    # Sales VAT (collected)
    invoices = await db.accounting_invoices.find({
        'tenant_id': current_user.tenant_id,
        'issue_date': {'$gte': start_date, '$lte': end_date}
    }, {'_id': 0}).to_list(1000)
    
    sales_vat = sum(inv['total_vat'] for inv in invoices)
    
    # Purchase VAT (paid)
    expenses = await db.expenses.find({
        'tenant_id': current_user.tenant_id,
        'date': {'$gte': start_date, '$lte': end_date}
    }, {'_id': 0}).to_list(1000)
    
    purchase_vat = sum(exp['vat_amount'] for exp in expenses)
    
    vat_payable = sales_vat - purchase_vat
    
    return {
        'period': {'start': start_date, 'end': end_date},
        'sales_vat': round(sales_vat, 2),
        'purchase_vat': round(purchase_vat, 2),
        'vat_payable': round(vat_payable, 2)
    }


@api_router.get("/accounting/reports/balance-sheet")
async def get_balance_sheet(current_user: User = Depends(get_current_user)):
    # Assets
    bank_accounts = await db.bank_accounts.find({'tenant_id': current_user.tenant_id}, {'_id': 0}).to_list(1000)
    total_cash = sum(acc['balance'] for acc in bank_accounts)
    
    inventory = await db.inventory_items.find({'tenant_id': current_user.tenant_id}, {'_id': 0}).to_list(1000)
    total_inventory = sum(item['quantity'] * item['unit_cost'] for item in inventory)
    
    # Receivables (unpaid invoices)
    receivables = await db.accounting_invoices.find({
        'tenant_id': current_user.tenant_id,
        'status': {'$in': ['pending', 'partial']}
    }, {'_id': 0}).to_list(1000)
    total_receivables = sum(inv['total'] for inv in receivables)
    
    total_assets = total_cash + total_inventory + total_receivables
    
    # Liabilities
    payables = await db.expenses.find({
        'tenant_id': current_user.tenant_id,
        'payment_status': 'pending'
    }, {'_id': 0}).to_list(1000)
    total_payables = sum(exp['total_amount'] for exp in payables)
    
    # Equity
    total_equity = total_assets - total_payables
    
    return {
        'assets': {
            'cash': round(total_cash, 2),
            'inventory': round(total_inventory, 2),
            'receivables': round(total_receivables, 2),
            'total': round(total_assets, 2)
        },
        'liabilities': {
            'payables': round(total_payables, 2),
            'total': round(total_payables, 2)
        },
        'equity': {
            'total': round(total_equity, 2)
        }
    }


@api_router.get("/accounting/dashboard")
async def get_accounting_dashboard(current_user: User = Depends(get_current_user)):
    # Get current month data
    today = datetime.now(timezone.utc)
    month_start = today.replace(day=1, hour=0, minute=0, second=0).isoformat()
    month_end = today.isoformat()
    
    invoices = await db.accounting_invoices.find({
        'tenant_id': current_user.tenant_id,
        'issue_date': {'$gte': month_start, '$lte': month_end}
    }, {'_id': 0}).to_list(1000)
    
    expenses = await db.expenses.find({
        'tenant_id': current_user.tenant_id,
        'date': {'$gte': month_start, '$lte': month_end}
    }, {'_id': 0}).to_list(1000)
    
    total_income = sum(inv['total'] for inv in invoices if inv['status'] == 'paid')
    total_expenses = sum(exp['total_amount'] for exp in expenses)
    pending_invoices = len([inv for inv in invoices if inv['status'] == 'pending'])
    overdue_invoices = len([inv for inv in invoices if inv['status'] == 'overdue'])
    
    # Get bank balances
    bank_accounts = await db.bank_accounts.find({'tenant_id': current_user.tenant_id}, {'_id': 0}).to_list(1000)
    total_bank_balance = sum(acc['balance'] for acc in bank_accounts)
    
    return {
        'monthly_income': round(total_income, 2),
        'monthly_expenses': round(total_expenses, 2),
        'net_income': round(total_income - total_expenses, 2),
        'pending_invoices': pending_invoices,
        'overdue_invoices': overdue_invoices,
        'total_bank_balance': round(total_bank_balance, 2)
    }

# Import and include AI endpoints
try:
    from ai_endpoints import api_router as ai_router
    api_router.include_router(ai_router, tags=["AI Intelligence"])
    print("✅ AI endpoints loaded successfully")
except ImportError as e:
    print(f"⚠️ AI endpoints not loaded: {e}")

# Include router at the very end after ALL endpoints are defined
app.include_router(api_router)
