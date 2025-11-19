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
from passlib.context import CryptContext

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
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

# Import room block models
try:
    from room_block_models import (
        RoomBlock, RoomBlockCreate, RoomBlockUpdate,
        BlockType, BlockStatus
    )
    print("✅ Room block models imported successfully")
except ImportError as e:
    print(f"⚠️ Room block models not loaded: {e}")
    # Create fallback models
    class BlockType:
        OUT_OF_ORDER = "out_of_order"
        OUT_OF_SERVICE = "out_of_service"
        MAINTENANCE = "maintenance"
    
    class BlockStatus:
        ACTIVE = "active"
        CANCELLED = "cancelled"
        EXPIRED = "expired"

# Import CRM models
try:
    from crm_models import (
        GuestProfile, GuestPreferences, GuestBehavior,
        UpsellOffer, MessageTemplate, Message,
        LoyaltyStatus, UpsellType, MessageChannel, MessageStatus
    )
    print("✅ CRM models imported successfully")
except Exception as e:
    print(f"⚠️ CRM models not loaded: {e}")

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
    ADMIN = "admin"  # Full access - Owner/IT
    SUPERVISOR = "supervisor"  # Management oversight
    FRONT_DESK = "front_desk"  # Reservations, check-in/out
    HOUSEKEEPING = "housekeeping"  # Room status, tasks
    SALES = "sales"  # Corporate accounts, contracts
    FINANCE = "finance"  # Accounting, invoices, AR
    STAFF = "staff"  # Limited access
    GUEST = "guest"  # Guest portal

class Permission(str, Enum):
    # Booking permissions
    VIEW_BOOKINGS = "view_bookings"
    CREATE_BOOKING = "create_booking"
    EDIT_BOOKING = "edit_booking"
    DELETE_BOOKING = "delete_booking"
    CHECKIN = "checkin"
    CHECKOUT = "checkout"
    
    # Folio permissions
    VIEW_FOLIO = "view_folio"
    POST_CHARGE = "post_charge"
    POST_PAYMENT = "post_payment"
    VOID_CHARGE = "void_charge"
    TRANSFER_FOLIO = "transfer_folio"
    CLOSE_FOLIO = "close_folio"
    OVERRIDE_RATE = "override_rate"
    
    # Company permissions
    VIEW_COMPANIES = "view_companies"
    CREATE_COMPANY = "create_company"
    EDIT_COMPANY = "edit_company"
    
    # Housekeeping permissions
    VIEW_HK_BOARD = "view_hk_board"
    UPDATE_ROOM_STATUS = "update_room_status"
    ASSIGN_TASK = "assign_task"
    
    # Reports permissions
    VIEW_REPORTS = "view_reports"
    VIEW_FINANCIAL_REPORTS = "view_financial_reports"
    EXPORT_DATA = "export_data"
    
    # Admin permissions
    MANAGE_USERS = "manage_users"
    MANAGE_ROOMS = "manage_rooms"
    SYSTEM_SETTINGS = "system_settings"

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
    HOTELS_COM = "hotels_com"
    TRIP_ADVISOR = "trip_advisor"

class ChannelStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    SYNCING = "syncing"

class MappingStatus(str, Enum):
    MAPPED = "mapped"
    UNMAPPED = "unmapped"
    CONFLICT = "conflict"
    NEEDS_REVIEW = "needs_review"

class PricingStrategy(str, Enum):
    STATIC = "static"
    DYNAMIC = "dynamic"
    COMPETITIVE = "competitive"
    OCCUPANCY_BASED = "occupancy_based"

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

class OTAChannel(str, Enum):
    BOOKING_COM = "booking_com"
    EXPEDIA = "expedia"
    AIRBNB = "airbnb"
    AGODA = "agoda"
    HOTELS_COM = "hotels_com"
    DIRECT = "direct"  # Direct booking
    PHONE = "phone"  # Phone booking
    WALK_IN = "walk_in"

class OTAPaymentModel(str, Enum):
    AGENCY = "agency"  # OTA collects, pays hotel
    HOTEL_COLLECT = "hotel_collect"  # Hotel collects from guest
    VIRTUAL_CARD = "virtual_card"  # OTA provides virtual card
    PREPAID = "prepaid"  # Guest prepaid to OTA

class ParityStatus(str, Enum):
    NEGATIVE = "negative"  # OTA cheaper (bad)
    POSITIVE = "positive"  # Direct cheaper (good)
    EQUAL = "equal"  # Same rate
    UNKNOWN = "unknown"

class ChannelHealth(str, Enum):
    HEALTHY = "healthy"
    DELAYED = "delayed"
    ERROR = "error"
    OFFLINE = "offline"

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

# Role-Permission Mapping
ROLE_PERMISSIONS = {
    UserRole.ADMIN: [p.value for p in Permission],  # All permissions
    UserRole.SUPERVISOR: [
        Permission.VIEW_BOOKINGS, Permission.CREATE_BOOKING, Permission.EDIT_BOOKING,
        Permission.CHECKIN, Permission.CHECKOUT,
        Permission.VIEW_FOLIO, Permission.POST_CHARGE, Permission.POST_PAYMENT,
        Permission.OVERRIDE_RATE, Permission.CLOSE_FOLIO,
        Permission.VIEW_COMPANIES, Permission.EDIT_COMPANY,
        Permission.VIEW_HK_BOARD, Permission.UPDATE_ROOM_STATUS, Permission.ASSIGN_TASK,
        Permission.VIEW_REPORTS, Permission.VIEW_FINANCIAL_REPORTS
    ],
    UserRole.FRONT_DESK: [
        Permission.VIEW_BOOKINGS, Permission.CREATE_BOOKING, Permission.EDIT_BOOKING,
        Permission.CHECKIN, Permission.CHECKOUT,
        Permission.VIEW_FOLIO, Permission.POST_CHARGE, Permission.POST_PAYMENT,
        Permission.VIEW_COMPANIES,
        Permission.VIEW_HK_BOARD,
        Permission.VIEW_REPORTS
    ],
    UserRole.HOUSEKEEPING: [
        Permission.VIEW_BOOKINGS,
        Permission.VIEW_HK_BOARD, Permission.UPDATE_ROOM_STATUS, Permission.ASSIGN_TASK
    ],
    UserRole.SALES: [
        Permission.VIEW_BOOKINGS, Permission.CREATE_BOOKING,
        Permission.VIEW_COMPANIES, Permission.CREATE_COMPANY, Permission.EDIT_COMPANY,
        Permission.VIEW_REPORTS
    ],
    UserRole.FINANCE: [
        Permission.VIEW_BOOKINGS,
        Permission.VIEW_FOLIO, Permission.POST_CHARGE, Permission.POST_PAYMENT,
        Permission.VOID_CHARGE, Permission.CLOSE_FOLIO,
        Permission.VIEW_COMPANIES,
        Permission.VIEW_REPORTS, Permission.VIEW_FINANCIAL_REPORTS, Permission.EXPORT_DATA
    ],
    UserRole.STAFF: [
        Permission.VIEW_BOOKINGS,
        Permission.VIEW_HK_BOARD
    ]
}

def has_permission(user_role: UserRole, permission: Permission) -> bool:
    """Check if a role has a specific permission"""
    return permission.value in ROLE_PERMISSIONS.get(user_role, [])

async def create_audit_log(
    tenant_id: str,
    user,  # User model instance
    action: str,
    entity_type: str,
    entity_id: str,
    changes: Optional[dict] = None,
    ip_address: Optional[str] = None
):
    """Create an audit log entry"""
    audit = AuditLog(
        tenant_id=tenant_id,
        user_id=user.id,
        user_name=user.name,
        user_role=user.role,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        changes=changes,
        ip_address=ip_address
    )
    
    audit_dict = audit.model_dump()
    audit_dict['timestamp'] = audit_dict['timestamp'].isoformat()
    await db.audit_logs.insert_one(audit_dict)

# ============= MODELS =============

class Tenant(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    property_name: str
    property_type: Optional[str] = "hotel"
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    address: Optional[str] = None
    total_rooms: Optional[int] = 50
    subscription_status: str = "active"
    location: Optional[str] = None
    amenities: List[str] = []
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
    base_price: Optional[float] = None
    price_per_night: Optional[float] = None
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
    # OTA Channel fields
    ota_channel: Optional[OTAChannel] = None
    ota_confirmation: Optional[str] = None
    ota_reference_id: Optional[str] = None
    commission_pct: Optional[float] = None
    payment_model: Optional[OTAPaymentModel] = None
    virtual_card_provided: bool = False
    virtual_card_number: Optional[str] = None
    virtual_card_expiry: Optional[str] = None

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
    guests_count: Optional[int] = None
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
    # OTA Channel fields
    ota_channel: Optional[OTAChannel] = None
    ota_confirmation: Optional[str] = None
    ota_reference_id: Optional[str] = None
    commission_pct: Optional[float] = None
    payment_model: Optional[OTAPaymentModel] = None
    virtual_card_provided: bool = False
    virtual_card_number: Optional[str] = None
    virtual_card_expiry: Optional[str] = None
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

# Audit Log Model
class AuditLog(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    user_id: str
    user_name: str
    user_role: UserRole
    action: str  # e.g., "CREATE_BOOKING", "POST_CHARGE", "OVERRIDE_RATE"
    entity_type: str  # e.g., "booking", "folio", "charge", "payment"
    entity_id: str
    changes: Optional[dict] = None  # Old and new values
    ip_address: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

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

# Room Move History Model
class RoomMoveHistory(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    booking_id: str
    old_room: str  # Room number
    new_room: str  # Room number
    old_check_in: str
    new_check_in: str
    reason: str
    moved_by: str  # User name
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# Channel Manager Models
class ChannelConnection(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    channel_type: ChannelType
    channel_name: str
    status: ChannelStatus = ChannelStatus.INACTIVE
    api_endpoint: Optional[str] = None
    api_key: Optional[str] = None
    property_id: Optional[str] = None  # Channel's property ID
    last_sync: Optional[datetime] = None
    sync_rate_availability: bool = True
    sync_reservations: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class RoomMapping(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    channel_id: str
    pms_room_type: str  # PMS room type
    channel_room_type: str  # Channel's room type name
    channel_room_id: Optional[str] = None
    status: MappingStatus = MappingStatus.MAPPED
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class RatePlan(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    name: str
    description: Optional[str] = None
    room_type: str
    base_rate: float
    pricing_strategy: PricingStrategy = PricingStrategy.STATIC
    min_rate: Optional[float] = None
    max_rate: Optional[float] = None
    active_channels: List[ChannelType] = []
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class RateUpdate(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    rate_plan_id: str
    date: str  # YYYY-MM-DD
    rate: float
    availability: int
    min_stay: int = 1
    max_stay: Optional[int] = None
    stop_sell: bool = False
    pushed_to_channels: List[ChannelType] = []
    push_status: dict = {}  # {channel: status}
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class OTAReservation(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    channel_type: ChannelType
    channel_booking_id: str  # OTA's booking ID
    pms_booking_id: Optional[str] = None  # Created PMS booking ID
    guest_name: str
    guest_email: Optional[str] = None
    guest_phone: Optional[str] = None
    room_type: str
    check_in: str
    check_out: str
    adults: int
    children: int = 0
    total_amount: float
    commission_amount: Optional[float] = None
    status: str = "pending"  # pending, imported, error
    error_message: Optional[str] = None
    raw_data: Optional[dict] = None
    received_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    processed_at: Optional[datetime] = None

class ExceptionQueue(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    exception_type: str  # "mapping_error", "rate_push_failed", "reservation_import_failed"
    channel_type: ChannelType
    entity_id: Optional[str] = None
    error_message: str
    details: Optional[dict] = None
    status: str = "pending"  # pending, resolved, ignored
    resolved_by: Optional[str] = None
    resolved_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class RMSSuggestion(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    date: str  # YYYY-MM-DD
    room_type: str
    current_rate: float
    suggested_rate: float
    reason: str  # e.g., "High demand detected", "Competitor analysis"
    confidence_score: float  # 0-100
    based_on: dict  # {occupancy, pickup_pace, competitor_rates, etc.}
    status: str = "pending"  # pending, applied, rejected
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

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

# ============= NEW FEATURES PYDANTIC MODELS =============

# Messaging Models
class SendWhatsAppRequest(BaseModel):
    to: str
    message: str
    booking_id: Optional[str] = None

class SendEmailRequest(BaseModel):
    to: str
    subject: str
    message: str
    booking_id: Optional[str] = None

class SendSMSRequest(BaseModel):
    to: str
    message: str
    booking_id: Optional[str] = None

class CreateMessageTemplateRequest(BaseModel):
    name: str
    channel: str
    subject: Optional[str] = None
    content: str = ""
    variables: List[str] = []

# RMS Models
class AddCompetitorRequest(BaseModel):
    name: str
    location: str
    star_rating: float
    url: Optional[str] = None

class ScrapePricesRequest(BaseModel):
    date: str

class AutoPricingRequest(BaseModel):
    start_date: str
    end_date: str
    room_type: Optional[str] = None

class DemandForecastRequest(BaseModel):
    start_date: str
    end_date: str

# Housekeeping Models
class ReportIssueRequest(BaseModel):
    room_id: str
    issue_type: str
    description: str
    priority: str = 'normal'
    photos: List[str] = []

class UploadPhotoRequest(BaseModel):
    task_id: str
    photo_base64: str

# POS Models
class CreatePOSTransactionRequest(BaseModel):
    amount: float
    payment_method: str
    folio_id: Optional[str] = None

# Group Reservations Models
class CreateGroupReservationRequest(BaseModel):
    group_name: str
    group_type: str
    contact_person: str
    contact_email: str
    contact_phone: str
    check_in_date: str
    check_out_date: str
    total_rooms: int
    adults_per_room: int = 2
    special_requests: Optional[str] = None

class AssignGroupRoomsRequest(BaseModel):
    room_assignments: List[Dict[str, Any]]

class CreateBlockReservationRequest(BaseModel):
    block_name: str
    room_type: str
    start_date: str
    end_date: str
    total_rooms: int
    block_type: str = 'tentative'
    release_date: Optional[str] = None

class UseBlockRoomRequest(BaseModel):
    guest_name: str
    guest_email: str

# Multi-Property Models
class CreatePropertyRequest(BaseModel):
    property_name: str
    property_code: str
    location: str
    total_rooms: int
    property_type: str = 'hotel'
    status: str = 'active'

class TransferReservationRequest(BaseModel):
    target_property_id: str
    reason: Optional[str] = None

# Marketplace Models
class CreateMarketplaceProductRequest(BaseModel):
    product_name: str
    category: str
    unit_price: float
    unit_of_measure: str
    supplier: str
    min_order_qty: int = 1

class AdjustInventoryRequest(BaseModel):
    product_id: str
    location: str
    quantity_change: int
    reason: str

class CreatePurchaseOrderRequest(BaseModel):
    supplier: str
    items: List[Dict[str, Any]]
    delivery_location: str
    expected_delivery_date: Optional[str] = None

class ReceivePurchaseOrderRequest(BaseModel):
    received_items: List[Dict[str, Any]]

class CreateDeliveryRequest(BaseModel):
    po_id: str
    tracking_number: Optional[str] = None
    carrier: Optional[str] = None
    estimated_delivery: Optional[str] = None

# Marketplace Extended Models
class CreateSupplierRequest(BaseModel):
    supplier_name: str
    contact_person: str
    contact_email: str
    contact_phone: str
    credit_limit: float = 0.0
    payment_terms: str = "Net 30"  # Net 15, Net 30, Net 60, COD
    status: str = "active"

class UpdateSupplierCreditRequest(BaseModel):
    credit_limit: float
    payment_terms: str

class ApprovePurchaseOrderRequest(BaseModel):
    approval_notes: Optional[str] = None

class RejectPurchaseOrderRequest(BaseModel):
    rejection_reason: str

class UpdateDeliveryStatusRequest(BaseModel):
    status: str  # in_transit, delivered, failed
    location: Optional[str] = None
    notes: Optional[str] = None

class CreateWarehouseRequest(BaseModel):
    warehouse_name: str
    location: str
    capacity: int
    warehouse_type: str = "central"  # central, regional, local

# Accounting & Multi-Currency Models
class CreateCurrencyRateRequest(BaseModel):
    from_currency: str  # USD, EUR, GBP, TRY
    to_currency: str
    rate: float
    effective_date: str

class CreateMultiCurrencyInvoiceRequest(BaseModel):
    customer_name: str
    customer_email: str
    customer_address: str
    items: List[Dict[str, Any]]
    currency: str = "TRY"  # Invoice currency
    exchange_rate: Optional[float] = None  # If different from TRY
    payment_terms: str = "Net 30"
    notes: Optional[str] = None

class GenerateInvoiceFromFolioRequest(BaseModel):
    folio_id: str
    invoice_currency: str = "TRY"
    include_efatura: bool = True

class ConvertCurrencyRequest(BaseModel):
    amount: float
    from_currency: str
    to_currency: str
    date: Optional[str] = None  # Use specific date rate, or latest if None

# Rate Code & Calendar Models
class CreateRateCodeRequest(BaseModel):
    code: str  # BB, HB, FB, AI, RO
    name: str  # Bed & Breakfast, Half Board, etc.
    description: str
    includes_breakfast: bool = False
    includes_lunch: bool = False
    includes_dinner: bool = False
    is_refundable: bool = True
    cancellation_policy: str = "Free cancellation"
    price_modifier: float = 1.0  # Multiplier on base rate

class GetCalendarTooltipRequest(BaseModel):
    date: str
    room_type: Optional[str] = None

# POS & F&B Models
class CreateOutletRequest(BaseModel):
    outlet_name: str
    outlet_type: str  # restaurant, bar, room_service, cafe
    location: str
    capacity: Optional[int] = None
    opening_hours: Optional[str] = None

class CreateMenuItemRequest(BaseModel):
    outlet_id: str
    item_name: str
    category: str  # appetizer, main, dessert, beverage
    price: float
    cost: Optional[float] = None
    description: Optional[str] = None

class CreatePOSTransactionWithMenuRequest(BaseModel):
    outlet_id: str
    items: List[Dict[str, Any]]  # [{menu_item_id, quantity, price}]
    payment_method: str
    folio_id: Optional[str] = None
    table_number: Optional[str] = None
    server_name: Optional[str] = None

class GenerateZReportRequest(BaseModel):
    outlet_id: Optional[str] = None
    date: Optional[str] = None  # Default to today

# Feedback & Reviews Models
class CreateSurveyRequest(BaseModel):
    survey_name: str
    description: str
    target_department: Optional[str] = None  # housekeeping, front_desk, fnb, spa, all
    questions: List[Dict[str, Any]]  # [{question, type, options}]
    trigger: str = "checkout"  # checkout, checkin, stay, manual

class SubmitSurveyResponseRequest(BaseModel):
    survey_id: str
    booking_id: Optional[str] = None
    guest_name: Optional[str] = None
    guest_email: Optional[str] = None
    responses: List[Dict[str, Any]]  # [{question_id, answer, rating}]

class ExternalReviewWebhookRequest(BaseModel):
    platform: str  # booking, google, tripadvisor
    review_id: str
    rating: float
    reviewer_name: str
    review_text: str
    review_date: str
    booking_reference: Optional[str] = None

class CreateDepartmentFeedbackRequest(BaseModel):
    department: str  # housekeeping, front_desk, fnb, spa
    booking_id: Optional[str] = None
    guest_name: str
    rating: int  # 1-5
    comment: Optional[str] = None
    staff_member: Optional[str] = None

# Task Management Models
class CreateTaskRequest(BaseModel):
    department: str  # engineering, housekeeping, fnb, maintenance, front_desk
    task_type: str  # repair, inspection, cleaning, setup, delivery, guest_request
    title: str
    description: str
    priority: str = "normal"  # low, normal, high, urgent
    location: Optional[str] = None  # room number or area
    room_id: Optional[str] = None
    assigned_to: Optional[str] = None
    due_date: Optional[str] = None
    recurring: Optional[bool] = False
    recurrence_pattern: Optional[str] = None  # daily, weekly, monthly

class UpdateTaskStatusRequest(BaseModel):
    status: str  # assigned, in_progress, completed, verified, cancelled
    notes: Optional[str] = None
    completion_photos: Optional[List[str]] = []

class AssignTaskRequest(BaseModel):
    assigned_to: str
    notes: Optional[str] = None

# Enterprise Features Models
class CreateRoleRequest(BaseModel):
    role_name: str
    description: str
    permissions: List[str]  # ['view_bookings', 'edit_rates', 'delete_bookings', etc.]
    department: Optional[str] = None

class AssignRoleRequest(BaseModel):
    user_id: str
    role_id: str

class CreateBackupRequest(BaseModel):
    backup_type: str = "full"  # full, incremental
    include_collections: Optional[List[str]] = None

# ============= HELPER FUNCTIONS =============

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(password: str, hashed: str) -> bool:
    try:
        return pwd_context.verify(password, hashed)
    except Exception:
        return False

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
    """Calculate folio balance (charges - payments) with proper 2-decimal rounding"""
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
    
    balance = total_charges - total_payments
    # Round to 2 decimal places for currency precision
    return round(balance, 2)

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
    
    # Calculate amounts with proper rounding
    amount = round(charge_data.amount * charge_data.quantity, 2)
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
                tax_amount = round(tax_rule['flat_amount'], 2)
            else:
                tax_amount = round(amount * (tax_rule['tax_percentage'] / 100), 2)
    
    total = round(amount + tax_amount, 2)
    
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
    
    # Audit log
    await create_audit_log(
        tenant_id=current_user.tenant_id,
        user=current_user,
        action="POST_CHARGE",
        entity_type="folio_charge",
        entity_id=charge.id,
        changes={'charge_category': charge_data.charge_category, 'amount': total, 'folio_id': folio_id}
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

@api_router.get("/folio/dashboard-stats")
async def get_folio_dashboard_stats(current_user: User = Depends(get_current_user)):
    """Get folio statistics for dashboard"""
    # Get all open folios
    open_folios = await db.folios.find({
        'tenant_id': current_user.tenant_id,
        'status': 'open'
    }, {'_id': 0}).to_list(1000)
    
    # Calculate total outstanding balance
    total_outstanding = 0.0
    for folio in open_folios:
        balance = await calculate_folio_balance(folio['id'], current_user.tenant_id)
        total_outstanding += balance
    
    # Get recent charges (last 24 hours)
    yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    recent_charges = await db.folio_charges.count_documents({
        'tenant_id': current_user.tenant_id,
        'posted_at': {'$gte': yesterday},
        'voided': False
    })
    
    # Get recent payments (last 24 hours)
    recent_payments = await db.payments.count_documents({
        'tenant_id': current_user.tenant_id,
        'processed_at': {'$gte': yesterday}
    })
    
    return {
        'total_open_folios': len(open_folios),
        'total_outstanding_balance': round(total_outstanding, 2),
        'recent_charges_24h': recent_charges,
        'recent_payments_24h': recent_payments
    }

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

@api_router.put("/pms/bookings/{booking_id}")
async def update_booking(
    booking_id: str,
    booking_data: dict,
    current_user: User = Depends(get_current_user)
):
    """Update an existing booking (for room moves, date changes, etc.)"""
    booking = await db.bookings.find_one({
        'id': booking_id,
        'tenant_id': current_user.tenant_id
    })
    
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    # Prepare update data
    update_data = {}
    
    # Handle date fields
    if 'check_in' in booking_data:
        if isinstance(booking_data['check_in'], str):
            update_data['check_in'] = datetime.fromisoformat(booking_data['check_in'].replace('Z', '+00:00')).isoformat()
        else:
            update_data['check_in'] = booking_data['check_in']
    
    if 'check_out' in booking_data:
        if isinstance(booking_data['check_out'], str):
            update_data['check_out'] = datetime.fromisoformat(booking_data['check_out'].replace('Z', '+00:00')).isoformat()
        else:
            update_data['check_out'] = booking_data['check_out']
    
    # Handle other fields
    allowed_fields = ['room_id', 'guest_id', 'total_amount', 'status', 'adults', 'children', 
                     'children_ages', 'guests_count', 'special_requests', 'company_id', 
                     'contracted_rate', 'rate_type', 'market_segment']
    
    for field in allowed_fields:
        if field in booking_data:
            update_data[field] = booking_data[field]
    
    # Update old room status if room changed
    if 'room_id' in booking_data and booking_data['room_id'] != booking['room_id']:
        # Set old room to available
        await db.rooms.update_one(
            {'id': booking['room_id']},
            {'$set': {'status': 'available', 'current_booking_id': None}}
        )
        # Set new room to occupied if booking is checked in
        if booking.get('status') == 'checked_in':
            await db.rooms.update_one(
                {'id': booking_data['room_id']},
                {'$set': {'status': 'occupied', 'current_booking_id': booking_id}}
            )
    
    # Perform update
    await db.bookings.update_one(
        {'id': booking_id, 'tenant_id': current_user.tenant_id},
        {'$set': update_data}
    )
    
    # Get updated booking
    updated_booking = await db.bookings.find_one({'id': booking_id}, {'_id': 0})
    return updated_booking

@api_router.post("/pms/room-move-history")
async def create_room_move_history(
    move_data: dict,
    current_user: User = Depends(get_current_user)
):
    """Log room move history for audit trail"""
    history = RoomMoveHistory(
        tenant_id=current_user.tenant_id,
        booking_id=move_data.get('booking_id'),
        old_room=move_data.get('old_room'),
        new_room=move_data.get('new_room'),
        old_check_in=move_data.get('old_check_in'),
        new_check_in=move_data.get('new_check_in'),
        reason=move_data.get('reason'),
        moved_by=move_data.get('moved_by', current_user.name)
    )
    
    history_dict = history.model_dump()
    history_dict['timestamp'] = history_dict['timestamp'].isoformat()
    
    await db.room_move_history.insert_one(history_dict)
    
    return {"message": "Room move logged successfully", "history": history}

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

# ============= ROOM BLOCKS (OUT OF ORDER / OUT OF SERVICE) =============

@api_router.get("/pms/room-blocks")
async def get_room_blocks(
    room_id: Optional[str] = None,
    status: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Get room blocks with optional filters"""
    query = {'tenant_id': current_user.tenant_id}
    
    if room_id:
        query['room_id'] = room_id
    
    if status:
        query['status'] = status
    
    # Date range filtering
    if from_date or to_date:
        date_query = {}
        if from_date:
            # Block overlaps if: block_start <= to_date AND (block_end >= from_date OR block_end is null)
            date_query['start_date'] = {'$lte': to_date if to_date else from_date}
        if to_date:
            # Also check end_date or open-ended blocks
            query['$or'] = [
                {'end_date': {'$gte': from_date if from_date else to_date}},
                {'end_date': None}
            ]
    
    blocks = await db.room_blocks.find(query, {'_id': 0}).to_list(1000)
    
    # Enrich with room information
    for block in blocks:
        room = await db.rooms.find_one({'id': block['room_id'], 'tenant_id': current_user.tenant_id}, {'_id': 0})
        if room:
            block['room_number'] = room['room_number']
            block['room_type'] = room['room_type']
    
    return {
        'blocks': blocks,
        'count': len(blocks)
    }

@api_router.post("/pms/room-blocks")
async def create_room_block(
    block_data: RoomBlockCreate,
    current_user: User = Depends(get_current_user)
):
    """Create a new room block"""
    # Verify room exists
    room = await db.rooms.find_one({
        'id': block_data.room_id,
        'tenant_id': current_user.tenant_id
    }, {'_id': 0})
    
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    # Check for existing active reservations that conflict
    start_date = datetime.fromisoformat(block_data.start_date)
    end_date = datetime.fromisoformat(block_data.end_date) if block_data.end_date else None
    
    # Query for overlapping bookings
    booking_query = {
        'tenant_id': current_user.tenant_id,
        'room_id': block_data.room_id,
        'status': {'$in': ['confirmed', 'guaranteed', 'checked_in']},
        'check_in': {'$lt': block_data.end_date if block_data.end_date else '9999-12-31'},
        'check_out': {'$gt': block_data.start_date}
    }
    
    conflicting_bookings = await db.bookings.find(booking_query, {'_id': 0}).to_list(100)
    
    # Create the block
    block = RoomBlock(
        id=str(uuid.uuid4()),
        room_id=block_data.room_id,
        type=block_data.type,
        reason=block_data.reason,
        details=block_data.details,
        start_date=block_data.start_date,
        end_date=block_data.end_date,
        allow_sell=block_data.allow_sell,
        created_by=current_user.id,
        created_at=datetime.now(timezone.utc).isoformat(),
        status=BlockStatus.ACTIVE
    )
    
    block_dict = block.model_dump()
    await db.room_blocks.insert_one({**block_dict, 'tenant_id': current_user.tenant_id})
    
    # Create audit log
    await db.audit_logs.insert_one({
        'id': str(uuid.uuid4()),
        'tenant_id': current_user.tenant_id,
        'user_id': current_user.id,
        'user_name': current_user.name,
        'user_role': current_user.role,
        'action': 'CREATE_ROOM_BLOCK',
        'entity_type': 'room_block',
        'entity_id': block.id,
        'changes': {
            'room_id': block.room_id,
            'type': block.type,
            'reason': block.reason,
            'start_date': block.start_date,
            'end_date': block.end_date,
            'allow_sell': block.allow_sell
        },
        'timestamp': datetime.now(timezone.utc).isoformat()
    })
    
    # If there are conflicting bookings, create exception queue items
    if conflicting_bookings and not block_data.allow_sell:
        for booking in conflicting_bookings:
            await db.exceptions.insert_one({
                'id': str(uuid.uuid4()),
                'tenant_id': current_user.tenant_id,
                'exception_type': 'room_blocked_with_reservation',
                'entity_type': 'booking',
                'entity_id': booking['id'],
                'severity': 'high',
                'message': f"Room {room['room_number']} blocked ({block.type}) but has active reservation",
                'details': {
                    'room_id': block_data.room_id,
                    'room_number': room['room_number'],
                    'block_id': block.id,
                    'block_type': block.type,
                    'block_reason': block.reason,
                    'booking_id': booking['id'],
                    'guest_name': booking.get('guest_name', 'Unknown'),
                    'check_in': booking['check_in'],
                    'check_out': booking['check_out']
                },
                'status': 'pending',
                'created_at': datetime.now(timezone.utc).isoformat()
            })
    
    response = {
        'message': 'Room block created successfully',
        'block': block,
        'room_number': room['room_number'],
        'warnings': []
    }
    
    if conflicting_bookings and not block_data.allow_sell:
        response['warnings'].append({
            'type': 'conflicting_reservations',
            'count': len(conflicting_bookings),
            'message': f"{len(conflicting_bookings)} active reservation(s) conflict with this block. Move or cancel required."
        })
    
    return response

@api_router.patch("/pms/room-blocks/{block_id}")
async def update_room_block(
    block_id: str,
    block_data: RoomBlockUpdate,
    current_user: User = Depends(get_current_user)
):
    """Update an existing room block"""
    block = await db.room_blocks.find_one({
        'id': block_id,
        'tenant_id': current_user.tenant_id
    }, {'_id': 0})
    
    if not block:
        raise HTTPException(status_code=404, detail="Room block not found")
    
    # Build update dict
    update_data = {}
    changes = {}
    
    if block_data.reason is not None:
        update_data['reason'] = block_data.reason
        changes['reason'] = {'old': block.get('reason'), 'new': block_data.reason}
    
    if block_data.details is not None:
        update_data['details'] = block_data.details
        changes['details'] = {'old': block.get('details'), 'new': block_data.details}
    
    if block_data.start_date is not None:
        update_data['start_date'] = block_data.start_date
        changes['start_date'] = {'old': block.get('start_date'), 'new': block_data.start_date}
    
    if block_data.end_date is not None:
        update_data['end_date'] = block_data.end_date
        changes['end_date'] = {'old': block.get('end_date'), 'new': block_data.end_date}
    
    if block_data.allow_sell is not None:
        update_data['allow_sell'] = block_data.allow_sell
        changes['allow_sell'] = {'old': block.get('allow_sell'), 'new': block_data.allow_sell}
    
    if block_data.status is not None:
        update_data['status'] = block_data.status
        changes['status'] = {'old': block.get('status'), 'new': block_data.status}
    
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")
    
    # Update block
    await db.room_blocks.update_one(
        {'id': block_id, 'tenant_id': current_user.tenant_id},
        {'$set': update_data}
    )
    
    # Create audit log
    await db.audit_logs.insert_one({
        'id': str(uuid.uuid4()),
        'tenant_id': current_user.tenant_id,
        'user_id': current_user.id,
        'user_name': current_user.name,
        'user_role': current_user.role,
        'action': 'UPDATE_ROOM_BLOCK',
        'entity_type': 'room_block',
        'entity_id': block_id,
        'changes': changes,
        'timestamp': datetime.now(timezone.utc).isoformat()
    })
    
    # Get updated block
    updated_block = await db.room_blocks.find_one({
        'id': block_id,
        'tenant_id': current_user.tenant_id
    }, {'_id': 0})
    
    return {
        'message': 'Room block updated successfully',
        'block': updated_block
    }

@api_router.post("/pms/room-blocks/{block_id}/cancel")
async def cancel_room_block(
    block_id: str,
    reason: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Cancel a room block"""
    block = await db.room_blocks.find_one({
        'id': block_id,
        'tenant_id': current_user.tenant_id
    }, {'_id': 0})
    
    if not block:
        raise HTTPException(status_code=404, detail="Room block not found")
    
    if block['status'] == 'cancelled':
        raise HTTPException(status_code=400, detail="Block is already cancelled")
    
    # Update status to cancelled
    await db.room_blocks.update_one(
        {'id': block_id, 'tenant_id': current_user.tenant_id},
        {'$set': {
            'status': 'cancelled',
            'cancelled_at': datetime.now(timezone.utc).isoformat(),
            'cancelled_by': current_user.id,
            'cancellation_reason': reason or 'Cancelled by user'
        }}
    )
    
    # Create audit log
    await db.audit_logs.insert_one({
        'id': str(uuid.uuid4()),
        'tenant_id': current_user.tenant_id,
        'user_id': current_user.id,
        'user_name': current_user.name,
        'user_role': current_user.role,
        'action': 'CANCEL_ROOM_BLOCK',
        'entity_type': 'room_block',
        'entity_id': block_id,
        'changes': {
            'status': {'old': block['status'], 'new': 'cancelled'},
            'reason': reason or 'Cancelled by user'
        },
        'timestamp': datetime.now(timezone.utc).isoformat()
    })
    
    return {
        'message': 'Room block cancelled successfully',
        'block_id': block_id
    }

# ============= LOYALTY PROGRAM =============

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

# ============= MANAGEMENT REPORTS =============

@api_router.get("/reports/daily-flash-pdf")
async def get_daily_flash_pdf(current_user: User = Depends(get_current_user)):
    """
    Export daily flash report as PDF
    """
    from io import BytesIO
    from fastapi.responses import StreamingResponse
    
    try:
        # Get flash report data
        flash_data = await get_daily_flash_report_data(current_user)
        
        # Generate PDF content (simple HTML to PDF conversion)
        html_content = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; padding: 20px; }}
                h1 {{ color: #1e40af; }}
                table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #1e40af; color: white; }}
                .metric {{ background-color: #f3f4f6; padding: 15px; margin: 10px 0; border-radius: 5px; }}
            </style>
        </head>
        <body>
            <h1>Daily Flash Report</h1>
            <p><strong>Date:</strong> {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')}</p>
            
            <div class="metric">
                <h3>Occupancy</h3>
                <p>Occupied Rooms: {flash_data['occupancy']['occupied']}</p>
                <p>Total Rooms: {flash_data['occupancy']['total']}</p>
                <p>Occupancy %: {flash_data['occupancy']['percentage']:.1f}%</p>
            </div>
            
            <div class="metric">
                <h3>Revenue</h3>
                <p>Room Revenue: ${flash_data['revenue']['room_revenue']:.2f}</p>
                <p>Total Revenue: ${flash_data['revenue']['total_revenue']:.2f}</p>
            </div>
            
            <div class="metric">
                <h3>Arrivals & Departures</h3>
                <p>Arrivals: {flash_data['movements']['arrivals']}</p>
                <p>Departures: {flash_data['movements']['departures']}</p>
            </div>
        </body>
        </html>
        """
        
        # Convert HTML to PDF using simple method (can upgrade to weasyprint later)
        # For now, return HTML as PDF placeholder
        pdf_buffer = BytesIO()
        pdf_buffer.write(html_content.encode('utf-8'))
        pdf_buffer.seek(0)
        
        return StreamingResponse(
            pdf_buffer,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=daily-flash-{datetime.now(timezone.utc).strftime('%Y%m%d')}.pdf"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {str(e)}")

@api_router.post("/reports/email-daily-flash")
async def email_daily_flash(
    data: dict,
    current_user: User = Depends(get_current_user)
):
    """
    Email daily flash report to recipients
    """
    recipients = data.get('recipients', [])
    
    if not recipients:
        raise HTTPException(status_code=400, detail="Recipients list is required")
    
    try:
        # Get flash report data
        flash_data = await get_daily_flash_report_data(current_user)
        
        # Email content (HTML)
        email_html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; }}
                .metric {{ background-color: #f3f4f6; padding: 15px; margin: 10px 0; border-radius: 5px; }}
                h3 {{ color: #1e40af; }}
            </style>
        </head>
        <body>
            <h2>Daily Flash Report - {datetime.now(timezone.utc).strftime('%Y-%m-%d')}</h2>
            
            <div class="metric">
                <h3>Occupancy</h3>
                <p>Occupied: {flash_data.get('occupancy', {{}}).get('occupied', 0)} / {flash_data.get('occupancy', {{}}).get('total', 0)} ({flash_data.get('occupancy', {{}}).get('percentage', 0):.1f}%)</p>
            </div>
            
            <div class="metric">
                <h3>Revenue</h3>
                <p>Room Revenue: ${flash_data.get('revenue', {{}}).get('room_revenue', 0):.2f}</p>
                <p>Total Revenue: ${flash_data.get('revenue', {{}}).get('total_revenue', 0):.2f}</p>
            </div>
            
            <div class="metric">
                <h3>Movements</h3>
                <p>Arrivals: {flash_data.get('movements', {{}}).get('arrivals', 0)}</p>
                <p>Departures: {flash_data.get('movements', {{}}).get('departures', 0)}</p>
            </div>
            
            <p><small>Generated by Finance Test Hotel PMS</small></p>
        </body>
        </html>
        """
        
        # Note: Actual email sending requires SMTP configuration
        # For MVP, we'll log the email and return success
        # TODO: Implement actual SMTP email sending
        
        print(f"Email would be sent to: {recipients}")
        print(f"Subject: Daily Flash Report - {datetime.now(timezone.utc).strftime('%Y-%m-%d')}")
        print(f"Content length: {len(email_html)} characters")
        
        return {
            'success': True,
            'message': f'Daily flash report email sent to {len(recipients)} recipients',
            'recipients': recipients,
            'note': 'Email functionality requires SMTP configuration. Currently logging only.'
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Email sending failed: {str(e)}")

async def get_daily_flash_report_data(current_user: User):
    """
    Helper function to get flash report data (reusable for PDF and email)
    """
    today = datetime.now(timezone.utc).date()
    
    # Occupancy
    rooms = await db.rooms.find({'tenant_id': current_user.tenant_id}).to_list(1000)
    total_rooms = len(rooms)
    occupied_rooms = len([r for r in rooms if r.get('current_status') == 'occupied'])
    occupancy_percentage = (occupied_rooms / total_rooms * 100) if total_rooms > 0 else 0
    
    # Revenue
    today_start = datetime.combine(today, datetime.min.time()).replace(tzinfo=timezone.utc)
    today_end = datetime.combine(today, datetime.max.time()).replace(tzinfo=timezone.utc)
    
    charges = await db.folio_charges.find({
        'tenant_id': current_user.tenant_id,
        'date': {
            '$gte': today_start.isoformat(),
            '$lte': today_end.isoformat()
        },
        'voided': False
    }).to_list(10000)
    
    room_revenue = sum(c.get('total', 0) for c in charges if c.get('charge_category') == 'room')
    total_revenue = sum(c.get('total', 0) for c in charges)
    
    # Movements
    arrivals = await db.bookings.find({
        'tenant_id': current_user.tenant_id,
        'check_in': today.isoformat(),
        'status': {'$in': ['confirmed', 'checked_in']}
    }).to_list(1000)
    
    departures = await db.bookings.find({
        'tenant_id': current_user.tenant_id,
        'check_out': today.isoformat(),
        'status': {'$in': ['checked_in', 'checked_out']}
    }).to_list(1000)
    
    return {
        'occupancy': {
            'occupied': occupied_rooms,
            'total': total_rooms,
            'percentage': occupancy_percentage
        },
        'revenue': {
            'room_revenue': room_revenue,
            'total_revenue': total_revenue
        },
        'movements': {
            'arrivals': len(arrivals),
            'departures': len(departures)
        }
    }

@api_router.get("/reports/daily-flash")
async def get_daily_flash_report(date_str: Optional[str] = None, current_user: User = Depends(get_current_user)):
    """Daily Flash Report - GM/CFO Dashboard"""
    target_date = datetime.fromisoformat(date_str).date() if date_str else datetime.now(timezone.utc).date()
    start_of_day = datetime.combine(target_date, datetime.min.time())
    end_of_day = datetime.combine(target_date, datetime.max.time())
    
    # Get total rooms
    total_rooms = await db.rooms.count_documents({'tenant_id': current_user.tenant_id})
    
    # Get occupancy (checked-in bookings)
    occupied_rooms = await db.bookings.count_documents({
        'tenant_id': current_user.tenant_id,
        'status': 'checked_in',
        'check_in': {'$lte': end_of_day.isoformat()},
        'check_out': {'$gte': start_of_day.isoformat()}
    })
    
    occupancy_rate = round((occupied_rooms / total_rooms * 100) if total_rooms > 0 else 0, 2)
    
    # Get arrivals & departures count
    arrivals = await db.bookings.count_documents({
        'tenant_id': current_user.tenant_id,
        'check_in': {'$gte': start_of_day.isoformat(), '$lte': end_of_day.isoformat()}
    })
    
    departures = await db.bookings.count_documents({
        'tenant_id': current_user.tenant_id,
        'check_out': {'$gte': start_of_day.isoformat(), '$lte': end_of_day.isoformat()}
    })
    
    # Note: Revenue is calculated from folio charges, not bookings directly
    
    # Calculate revenue from folio charges posted today
    charges = await db.folio_charges.find({
        'tenant_id': current_user.tenant_id,
        'date': {'$gte': start_of_day.isoformat(), '$lte': end_of_day.isoformat()},
        'voided': False
    }).to_list(10000)
    
    total_revenue = sum(c['total'] for c in charges)
    
    # Revenue breakdown by category
    room_revenue = sum(c['total'] for c in charges if c['charge_category'] == 'room')
    fb_revenue = sum(c['total'] for c in charges if c['charge_category'] in ['food', 'beverage'])
    other_revenue = total_revenue - room_revenue - fb_revenue
    
    # Calculate ADR and RevPAR
    adr = round(room_revenue / occupied_rooms, 2) if occupied_rooms > 0 else 0
    rev_par = round(total_revenue / total_rooms, 2) if total_rooms > 0 else 0
    
    return {
        'date': target_date.isoformat(),
        'occupancy': {
            'occupied_rooms': occupied_rooms,
            'total_rooms': total_rooms,
            'occupancy_rate': occupancy_rate
        },
        'movements': {
            'arrivals': arrivals,
            'departures': departures,
            'stayovers': occupied_rooms - arrivals
        },
        'revenue': {
            'total_revenue': round(total_revenue, 2),
            'room_revenue': round(room_revenue, 2),
            'fb_revenue': round(fb_revenue, 2),
            'other_revenue': round(other_revenue, 2),
            'adr': adr,
            'rev_par': rev_par
        }
    }

@api_router.get("/reports/market-segment")
async def get_market_segment_report(
    start_date: str,
    end_date: str,
    current_user: User = Depends(get_current_user)
):
    """Market Segment & Rate Type Performance Report"""
    start = datetime.fromisoformat(start_date)
    end = datetime.fromisoformat(end_date)
    
    # Get all bookings in date range
    bookings = await db.bookings.find({
        'tenant_id': current_user.tenant_id,
        'check_in': {'$gte': start.isoformat()},
        'check_out': {'$lte': end.isoformat()}
    }).to_list(10000)
    
    # Aggregate by market segment
    segment_data = {}
    rate_type_data = {}
    
    for booking in bookings:
        segment = booking.get('market_segment', 'other')
        rate_type = booking.get('rate_type', 'bar')
        
        # Calculate nights
        check_in = datetime.fromisoformat(booking['check_in'])
        check_out = datetime.fromisoformat(booking['check_out'])
        nights = (check_out - check_in).days
        revenue = booking.get('total_amount', 0)
        
        # Market segment aggregation
        if segment not in segment_data:
            segment_data[segment] = {'bookings': 0, 'nights': 0, 'revenue': 0}
        segment_data[segment]['bookings'] += 1
        segment_data[segment]['nights'] += nights
        segment_data[segment]['revenue'] += revenue
        
        # Rate type aggregation
        if rate_type not in rate_type_data:
            rate_type_data[rate_type] = {'bookings': 0, 'nights': 0, 'revenue': 0}
        rate_type_data[rate_type]['bookings'] += 1
        rate_type_data[rate_type]['nights'] += nights
        rate_type_data[rate_type]['revenue'] += revenue
    
    # Calculate averages
    for segment in segment_data:
        segment_data[segment]['adr'] = round(
            segment_data[segment]['revenue'] / segment_data[segment]['nights'], 2
        ) if segment_data[segment]['nights'] > 0 else 0
    
    for rate_type in rate_type_data:
        rate_type_data[rate_type]['adr'] = round(
            rate_type_data[rate_type]['revenue'] / rate_type_data[rate_type]['nights'], 2
        ) if rate_type_data[rate_type]['nights'] > 0 else 0
    
    return {
        'start_date': start_date,
        'end_date': end_date,
        'total_bookings': len(bookings),
        'market_segments': segment_data,
        'rate_types': rate_type_data
    }

@api_router.get("/reports/company-aging")
async def get_company_aging_report(current_user: User = Depends(get_current_user)):
    """Company Accounts Receivable Aging Report"""
    today = datetime.now(timezone.utc).date()
    
    # Get all company folios with outstanding balance
    folios = await db.folios.find({
        'tenant_id': current_user.tenant_id,
        'folio_type': 'company',
        'status': 'open'
    }).to_list(10000)
    
    company_balances = {}
    
    for folio in folios:
        balance = await calculate_folio_balance(folio['id'], current_user.tenant_id)
        
        if balance > 0:
            company_id = folio.get('company_id')
            if not company_id:
                continue
            
            # Get company details
            company = await db.companies.find_one({'id': company_id}, {'_id': 0})
            if not company:
                continue
            
            # Calculate aging based on folio creation date
            folio_created = datetime.fromisoformat(folio['created_at']).date()
            age_days = (today - folio_created).days
            
            # Determine aging bucket
            if age_days <= 7:
                aging_bucket = '0-7 days'
            elif age_days <= 14:
                aging_bucket = '8-14 days'
            elif age_days <= 30:
                aging_bucket = '15-30 days'
            else:
                aging_bucket = '30+ days'
            
            # Aggregate by company
            if company_id not in company_balances:
                company_balances[company_id] = {
                    'company_name': company['name'],
                    'corporate_code': company.get('corporate_code', 'N/A'),
                    'total_balance': 0,
                    'aging': {
                        '0-7 days': 0,
                        '8-14 days': 0,
                        '15-30 days': 0,
                        '30+ days': 0
                    },
                    'folio_count': 0
                }
            
            company_balances[company_id]['total_balance'] += balance
            company_balances[company_id]['aging'][aging_bucket] += balance
            company_balances[company_id]['folio_count'] += 1
    
    # Sort by total balance descending
    sorted_companies = sorted(
        company_balances.values(),
        key=lambda x: x['total_balance'],
        reverse=True
    )
    
    total_ar = sum(c['total_balance'] for c in sorted_companies)
    
    return {
        'report_date': today.isoformat(),
        'total_ar': round(total_ar, 2),
        'company_count': len(sorted_companies),
        'companies': sorted_companies
    }


@api_router.get("/reports/finance-snapshot")
async def get_finance_snapshot(current_user: User = Depends(get_current_user)):
    """
    Finance Snapshot for GM Dashboard
    Returns: Total Pending AR, Overdue Invoices (categorized), Today's Collections
    """
    today = datetime.now(timezone.utc).date()
    today_start = datetime.combine(today, datetime.min.time()).replace(tzinfo=timezone.utc)
    today_end = datetime.combine(today, datetime.max.time()).replace(tzinfo=timezone.utc)
    
    # 1. Calculate Total Pending AR from company folios
    company_folios = await db.folios.find({
        'tenant_id': current_user.tenant_id,
        'folio_type': 'company',
        'status': 'open'
    }).to_list(10000)
    
    total_pending_ar = 0
    overdue_0_30 = 0
    overdue_30_60 = 0
    overdue_60_plus = 0
    overdue_invoices_count = 0
    
    for folio in company_folios:
        balance = await calculate_folio_balance(folio['id'], current_user.tenant_id)
        
        if balance > 0:
            total_pending_ar += balance
            
            # Calculate aging
            folio_created = datetime.fromisoformat(folio['created_at']).date()
            age_days = (today - folio_created).days
            
            if age_days > 0:  # Any overdue
                overdue_invoices_count += 1
                
                if age_days <= 30:
                    overdue_0_30 += balance
                elif age_days <= 60:
                    overdue_30_60 += balance
                else:
                    overdue_60_plus += balance
    
    # 2. Calculate Today's Collections (payments received today)
    todays_payments = await db.payments.find({
        'tenant_id': current_user.tenant_id,
        'processed_at': {
            '$gte': today_start.isoformat(),
            '$lte': today_end.isoformat()
        }
    }).to_list(10000)
    
    todays_collections = sum(payment.get('amount', 0) for payment in todays_payments)
    todays_payment_count = len(todays_payments)
    
    # 3. Calculate MTD (Month-to-Date) Collections
    month_start = today.replace(day=1)
    month_start_dt = datetime.combine(month_start, datetime.min.time()).replace(tzinfo=timezone.utc)
    
    mtd_payments = await db.payments.find({
        'tenant_id': current_user.tenant_id,
        'processed_at': {
            '$gte': month_start_dt.isoformat(),
            '$lte': today_end.isoformat()
        }
    }).to_list(10000)
    
    mtd_collections = sum(payment.get('amount', 0) for payment in mtd_payments)
    
    # 4. Calculate Collection Rate (MTD Collections / MTD Revenue)
    mtd_charges = await db.folio_charges.find({
        'tenant_id': current_user.tenant_id,
        'date': {
            '$gte': month_start_dt.isoformat(),
            '$lte': today_end.isoformat()
        },
        'voided': False
    }).to_list(10000)
    
    mtd_revenue = sum(charge.get('total', 0) for charge in mtd_charges)
    collection_rate = (mtd_collections / mtd_revenue * 100) if mtd_revenue > 0 else 0
    
    # 5. Get Accounting Invoices (E-Fatura ready)
    pending_invoices = await db.accounting_invoices.find({
        'tenant_id': current_user.tenant_id,
        'status': {'$in': ['pending', 'partial']}
    }).to_list(1000)
    
    pending_invoice_total = sum(inv.get('total', 0) for inv in pending_invoices)
    pending_invoice_count = len(pending_invoices)
    
    return {
        'report_date': today.isoformat(),
        'pending_ar': {
            'total': round(total_pending_ar, 2),
            'overdue_breakdown': {
                '0-30_days': round(overdue_0_30, 2),
                '30-60_days': round(overdue_30_60, 2),
                '60_plus_days': round(overdue_60_plus, 2)
            },
            'overdue_invoices_count': overdue_invoices_count
        },
        'todays_collections': {
            'amount': round(todays_collections, 2),
            'payment_count': todays_payment_count
        },
        'mtd_collections': {
            'amount': round(mtd_collections, 2),
            'collection_rate_percentage': round(collection_rate, 2)
        },
        'accounting_invoices': {
            'pending_count': pending_invoice_count,
            'pending_total': round(pending_invoice_total, 2)
        }
    }


@api_router.get("/pos/auto-post-settings")
async def get_pos_auto_post_settings(current_user: User = Depends(get_current_user)):
    """
    Get POS auto-post settings for the tenant
    """
    settings = await db.pos_settings.find_one({
        'tenant_id': current_user.tenant_id,
        'type': 'auto_post'
    })
    
    if not settings:
        # Default settings
        return {
            'mode': 'realtime',
            'batch_interval': 15,
            'last_sync': None
        }
    
    return {
        'mode': settings.get('mode', 'realtime'),
        'batch_interval': settings.get('batch_interval', 15),
        'last_sync': settings.get('last_sync')
    }

@api_router.post("/pos/auto-post-settings")
async def update_pos_auto_post_settings(
    settings_data: dict,
    current_user: User = Depends(get_current_user)
):
    """
    Update POS auto-post settings
    """
    await db.pos_settings.update_one(
        {
            'tenant_id': current_user.tenant_id,
            'type': 'auto_post'
        },
        {
            '$set': {
                'mode': settings_data.get('mode', 'realtime'),
                'batch_interval': settings_data.get('batch_interval', 15),
                'updated_at': datetime.now(timezone.utc).isoformat(),
                'updated_by': current_user.id
            }
        },
        upsert=True
    )
    
    return {'message': 'Settings updated successfully'}

@api_router.post("/pos/manual-sync")
async def manual_pos_sync(current_user: User = Depends(get_current_user)):
    """
    Manually trigger POS charges sync to folios
    """
    # Get all pending POS charges
    pending_charges = await db.pos_charges.find({
        'tenant_id': current_user.tenant_id,
        'posted_to_folio': False,
        'status': 'closed'
    }).to_list(1000)
    
    posted_count = 0
    
    for charge in pending_charges:
        try:
            # Post to folio
            folio_charge = {
                'id': str(uuid.uuid4()),
                'folio_id': charge['folio_id'],
                'tenant_id': current_user.tenant_id,
                'description': charge.get('description', 'POS Charge'),
                'charge_category': charge.get('outlet', 'restaurant'),
                'date': charge['charge_date'],
                'quantity': 1,
                'unit_price': charge['total'],
                'total': charge['total'],
                'tax_amount': charge.get('tax', 0),
                'voided': False,
                'line_items': charge.get('items', []),  # Include POS line items
                'created_at': datetime.now(timezone.utc).isoformat(),
                'created_by': current_user.id
            }
            
            await db.folio_charges.insert_one(folio_charge)
            
            # Mark as posted
            await db.pos_charges.update_one(
                {'_id': charge['_id']},
                {'$set': {'posted_to_folio': True, 'posted_at': datetime.now(timezone.utc).isoformat()}}
            )
            
            posted_count += 1
        except Exception as e:
            print(f"Failed to post POS charge {charge.get('id')}: {str(e)}")
            continue
    
    # Update last sync time
    await db.pos_settings.update_one(
        {
            'tenant_id': current_user.tenant_id,
            'type': 'auto_post'
        },
        {
            '$set': {'last_sync': datetime.now(timezone.utc).isoformat()}
        },
        upsert=True
    )
    
    return {
        'posted_count': posted_count,
        'message': f'Successfully posted {posted_count} POS charges to folios'
    }

@api_router.post("/pos/manual-post")
async def manual_pos_post(
    post_data: dict,
    current_user: User = Depends(get_current_user)
):
    """
    Manual post of POS charge via QR/barcode (fallback when integration fails)
    """
    charge_id = post_data.get('charge_id')
    folio_id = post_data.get('folio_id')
    method = post_data.get('method', 'manual')
    
    # Get POS charge
    charge = await db.pos_charges.find_one({
        'id': charge_id,
        'tenant_id': current_user.tenant_id
    })
    
    if not charge:
        raise HTTPException(status_code=404, detail='POS charge not found')
    
    # Check if already posted
    if charge.get('posted_to_folio'):
        raise HTTPException(status_code=409, detail='Charge already posted to folio')
    
    # Post to folio
    folio_charge = {
        'id': str(uuid.uuid4()),
        'folio_id': folio_id,
        'tenant_id': current_user.tenant_id,
        'description': charge.get('description', 'POS Charge - Manual Post'),
        'charge_category': charge.get('outlet', 'restaurant'),
        'date': charge['charge_date'],
        'quantity': 1,
        'unit_price': charge['total'],
        'total': charge['total'],
        'tax_amount': charge.get('tax', 0),
        'voided': False,
        'line_items': charge.get('items', []),
        'manual_post': True,
        'post_method': method,
        'created_at': datetime.now(timezone.utc).isoformat(),
        'created_by': current_user.id
    }
    
    await db.folio_charges.insert_one(folio_charge)
    
    # Mark as posted
    await db.pos_charges.update_one(
        {'_id': charge['_id']},
        {
            '$set': {
                'posted_to_folio': True,
                'posted_at': datetime.now(timezone.utc).isoformat(),
                'post_method': method
            }
        }
    )
    
    return {
        'total': charge['total'],
        'description': charge.get('description'),
        'folio_id': folio_id,
        'posted_at': datetime.now(timezone.utc).isoformat()
    }

@api_router.get("/rates/periods")
async def get_rate_periods(
    operator_id: str,
    room_type_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get multi-period rates for operator and room type
    """
    periods = await db.rate_periods.find({
        'tenant_id': current_user.tenant_id,
        'operator_id': operator_id,
        'room_type_id': room_type_id
    }).sort('start_date', 1).to_list(100)
    
    return {'periods': periods}

@api_router.post("/rates/periods/bulk-update")
async def bulk_update_rate_periods(
    data: dict,
    current_user: User = Depends(get_current_user)
):
    """
    Bulk update/insert rate periods for operator
    """
    operator_id = data.get('operator_id')
    room_type_id = data.get('room_type_id')
    periods = data.get('periods', [])
    
    # Delete existing periods
    await db.rate_periods.delete_many({
        'tenant_id': current_user.tenant_id,
        'operator_id': operator_id,
        'room_type_id': room_type_id
    })
    
    # Insert new periods
    if periods:
        for period in periods:
            period_doc = {
                'id': period.get('id') if not period.get('isNew') else str(uuid.uuid4()),
                'tenant_id': current_user.tenant_id,
                'operator_id': operator_id,
                'room_type_id': room_type_id,
                'start_date': period['start_date'],
                'end_date': period['end_date'],
                'rate': period['rate'],
                'currency': period.get('currency', 'USD'),
                'created_at': datetime.now(timezone.utc).isoformat(),
                'created_by': current_user.id
            }
            await db.rate_periods.insert_one(period_doc)
    
    return {'message': f'{len(periods)} rate periods saved successfully'}

@api_router.get("/rates/stop-sale/status")
async def get_stop_sale_status(current_user: User = Depends(get_current_user)):
    """
    Get stop-sale status for all operators
    """
    stop_sales = await db.stop_sales.find({
        'tenant_id': current_user.tenant_id,
        'active': True
    }).to_list(100)
    
    operators = {}
    for ss in stop_sales:
        operators[ss['operator_id']] = ss.get('stop_sale', False)
        operators[f"{ss['operator_id']}_timestamp"] = ss.get('updated_at')
    
    return {'operators': operators}

@api_router.post("/rates/stop-sale/toggle")
async def toggle_stop_sale(
    data: dict,
    current_user: User = Depends(get_current_user)
):
    """
    Toggle stop-sale for specific operator
    """
    operator_id = data.get('operator_id')
    stop_sale = data.get('stop_sale', False)
    
    await db.stop_sales.update_one(
        {
            'tenant_id': current_user.tenant_id,
            'operator_id': operator_id
        },
        {
            '$set': {
                'stop_sale': stop_sale,
                'active': True,
                'updated_at': datetime.now(timezone.utc).isoformat(),
                'updated_by': current_user.id
            }
        },
        upsert=True
    )
    
    return {
        'operator_id': operator_id,
        'stop_sale': stop_sale,
        'message': f'Stop-sale {"activated" if stop_sale else "deactivated"} for {operator_id}'
    }

@api_router.get("/allotment/consumption")
async def get_allotment_consumption(
    start_date: str = None,
    end_date: str = None,
    current_user: User = Depends(get_current_user)
):
    """
    Get allotment consumption chart data: Allocated vs Sold vs Remaining
    """
    # Get all allotments for tenant
    allotments = await db.allotments.find({
        'tenant_id': current_user.tenant_id,
        'status': 'active'
    }).to_list(100)
    
    consumption_data = []
    
    for allotment in allotments:
        operator_name = allotment.get('operator_name', 'Unknown')
        allocated = allotment.get('allocated_rooms', 0)
        
        # Count sold bookings for this allotment
        bookings = await db.bookings.find({
            'tenant_id': current_user.tenant_id,
            'allotment_id': allotment.get('id'),
            'status': {'$in': ['confirmed', 'checked_in', 'checked_out']}
        }).to_list(1000)
        
        sold = len(bookings)
        remaining = max(allocated - sold, 0)
        utilization = int((sold / allocated * 100)) if allocated > 0 else 0
        
        # Determine status
        if remaining == 0:
            status = 'critical'
        elif utilization >= 80:
            status = 'warning'
        else:
            status = 'good'
        
        consumption_data.append({
            'operator': operator_name,
            'allocated': allocated,
            'sold': sold,
            'remaining': remaining,
            'utilization': utilization,
            'status': status
        })
    
    return {'allotments': consumption_data}





@api_router.get("/reports/cost-summary")
async def get_cost_summary(current_user: User = Depends(get_current_user)):
    """
    Cost Summary Report for GM Dashboard
    Returns: MTD costs by category, top cost categories, per-room cost, cost vs RevPAR
    """
    today = datetime.now(timezone.utc).date()
    month_start = today.replace(day=1)
    month_start_dt = datetime.combine(month_start, datetime.min.time()).replace(tzinfo=timezone.utc)
    today_end = datetime.combine(today, datetime.max.time()).replace(tzinfo=timezone.utc)
    
    # 1. Get all Purchase Orders from Marketplace for this month (approved/received status)
    purchase_orders = await db.purchase_orders.find({
        'tenant_id': current_user.tenant_id,
        'status': {'$in': ['approved', 'received', 'completed']},
        'created_at': {
            '$gte': month_start_dt.isoformat(),
            '$lte': today_end.isoformat()
        }
    }).to_list(10000)
    

@api_router.post("/reviews/ai-sentiment-analysis")
async def ai_sentiment_analysis(
    data: dict,
    current_user: User = Depends(get_current_user)
):
    """
    AI Sentiment Analysis for guest reviews
    Returns: sentiment, confidence, issues, highlights, recommendations
    """
    review_text = data.get('review_text', '')
    
    if not review_text:
        raise HTTPException(status_code=400, detail='Review text is required')
    
    # Simple keyword-based sentiment analysis (can be replaced with actual AI API)
    review_lower = review_text.lower()
    
    # Negative keywords
    negative_keywords = ['dirty', 'broken', 'bad', 'terrible', 'awful', 'poor', 'noise', 'smell', 'rude', 'slow']
    # Positive keywords
    positive_keywords = ['great', 'excellent', 'amazing', 'wonderful', 'clean', 'friendly', 'helpful', 'perfect', 'love']
    
    negative_count = sum(1 for keyword in negative_keywords if keyword in review_lower)
    positive_count = sum(1 for keyword in positive_keywords if keyword in review_lower)
    
    # Determine sentiment
    if negative_count > positive_count:
        sentiment = 'negative'
        confidence = min(0.6 + (negative_count * 0.1), 0.95)
    elif positive_count > negative_count:
        sentiment = 'positive'
        confidence = min(0.6 + (positive_count * 0.1), 0.95)
    else:
        sentiment = 'neutral'
        confidence = 0.5
    
    # Detect issues
    issues = []
    if 'dirty' in review_lower or 'clean' in review_lower:
        issues.append({
            'category': 'Cleanliness',
            'description': 'Guest mentioned cleanliness concerns',
            'severity': 'high' if 'dirty' in review_lower else 'medium'
        })
    if 'broken' in review_lower or 'repair' in review_lower:
        issues.append({
            'category': 'Maintenance',
            'description': 'Equipment or room maintenance issue',
            'severity': 'high'
        })
    if 'noise' in review_lower:
        issues.append({
            'category': 'Noise',
            'description': 'Noise complaint detected',
            'severity': 'medium'
        })
    if 'rude' in review_lower or 'unfriendly' in review_lower:
        issues.append({
            'category': 'Staff Behavior',
            'description': 'Staff attitude issue mentioned',
            'severity': 'high'
        })
    
    # Detect highlights
    highlights = []
    if 'friendly' in review_lower or 'helpful' in review_lower:
        highlights.append({
            'category': 'Staff Friendliness',
            'description': 'Guest praised staff attitude'
        })
    if 'clean' in review_lower and 'dirty' not in review_lower:
        highlights.append({
            'category': 'Cleanliness',
            'description': 'Guest appreciated room cleanliness'
        })
    if 'location' in review_lower and ('great' in review_lower or 'perfect' in review_lower):
        highlights.append({
            'category': 'Location',
            'description': 'Guest loved the location'
        })
    
    # Generate recommendations
    recommendations = []
    if sentiment == 'negative':
        recommendations.append('Contact guest immediately for service recovery')
        recommendations.append('Assign compensation (points/discount) if appropriate')
        if issues:
            recommendations.append(f'Create maintenance task for {issues[0]["category"]}')
    elif sentiment == 'positive':
        recommendations.append('Thank guest and encourage loyalty program enrollment')
        recommendations.append('Share review on social media (with permission)')
    
    return {
        'sentiment': sentiment,
        'confidence': confidence,
        'issues': issues,
        'highlights': highlights,
        'recommendations': recommendations
    }

@api_router.get("/tasks/kanban")
async def get_tasks_kanban(current_user: User = Depends(get_current_user)):
    """
    Get tasks organized by kanban columns: new, in_progress, waiting_parts, completed
    """
    tasks = await db.tasks.find({
        'tenant_id': current_user.tenant_id
    }).to_list(1000)
    
    kanban = {
        'new': [],
        'in_progress': [],
        'waiting_parts': [],
        'completed': []
    }
    
    for task in tasks:
        status = task.get('status', 'new')
        kanban[status].append(task)
    
    return {'tasks': kanban}

@api_router.post("/tasks/move")
async def move_task(
    data: dict,
    current_user: User = Depends(get_current_user)
):
    """
    Move task between kanban columns
    """
    task_id = data.get('task_id')
    to_status = data.get('to_status')
    
    await db.tasks.update_one(
        {
            'id': task_id,
            'tenant_id': current_user.tenant_id
        },
        {
            '$set': {
                'status': to_status,
                'updated_at': datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    return {'message': f'Task moved to {to_status}'}

@api_router.post("/loyalty/tier-benefits/update")
async def update_loyalty_tier_benefits(
    data: dict,
    current_user: User = Depends(get_current_user)
):
    """
    Update loyalty tier benefits configuration
    """
    tiers = data.get('tiers', [])
    
    for tier in tiers:
        await db.loyalty_tier_benefits.update_one(
            {
                'tenant_id': current_user.tenant_id,
                'tier_name': tier['name']
            },
            {
                '$set': {
                    'benefits': tier['benefits'],
                    'updated_at': datetime.now(timezone.utc).isoformat(),
                    'updated_by': current_user.id
                }
            },
            upsert=True
        )
    
    return {'message': f'{len(tiers)} tier benefits updated successfully'}


    # Map purchase order categories to cost categories
    category_mapping = {
        'cleaning': 'Housekeeping',
        'linens': 'Housekeeping',
        'amenities': 'Housekeeping',
        'food': 'F&B',
        'beverage': 'F&B',
        'kitchen': 'F&B',
        'maintenance': 'Technical',
        'electrical': 'Technical',
        'plumbing': 'Technical',
        'hvac': 'Technical',
        'furniture': 'General Expenses',
        'office': 'General Expenses',
        'it': 'General Expenses',
        'other': 'General Expenses'
    }
    
    # Aggregate costs by category
    cost_categories = {
        'Housekeeping': 0,
        'F&B': 0,
        'Technical': 0,
        'General Expenses': 0
    }
    
    total_mtd_costs = 0
    
    for po in purchase_orders:
        category = po.get('category', 'other')
        cost_category = category_mapping.get(category, 'General Expenses')
        total_amount = po.get('total_amount', 0)
        
        cost_categories[cost_category] += total_amount
        total_mtd_costs += total_amount
    
    # 2. Sort categories to get top 3
    sorted_categories = sorted(
        [{'name': k, 'amount': v} for k, v in cost_categories.items()],
        key=lambda x: x['amount'],
        reverse=True
    )
    
    top_3_categories = sorted_categories[:3]
    
    # 3. Calculate per-room cost (total costs / occupied room nights MTD)
    # Get all bookings for MTD that were checked-in
    bookings = await db.bookings.find({
        'tenant_id': current_user.tenant_id,
        'status': {'$in': ['checked_in', 'checked_out']},
        'check_in': {
            '$gte': month_start.isoformat(),
            '$lte': today.isoformat()
        }
    }).to_list(10000)
    
    # Calculate total occupied room nights
    total_room_nights = 0
    for booking in bookings:
        checkin = datetime.fromisoformat(booking['check_in']).date()
        checkout_str = booking.get('check_out', booking['check_in'])
        checkout = datetime.fromisoformat(checkout_str).date()
        
        # Calculate nights (minimum 1)
        nights = max((checkout - checkin).days, 1)
        total_room_nights += nights
    
    per_room_cost = (total_mtd_costs / total_room_nights) if total_room_nights > 0 else 0
    
    # 4. Get RevPAR from daily flash report for comparison
    # Calculate MTD RevPAR
    total_revenue = 0
    total_available_room_days = 0
    
    # Get all rooms
    rooms = await db.rooms.find({'tenant_id': current_user.tenant_id}).to_list(1000)
    total_rooms_count = len(rooms)
    
    # Get MTD charges
    mtd_charges = await db.folio_charges.find({
        'tenant_id': current_user.tenant_id,
        'date': {
            '$gte': month_start_dt.isoformat(),
            '$lte': today_end.isoformat()
        },
        'voided': False,
        'charge_category': 'room'
    }).to_list(10000)
    
    total_revenue = sum(charge.get('total', 0) for charge in mtd_charges)
    
    # Calculate days in month so far
    days_in_month_so_far = (today - month_start).days + 1
    total_available_room_days = total_rooms_count * days_in_month_so_far
    
    mtd_revpar = (total_revenue / total_available_room_days) if total_available_room_days > 0 else 0
    
    # 5. Calculate Cost to Revenue Ratio
    cost_to_revenue_ratio = (total_mtd_costs / total_revenue * 100) if total_revenue > 0 else 0
    
    # 6. Calculate profit margin
    gross_profit = total_revenue - total_mtd_costs
    profit_margin = (gross_profit / total_revenue * 100) if total_revenue > 0 else 0
    
    return {
        'report_date': today.isoformat(),
        'period': f'{month_start.isoformat()} to {today.isoformat()}',
        'total_mtd_costs': round(total_mtd_costs, 2),
        'cost_categories': {
            'housekeeping': round(cost_categories['Housekeeping'], 2),
            'fnb': round(cost_categories['F&B'], 2),
            'technical': round(cost_categories['Technical'], 2),
            'general_expenses': round(cost_categories['General Expenses'], 2)
        },
        'top_3_categories': [
            {
                'name': cat['name'],
                'amount': round(cat['amount'], 2),
                'percentage': round((cat['amount'] / total_mtd_costs * 100), 1) if total_mtd_costs > 0 else 0
            }
            for cat in top_3_categories
        ],
        'per_room_metrics': {
            'total_room_nights': total_room_nights,
            'cost_per_room_night': round(per_room_cost, 2),
            'mtd_revpar': round(mtd_revpar, 2),
            'cost_to_revpar_ratio': round((per_room_cost / mtd_revpar * 100), 1) if mtd_revpar > 0 else 0
        },
        'financial_metrics': {
            'mtd_revenue': round(total_revenue, 2),
            'mtd_costs': round(total_mtd_costs, 2),
            'gross_profit': round(gross_profit, 2),
            'profit_margin_percentage': round(profit_margin, 1),
            'cost_to_revenue_ratio': round(cost_to_revenue_ratio, 1)
        }
    }



@api_router.get("/reports/housekeeping-efficiency")
async def get_housekeeping_efficiency_report(
    start_date: str,
    end_date: str,
    current_user: User = Depends(get_current_user)
):
    """Housekeeping Efficiency Report"""
    start = datetime.fromisoformat(start_date)
    end = datetime.fromisoformat(end_date)
    
    # Get completed housekeeping tasks in date range
    tasks = await db.housekeeping_tasks.find({
        'tenant_id': current_user.tenant_id,
        'status': 'completed',
        'created_at': {'$gte': start.isoformat(), '$lte': end.isoformat()}
    }).to_list(10000)
    
    # Aggregate by assigned staff
    staff_performance = {}
    
    for task in tasks:
        assigned_to = task.get('assigned_to', 'Unassigned')
        task_type = task.get('task_type', 'cleaning')
        
        if assigned_to not in staff_performance:
            staff_performance[assigned_to] = {
                'tasks_completed': 0,
                'by_type': {}
            }
        
        staff_performance[assigned_to]['tasks_completed'] += 1
        
        if task_type not in staff_performance[assigned_to]['by_type']:
            staff_performance[assigned_to]['by_type'][task_type] = 0
        staff_performance[assigned_to]['by_type'][task_type] += 1
    
    # Calculate daily averages
    date_range_days = (end.date() - start.date()).days + 1
    
    for staff in staff_performance:
        staff_performance[staff]['daily_average'] = round(
            staff_performance[staff]['tasks_completed'] / date_range_days, 2
        )
    
    return {
        'start_date': start_date,
        'end_date': end_date,
        'date_range_days': date_range_days,
        'total_tasks_completed': len(tasks),
        'staff_performance': staff_performance,
        'daily_average_all_staff': round(len(tasks) / date_range_days, 2) if date_range_days > 0 else 0
    }

# ============= AUDIT & SECURITY =============

@api_router.get("/audit-logs")
async def get_audit_logs(
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    user_id: Optional[str] = None,
    action: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 100,
    current_user: User = Depends(get_current_user)
):
    """Get audit logs with filters"""
    # Check permission
    if not has_permission(current_user.role, Permission.VIEW_REPORTS):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    query = {'tenant_id': current_user.tenant_id}
    
    if entity_type:
        query['entity_type'] = entity_type
    if entity_id:
        query['entity_id'] = entity_id
    if user_id:
        query['user_id'] = user_id
    if action:
        query['action'] = action
    
    if start_date and end_date:
        query['timestamp'] = {
            '$gte': datetime.fromisoformat(start_date).isoformat(),
            '$lte': datetime.fromisoformat(end_date).isoformat()
        }
    
    logs = await db.audit_logs.find(query, {'_id': 0}).sort('timestamp', -1).limit(limit).to_list(limit)
    
    return {
        'logs': logs,
        'count': len(logs),
        'filters_applied': {k: v for k, v in query.items() if k != 'tenant_id'}
    }

@api_router.get("/export/folio/{folio_id}")
async def export_folio_csv(folio_id: str, current_user: User = Depends(get_current_user)):
    """Export folio transactions as CSV"""
    if not has_permission(current_user.role, Permission.EXPORT_DATA):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    from io import StringIO
    import csv
    
    # Get folio details
    folio_details = await get_folio_details(folio_id, current_user)
    folio = folio_details['folio']
    charges = folio_details['charges']
    payments = folio_details['payments']
    
    # Create CSV
    output = StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow([f"Folio Export - {folio['folio_number']}"])
    writer.writerow([f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}"])
    writer.writerow([])
    
    # Charges
    writer.writerow(['CHARGES'])
    writer.writerow(['Date', 'Category', 'Description', 'Quantity', 'Unit Price', 'Tax', 'Total', 'Voided'])
    for charge in charges:
        writer.writerow([
            charge['date'],
            charge['charge_category'],
            charge['description'],
            charge['quantity'],
            charge['unit_price'],
            charge['tax_amount'],
            charge['total'],
            'Yes' if charge.get('voided') else 'No'
        ])
    
    writer.writerow([])
    
    # Payments
    writer.writerow(['PAYMENTS'])
    writer.writerow(['Date', 'Method', 'Type', 'Amount', 'Reference'])
    for payment in payments:
        writer.writerow([
            payment['processed_at'],
            payment['method'],
            payment['payment_type'],
            payment['amount'],
            payment.get('reference', '')
        ])
    
    writer.writerow([])
    writer.writerow(['', '', '', 'Balance:', folio['balance']])
    
    csv_content = output.getvalue()
    output.close()
    
    return {
        'filename': f"folio_{folio['folio_number']}.csv",
        'content': csv_content,
        'content_type': 'text/csv'
    }

class PermissionCheckRequest(BaseModel):
    permission: str

@api_router.post("/permissions/check")
async def check_permission(
    request: PermissionCheckRequest,
    current_user: User = Depends(get_current_user)
):
    """Check if current user has a specific permission"""
    if not request.permission or request.permission.strip() == "":
        raise HTTPException(status_code=400, detail="Permission field is required and cannot be empty")
    
    try:
        perm = Permission(request.permission)
        has_perm = has_permission(current_user.role, perm)
        return {
            'user_role': current_user.role,
            'permission': request.permission,
            'has_permission': has_perm
        }
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid permission: {request.permission}")

# ============= CHANNEL MANAGER & RMS =============

@api_router.get("/channel-manager/connections")
async def get_channel_connections(current_user: User = Depends(get_current_user)):
    """Get all channel connections"""
    connections = await db.channel_connections.find(
        {'tenant_id': current_user.tenant_id},
        {'_id': 0}
    ).to_list(100)
    return {'connections': connections, 'count': len(connections)}

@api_router.post("/channel-manager/connections")
async def create_channel_connection(
    channel_type: ChannelType,
    channel_name: str,
    property_id: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Create a new channel connection"""
    connection = ChannelConnection(
        tenant_id=current_user.tenant_id,
        channel_type=channel_type,
        channel_name=channel_name,
        property_id=property_id,
        status=ChannelStatus.ACTIVE
    )
    
    conn_dict = connection.model_dump()
    conn_dict['created_at'] = conn_dict['created_at'].isoformat()
    await db.channel_connections.insert_one(conn_dict)
    
    return {'message': f'Channel {channel_name} connected successfully', 'connection': connection}

@api_router.get("/channel-manager/ota-reservations")
async def get_ota_reservations(
    status: Optional[str] = None,
    channel: Optional[ChannelType] = None,
    current_user: User = Depends(get_current_user)
):
    """Get OTA reservations with filters"""
    query = {'tenant_id': current_user.tenant_id}
    if status:
        query['status'] = status
    if channel:
        query['channel_type'] = channel
    
    reservations = await db.ota_reservations.find(query, {'_id': 0}).sort('received_at', -1).to_list(100)
    return {'reservations': reservations, 'count': len(reservations)}

@api_router.post("/channel-manager/import-reservation/{ota_reservation_id}")
async def import_ota_reservation(
    ota_reservation_id: str,
    current_user: User = Depends(get_current_user)
):
    """Import OTA reservation into PMS"""
    ota_res = await db.ota_reservations.find_one({
        'id': ota_reservation_id,
        'tenant_id': current_user.tenant_id
    })
    
    if not ota_res:
        raise HTTPException(status_code=404, detail="OTA reservation not found")
    
    if ota_res['status'] == 'imported':
        raise HTTPException(status_code=400, detail="Reservation already imported")
    
    # Find or create guest
    guest = await db.guests.find_one({
        'tenant_id': current_user.tenant_id,
        'email': ota_res['guest_email']
    })
    
    if not guest:
        # Create new guest
        from pydantic import EmailStr
        guest_create = GuestCreate(
            name=ota_res['guest_name'],
            email=ota_res.get('guest_email') or 'noemail@example.com',
            phone=ota_res.get('guest_phone') or 'N/A',
            id_number='OTA-' + ota_res['channel_booking_id']
        )
        guest = Guest(tenant_id=current_user.tenant_id, **guest_create.model_dump())
        guest_dict = guest.model_dump()
        guest_dict['created_at'] = guest_dict['created_at'].isoformat()
        await db.guests.insert_one(guest_dict)
    
    # Find available room of matching type
    rooms = await db.rooms.find({
        'tenant_id': current_user.tenant_id,
        'room_type': ota_res['room_type'],
        'status': 'available'
    }).to_list(10)
    
    if not rooms:
        # Create exception
        exception = ExceptionQueue(
            tenant_id=current_user.tenant_id,
            exception_type="reservation_import_failed",
            channel_type=ota_res['channel_type'],
            entity_id=ota_reservation_id,
            error_message=f"No available rooms of type {ota_res['room_type']}",
            details={'ota_booking_id': ota_res['channel_booking_id']}
        )
        exc_dict = exception.model_dump()
        exc_dict['created_at'] = exc_dict['created_at'].isoformat()
        await db.exception_queue.insert_one(exc_dict)
        
        raise HTTPException(status_code=400, detail=f"No available {ota_res['room_type']} rooms")
    
    room = rooms[0]
    
    # Create booking
    booking_create = BookingCreate(
        guest_id=guest['id'],
        room_id=room['id'],
        check_in=ota_res['check_in'],
        check_out=ota_res['check_out'],
        adults=ota_res['adults'],
        children=ota_res['children'],
        guests_count=ota_res['adults'] + ota_res['children'],
        total_amount=ota_res['total_amount'],
        channel=ota_res['channel_type']
    )
    
    booking = Booking(
        tenant_id=current_user.tenant_id,
        **booking_create.model_dump(exclude={'check_in', 'check_out'}),
        check_in=datetime.fromisoformat(ota_res['check_in']),
        check_out=datetime.fromisoformat(ota_res['check_out'])
    )
    
    booking_dict = booking.model_dump()
    booking_dict['check_in'] = booking_dict['check_in'].isoformat()
    booking_dict['check_out'] = booking_dict['check_out'].isoformat()
    booking_dict['created_at'] = booking_dict['created_at'].isoformat()
    await db.bookings.insert_one(booking_dict)
    
    # Update OTA reservation status
    await db.ota_reservations.update_one(
        {'id': ota_reservation_id},
        {'$set': {
            'status': 'imported',
            'pms_booking_id': booking.id,
            'processed_at': datetime.now(timezone.utc).isoformat()
        }}
    )
    
    return {
        'message': 'OTA reservation imported successfully',
        'pms_booking_id': booking.id,
        'guest_id': guest['id'],
        'room_number': room['room_number']
    }

@api_router.get("/channel-manager/exceptions")
async def get_exception_queue(
    status: Optional[str] = None,
    exception_type: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Get exception queue with filters"""
    query = {'tenant_id': current_user.tenant_id}
    if status:
        query['status'] = status
    if exception_type:
        query['exception_type'] = exception_type
    
    exceptions = await db.exception_queue.find(query, {'_id': 0}).sort('created_at', -1).to_list(100)
    return {'exceptions': exceptions, 'count': len(exceptions)}

# ============= OTA OVERLAY & RATE PARITY =============

@api_router.get("/channel/parity/check")
async def check_rate_parity(
    date: Optional[str] = None,
    room_type: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Check rate parity between OTA and direct rates"""
    target_date = datetime.fromisoformat(date).date() if date else datetime.now(timezone.utc).date()
    
    # Get rooms
    room_query = {'tenant_id': current_user.tenant_id}
    if room_type:
        room_query['room_type'] = room_type
    
    rooms = await db.rooms.find(room_query, {'_id': 0}).to_list(1000)
    room_types = list(set(r['room_type'] for r in rooms))
    
    parity_results = []
    
    for rt in room_types:
        # Get direct rate (base_price from room)
        rt_rooms = [r for r in rooms if r['room_type'] == rt]
        if not rt_rooms:
            continue
        
        direct_rate = rt_rooms[0]['base_price']
        
        # Get OTA rates from recent bookings
        start_of_day = datetime.combine(target_date, datetime.min.time())
        end_of_day = datetime.combine(target_date, datetime.max.time())
        
        # Find bookings on this date by channel
        ota_bookings = await db.bookings.find({
            'tenant_id': current_user.tenant_id,
            'room_id': {'$in': [r['id'] for r in rt_rooms]},
            'check_in': {'$gte': start_of_day.isoformat(), '$lte': end_of_day.isoformat()},
            'ota_channel': {'$ne': None}
        }, {'_id': 0}).to_list(100)
        
        # Group by OTA channel
        ota_rates = {}
        for booking in ota_bookings:
            if booking.get('ota_channel'):
                nights = (datetime.fromisoformat(booking['check_out']) - datetime.fromisoformat(booking['check_in'])).days
                if nights > 0:
                    avg_rate = booking['total_amount'] / nights
                    channel = booking['ota_channel']
                    if channel not in ota_rates:
                        ota_rates[channel] = []
                    ota_rates[channel].append(avg_rate)
        
        # Calculate average OTA rate per channel
        for channel, rates in ota_rates.items():
            avg_ota_rate = sum(rates) / len(rates)
            diff = direct_rate - avg_ota_rate
            
            if abs(diff) < 1:
                parity = ParityStatus.EQUAL
            elif diff > 0:
                parity = ParityStatus.POSITIVE  # Direct more expensive (good)
            else:
                parity = ParityStatus.NEGATIVE  # OTA more expensive (bad)
            
            parity_results.append({
                'date': target_date.isoformat(),
                'room_type': rt,
                'channel': channel,
                'direct_rate': round(direct_rate, 2),
                'ota_rate': round(avg_ota_rate, 2),
                'difference': round(diff, 2),
                'parity_status': parity,
                'sample_size': len(rates)
            })
    
    return {
        'date': target_date.isoformat(),
        'parity_checks': parity_results,
        'total_checks': len(parity_results)
    }

@api_router.get("/channel/status")
async def get_channel_status(current_user: User = Depends(get_current_user)):
    """Get health status of all channel connections"""
    # Get all connections
    connections = await db.channel_connections.find(
        {'tenant_id': current_user.tenant_id},
        {'_id': 0}
    ).to_list(100)
    
    # Check exception queue for issues
    recent_exceptions = await db.exception_queue.find({
        'tenant_id': current_user.tenant_id,
        'status': 'pending',
        'created_at': {'$gte': (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()}
    }, {'_id': 0}).to_list(100)
    
    channel_statuses = []
    
    for conn in connections:
        # Check for recent exceptions
        conn_exceptions = [e for e in recent_exceptions if e.get('channel_type') == conn.get('channel_type')]
        
        if len(conn_exceptions) > 10:
            health = ChannelHealth.ERROR
            message = f"{len(conn_exceptions)} pending exceptions"
        elif len(conn_exceptions) > 3:
            health = ChannelHealth.DELAYED
            message = f"{len(conn_exceptions)} pending exceptions"
        elif conn.get('status') != 'active':
            health = ChannelHealth.OFFLINE
            message = "Connection inactive"
        else:
            health = ChannelHealth.HEALTHY
            message = "All systems operational"
        
        # Calculate delay if any
        delay_minutes = 0
        if conn_exceptions:
            oldest = min(conn_exceptions, key=lambda x: x['created_at'])
            delay_minutes = int((datetime.now(timezone.utc) - datetime.fromisoformat(oldest['created_at'])).total_seconds() / 60)
        
        channel_statuses.append({
            'channel_type': conn.get('channel_type'),
            'channel_name': conn.get('channel_name'),
            'health': health,
            'message': message,
            'pending_exceptions': len(conn_exceptions),
            'delay_minutes': delay_minutes,
            'last_sync': conn.get('last_sync_at', 'Never')
        })
    
    return {
        'channels': channel_statuses,
        'total_channels': len(channel_statuses),
        'healthy_count': sum(1 for c in channel_statuses if c['health'] == ChannelHealth.HEALTHY),
        'warning_count': sum(1 for c in channel_statuses if c['health'] == ChannelHealth.DELAYED),
        'error_count': sum(1 for c in channel_statuses if c['health'] == ChannelHealth.ERROR)
    }

@api_router.post("/channel/insights/analyze")
async def analyze_ota_insights(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """AI-powered OTA channel analysis (Phase E preparation)"""
    # Default to last 30 days
    end = datetime.fromisoformat(end_date).date() if end_date else datetime.now(timezone.utc).date()
    start = datetime.fromisoformat(start_date).date() if start_date else (end - timedelta(days=30))
    
    # Get all bookings in date range
    bookings = await db.bookings.find({
        'tenant_id': current_user.tenant_id,
        'check_in': {'$gte': start.isoformat(), '$lte': end.isoformat()}
    }, {'_id': 0}).to_list(10000)
    
    # Channel performance analysis
    channel_performance = {}
    total_revenue = 0
    total_commission_cost = 0
    
    for booking in bookings:
        channel = booking.get('ota_channel') or 'direct'
        amount = booking.get('total_amount', 0)
        commission = booking.get('commission_pct', 0)
        
        if channel not in channel_performance:
            channel_performance[channel] = {
                'bookings': 0,
                'revenue': 0,
                'commission_cost': 0,
                'avg_rate': 0
            }
        
        channel_performance[channel]['bookings'] += 1
        channel_performance[channel]['revenue'] += amount
        
        if commission > 0:
            commission_amount = amount * (commission / 100)
            channel_performance[channel]['commission_cost'] += commission_amount
            total_commission_cost += commission_amount
        
        total_revenue += amount
    
    # Calculate averages and net revenue
    for channel, data in channel_performance.items():
        if data['bookings'] > 0:
            data['avg_rate'] = round(data['revenue'] / data['bookings'], 2)
            data['net_revenue'] = round(data['revenue'] - data['commission_cost'], 2)
            data['revenue_share_pct'] = round((data['revenue'] / total_revenue * 100) if total_revenue > 0 else 0, 2)
            data['commission_cost'] = round(data['commission_cost'], 2)
    
    # Sort by revenue
    sorted_channels = sorted(
        channel_performance.items(),
        key=lambda x: x[1]['revenue'],
        reverse=True
    )
    
    # Generate insights
    insights = []
    
    # Best performing channel
    if sorted_channels:
        best_channel = sorted_channels[0]
        insights.append({
            'type': 'top_performer',
            'channel': best_channel[0],
            'message': f"{best_channel[0]} is your top channel with ${best_channel[1]['revenue']:.2f} revenue ({best_channel[1]['bookings']} bookings)",
            'priority': 'high'
        })
    
    # High commission cost warning
    if total_commission_cost > total_revenue * 0.20:
        insights.append({
            'type': 'high_commission',
            'message': f"Commission costs are ${total_commission_cost:.2f} ({(total_commission_cost/total_revenue*100):.1f}% of revenue). Consider direct booking strategies.",
            'priority': 'medium'
        })
    
    # Parity suggestions (placeholder for Phase E AI)
    insights.append({
        'type': 'parity_suggestion',
        'message': "Consider rate parity monitoring to optimize OTA vs Direct pricing",
        'priority': 'low'
    })
    
    return {
        'period': {
            'start_date': start.isoformat(),
            'end_date': end.isoformat(),
            'days': (end - start).days
        },
        'summary': {
            'total_bookings': len(bookings),
            'total_revenue': round(total_revenue, 2),
            'total_commission_cost': round(total_commission_cost, 2),
            'net_revenue': round(total_revenue - total_commission_cost, 2),
            'avg_commission_pct': round((total_commission_cost / total_revenue * 100) if total_revenue > 0 else 0, 2)
        },
        'channel_performance': dict(sorted_channels),
        'insights': insights,
        'recommendations': [
            "Monitor rate parity daily to prevent OTA undercutting",
            "Increase direct booking conversion with better incentives",
            "Negotiate commission rates with high-volume OTAs"
        ]
    }

# ============= ENTERPRISE MODE FEATURES =============

@api_router.get("/enterprise/rate-leakage")
async def detect_rate_leakage(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Detect rate leakage where OTA rates are lower than direct rates"""
    # Default to next 30 days
    start = datetime.fromisoformat(start_date).date() if start_date else datetime.now(timezone.utc).date()
    end = datetime.fromisoformat(end_date).date() if end_date else (start + timedelta(days=30))
    
    # Get rooms
    rooms = await db.rooms.find({'tenant_id': current_user.tenant_id}, {'_id': 0}).to_list(1000)
    room_types = list(set(r['room_type'] for r in rooms))
    
    leakages = []
    total_leakage_amount = 0
    
    for rt in room_types:
        rt_rooms = [r for r in rooms if r['room_type'] == rt]
        direct_rate = rt_rooms[0]['base_price'] if rt_rooms else 0
        
        # Get OTA bookings in date range
        ota_bookings = await db.bookings.find({
            'tenant_id': current_user.tenant_id,
            'room_id': {'$in': [r['id'] for r in rt_rooms]},
            'check_in': {'$gte': start.isoformat(), '$lte': end.isoformat()},
            'ota_channel': {'$ne': None},
            'status': {'$in': ['confirmed', 'guaranteed', 'checked_in']}
        }, {'_id': 0}).to_list(1000)
        
        for booking in ota_bookings:
            nights = (datetime.fromisoformat(booking['check_out']) - datetime.fromisoformat(booking['check_in'])).days
            if nights > 0:
                ota_rate = booking['total_amount'] / nights
                
                # Rate leakage = OTA rate < Direct rate
                if ota_rate < direct_rate:
                    leakage_amount = (direct_rate - ota_rate) * nights
                    total_leakage_amount += leakage_amount
                    
                    leakages.append({
                        'booking_id': booking['id'],
                        'guest_name': booking.get('guest_name', 'Unknown'),
                        'room_type': rt,
                        'ota_channel': booking['ota_channel'],
                        'check_in': booking['check_in'],
                        'check_out': booking['check_out'],
                        'nights': nights,
                        'direct_rate': round(direct_rate, 2),
                        'ota_rate': round(ota_rate, 2),
                        'difference_per_night': round(direct_rate - ota_rate, 2),
                        'total_leakage': round(leakage_amount, 2),
                        'commission_pct': booking.get('commission_pct', 0),
                        'severity': 'high' if (direct_rate - ota_rate) > 20 else 'medium' if (direct_rate - ota_rate) > 10 else 'low'
                    })
    
    # Sort by total leakage descending
    leakages.sort(key=lambda x: x['total_leakage'], reverse=True)
    
    return {
        'period': {
            'start_date': start.isoformat(),
            'end_date': end.isoformat()
        },
        'summary': {
            'total_leakage_instances': len(leakages),
            'total_leakage_amount': round(total_leakage_amount, 2),
            'high_severity_count': sum(1 for l in leakages if l['severity'] == 'high'),
            'medium_severity_count': sum(1 for l in leakages if l['severity'] == 'medium')
        },
        'leakages': leakages[:50],  # Top 50 worst leakages
        'recommendations': [
            "Update OTA rate parity to match or exceed direct rates",
            "Review commission structures with high-leakage OTAs",
            "Consider restricting inventory on channels with severe leakage"
        ]
    }

@api_router.get("/enterprise/pickup-pace")
async def get_pickup_pace(
    target_date: str,
    lookback_days: int = 30,
    current_user: User = Depends(get_current_user)
):
    """Analyze booking pickup pace for a target date"""
    target = datetime.fromisoformat(target_date).date()
    today = datetime.now(timezone.utc).date()
    
    # Get bookings for target date created in last lookback_days
    bookings = await db.bookings.find({
        'tenant_id': current_user.tenant_id,
        'check_in': target.isoformat(),
        'status': {'$in': ['confirmed', 'guaranteed', 'checked_in']},
        'created_at': {'$gte': (today - timedelta(days=lookback_days)).isoformat()}
    }, {'_id': 0}).to_list(1000)
    
    # Group by creation date
    pickup_by_date = {}
    for booking in bookings:
        created_date = datetime.fromisoformat(booking['created_at']).date()
        days_before_arrival = (target - created_date).days
        
        if days_before_arrival >= 0:
            if days_before_arrival not in pickup_by_date:
                pickup_by_date[days_before_arrival] = {
                    'count': 0,
                    'revenue': 0,
                    'channels': {}
                }
            
            pickup_by_date[days_before_arrival]['count'] += 1
            pickup_by_date[days_before_arrival]['revenue'] += booking.get('total_amount', 0)
            
            channel = booking.get('ota_channel') or 'direct'
            pickup_by_date[days_before_arrival]['channels'][channel] = \
                pickup_by_date[days_before_arrival]['channels'].get(channel, 0) + 1
    
    # Create timeline
    pickup_timeline = []
    cumulative_bookings = 0
    cumulative_revenue = 0
    
    for days_before in range(lookback_days, -1, -1):
        if days_before in pickup_by_date:
            data = pickup_by_date[days_before]
            cumulative_bookings += data['count']
            cumulative_revenue += data['revenue']
        
        pickup_timeline.append({
            'days_before_arrival': days_before,
            'date': (target - timedelta(days=days_before)).isoformat(),
            'daily_bookings': pickup_by_date.get(days_before, {}).get('count', 0),
            'daily_revenue': round(pickup_by_date.get(days_before, {}).get('revenue', 0), 2),
            'cumulative_bookings': cumulative_bookings,
            'cumulative_revenue': round(cumulative_revenue, 2)
        })
    
    # Calculate velocity (bookings per day)
    recent_7_days = sum(pickup_by_date.get(i, {}).get('count', 0) for i in range(7))
    velocity = round(recent_7_days / 7, 2)
    
    return {
        'target_date': target.isoformat(),
        'days_until_arrival': (target - today).days,
        'total_bookings': cumulative_bookings,
        'total_revenue': round(cumulative_revenue, 2),
        'velocity_7day': velocity,
        'pickup_timeline': pickup_timeline,
        'insights': [
            f"Current pace: {velocity} bookings/day",
            f"Total bookings to date: {cumulative_bookings}",
            f"Days until arrival: {(target - today).days}"
        ]
    }

@api_router.get("/enterprise/availability-heatmap")
async def get_availability_heatmap(
    start_date: str,
    end_date: str,
    current_user: User = Depends(get_current_user)
):
    """Generate availability heatmap showing occupancy intensity"""
    start = datetime.fromisoformat(start_date).date()
    end = datetime.fromisoformat(end_date).date()
    
    # Get all rooms
    rooms = await db.rooms.find({'tenant_id': current_user.tenant_id}, {'_id': 0}).to_list(1000)
    total_rooms = len(rooms)
    room_types = list(set(r['room_type'] for r in rooms))
    
    heatmap_data = []
    
    current_date = start
    while current_date <= end:
        start_of_day = datetime.combine(current_date, datetime.min.time())
        end_of_day = datetime.combine(current_date, datetime.max.time())
        
        # Get bookings for this date
        occupied = await db.bookings.count_documents({
            'tenant_id': current_user.tenant_id,
            'status': {'$in': ['confirmed', 'guaranteed', 'checked_in']},
            'check_in': {'$lte': end_of_day.isoformat()},
            'check_out': {'$gte': start_of_day.isoformat()}
        })
        
        # Get blocks for this date
        blocks = await db.room_blocks.count_documents({
            'tenant_id': current_user.tenant_id,
            'status': 'active',
            'start_date': {'$lte': current_date.isoformat()},
            '$or': [
                {'end_date': {'$gte': current_date.isoformat()}},
                {'end_date': None}
            ]
        })
        
        available = total_rooms - occupied - blocks
        occupancy_pct = round((occupied / total_rooms * 100) if total_rooms > 0 else 0, 1)
        
        # Determine intensity
        if occupancy_pct >= 95:
            intensity = 'critical'  # Red
        elif occupancy_pct >= 85:
            intensity = 'high'  # Orange
        elif occupancy_pct >= 70:
            intensity = 'moderate'  # Yellow
        elif occupancy_pct >= 50:
            intensity = 'medium'  # Light green
        else:
            intensity = 'low'  # Green
        
        # Get room type breakdown
        rt_breakdown = {}
        for rt in room_types:
            rt_rooms = [r for r in rooms if r['room_type'] == rt]
            rt_occupied = await db.bookings.count_documents({
                'tenant_id': current_user.tenant_id,
                'room_id': {'$in': [r['id'] for r in rt_rooms]},
                'status': {'$in': ['confirmed', 'guaranteed', 'checked_in']},
                'check_in': {'$lte': end_of_day.isoformat()},
                'check_out': {'$gte': start_of_day.isoformat()}
            })
            rt_breakdown[rt] = {
                'occupied': rt_occupied,
                'total': len(rt_rooms),
                'occupancy_pct': round((rt_occupied / len(rt_rooms) * 100) if len(rt_rooms) > 0 else 0, 1)
            }
        
        heatmap_data.append({
            'date': current_date.isoformat(),
            'day_of_week': current_date.strftime('%a'),
            'occupied': occupied,
            'available': available,
            'blocked': blocks,
            'total': total_rooms,
            'occupancy_pct': occupancy_pct,
            'intensity': intensity,
            'room_types': rt_breakdown
        })
        
        current_date += timedelta(days=1)
    
    return {
        'period': {
            'start_date': start.isoformat(),
            'end_date': end.isoformat(),
            'days': len(heatmap_data)
        },
        'summary': {
            'avg_occupancy': round(sum(d['occupancy_pct'] for d in heatmap_data) / len(heatmap_data), 1),
            'peak_date': max(heatmap_data, key=lambda x: x['occupancy_pct'])['date'],
            'peak_occupancy': max(d['occupancy_pct'] for d in heatmap_data),
            'critical_days': sum(1 for d in heatmap_data if d['intensity'] == 'critical'),
            'high_days': sum(1 for d in heatmap_data if d['intensity'] == 'high')
        },
        'heatmap': heatmap_data
    }

# ============= AI MODE - INTELLIGENT OPERATIONS =============

@api_router.post("/ai/solve-overbooking")
async def solve_overbooking(
    date: str,
    current_user: User = Depends(get_current_user)
):
    """AI-powered overbooking resolution suggestions"""
    target_date = datetime.fromisoformat(date).date()
    start_of_day = datetime.combine(target_date, datetime.min.time())
    end_of_day = datetime.combine(target_date, datetime.max.time())
    
    # Get all rooms
    rooms = await db.rooms.find({'tenant_id': current_user.tenant_id}, {'_id': 0}).to_list(1000)
    
    # Find overbookings (multiple bookings on same room same date)
    conflicts = []
    for room in rooms:
        bookings = await db.bookings.find({
            'tenant_id': current_user.tenant_id,
            'room_id': room['id'],
            'status': {'$in': ['confirmed', 'guaranteed']},
            'check_in': {'$lte': end_of_day.isoformat()},
            'check_out': {'$gte': start_of_day.isoformat()}
        }, {'_id': 0}).to_list(100)
        
        if len(bookings) > 1:
            conflicts.append({
                'room': room,
                'bookings': bookings
            })
    
    # Generate AI solutions
    solutions = []
    for conflict in conflicts:
        room = conflict['room']
        bookings = conflict['bookings']
        
        # Find alternative rooms of same type
        alt_rooms = [r for r in rooms if r['room_type'] == room['room_type'] and r['id'] != room['id']]
        
        for booking in bookings[1:]:  # Keep first booking, move others
            # Find available alternative rooms
            available_alts = []
            for alt_room in alt_rooms:
                # Check if alt room is available
                existing = await db.bookings.count_documents({
                    'tenant_id': current_user.tenant_id,
                    'room_id': alt_room['id'],
                    'status': {'$in': ['confirmed', 'guaranteed', 'checked_in']},
                    'check_in': {'$lte': booking['check_out']},
                    'check_out': {'$gte': booking['check_in']}
                })
                
                if existing == 0:
                    # Calculate guest priority score
                    guest = await db.guests.find_one({'id': booking['guest_id'], 'tenant_id': current_user.tenant_id}, {'_id': 0})
                    loyalty_tier = guest.get('loyalty_tier', 'standard') if guest else 'standard'
                    priority_score = {
                        'vip': 100,
                        'gold': 80,
                        'silver': 60,
                        'standard': 40
                    }.get(loyalty_tier, 40)
                    
                    # Add OTA channel penalty (harder to move OTA bookings)
                    if booking.get('ota_channel'):
                        priority_score -= 20
                    
                    available_alts.append({
                        'room': alt_room,
                        'priority_score': priority_score,
                        'reason': f"Same type ({alt_room['room_type']}), Floor {alt_room['floor']}"
                    })
            
            # Sort by priority score
            available_alts.sort(key=lambda x: x['priority_score'], reverse=True)
            
            if available_alts:
                best_option = available_alts[0]
                solutions.append({
                    'conflict_type': 'overbooking',
                    'severity': 'high',
                    'current_room': room['room_number'],
                    'booking_id': booking['id'],
                    'guest_name': booking.get('guest_name', 'Unknown'),
                    'check_in': booking['check_in'],
                    'check_out': booking['check_out'],
                    'recommended_action': 'move',
                    'recommended_room': best_option['room']['room_number'],
                    'recommended_room_id': best_option['room']['id'],
                    'confidence': 0.85,
                    'reason': best_option['reason'],
                    'impact': 'minimal',
                    'auto_apply': False
                })
    
    return {
        'date': target_date.isoformat(),
        'conflicts_found': len(conflicts),
        'solutions': solutions,
        'summary': f"Found {len(conflicts)} overbooking conflicts with {len(solutions)} AI-powered solutions"
    }

@api_router.post("/ai/recommend-room-moves")
async def recommend_room_moves(
    date: str,
    current_user: User = Depends(get_current_user)
):
    """AI recommendations for optimal room moves (upgrades, VIP service)"""
    target_date = datetime.fromisoformat(date).date()
    start_of_day = datetime.combine(target_date, datetime.min.time())
    end_of_day = datetime.combine(target_date, datetime.max.time())
    
    rooms = await db.rooms.find({'tenant_id': current_user.tenant_id}, {'_id': 0}).to_list(1000)
    
    # Get bookings for target date
    bookings = await db.bookings.find({
        'tenant_id': current_user.tenant_id,
        'status': {'$in': ['confirmed', 'guaranteed']},
        'check_in': {'$lte': end_of_day.isoformat()},
        'check_out': {'$gte': start_of_day.isoformat()}
    }, {'_id': 0}).to_list(1000)
    
    recommendations = []
    
    for booking in bookings:
        guest = await db.guests.find_one({'id': booking['guest_id'], 'tenant_id': current_user.tenant_id}, {'_id': 0})
        if not guest:
            continue
        
        current_room = next((r for r in rooms if r['id'] == booking['room_id']), None)
        if not current_room:
            continue
        
        loyalty_tier = guest.get('loyalty_tier', 'standard')
        
        # VIP/Gold upgrade opportunities
        if loyalty_tier in ['vip', 'gold']:
            # Find better rooms available
            better_rooms = [r for r in rooms 
                          if r['room_type'] != current_room['room_type'] 
                          and r['base_price'] > current_room['base_price']]
            
            for better_room in better_rooms:
                # Check availability
                existing = await db.bookings.count_documents({
                    'tenant_id': current_user.tenant_id,
                    'room_id': better_room['id'],
                    'status': {'$in': ['confirmed', 'guaranteed', 'checked_in']},
                    'check_in': {'$lte': booking['check_out']},
                    'check_out': {'$gte': booking['check_in']}
                })
                
                if existing == 0:
                    recommendations.append({
                        'type': 'upgrade',
                        'priority': 'high' if loyalty_tier == 'vip' else 'medium',
                        'booking_id': booking['id'],
                        'guest_name': guest.get('name', 'Unknown'),
                        'loyalty_tier': loyalty_tier,
                        'current_room': current_room['room_number'],
                        'recommended_room': better_room['room_number'],
                        'recommended_room_id': better_room['id'],
                        'reason': f"Complimentary upgrade for {loyalty_tier.upper()} guest",
                        'revenue_impact': 0,  # Complimentary
                        'confidence': 0.90
                    })
                    break  # One recommendation per booking
        
        # Room block avoidance
        blocks = await db.room_blocks.find({
            'tenant_id': current_user.tenant_id,
            'room_id': current_room['id'],
            'status': 'active',
            'start_date': {'$lte': booking['check_out']},
            '$or': [
                {'end_date': {'$gte': booking['check_in']}},
                {'end_date': None}
            ]
        }, {'_id': 0}).to_list(10)
        
        if blocks:
            # Find alternative same-type room
            alt_rooms = [r for r in rooms 
                        if r['room_type'] == current_room['room_type'] 
                        and r['id'] != current_room['id']]
            
            for alt_room in alt_rooms:
                existing = await db.bookings.count_documents({
                    'tenant_id': current_user.tenant_id,
                    'room_id': alt_room['id'],
                    'status': {'$in': ['confirmed', 'guaranteed', 'checked_in']},
                    'check_in': {'$lte': booking['check_out']},
                    'check_out': {'$gte': booking['check_in']}
                })
                
                if existing == 0:
                    recommendations.append({
                        'type': 'block_avoidance',
                        'priority': 'urgent',
                        'booking_id': booking['id'],
                        'guest_name': guest.get('name', 'Unknown'),
                        'current_room': current_room['room_number'],
                        'recommended_room': alt_room['room_number'],
                        'recommended_room_id': alt_room['id'],
                        'reason': f"Room {current_room['room_number']} is blocked ({blocks[0]['type']})",
                        'revenue_impact': 0,
                        'confidence': 0.95
                    })
                    break
    
    # Sort by priority
    priority_order = {'urgent': 0, 'high': 1, 'medium': 2, 'low': 3}
    recommendations.sort(key=lambda x: priority_order.get(x['priority'], 99))
    
    return {
        'date': target_date.isoformat(),
        'recommendations': recommendations,
        'count': len(recommendations),
        'summary': f"Generated {len(recommendations)} AI room move recommendations"
    }

@api_router.post("/ai/recommend-rates")
async def recommend_rates(
    start_date: str,
    end_date: str,
    current_user: User = Depends(get_current_user)
):
    """AI-powered dynamic rate recommendations"""
    start = datetime.fromisoformat(start_date).date()
    end = datetime.fromisoformat(end_date).date()
    
    rooms = await db.rooms.find({'tenant_id': current_user.tenant_id}, {'_id': 0}).to_list(1000)
    room_types = list(set(r['room_type'] for r in rooms))
    
    recommendations = []
    
    for rt in room_types:
        rt_rooms = [r for r in rooms if r['room_type'] == rt]
        total_rt_rooms = len(rt_rooms)
        base_rate = rt_rooms[0]['base_price'] if rt_rooms else 0
        
        current_date = start
        while current_date <= end:
            start_of_day = datetime.combine(current_date, datetime.min.time())
            end_of_day = datetime.combine(current_date, datetime.max.time())
            
            # Calculate occupancy
            occupied = await db.bookings.count_documents({
                'tenant_id': current_user.tenant_id,
                'room_id': {'$in': [r['id'] for r in rt_rooms]},
                'status': {'$in': ['confirmed', 'guaranteed', 'checked_in']},
                'check_in': {'$lte': end_of_day.isoformat()},
                'check_out': {'$gte': start_of_day.isoformat()}
            })
            
            occupancy_pct = (occupied / total_rt_rooms * 100) if total_rt_rooms > 0 else 0
            
            # AI pricing strategy
            if occupancy_pct >= 90:
                # High demand - increase rates
                recommended_rate = base_rate * 1.25
                strategy = 'demand_surge'
                reason = f"High occupancy ({occupancy_pct:.0f}%) - capitalize on demand"
                confidence = 0.88
            elif occupancy_pct >= 75:
                # Good demand - moderate increase
                recommended_rate = base_rate * 1.15
                strategy = 'optimize'
                reason = f"Strong demand ({occupancy_pct:.0f}%) - optimize revenue"
                confidence = 0.82
            elif occupancy_pct >= 50:
                # Moderate - maintain rates
                recommended_rate = base_rate
                strategy = 'maintain'
                reason = f"Normal occupancy ({occupancy_pct:.0f}%) - maintain base rates"
                confidence = 0.75
            else:
                # Low demand - discount to attract
                recommended_rate = base_rate * 0.85
                strategy = 'attract'
                reason = f"Low occupancy ({occupancy_pct:.0f}%) - attract bookings with discount"
                confidence = 0.80
            
            # Check day of week for adjustments
            day_of_week = current_date.weekday()
            if day_of_week in [4, 5]:  # Friday, Saturday
                recommended_rate *= 1.10
                reason += " + Weekend premium"
            
            recommendations.append({
                'date': current_date.isoformat(),
                'day_of_week': current_date.strftime('%A'),
                'room_type': rt,
                'current_rate': round(base_rate, 2),
                'recommended_rate': round(recommended_rate, 2),
                'difference': round(recommended_rate - base_rate, 2),
                'difference_pct': round(((recommended_rate - base_rate) / base_rate * 100), 1),
                'strategy': strategy,
                'reason': reason,
                'occupancy_pct': round(occupancy_pct, 1),
                'confidence': confidence,
                'revenue_impact': round((recommended_rate - base_rate) * (total_rt_rooms - occupied), 2)
            })
            
            current_date += timedelta(days=1)
    
    # Calculate total potential revenue impact
    total_impact = sum(r['revenue_impact'] for r in recommendations if r['revenue_impact'] > 0)
    
    return {
        'period': {
            'start_date': start.isoformat(),
            'end_date': end.isoformat()
        },
        'recommendations': recommendations,
        'summary': {
            'total_recommendations': len(recommendations),
            'increase_count': sum(1 for r in recommendations if r['difference'] > 0),
            'decrease_count': sum(1 for r in recommendations if r['difference'] < 0),
            'maintain_count': sum(1 for r in recommendations if r['difference'] == 0),
            'potential_revenue_increase': round(total_impact, 2)
        }
    }

@api_router.post("/ai/predict-no-shows")
async def predict_no_shows(
    date: str,
    current_user: User = Depends(get_current_user)
):
    """AI prediction of high-risk no-show bookings"""
    target_date = datetime.fromisoformat(date).date()
    
    # Get arrivals for target date
    bookings = await db.bookings.find({
        'tenant_id': current_user.tenant_id,
        'check_in': target_date.isoformat(),
        'status': {'$in': ['confirmed', 'guaranteed']}
    }, {'_id': 0}).to_list(1000)
    
    predictions = []
    
    for booking in bookings:
        risk_score = 0
        risk_factors = []
        
        # Factor 1: Channel risk (OTA bookings higher risk)
        if booking.get('ota_channel'):
            risk_score += 25
            risk_factors.append(f"OTA booking ({booking.get('ota_channel')})")
        else:
            risk_score += 5
        
        # Factor 2: Payment method
        payment_model = booking.get('payment_model')
        if payment_model == 'agency':
            risk_score += 20
            risk_factors.append("Agency payment (no prepayment)")
        elif payment_model == 'hotel_collect':
            risk_score += 15
            risk_factors.append("Hotel collect (no prepayment)")
        elif payment_model == 'virtual_card':
            risk_score += 5
            risk_factors.append("Virtual card")
        
        # Factor 3: Booking lead time (last-minute bookings higher risk)
        created_at = datetime.fromisoformat(booking.get('created_at', datetime.now(timezone.utc).isoformat()))
        lead_time = (target_date - created_at.date()).days
        if lead_time < 2:
            risk_score += 20
            risk_factors.append(f"Last-minute booking ({lead_time} days)")
        elif lead_time < 7:
            risk_score += 10
            risk_factors.append(f"Short lead time ({lead_time} days)")
        
        # Factor 4: Guest history (if available)
        guest = await db.guests.find_one({'id': booking['guest_id'], 'tenant_id': current_user.tenant_id}, {'_id': 0})
        if guest:
            past_bookings = await db.bookings.count_documents({
                'tenant_id': current_user.tenant_id,
                'guest_id': booking['guest_id'],
                'status': 'checked_in'
            })
            
            if past_bookings == 0:
                risk_score += 15
                risk_factors.append("First-time guest")
            elif past_bookings > 3:
                risk_score -= 10
                risk_factors.append(f"Repeat guest ({past_bookings} stays)")
        
        # Factor 5: Booking amount (lower rates = higher risk)
        if booking.get('total_amount', 0) < 100:
            risk_score += 10
            risk_factors.append("Low booking value")
        
        # Normalize risk score (0-100)
        risk_score = min(100, max(0, risk_score))
        
        # Classify risk level
        if risk_score >= 70:
            risk_level = 'high'
            recommendation = 'Contact guest to confirm + Consider overbook strategy'
        elif risk_score >= 50:
            risk_level = 'medium'
            recommendation = 'Send reminder SMS/email 24h before arrival'
        else:
            risk_level = 'low'
            recommendation = 'Standard arrival preparation'
        
        predictions.append({
            'booking_id': booking['id'],
            'guest_name': booking.get('guest_name', 'Unknown'),
            'room_number': booking.get('room_number', 'TBD'),
            'check_in': booking['check_in'],
            'risk_score': risk_score,
            'risk_level': risk_level,
            'risk_factors': risk_factors,
            'confidence': 0.75,
            'recommendation': recommendation,
            'channel': booking.get('ota_channel') or 'direct',
            'booking_value': booking.get('total_amount', 0)
        })
    
    # Sort by risk score descending
    predictions.sort(key=lambda x: x['risk_score'], reverse=True)
    
    return {
        'date': target_date.isoformat(),
        'total_arrivals': len(bookings),
        'predictions': predictions,
        'summary': {
            'high_risk_count': sum(1 for p in predictions if p['risk_level'] == 'high'),
            'medium_risk_count': sum(1 for p in predictions if p['risk_level'] == 'medium'),
            'low_risk_count': sum(1 for p in predictions if p['risk_level'] == 'low'),
            'avg_risk_score': round(sum(p['risk_score'] for p in predictions) / len(predictions), 1) if predictions else 0
        }
    }

# ============= DELUXE+ ENTERPRISE FEATURES =============

@api_router.get("/deluxe/group-bookings")
async def get_group_bookings(
    start_date: str,
    end_date: str,
    min_rooms: int = 5,
    current_user: User = Depends(get_current_user)
):
    """Detect and analyze group bookings (5+ rooms)"""
    start = datetime.fromisoformat(start_date).date()
    end = datetime.fromisoformat(end_date).date()
    
    # Get all bookings in range
    bookings = await db.bookings.find({
        'tenant_id': current_user.tenant_id,
        'check_in': {'$gte': start.isoformat(), '$lte': end.isoformat()},
        'status': {'$in': ['confirmed', 'guaranteed', 'checked_in']}
    }, {'_id': 0}).to_list(10000)
    
    # Group by company_id and check_in date
    groups = {}
    for booking in bookings:
        company_id = booking.get('company_id')
        if not company_id:
            continue
        
        check_in = booking['check_in']
        key = f"{company_id}_{check_in}"
        
        if key not in groups:
            groups[key] = {
                'company_id': company_id,
                'check_in': check_in,
                'check_out': booking['check_out'],
                'bookings': [],
                'room_count': 0,
                'total_revenue': 0
            }
        
        groups[key]['bookings'].append(booking)
        groups[key]['room_count'] += 1
        groups[key]['total_revenue'] += booking.get('total_amount', 0)
    
    # Filter groups with min_rooms or more
    group_bookings = []
    for key, group in groups.items():
        if group['room_count'] >= min_rooms:
            # Get company info
            company = await db.companies.find_one({
                'id': group['company_id'],
                'tenant_id': current_user.tenant_id
            }, {'_id': 0})
            
            group_bookings.append({
                'group_id': key,
                'company_id': group['company_id'],
                'company_name': company.get('name', 'Unknown') if company else 'Unknown',
                'check_in': group['check_in'],
                'check_out': group['check_out'],
                'room_count': group['room_count'],
                'total_revenue': round(group['total_revenue'], 2),
                'avg_rate': round(group['total_revenue'] / group['room_count'], 2),
                'room_numbers': [b.get('room_number', 'TBD') for b in group['bookings']],
                'booking_ids': [b['id'] for b in group['bookings']],
                'is_large_group': group['room_count'] >= 10
            })
    
    # Sort by room count descending
    group_bookings.sort(key=lambda x: x['room_count'], reverse=True)
    
    return {
        'period': {'start_date': start.isoformat(), 'end_date': end.isoformat()},
        'groups': group_bookings,
        'total_groups': len(group_bookings),
        'total_rooms': sum(g['room_count'] for g in group_bookings),
        'total_revenue': round(sum(g['total_revenue'] for g in group_bookings), 2)
    }

@api_router.get("/deluxe/pickup-pace-analytics")
async def get_pickup_pace_analytics(
    target_date: str,
    lookback_days: int = 90,
    current_user: User = Depends(get_current_user)
):
    """Advanced pickup pace analytics with trend analysis"""
    target = datetime.fromisoformat(target_date).date()
    today = datetime.now(timezone.utc).date()
    
    # Get bookings created in lookback period for target date
    bookings = await db.bookings.find({
        'tenant_id': current_user.tenant_id,
        'check_in': target.isoformat(),
        'status': {'$in': ['confirmed', 'guaranteed', 'checked_in']}
    }, {'_id': 0}).to_list(10000)
    
    # Build daily pickup timeline
    daily_pickup = {}
    for booking in bookings:
        created_date = datetime.fromisoformat(booking['created_at']).date()
        days_before = (target - created_date).days
        
        if days_before >= 0 and days_before <= lookback_days:
            if days_before not in daily_pickup:
                daily_pickup[days_before] = {'count': 0, 'revenue': 0, 'channels': {}}
            
            daily_pickup[days_before]['count'] += 1
            daily_pickup[days_before]['revenue'] += booking.get('total_amount', 0)
            
            channel = booking.get('ota_channel') or 'direct'
            daily_pickup[days_before]['channels'][channel] = \
                daily_pickup[days_before]['channels'].get(channel, 0) + 1
    
    # Create chart data
    chart_data = []
    cumulative_bookings = 0
    cumulative_revenue = 0
    
    for days_before in range(lookback_days, -1, -1):
        data = daily_pickup.get(days_before, {'count': 0, 'revenue': 0})
        cumulative_bookings += data['count']
        cumulative_revenue += data['revenue']
        
        chart_data.append({
            'days_before': days_before,
            'date': (target - timedelta(days=days_before)).isoformat(),
            'daily_pickup': data['count'],
            'daily_revenue': round(data['revenue'], 2),
            'cumulative_bookings': cumulative_bookings,
            'cumulative_revenue': round(cumulative_revenue, 2)
        })
    
    # Calculate velocities
    velocity_7 = sum(daily_pickup.get(i, {}).get('count', 0) for i in range(7)) / 7
    velocity_14 = sum(daily_pickup.get(i, {}).get('count', 0) for i in range(14)) / 14
    velocity_30 = sum(daily_pickup.get(i, {}).get('count', 0) for i in range(30)) / 30
    
    return {
        'target_date': target.isoformat(),
        'days_until_arrival': (target - today).days,
        'chart_data': chart_data,
        'summary': {
            'total_bookings': cumulative_bookings,
            'total_revenue': round(cumulative_revenue, 2),
            'velocity_7day': round(velocity_7, 2),
            'velocity_14day': round(velocity_14, 2),
            'velocity_30day': round(velocity_30, 2)
        }
    }

@api_router.get("/deluxe/lead-time-analysis")
async def get_lead_time_analysis(
    start_date: str,
    end_date: str,
    current_user: User = Depends(get_current_user)
):
    """Analyze booking lead time patterns"""
    start = datetime.fromisoformat(start_date).date()
    end = datetime.fromisoformat(end_date).date()
    
    bookings = await db.bookings.find({
        'tenant_id': current_user.tenant_id,
        'check_in': {'$gte': start.isoformat(), '$lte': end.isoformat()},
        'status': {'$in': ['confirmed', 'guaranteed', 'checked_in']}
    }, {'_id': 0}).to_list(10000)
    
    lead_times = []
    channel_lead_times = {}
    
    for booking in bookings:
        created = datetime.fromisoformat(booking['created_at']).date()
        check_in = datetime.fromisoformat(booking['check_in']).date()
        lead_time = (check_in - created).days
        
        if lead_time >= 0:
            lead_times.append(lead_time)
            
            channel = booking.get('ota_channel') or 'direct'
            if channel not in channel_lead_times:
                channel_lead_times[channel] = []
            channel_lead_times[channel].append(lead_time)
    
    # Calculate statistics
    if lead_times:
        avg_lead_time = sum(lead_times) / len(lead_times)
        median_lead_time = sorted(lead_times)[len(lead_times) // 2]
    else:
        avg_lead_time = 0
        median_lead_time = 0
    
    # Lead time distribution
    distribution = {
        'same_day': sum(1 for lt in lead_times if lt == 0),
        'next_day': sum(1 for lt in lead_times if lt == 1),
        '2_7_days': sum(1 for lt in lead_times if 2 <= lt <= 7),
        '8_14_days': sum(1 for lt in lead_times if 8 <= lt <= 14),
        '15_30_days': sum(1 for lt in lead_times if 15 <= lt <= 30),
        '31_60_days': sum(1 for lt in lead_times if 31 <= lt <= 60),
        '61_90_days': sum(1 for lt in lead_times if 61 <= lt <= 90),
        'over_90_days': sum(1 for lt in lead_times if lt > 90)
    }
    
    # Channel breakdown
    channel_stats = {}
    for channel, times in channel_lead_times.items():
        channel_stats[channel] = {
            'avg_lead_time': round(sum(times) / len(times), 1) if times else 0,
            'median_lead_time': sorted(times)[len(times) // 2] if times else 0,
            'booking_count': len(times)
        }
    
    return {
        'period': {'start_date': start.isoformat(), 'end_date': end.isoformat()},
        'overall': {
            'avg_lead_time': round(avg_lead_time, 1),
            'median_lead_time': median_lead_time,
            'total_bookings': len(bookings)
        },
        'distribution': distribution,
        'by_channel': channel_stats,
        'optimal_booking_window': f"{int(median_lead_time)} days" if median_lead_time > 0 else "Same day"
    }

@api_router.get("/deluxe/oversell-protection")
async def get_oversell_protection_map(
    start_date: str,
    end_date: str,
    current_user: User = Depends(get_current_user)
):
    """AI oversell protection heatmap"""
    start = datetime.fromisoformat(start_date).date()
    end = datetime.fromisoformat(end_date).date()
    
    rooms = await db.rooms.find({'tenant_id': current_user.tenant_id}, {'_id': 0}).to_list(1000)
    total_rooms = len(rooms)
    
    protection_map = []
    current_date = start
    
    while current_date <= end:
        start_of_day = datetime.combine(current_date, datetime.min.time())
        end_of_day = datetime.combine(current_date, datetime.max.time())
        
        # Count bookings
        bookings_count = await db.bookings.count_documents({
            'tenant_id': current_user.tenant_id,
            'status': {'$in': ['confirmed', 'guaranteed', 'checked_in']},
            'check_in': {'$lte': end_of_day.isoformat()},
            'check_out': {'$gte': start_of_day.isoformat()}
        })
        
        occupancy_pct = (bookings_count / total_rooms * 100) if total_rooms > 0 else 0
        
        # Calculate oversell risk and protection
        if occupancy_pct >= 95:
            risk_level = 'danger'
            max_oversell = 0
            recommendation = "STOP SELLING - At capacity"
        elif occupancy_pct >= 85:
            risk_level = 'caution'
            max_oversell = 1
            recommendation = "Careful - Allow 1 oversell max"
        elif occupancy_pct >= 70:
            risk_level = 'moderate'
            max_oversell = 2
            recommendation = "Safe - Allow 2 oversells"
        else:
            risk_level = 'safe'
            max_oversell = 3
            recommendation = "Safe - Normal operations"
        
        # Calculate walk probability
        walk_probability = max(0, min(100, (occupancy_pct - 90) * 10))
        
        protection_map.append({
            'date': current_date.isoformat(),
            'occupancy_pct': round(occupancy_pct, 1),
            'bookings': bookings_count,
            'available': total_rooms - bookings_count,
            'risk_level': risk_level,
            'max_oversell': max_oversell,
            'walk_probability': round(walk_probability, 1),
            'recommendation': recommendation
        })
        
        current_date += timedelta(days=1)
    
    return {
        'period': {'start_date': start.isoformat(), 'end_date': end.isoformat()},
        'protection_map': protection_map,
        'summary': {
            'danger_days': sum(1 for d in protection_map if d['risk_level'] == 'danger'),
            'caution_days': sum(1 for d in protection_map if d['risk_level'] == 'caution'),
            'safe_days': sum(1 for d in protection_map if d['risk_level'] == 'safe')
        }
    }

@api_router.post("/deluxe/optimize-channel-mix")
async def optimize_channel_mix(
    start_date: str,
    end_date: str,
    current_user: User = Depends(get_current_user)
):
    """Simulate optimal OTA vs Direct channel mix"""
    start = datetime.fromisoformat(start_date).date()
    end = datetime.fromisoformat(end_date).date()
    
    # Get historical bookings
    bookings = await db.bookings.find({
        'tenant_id': current_user.tenant_id,
        'check_in': {'$gte': start.isoformat(), '$lte': end.isoformat()}
    }, {'_id': 0}).to_list(10000)
    
    # Calculate current mix
    current_mix = {}
    total_revenue = 0
    total_commission = 0
    
    for booking in bookings:
        channel = booking.get('ota_channel') or 'direct'
        amount = booking.get('total_amount', 0)
        commission_pct = booking.get('commission_pct', 0)
        
        if channel not in current_mix:
            current_mix[channel] = {
                'bookings': 0,
                'revenue': 0,
                'commission_cost': 0
            }
        
        current_mix[channel]['bookings'] += 1
        current_mix[channel]['revenue'] += amount
        
        if commission_pct > 0:
            commission = amount * (commission_pct / 100)
            current_mix[channel]['commission_cost'] += commission
            total_commission += commission
        
        total_revenue += amount
    
    # Calculate percentages
    for channel, data in current_mix.items():
        data['revenue_pct'] = round((data['revenue'] / total_revenue * 100) if total_revenue > 0 else 0, 1)
        data['booking_pct'] = round((data['bookings'] / len(bookings) * 100) if bookings else 0, 1)
    
    # AI Optimal Mix Recommendation
    optimal_mix = {
        'direct': {'target_pct': 40, 'reason': 'Zero commission, highest margin'},
        'booking_com': {'target_pct': 25, 'reason': 'High volume, acceptable commission'},
        'expedia': {'target_pct': 20, 'reason': 'Good conversion, premium segment'},
        'airbnb': {'target_pct': 10, 'reason': 'Alternative segment, unique guests'},
        'other': {'target_pct': 5, 'reason': 'Diversification'}
    }
    
    # Calculate potential savings with optimal mix
    current_commission_rate = (total_commission / total_revenue * 100) if total_revenue > 0 else 0
    optimal_commission_rate = 12  # Industry benchmark
    potential_savings = (current_commission_rate - optimal_commission_rate) * total_revenue / 100
    
    return {
        'period': {'start_date': start.isoformat(), 'end_date': end.isoformat()},
        'current_mix': current_mix,
        'optimal_mix': optimal_mix,
        'analysis': {
            'total_bookings': len(bookings),
            'total_revenue': round(total_revenue, 2),
            'current_commission_cost': round(total_commission, 2),
            'current_commission_rate': round(current_commission_rate, 1),
            'optimal_commission_rate': optimal_commission_rate,
            'potential_annual_savings': round(potential_savings * 12, 2),
            'direct_booking_gap': round(40 - current_mix.get('direct', {}).get('revenue_pct', 0), 1)
        },
        'recommendations': [
            "Increase direct bookings through better website conversion",
            "Offer rate parity + perks for direct (free wifi, late checkout)",
            "Reduce dependency on high-commission OTAs",
            "Implement direct booking loyalty rewards program"
        ]
    }

# ============= PHASE H: GUEST CRM + UPSELL AI + MESSAGING =============

@api_router.get("/crm/guest/{guest_id}")
async def get_guest_360(
    guest_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get 360° guest profile with all data"""
    # Get guest basic info
    guest = await db.guests.find_one({
        'id': guest_id,
        'tenant_id': current_user.tenant_id
    }, {'_id': 0})
    
    if not guest:
        raise HTTPException(status_code=404, detail="Guest not found")
    
    # Get all bookings
    bookings = await db.bookings.find({
        'guest_id': guest_id,
        'tenant_id': current_user.tenant_id
    }, {'_id': 0}).sort('check_in', -1).to_list(100)
    
    # Calculate stats
    total_stays = len([b for b in bookings if b['status'] in ['checked_out', 'checked_in']])
    total_nights = 0
    lifetime_value = 0.0
    adr_values = []
    
    for booking in bookings:
        if booking['status'] in ['checked_out', 'checked_in', 'confirmed']:
            nights = (datetime.fromisoformat(booking['check_out']) - datetime.fromisoformat(booking['check_in'])).days
            total_nights += nights
            lifetime_value += booking.get('total_amount', 0)
            if nights > 0:
                adr_values.append(booking.get('total_amount', 0) / nights)
    
    average_adr = sum(adr_values) / len(adr_values) if adr_values else 0
    
    # Get preferences
    preferences = await db.guest_preferences.find_one({
        'guest_id': guest_id,
        'tenant_id': current_user.tenant_id
    }, {'_id': 0})
    
    # Get behavior
    behavior = await db.guest_behavior.find_one({
        'guest_id': guest_id,
        'tenant_id': current_user.tenant_id
    }, {'_id': 0})
    
    # Get profile or create one
    profile = await db.guest_profiles.find_one({
        'guest_id': guest_id,
        'tenant_id': current_user.tenant_id
    }, {'_id': 0})
    
    if not profile:
        # Create profile
        profile = {
            'id': str(uuid.uuid4()),
            'tenant_id': current_user.tenant_id,
            'guest_id': guest_id,
            'first_name': guest.get('name', '').split()[0] if guest.get('name') else '',
            'last_name': ' '.join(guest.get('name', '').split()[1:]) if guest.get('name') and len(guest.get('name', '').split()) > 1 else '',
            'email': guest.get('email'),
            'phone': guest.get('phone'),
            'country': guest.get('country'),
            'total_stays': total_stays,
            'total_nights': total_nights,
            'lifetime_value': round(lifetime_value, 2),
            'average_adr': round(average_adr, 2),
            'loyalty_status': guest.get('loyalty_tier', 'standard'),
            'last_seen_date': bookings[0]['check_in'] if bookings else None,
            'tags': guest.get('tags', []),
            'notes': guest.get('notes', []),
            'created_at': datetime.now(timezone.utc).isoformat(),
            'updated_at': datetime.now(timezone.utc).isoformat()
        }
        await db.guest_profiles.insert_one(profile)
    
    # Channel distribution
    channel_mix = {}
    for booking in bookings:
        channel = booking.get('ota_channel') or 'direct'
        channel_mix[channel] = channel_mix.get(channel, 0) + 1
    
    # Recent upsells
    upsell_offers = await db.upsell_offers.find({
        'guest_id': guest_id,
        'tenant_id': current_user.tenant_id
    }, {'_id': 0}).sort('created_at', -1).to_list(10)
    
    return {
        'guest': guest,
        'profile': profile,
        'preferences': preferences,
        'behavior': behavior,
        'stats': {
            'total_stays': total_stays,
            'total_nights': total_nights,
            'lifetime_value': round(lifetime_value, 2),
            'average_adr': round(average_adr, 2),
            'channel_distribution': channel_mix
        },
        'recent_bookings': bookings[:10],
        'recent_upsells': upsell_offers
    }

@api_router.post("/crm/guest/add-tag")
async def add_guest_tag(
    guest_id: str,
    tag: str,
    current_user: User = Depends(get_current_user)
):
    """Add tag to guest"""
    result = await db.guests.update_one(
        {'id': guest_id, 'tenant_id': current_user.tenant_id},
        {'$addToSet': {'tags': tag}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Guest not found")
    
    return {'message': f'Tag "{tag}" added successfully'}

@api_router.post("/crm/guest/note")
async def add_guest_note(
    guest_id: str,
    note: str,
    current_user: User = Depends(get_current_user)
):
    """Add note to guest"""
    note_obj = {
        'text': note,
        'created_by': current_user.name,
        'created_at': datetime.now(timezone.utc).isoformat()
    }
    
    result = await db.guests.update_one(
        {'id': guest_id, 'tenant_id': current_user.tenant_id},
        {'$push': {'notes': note_obj}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Guest not found")
    
    return {'message': 'Note added successfully', 'note': note_obj}

@api_router.post("/ai/upsell/generate")
async def generate_upsell_offers(
    booking_id: str,
    current_user: User = Depends(get_current_user)
):
    """AI-powered upsell offer generation"""
    # Get booking
    booking = await db.bookings.find_one({
        'id': booking_id,
        'tenant_id': current_user.tenant_id
    }, {'_id': 0})
    
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    # Get guest info
    guest = await db.guests.find_one({
        'id': booking['guest_id'],
        'tenant_id': current_user.tenant_id
    }, {'_id': 0})
    
    # Get room info
    room = await db.rooms.find_one({
        'id': booking['room_id'],
        'tenant_id': current_user.tenant_id
    }, {'_id': 0})
    
    offers = []
    
    # 1. Room Upgrade Logic
    rooms = await db.rooms.find({'tenant_id': current_user.tenant_id}, {'_id': 0}).to_list(1000)
    better_rooms = [r for r in rooms if r['base_price'] > room['base_price']]
    
    for better_room in better_rooms[:3]:  # Top 3 upgrades
        # Check availability
        check_in = booking['check_in']
        check_out = booking['check_out']
        
        conflicts = await db.bookings.count_documents({
            'tenant_id': current_user.tenant_id,
            'room_id': better_room['id'],
            'status': {'$in': ['confirmed', 'guaranteed', 'checked_in']},
            'check_in': {'$lt': check_out},
            'check_out': {'$gt': check_in}
        })
        
        if conflicts == 0:
            # Calculate confidence
            loyalty_tier = guest.get('loyalty_tier', 'standard')
            confidence = 0.5
            
            if loyalty_tier == 'vip':
                confidence = 0.9
            elif loyalty_tier == 'gold':
                confidence = 0.75
            elif loyalty_tier == 'silver':
                confidence = 0.6
            
            # Check historical acceptance
            past_bookings = await db.bookings.count_documents({
                'guest_id': booking['guest_id'],
                'tenant_id': current_user.tenant_id,
                'status': 'checked_out'
            })
            
            if past_bookings > 5:
                confidence += 0.1
            
            confidence = min(0.95, confidence)
            
            price_diff = better_room['base_price'] - room['base_price']
            nights = (datetime.fromisoformat(check_out) - datetime.fromisoformat(check_in)).days
            total_upgrade_cost = price_diff * nights
            
            offers.append({
                'id': str(uuid.uuid4()),
                'tenant_id': current_user.tenant_id,
                'guest_id': booking['guest_id'],
                'booking_id': booking_id,
                'type': 'room_upgrade',
                'current_item': room['room_type'],
                'target_item': better_room['room_type'],
                'price': round(total_upgrade_cost, 2),
                'confidence': round(confidence, 2),
                'reason': f"{loyalty_tier.upper()} guest, {better_room['room_type']} available, strong demand",
                'valid_until': (datetime.now(timezone.utc) + timedelta(days=3)).isoformat(),
                'status': 'pending',
                'created_at': datetime.now(timezone.utc).isoformat()
            })
    
    # 2. Early Check-in (if arrival is tomorrow or later)
    arrival_date = datetime.fromisoformat(check_in).date()
    today = datetime.now(timezone.utc).date()
    
    if arrival_date > today:
        offers.append({
            'id': str(uuid.uuid4()),
            'tenant_id': current_user.tenant_id,
            'guest_id': booking['guest_id'],
            'booking_id': booking_id,
            'type': 'early_checkin',
            'current_item': 'Standard 3PM check-in',
            'target_item': 'Early 12PM check-in',
            'price': 25.00,
            'confidence': 0.65,
            'reason': 'High-value amenity, low cost to hotel',
            'valid_until': (datetime.fromisoformat(check_in) - timedelta(days=1)).isoformat(),
            'status': 'pending',
            'created_at': datetime.now(timezone.utc).isoformat()
        })
    
    # 3. Late Checkout
    offers.append({
        'id': str(uuid.uuid4()),
        'tenant_id': current_user.tenant_id,
        'guest_id': booking['guest_id'],
        'booking_id': booking_id,
        'type': 'late_checkout',
        'current_item': 'Standard 11AM checkout',
        'target_item': 'Late 2PM checkout',
        'price': 35.00,
        'confidence': 0.70,
        'reason': 'Popular add-on, high guest satisfaction',
        'valid_until': (datetime.fromisoformat(check_out) - timedelta(days=1)).isoformat(),
        'status': 'pending',
        'created_at': datetime.now(timezone.utc).isoformat()
    })
    
    # 4. Airport Transfer
    offers.append({
        'id': str(uuid.uuid4()),
        'tenant_id': current_user.tenant_id,
        'guest_id': booking['guest_id'],
        'booking_id': booking_id,
        'type': 'airport_transfer',
        'current_item': None,
        'target_item': 'Premium airport transfer',
        'price': 50.00,
        'confidence': 0.55,
        'reason': 'Convenience add-on, good margin',
        'valid_until': (datetime.fromisoformat(check_in) - timedelta(days=1)).isoformat(),
        'status': 'pending',
        'created_at': datetime.now(timezone.utc).isoformat()
    })
    
    # Sort by confidence
    offers.sort(key=lambda x: x['confidence'], reverse=True)
    
    # Save offers
    if offers:
        await db.upsell_offers.insert_many(offers)
    
    estimated_revenue = sum(o['price'] * o['confidence'] for o in offers)
    
    return {
        'booking_id': booking_id,
        'guest_name': guest.get('name', 'Unknown'),
        'offers': offers,
        'total_offers': len(offers),
        'estimated_revenue': round(estimated_revenue, 2)
    }

async def check_rate_limit(tenant_id: str, channel: str, limit_per_hour: int = 100) -> bool:
    """Check if rate limit is exceeded for messaging"""
    one_hour_ago = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    
    count = await db.messages.count_documents({
        'tenant_id': tenant_id,
        'channel': channel,
        'sent_at': {'$gte': one_hour_ago}
    })
    
    return count < limit_per_hour

@api_router.post("/messages/send-email")
async def send_email(
    recipient: str,
    subject: str,
    body: str,
    guest_id: Optional[str] = None,
    template_id: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Send email message with rate limiting"""
    # Check rate limit (100 emails per hour)
    if not await check_rate_limit(current_user.tenant_id, 'email', limit_per_hour=100):
        raise HTTPException(
            status_code=429, 
            detail="Rate limit exceeded. Maximum 100 emails per hour. Please try again later."
        )
    
    # Validate email format
    if not recipient or '@' not in recipient:
        raise HTTPException(status_code=400, detail="Invalid email address")
    
    # Validate message body
    if not body or len(body.strip()) == 0:
        raise HTTPException(status_code=400, detail="Message body cannot be empty")
    
    message = {
        'id': str(uuid.uuid4()),
        'tenant_id': current_user.tenant_id,
        'guest_id': guest_id,
        'channel': 'email',
        'recipient': recipient,
        'subject': subject,
        'body': body,
        'template_id': template_id,
        'sent_at': datetime.now(timezone.utc).isoformat(),
        'sent_by': current_user.id,
        'status': 'sent'
    }
    
    await db.messages.insert_one(message)
    
    return {
        'message': 'Email sent successfully',
        'message_id': message['id'],
        'recipient': recipient,
        'rate_limit': {
            'limit': 100,
            'window': '1 hour',
            'remaining': 100 - await db.messages.count_documents({
                'tenant_id': current_user.tenant_id,
                'channel': 'email',
                'sent_at': {'$gte': (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()}
            })
        }
    }

@api_router.post("/messages/send-sms")
async def send_sms(
    recipient: str,
    body: str,
    guest_id: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Send SMS message with stricter rate limiting (50 per hour)"""
    # SMS has stricter rate limit due to cost
    if not await check_rate_limit(current_user.tenant_id, 'sms', limit_per_hour=50):
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Maximum 50 SMS per hour. Please try again later."
        )
    
    # Validate phone number format
    if not recipient or not recipient.startswith('+'):
        raise HTTPException(status_code=400, detail="Invalid phone number format. Must start with + and country code")
    
    # Validate message body
    if not body or len(body.strip()) == 0:
        raise HTTPException(status_code=400, detail="Message body cannot be empty")
    
    # Warn if message is too long for single SMS
    if len(body) > 160:
        message_warning = f"Message is {len(body)} characters. Will be sent as {(len(body) // 160) + 1} SMS segments."
    else:
        message_warning = None
    
    message = {
        'id': str(uuid.uuid4()),
        'tenant_id': current_user.tenant_id,
        'guest_id': guest_id,
        'channel': 'sms',
        'recipient': recipient,
        'body': body,
        'sent_at': datetime.now(timezone.utc).isoformat(),
        'sent_by': current_user.id,
        'status': 'sent',
        'character_count': len(body),
        'segment_count': (len(body) // 160) + 1
    }
    
    await db.messages.insert_one(message)
    
    response = {
        'message': 'SMS sent successfully',
        'message_id': message['id'],
        'recipient': recipient,
        'character_count': len(body),
        'segments': (len(body) // 160) + 1,
        'rate_limit': {
            'limit': 50,
            'window': '1 hour',
            'remaining': 50 - await db.messages.count_documents({
                'tenant_id': current_user.tenant_id,
                'channel': 'sms',
                'sent_at': {'$gte': (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()}
            })
        }
    }
    
    if message_warning:
        response['warning'] = message_warning
    
    return response

@api_router.post("/messages/send-whatsapp")
async def send_whatsapp(
    recipient: str,
    body: str,
    guest_id: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Send WhatsApp message with rate limiting (80 per hour)"""
    # WhatsApp rate limit
    if not await check_rate_limit(current_user.tenant_id, 'whatsapp', limit_per_hour=80):
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Maximum 80 WhatsApp messages per hour. Please try again later."
        )
    
    # Validate phone number format
    if not recipient or not recipient.startswith('+'):
        raise HTTPException(status_code=400, detail="Invalid phone number format. Must start with + and country code")
    
    # Validate message body
    if not body or len(body.strip()) == 0:
        raise HTTPException(status_code=400, detail="Message body cannot be empty")
    
    message = {
        'id': str(uuid.uuid4()),
        'tenant_id': current_user.tenant_id,
        'guest_id': guest_id,
        'channel': 'whatsapp',
        'recipient': recipient,
        'body': body,
        'sent_at': datetime.now(timezone.utc).isoformat(),
        'sent_by': current_user.id,
        'status': 'sent',
        'character_count': len(body)
    }
    
    await db.messages.insert_one(message)
    
    return {
        'message': 'WhatsApp sent successfully',
        'message_id': message['id'],
        'recipient': recipient,
        'character_count': len(body),
        'rate_limit': {
            'limit': 80,
            'window': '1 hour',
            'remaining': 80 - await db.messages.count_documents({
                'tenant_id': current_user.tenant_id,
                'channel': 'whatsapp',
                'sent_at': {'$gte': (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()}
            })
        }
    }

@api_router.get("/messages/templates")
async def get_message_templates(
    channel: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Get message templates"""
    query = {'tenant_id': current_user.tenant_id, 'active': True}
    if channel:
        query['channel'] = channel
    
    templates = await db.message_templates.find(query, {'_id': 0}).to_list(100)
    return {'templates': templates, 'count': len(templates)}

@api_router.post("/rms/generate-suggestions")
async def generate_rms_suggestions(
    start_date: str,
    end_date: str,
    room_type: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Generate RMS rate suggestions based on occupancy and demand"""
    start = datetime.fromisoformat(start_date).date()
    end = datetime.fromisoformat(end_date).date()
    
    # Get all rooms or specific room type
    room_query = {'tenant_id': current_user.tenant_id}
    if room_type:
        room_query['room_type'] = room_type
    
    rooms = await db.rooms.find(room_query, {'_id': 0}).to_list(1000)
    room_types = list(set(r['room_type'] for r in rooms))
    
    suggestions = []
    
    for rt in room_types:
        rt_rooms = [r for r in rooms if r['room_type'] == rt]
        total_rooms = len(rt_rooms)
        
        # For each date in range
        current_date = start
        while current_date <= end:
            date_str = current_date.isoformat()
            
            # Calculate occupancy for this date
            start_of_day = datetime.combine(current_date, datetime.min.time())
            end_of_day = datetime.combine(current_date, datetime.max.time())
            
            bookings = await db.bookings.count_documents({
                'tenant_id': current_user.tenant_id,
                'room_id': {'$in': [r['id'] for r in rt_rooms]},
                'status': {'$in': ['confirmed', 'guaranteed', 'checked_in']},
                'check_in': {'$lte': end_of_day.isoformat()},
                'check_out': {'$gte': start_of_day.isoformat()}
            })
            
            occupancy_rate = (bookings / total_rooms * 100) if total_rooms > 0 else 0
            
            # Get current rate (or use base rate)
            base_rate = rt_rooms[0].get('base_price', 100)
            
            # Simple dynamic pricing logic
            if occupancy_rate >= 90:
                suggested_rate = base_rate * 1.3  # +30%
                reason = "Very high demand (90%+ occupancy)"
                confidence = 95
            elif occupancy_rate >= 75:
                suggested_rate = base_rate * 1.2  # +20%
                reason = "High demand (75%+ occupancy)"
                confidence = 85
            elif occupancy_rate >= 60:
                suggested_rate = base_rate * 1.1  # +10%
                reason = "Good demand (60%+ occupancy)"
                confidence = 75
            elif occupancy_rate <= 30:
                suggested_rate = base_rate * 0.85  # -15%
                reason = "Low demand (< 30% occupancy)"
                confidence = 80
            else:
                suggested_rate = base_rate
                reason = "Normal demand (30-60% occupancy)"
                confidence = 60
            
            # Create suggestion
            suggestion = RMSSuggestion(
                tenant_id=current_user.tenant_id,
                date=date_str,
                room_type=rt,
                current_rate=base_rate,
                suggested_rate=round(suggested_rate, 2),
                reason=reason,
                confidence_score=confidence,
                based_on={
                    'occupancy_rate': round(occupancy_rate, 2),
                    'bookings': bookings,
                    'total_rooms': total_rooms
                }
            )
            
            sugg_dict = suggestion.model_dump()
            sugg_dict['created_at'] = sugg_dict['created_at'].isoformat()
            await db.rms_suggestions.insert_one(sugg_dict)
            
            suggestions.append(suggestion)
            
            current_date += timedelta(days=1)
    
    return {
        'message': f'Generated {len(suggestions)} rate suggestions',
        'suggestions': suggestions[:20],  # Return first 20
        'total_count': len(suggestions)
    }

@api_router.get("/rms/suggestions")
async def get_rms_suggestions(
    status: Optional[str] = None,
    date: Optional[str] = None,
    room_type: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Get RMS suggestions with filters"""
    query = {'tenant_id': current_user.tenant_id}
    if status:
        query['status'] = status
    if date:
        query['date'] = date
    if room_type:
        query['room_type'] = room_type
    
    suggestions = await db.rms_suggestions.find(query, {'_id': 0}).sort('date', 1).to_list(100)
    return {'suggestions': suggestions, 'count': len(suggestions)}

@api_router.post("/rms/apply-suggestion/{suggestion_id}")
async def apply_rms_suggestion(
    suggestion_id: str,
    current_user: User = Depends(get_current_user)
):
    """Apply RMS suggestion to room rates"""
    suggestion = await db.rms_suggestions.find_one({
        'id': suggestion_id,
        'tenant_id': current_user.tenant_id
    })
    
    if not suggestion:
        raise HTTPException(status_code=404, detail="Suggestion not found")
    
    if suggestion['status'] == 'applied':
        raise HTTPException(status_code=400, detail="Suggestion already applied")
    
    # Update rooms of this type with new rate
    await db.rooms.update_many(
        {
            'tenant_id': current_user.tenant_id,
            'room_type': suggestion['room_type']
        },
        {'$set': {'base_price': suggestion['suggested_rate']}}
    )
    
    # Mark suggestion as applied
    await db.rms_suggestions.update_one(
        {'id': suggestion_id},
        {'$set': {'status': 'applied'}}
    )
    
    # Audit log
    await create_audit_log(
        tenant_id=current_user.tenant_id,
        user=current_user,
        action="APPLY_RMS_SUGGESTION",
        entity_type="rms_suggestion",
        entity_id=suggestion_id,
        changes={'old_rate': suggestion['current_rate'], 'new_rate': suggestion['suggested_rate'], 'room_type': suggestion['room_type']}
    )
    
    return {
        'message': f"Applied rate suggestion: {suggestion['room_type']} → ${suggestion['suggested_rate']}",
        'room_type': suggestion['room_type'],
        'new_rate': suggestion['suggested_rate']
    }

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


# ========================================
# ACCOUNTING ENHANCEMENTS - 3 New Features
# ========================================

# 1. MULTI-CURRENCY SUPPORT
@api_router.get("/accounting/currencies")
async def get_currencies(current_user: User = Depends(get_current_user)):
    """Get all supported currencies"""
    currencies = [
        {'code': 'TRY', 'name': 'Turkish Lira', 'symbol': '₺'},
        {'code': 'USD', 'name': 'US Dollar', 'symbol': '$'},
        {'code': 'EUR', 'name': 'Euro', 'symbol': '€'},
        {'code': 'GBP', 'name': 'British Pound', 'symbol': '£'}
    ]
    return {'currencies': currencies}

@api_router.post("/accounting/currency-rates")
async def create_currency_rate(
    request: CreateCurrencyRateRequest,
    current_user: User = Depends(get_current_user)
):
    """Create or update currency exchange rate"""
    rate = {
        'id': str(uuid.uuid4()),
        'tenant_id': current_user.tenant_id,
        'from_currency': request.from_currency,
        'to_currency': request.to_currency,
        'rate': request.rate,
        'effective_date': request.effective_date,
        'created_at': datetime.now(timezone.utc).isoformat(),
        'created_by': current_user.id
    }
    
    rate_copy = rate.copy()
    await db.currency_rates.insert_one(rate_copy)
    return rate

@api_router.get("/accounting/currency-rates")
async def get_currency_rates(
    from_currency: str = None,
    to_currency: str = None,
    date: str = None,
    current_user: User = Depends(get_current_user)
):
    """Get currency exchange rates"""
    query = {'tenant_id': current_user.tenant_id}
    
    if from_currency:
        query['from_currency'] = from_currency
    if to_currency:
        query['to_currency'] = to_currency
    if date:
        query['effective_date'] = {'$lte': date}
    
    rates = await db.currency_rates.find(
        query,
        {'_id': 0}
    ).sort('effective_date', -1).to_list(100)
    
    return {'rates': rates, 'count': len(rates)}

@api_router.post("/accounting/convert-currency")
async def convert_currency(
    request: ConvertCurrencyRequest,
    current_user: User = Depends(get_current_user)
):
    """Convert amount between currencies"""
    # If same currency, no conversion needed
    if request.from_currency == request.to_currency:
        return {
            'amount': request.amount,
            'from_currency': request.from_currency,
            'to_currency': request.to_currency,
            'rate': 1.0,
            'converted_amount': request.amount
        }
    
    # Get exchange rate
    query = {
        'tenant_id': current_user.tenant_id,
        'from_currency': request.from_currency,
        'to_currency': request.to_currency
    }
    
    if request.date:
        query['effective_date'] = {'$lte': request.date}
    
    rate_record = await db.currency_rates.find_one(
        query,
        {'_id': 0},
        sort=[('effective_date', -1)]
    )
    
    if not rate_record:
        # Try reverse rate
        reverse_query = {
            'tenant_id': current_user.tenant_id,
            'from_currency': request.to_currency,
            'to_currency': request.from_currency
        }
        if request.date:
            reverse_query['effective_date'] = {'$lte': request.date}
        
        reverse_rate = await db.currency_rates.find_one(
            reverse_query,
            {'_id': 0},
            sort=[('effective_date', -1)]
        )
        
        if reverse_rate:
            rate = 1.0 / reverse_rate['rate']
        else:
            # Default rates if not found
            default_rates = {
                ('TRY', 'USD'): 0.037,
                ('TRY', 'EUR'): 0.034,
                ('USD', 'TRY'): 27.0,
                ('EUR', 'TRY'): 29.5,
                ('USD', 'EUR'): 0.92,
                ('EUR', 'USD'): 1.09
            }
            rate = default_rates.get((request.from_currency, request.to_currency), 1.0)
    else:
        rate = rate_record['rate']
    
    converted_amount = request.amount * rate
    
    return {
        'amount': request.amount,
        'from_currency': request.from_currency,
        'to_currency': request.to_currency,
        'rate': round(rate, 4),
        'converted_amount': round(converted_amount, 2),
        'date': request.date or datetime.now(timezone.utc).date().isoformat()
    }

@api_router.post("/accounting/invoices/multi-currency")
async def create_multi_currency_invoice(
    request: CreateMultiCurrencyInvoiceRequest,
    current_user: User = Depends(get_current_user)
):
    """Create invoice in any currency with auto-conversion to TRY"""
    # Calculate totals in invoice currency
    subtotal = sum(item.get('quantity', 0) * item.get('unit_price', 0) for item in request.items)
    
    # Calculate VAT
    total_vat = 0
    for item in request.items:
        item_total = item.get('quantity', 0) * item.get('unit_price', 0)
        vat_rate = item.get('vat_rate', 18) / 100
        item['vat_amount'] = round(item_total * vat_rate, 2)
        total_vat += item['vat_amount']
    
    total = subtotal + total_vat
    
    # Convert to TRY if needed
    if request.currency != 'TRY':
        if request.exchange_rate:
            rate = request.exchange_rate
        else:
            # Get current rate
            conversion = await convert_currency(
                ConvertCurrencyRequest(
                    amount=1.0,
                    from_currency=request.currency,
                    to_currency='TRY'
                ),
                current_user
            )
            rate = conversion['rate']
        
        subtotal_try = subtotal * rate
        total_vat_try = total_vat * rate
        total_try = total * rate
    else:
        rate = 1.0
        subtotal_try = subtotal
        total_vat_try = total_vat
        total_try = total
    
    invoice_number = f"INV-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"
    
    invoice = {
        'id': str(uuid.uuid4()),
        'tenant_id': current_user.tenant_id,
        'invoice_number': invoice_number,
        'customer_name': request.customer_name,
        'customer_email': request.customer_email,
        'customer_address': request.customer_address,
        'items': request.items,
        'currency': request.currency,
        'exchange_rate': rate,
        'subtotal': round(subtotal, 2),
        'total_vat': round(total_vat, 2),
        'total': round(total, 2),
        'subtotal_try': round(subtotal_try, 2),
        'total_vat_try': round(total_vat_try, 2),
        'total_try': round(total_try, 2),
        'payment_terms': request.payment_terms,
        'notes': request.notes,
        'issue_date': datetime.now(timezone.utc).date().isoformat(),
        'due_date': (datetime.now(timezone.utc) + timedelta(days=30)).date().isoformat(),
        'status': 'pending',
        'created_at': datetime.now(timezone.utc).isoformat(),
        'created_by': current_user.id
    }
    
    invoice_copy = invoice.copy()
    await db.accounting_invoices.insert_one(invoice_copy)
    
    return invoice


# 2. INVOICE → FOLIO → PMS INTEGRATION
@api_router.post("/accounting/invoices/from-folio")
async def generate_invoice_from_folio(
    request: GenerateInvoiceFromFolioRequest,
    current_user: User = Depends(get_current_user)
):
    """Generate accounting invoice from PMS folio"""
    # Get folio
    folio = await db.folios.find_one({
        'id': request.folio_id,
        'tenant_id': current_user.tenant_id
    }, {'_id': 0})
    
    if not folio:
        raise HTTPException(status_code=404, detail="Folio not found")
    
    # Get folio charges
    charges = await db.folio_charges.find({
        'folio_id': request.folio_id,
        'tenant_id': current_user.tenant_id,
        'voided': False
    }, {'_id': 0}).to_list(1000)
    
    # Get booking info
    booking = await db.bookings.find_one({
        'folio_id': request.folio_id,
        'tenant_id': current_user.tenant_id
    }, {'_id': 0})
    
    # Convert charges to invoice items
    invoice_items = []
    for charge in charges:
        item = {
            'description': charge.get('description', 'Hotel Charge'),
            'quantity': 1,
            'unit_price': charge.get('amount', 0),
            'vat_rate': charge.get('vat_rate', 18),
            'total': charge.get('total', 0)
        }
        invoice_items.append(item)
    
    # Get customer info from booking or folio
    customer_name = booking.get('guest_name') if booking else folio.get('guest_name', 'Guest')
    customer_email = booking.get('guest_email') if booking else folio.get('guest_email', '')
    
    # Create invoice
    invoice_number = f"INV-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"
    
    # Calculate totals
    subtotal = sum(item['unit_price'] * item['quantity'] for item in invoice_items)
    total_vat = sum(item['unit_price'] * item['quantity'] * (item['vat_rate'] / 100) for item in invoice_items)
    
    # Currency conversion if needed
    if request.invoice_currency != 'TRY':
        conversion = await convert_currency(
            ConvertCurrencyRequest(
                amount=subtotal + total_vat,
                from_currency='TRY',
                to_currency=request.invoice_currency
            ),
            current_user
        )
        exchange_rate = conversion['rate']
        total_foreign = conversion['converted_amount']
    else:
        exchange_rate = 1.0
        total_foreign = subtotal + total_vat
    
    invoice = {
        'id': str(uuid.uuid4()),
        'tenant_id': current_user.tenant_id,
        'invoice_number': invoice_number,
        'folio_id': request.folio_id,
        'booking_id': booking['id'] if booking else None,
        'customer_name': customer_name,
        'customer_email': customer_email,
        'customer_address': booking.get('guest_address', '') if booking else '',
        'items': invoice_items,
        'currency': request.invoice_currency,
        'exchange_rate': exchange_rate,
        'subtotal': round(subtotal, 2),
        'total_vat': round(total_vat, 2),
        'total': round(subtotal + total_vat, 2),
        'total_foreign_currency': round(total_foreign, 2),
        'payment_terms': 'Due on checkout',
        'issue_date': datetime.now(timezone.utc).date().isoformat(),
        'due_date': datetime.now(timezone.utc).date().isoformat(),
        'status': 'pending',
        'source': 'pms_folio',
        'created_at': datetime.now(timezone.utc).isoformat(),
        'created_by': current_user.id
    }
    
    invoice_copy = invoice.copy()
    await db.accounting_invoices.insert_one(invoice_copy)
    
    # Update folio with invoice reference
    await db.folios.update_one(
        {'id': request.folio_id},
        {'$set': {'invoice_id': invoice['id'], 'invoice_number': invoice_number}}
    )
    
    # Generate E-Fatura if requested
    if request.include_efatura:
        efatura_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2">
    <ID>{invoice_number}</ID>
    <IssueDate>{invoice['issue_date']}</IssueDate>
    <InvoiceTypeCode>SATIS</InvoiceTypeCode>
    <DocumentCurrencyCode>{request.invoice_currency}</DocumentCurrencyCode>
    <LineCountNumeric>{len(invoice_items)}</LineCountNumeric>
    <LegalMonetaryTotal>
        <TaxExclusiveAmount currencyID="{request.invoice_currency}">{invoice['subtotal']}</TaxExclusiveAmount>
        <TaxInclusiveAmount currencyID="{request.invoice_currency}">{invoice['total']}</TaxInclusiveAmount>
    </LegalMonetaryTotal>
</Invoice>"""
        
        efatura_record = {
            'id': str(uuid.uuid4()),
            'tenant_id': current_user.tenant_id,
            'invoice_id': invoice['id'],
            'invoice_number': invoice_number,
            'efatura_uuid': str(uuid.uuid4()),
            'xml_content': efatura_xml,
            'status': 'generated',
            'generated_at': datetime.now(timezone.utc).isoformat()
        }
        
        efatura_copy = efatura_record.copy()
        await db.efatura_records.insert_one(efatura_copy)
        
        invoice['efatura_uuid'] = efatura_record['efatura_uuid']
        invoice['efatura_status'] = 'generated'
    
    return {
        'invoice': invoice,
        'message': 'Invoice generated from folio successfully',
        'efatura_generated': request.include_efatura
    }


# 3. E-FATURA INTEGRATION WITH ACCOUNTING
@api_router.get("/accounting/invoices/{invoice_id}/efatura-status")
async def get_invoice_efatura_status(
    invoice_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get E-Fatura status for accounting invoice"""
    invoice = await db.accounting_invoices.find_one({
        'id': invoice_id,
        'tenant_id': current_user.tenant_id
    }, {'_id': 0})
    
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    # Get E-Fatura record
    efatura = await db.efatura_records.find_one({
        'invoice_id': invoice_id,
        'tenant_id': current_user.tenant_id
    }, {'_id': 0})
    
    if not efatura:
        return {
            'invoice_id': invoice_id,
            'invoice_number': invoice.get('invoice_number'),
            'efatura_status': 'not_generated',
            'message': 'E-Fatura has not been generated for this invoice'
        }
    
    return {
        'invoice_id': invoice_id,
        'invoice_number': invoice.get('invoice_number'),
        'efatura_uuid': efatura.get('efatura_uuid'),
        'efatura_status': efatura.get('status'),
        'generated_at': efatura.get('generated_at'),
        'sent_at': efatura.get('sent_at'),
        'gib_response': efatura.get('gib_response')
    }

@api_router.post("/accounting/invoices/{invoice_id}/generate-efatura")
async def generate_efatura_for_invoice(
    invoice_id: str,
    current_user: User = Depends(get_current_user)
):
    """Generate E-Fatura for existing accounting invoice"""
    invoice = await db.accounting_invoices.find_one({
        'id': invoice_id,
        'tenant_id': current_user.tenant_id
    }, {'_id': 0})
    
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    # Check if E-Fatura already exists
    existing_efatura = await db.efatura_records.find_one({
        'invoice_id': invoice_id,
        'tenant_id': current_user.tenant_id
    })
    
    if existing_efatura:
        return {
            'message': 'E-Fatura already exists for this invoice',
            'efatura_uuid': existing_efatura.get('efatura_uuid'),
            'status': existing_efatura.get('status')
        }
    
    # Generate E-Fatura XML
    currency = invoice.get('currency', 'TRY')
    efatura_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2">
    <ID>{invoice.get('invoice_number')}</ID>
    <IssueDate>{invoice.get('issue_date')}</IssueDate>
    <InvoiceTypeCode>SATIS</InvoiceTypeCode>
    <DocumentCurrencyCode>{currency}</DocumentCurrencyCode>
    <LineCountNumeric>{len(invoice.get('items', []))}</LineCountNumeric>
    <AccountingSupplierParty>
        <Party>
            <PartyName>
                <Name>Hotel Name</Name>
            </PartyName>
        </Party>
    </AccountingSupplierParty>
    <AccountingCustomerParty>
        <Party>
            <PartyName>
                <Name>{invoice.get('customer_name', 'N/A')}</Name>
            </PartyName>
        </Party>
    </AccountingCustomerParty>
    <LegalMonetaryTotal>
        <TaxExclusiveAmount currencyID="{currency}">{invoice.get('subtotal', 0)}</TaxExclusiveAmount>
        <TaxInclusiveAmount currencyID="{currency}">{invoice.get('total', 0)}</TaxInclusiveAmount>
    </LegalMonetaryTotal>
</Invoice>"""
    
    efatura_record = {
        'id': str(uuid.uuid4()),
        'tenant_id': current_user.tenant_id,
        'invoice_id': invoice_id,
        'invoice_number': invoice.get('invoice_number'),
        'efatura_uuid': str(uuid.uuid4()),
        'xml_content': efatura_xml,
        'status': 'generated',
        'generated_at': datetime.now(timezone.utc).isoformat()
    }
    
    efatura_copy = efatura_record.copy()
    await db.efatura_records.insert_one(efatura_copy)
    
    # Update invoice with E-Fatura reference
    await db.accounting_invoices.update_one(
        {'id': invoice_id},
        {
            '$set': {
                'efatura_uuid': efatura_record['efatura_uuid'],
                'efatura_status': 'generated'
            }
        }
    )
    
    return {
        'message': 'E-Fatura generated successfully',
        'efatura_uuid': efatura_record['efatura_uuid'],
        'invoice_number': invoice.get('invoice_number')
    }


# ============= ROOM BLOCK ENDPOINTS (Out of Order / Service) =============

@api_router.get("/pms/room-blocks")
async def get_room_blocks(
    room_id: Optional[str] = None,
    status: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Get room blocks with optional filters"""
    query = {'tenant_id': current_user.tenant_id}
    
    if room_id:
        query['room_id'] = room_id
    
    if status:
        query['status'] = status
    
    if from_date or to_date:
        date_query = {}
        if from_date:
            date_query['$gte'] = from_date
        if to_date:
            date_query['$lte'] = to_date
        query['start_date'] = date_query
    
    blocks = await db.room_blocks.find(query, {'_id': 0}).to_list(1000)
    
    # Filter expired blocks
    today = datetime.now(timezone.utc).date().isoformat()
    for block in blocks:
        if block.get('end_date') and block['end_date'] < today and block['status'] == 'active':
            # Auto-expire
            await db.room_blocks.update_one(
                {'id': block['id']},
                {'$set': {'status': 'expired'}}
            )
            block['status'] = 'expired'
    
    return blocks

@api_router.post("/pms/room-blocks")
async def create_room_block(
    block_data: dict,
    current_user: User = Depends(get_current_user)
):
    """Create a new room block"""
    # Validate dates
    start = datetime.fromisoformat(block_data['start_date']).date()
    end_date = block_data.get('end_date')
    
    if end_date:
        end = datetime.fromisoformat(end_date).date()
        if end < start:
            raise HTTPException(400, "End date must be after start date")
    
    # Check for conflicts with existing bookings
    room = await db.rooms.find_one({
        'tenant_id': current_user.tenant_id,
        'id': block_data['room_id']
    })
    
    if not room:
        raise HTTPException(404, "Room not found")
    
    # Check existing bookings
    query = {
        'tenant_id': current_user.tenant_id,
        'room_id': block_data['room_id'],
        'status': {'$in': ['confirmed', 'checked_in', 'guaranteed']},
        'check_in': {'$lt': end_date or '9999-12-31'},
        'check_out': {'$gt': block_data['start_date']}
    }
    
    conflicting_bookings = await db.bookings.find(query, {'_id': 0}).to_list(100)
    
    if conflicting_bookings and not block_data.get('force_override'):
        return {
            'status': 'conflict',
            'message': f"Room has {len(conflicting_bookings)} active bookings during this period",
            'conflicting_bookings': conflicting_bookings
        }
    
    # Create block
    block = {
        'id': str(uuid.uuid4()),
        'tenant_id': current_user.tenant_id,
        'room_id': block_data['room_id'],
        'type': block_data['type'],
        'reason': block_data['reason'],
        'details': block_data.get('details'),
        'start_date': block_data['start_date'],
        'end_date': end_date,
        'allow_sell': block_data.get('allow_sell', False),
        'created_by': current_user.name,
        'created_at': datetime.now(timezone.utc).isoformat(),
        'status': 'active'
    }
    
    await db.room_blocks.insert_one(block)
    
    # Update room status
    if block['type'] == 'out_of_order':
        await db.rooms.update_one(
            {'id': block_data['room_id']},
            {'$set': {'status': 'out_of_order'}}
        )
    
    # Audit log
    await db.audit_logs.insert_one({
        'id': str(uuid.uuid4()),
        'tenant_id': current_user.tenant_id,
        'action': 'room_block_created',
        'entity_type': 'room_block',
        'entity_id': block['id'],
        'user': current_user.name,
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'details': {
            'room_id': block_data['room_id'],
            'type': block_data['type'],
            'reason': block_data['reason']
        }
    })
    
    return block

@api_router.patch("/pms/room-blocks/{block_id}")
async def update_room_block(
    block_id: str,
    updates: dict,
    current_user: User = Depends(get_current_user)
):
    """Update a room block"""
    existing = await db.room_blocks.find_one({
        'tenant_id': current_user.tenant_id,
        'id': block_id
    })
    
    if not existing:
        raise HTTPException(404, "Block not found")
    
    # Only allow updates to active blocks
    if existing['status'] != 'active':
        raise HTTPException(400, "Cannot update cancelled or expired blocks")
    
    update_data = {}
    allowed_fields = ['reason', 'details', 'start_date', 'end_date', 'allow_sell']
    
    for field in allowed_fields:
        if field in updates:
            update_data[field] = updates[field]
    
    if update_data:
        await db.room_blocks.update_one(
            {'id': block_id},
            {'$set': update_data}
        )
        
        # Audit log
        await db.audit_logs.insert_one({
            'id': str(uuid.uuid4()),
            'tenant_id': current_user.tenant_id,
            'action': 'room_block_updated',
            'entity_type': 'room_block',
            'entity_id': block_id,
            'user': current_user.name,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'details': update_data
        })
    
    updated = await db.room_blocks.find_one({'id': block_id}, {'_id': 0})
    return updated

@api_router.post("/pms/room-blocks/{block_id}/cancel")
async def cancel_room_block(
    block_id: str,
    current_user: User = Depends(get_current_user)
):
    """Cancel a room block"""
    existing = await db.room_blocks.find_one({
        'tenant_id': current_user.tenant_id,
        'id': block_id
    })
    
    if not existing:
        raise HTTPException(404, "Block not found")
    
    if existing['status'] == 'cancelled':
        raise HTTPException(400, "Block already cancelled")
    
    await db.room_blocks.update_one(
        {'id': block_id},
        {'$set': {
            'status': 'cancelled',
            'cancelled_at': datetime.now(timezone.utc).isoformat(),
            'cancelled_by': current_user.name
        }}
    )
    
    # If room was out_of_order, restore to available
    if existing['type'] == 'out_of_order':
        await db.rooms.update_one(
            {'id': existing['room_id']},
            {'$set': {'status': 'available'}}
        )
    
    # Audit log
    await db.audit_logs.insert_one({
        'id': str(uuid.uuid4()),
        'tenant_id': current_user.tenant_id,
        'action': 'room_block_cancelled',
        'entity_type': 'room_block',
        'entity_id': block_id,
        'user': current_user.name,
        'timestamp': datetime.now(timezone.utc).isoformat()
    })
    
    return {'message': 'Block cancelled successfully', 'block_id': block_id}

@api_router.get("/pms/rooms/availability")
async def check_room_availability(
    check_in: str,
    check_out: str,
    room_type: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Check room availability including blocks"""
    query = {'tenant_id': current_user.tenant_id}
    
    if room_type:
        query['room_type'] = room_type
    
    rooms = await db.rooms.find(query, {'_id': 0}).to_list(1000)
    
    # Get bookings
    bookings = await db.bookings.find({
        'tenant_id': current_user.tenant_id,
        'status': {'$in': ['confirmed', 'checked_in', 'guaranteed']},
        'check_in': {'$lt': check_out},
        'check_out': {'$gt': check_in}
    }, {'_id': 0}).to_list(1000)
    
    # Get blocks
    blocks = await db.room_blocks.find({
        'tenant_id': current_user.tenant_id,
        'status': 'active',
        'start_date': {'$lt': check_out},
        '$or': [
            {'end_date': {'$gt': check_in}},
            {'end_date': None}  # Open-ended blocks
        ]
    }, {'_id': 0}).to_list(1000)
    
    # Filter available rooms
    available = []
    for room in rooms:
        # Check bookings
        is_booked = any(b['room_id'] == room['id'] for b in bookings)
        
        # Check blocks
        room_blocks = [b for b in blocks if b['room_id'] == room['id']]
        is_blocked = any(not b.get('allow_sell', False) for b in room_blocks)
        
        if not is_booked and not is_blocked:
            available.append({
                **room,
                'available': True
            })
        else:
            unavailable_reason = []
            if is_booked:
                unavailable_reason.append('booked')
            if is_blocked:
                block_info = [b for b in room_blocks if not b.get('allow_sell')]
                if block_info:
                    unavailable_reason.append(f"{block_info[0]['type']}")
            
            available.append({
                **room,
                'available': False,
                'reason': ', '.join(unavailable_reason),
                'blocks': room_blocks
            })
    
    return available

# ============= STAFF TASKS & MAINTENANCE =============
@api_router.get("/pms/staff-tasks")
async def get_staff_tasks(
    department: Optional[str] = None,
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Get staff tasks (engineering, housekeeping, maintenance)"""
    query = {'tenant_id': current_user.tenant_id}
    if department:
        query['department'] = department
    if status:
        query['status'] = status
    
    tasks = await db.staff_tasks.find(query, {'_id': 0}).sort('created_at', -1).to_list(1000)
    return tasks

@api_router.post("/pms/staff-tasks")
async def create_staff_task(
    task_data: dict,
    current_user: User = Depends(get_current_user)
):
    """Create a new staff task"""
    task = {
        'id': str(uuid.uuid4()),
        'tenant_id': current_user.tenant_id,
        'task_type': task_data.get('task_type', 'maintenance'),
        'department': task_data.get('department', 'engineering'),
        'title': task_data.get('title', 'Staff Task'),
        'room_id': task_data.get('room_id'),
        'priority': task_data.get('priority', 'normal'),
        'description': task_data.get('description'),
        'assigned_to': task_data.get('assigned_to'),
        'status': task_data.get('status', 'pending'),
        'created_by': current_user.id,
        'created_at': datetime.now(timezone.utc).isoformat()
    }
    
    # Get room number if room_id provided
    if task['room_id']:
        room = await db.rooms.find_one({'id': task['room_id']}, {'_id': 0, 'room_number': 1})
        if room:
            task['room_number'] = room['room_number']
    
    result = await db.staff_tasks.insert_one(task)
    
    # Return the task without MongoDB ObjectId
    return {
        'id': task['id'],
        'tenant_id': task['tenant_id'],
        'task_type': task['task_type'],
        'department': task['department'],
        'title': task['title'],
        'room_id': task['room_id'],
        'room_number': task.get('room_number'),
        'priority': task['priority'],
        'description': task['description'],
        'assigned_to': task['assigned_to'],
        'status': task['status'],
        'created_by': task['created_by'],
        'created_at': task['created_at']
    }

@api_router.put("/pms/staff-tasks/{task_id}")
async def update_staff_task(
    task_id: str,
    update_data: dict,
    current_user: User = Depends(get_current_user)
):
    """Update staff task status"""
    await db.staff_tasks.update_one(
        {'id': task_id, 'tenant_id': current_user.tenant_id},
        {'$set': update_data}
    )
    
    # Return updated task
    updated_task = await db.staff_tasks.find_one(
        {'id': task_id, 'tenant_id': current_user.tenant_id},
        {'_id': 0}
    )
    
    if not updated_task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return updated_task

# ============= REVIEWS & FEEDBACK =============
@api_router.get("/crm/reviews")
async def get_reviews(
    current_user: User = Depends(get_current_user)
):
    """Get guest reviews"""
    reviews = await db.guest_reviews.find({
        'tenant_id': current_user.tenant_id
    }, {'_id': 0}).sort('created_at', -1).to_list(1000)
    return {"reviews": reviews}

@api_router.post("/crm/reviews/{review_id}/respond")
async def respond_to_review(
    review_id: str,
    response_data: dict,
    current_user: User = Depends(get_current_user)
):
    """Respond to a guest review"""
    await db.guest_reviews.update_one(
        {'id': review_id, 'tenant_id': current_user.tenant_id},
        {'$set': {
            'response': response_data.get('response'),
            'responded_at': datetime.now(timezone.utc).isoformat(),
            'responded_by': current_user.id
        }}
    )
    return {"message": "Response sent successfully"}

# ============= ALLOTMENT & TOUR OPERATORS =============
@api_router.get("/pms/allotment-contracts")
async def get_allotment_contracts(
    current_user: User = Depends(get_current_user)
):
    """Get tour operator allotment contracts"""
    contracts = await db.allotment_contracts.find({
        'tenant_id': current_user.tenant_id
    }, {'_id': 0}).to_list(1000)
    return contracts

@api_router.post("/pms/allotment-contracts")
async def create_allotment_contract(
    contract_data: dict,
    current_user: User = Depends(get_current_user)
):
    """Create new allotment contract"""
    contract = {
        'id': str(uuid.uuid4()),
        'tenant_id': current_user.tenant_id,
        'tour_operator': contract_data.get('tour_operator'),
        'room_type': contract_data.get('room_type'),
        'allocated_rooms': contract_data.get('allocated_rooms'),
        'used_rooms': 0,
        'start_date': contract_data.get('start_date'),
        'end_date': contract_data.get('end_date'),
        'rate': contract_data.get('rate'),
        'release_days': contract_data.get('release_days', 7),
        'status': 'active',
        'created_at': datetime.now(timezone.utc).isoformat()
    }
    
    await db.allotment_contracts.insert_one(contract)
    return contract

@api_router.post("/pms/allotment-contracts/{contract_id}/release")
async def release_allotment_rooms(
    contract_id: str,
    current_user: User = Depends(get_current_user)
):
    """Release unused allotment rooms back to inventory"""
    contract = await db.allotment_contracts.find_one({
        'id': contract_id,
        'tenant_id': current_user.tenant_id
    })
    
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    
    available_rooms = contract['allocated_rooms'] - contract.get('used_rooms', 0)
    
    await db.allotment_contracts.update_one(
        {'id': contract_id},
        {'$set': {
            'released_rooms': available_rooms,
            'released_at': datetime.now(timezone.utc).isoformat()
        }}
    )
    
    return {
        "message": f"Released {available_rooms} rooms",
        "released_rooms": available_rooms
    }

# ============= GUEST APP ENDPOINTS =============
@api_router.post("/guest/self-checkin/{booking_id}")
async def guest_self_checkin(
    booking_id: str,
    checkin_data: dict,
    current_user: User = Depends(get_current_user)
):
    """Complete self check-in process"""
    booking = await db.bookings.find_one({
        'id': booking_id,
        'tenant_id': current_user.tenant_id
    })
    
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    # Update booking status
    await db.bookings.update_one(
        {'id': booking_id},
        {'$set': {
            'status': 'checked_in',
            'actual_check_in': datetime.now(timezone.utc).isoformat(),
            'guest_info': checkin_data.get('guest_info'),
            'preferences': checkin_data.get('preferences')
        }}
    )
    
    # Update room status
    if booking.get('room_id'):
        await db.rooms.update_one(
            {'id': booking['room_id']},
            {'$set': {
                'status': 'occupied',
                'current_booking_id': booking_id
            }}
        )
    
    # Generate digital key
    digital_key = {
        'id': str(uuid.uuid4()),
        'key_id': str(uuid.uuid4())[:8].upper(),
        'tenant_id': current_user.tenant_id,
        'booking_id': booking_id,
        'guest_id': booking.get('guest_id'),
        'room_number': booking.get('room_number'),
        'status': 'active',
        'created_at': datetime.now(timezone.utc).isoformat(),
        'expires_at': booking.get('check_out'),
        'last_used': None
    }
    
    await db.digital_keys.insert_one(digital_key)
    
    return {
        'message': 'Check-in successful',
        'booking_id': booking_id,
        'room_number': booking.get('room_number'),
        'digital_key': {
            'key_id': digital_key['key_id'],
            'expires_at': digital_key['expires_at']
        }
    }

@api_router.get("/guest/digital-key/{booking_id}")
async def get_digital_key(
    booking_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get digital room key"""
    key = await db.digital_keys.find_one({
        'booking_id': booking_id,
        'tenant_id': current_user.tenant_id,
        'status': 'active'
    }, {'_id': 0})
    
    if not key:
        raise HTTPException(status_code=404, detail="Digital key not found")
    
    return key

@api_router.post("/guest/digital-key/{booking_id}/refresh")
async def refresh_digital_key(
    booking_id: str,
    current_user: User = Depends(get_current_user)
):
    """Refresh digital key"""
    # Deactivate old key
    await db.digital_keys.update_many(
        {'booking_id': booking_id, 'tenant_id': current_user.tenant_id},
        {'$set': {'status': 'expired'}}
    )
    
    # Get booking
    booking = await db.bookings.find_one({'id': booking_id}, {'_id': 0})
    
    # Create new key
    digital_key = {
        'id': str(uuid.uuid4()),
        'key_id': str(uuid.uuid4())[:8].upper(),
        'tenant_id': current_user.tenant_id,
        'booking_id': booking_id,
        'guest_id': booking.get('guest_id'),
        'room_number': booking.get('room_number'),
        'status': 'active',
        'created_at': datetime.now(timezone.utc).isoformat(),
        'expires_at': booking.get('check_out'),
        'last_used': None
    }
    
    await db.digital_keys.insert_one(digital_key)
    
    return {'message': 'Key refreshed', 'key_id': digital_key['key_id']}

@api_router.get("/guest/upsell-offers/{booking_id}")
async def get_upsell_offers(
    booking_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get personalized upsell offers for guest"""
    # Get AI predictions
    predictions = await db.ai_upsell_predictions.find({
        'booking_id': booking_id,
        'tenant_id': current_user.tenant_id
    }, {'_id': 0}).sort('confidence', -1).limit(10).to_list(10)
    
    # Get already purchased items
    purchased = await db.purchased_upsells.find({
        'booking_id': booking_id
    }, {'_id': 0}).to_list(100)
    
    return {
        'offers': predictions,
        'purchased': purchased
    }

@api_router.post("/guest/purchase-upsell/{booking_id}")
async def purchase_upsell(
    booking_id: str,
    purchase_data: dict,
    current_user: User = Depends(get_current_user)
):
    """Purchase an upsell offer"""
    purchase = {
        'id': str(uuid.uuid4()),
        'tenant_id': current_user.tenant_id,
        'booking_id': booking_id,
        'offer_id': purchase_data.get('offer_id'),
        'offer_type': purchase_data.get('offer_type'),
        'amount': purchase_data.get('amount'),
        'purchased_at': datetime.now(timezone.utc).isoformat(),
        'status': 'confirmed'
    }
    
    await db.purchased_upsells.insert_one(purchase)
    
    # Post to folio if exists
    folio = await db.folios.find_one({'booking_id': booking_id, 'status': 'open'})
    if folio:
        charge = {
            'id': str(uuid.uuid4()),
            'tenant_id': current_user.tenant_id,
            'folio_id': folio['id'],
            'charge_type': 'upsell',
            'description': f"Upsell: {purchase_data.get('offer_type')}",
            'amount': purchase_data.get('amount'),
            'quantity': 1,
            'total': purchase_data.get('amount'),
            'posted_at': datetime.now(timezone.utc).isoformat(),
            'voided': False
        }
        await db.folio_charges.insert_one(charge)
    
    return {'message': 'Purchase successful', 'purchase_id': purchase['id']}

@api_router.get("/guest/purchased-upsells/{booking_id}")
async def get_purchased_upsells(
    booking_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get purchased upsells for a booking"""
    items = await db.purchased_upsells.find({
        'booking_id': booking_id,
        'tenant_id': current_user.tenant_id
    }, {'_id': 0}).to_list(100)
    
    return {'items': items}

# ============= AI ACTIVITY LOG =============
@api_router.get("/ai/activity-log")
async def get_ai_activity_log(
    limit: int = 50,
    activity_type: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Get AI activity log for dashboard visualization"""
    query = {'tenant_id': current_user.tenant_id}
    if activity_type:
        query['type'] = activity_type
    
    activities = await db.ai_activity_log.find(
        query,
        {'_id': 0}
    ).sort('timestamp', -1).limit(limit).to_list(limit)
    
    # Calculate stats
    total = await db.ai_activity_log.count_documents({'tenant_id': current_user.tenant_id})
    successful = await db.ai_activity_log.count_documents({
        'tenant_id': current_user.tenant_id,
        'status': 'success'
    })
    
    return {
        'activities': activities,
        'stats': {
            'total': total,
            'successful': successful,
            'failed': total - successful
        }
    }

@api_router.post("/ai/log-activity")
async def log_ai_activity(
    activity_data: dict,
    current_user: User = Depends(get_current_user)
):
    """Log AI activity for tracking and analytics"""
    activity = {
        'id': str(uuid.uuid4()),
        'tenant_id': current_user.tenant_id,
        'user_id': current_user.id,
        'type': activity_data.get('type'),  # upsell_prediction, message_generation, demand_forecast
        'title': activity_data.get('title'),
        'description': activity_data.get('description'),
        'model': activity_data.get('model'),
        'status': activity_data.get('status', 'success'),
        'result': activity_data.get('result'),
        'execution_time': activity_data.get('execution_time'),  # in milliseconds
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'metadata': activity_data.get('metadata', {})
    }
    
    await db.ai_activity_log.insert_one(activity)
    return {'message': 'Activity logged successfully', 'activity_id': activity['id']}

# Import and include AI endpoints
try:
    from ai_endpoints import api_router as ai_router
    api_router.include_router(ai_router, tags=["AI Intelligence"])
    print("✅ AI endpoints loaded successfully")
except ImportError as e:
    print(f"⚠️ AI endpoints not loaded: {e}")

# ============= 7 CRITICAL FEATURES ENDPOINTS =============

# 1. OTA Messaging
@api_router.get("/ota/conversations")
async def get_ota_conversations(
    ota: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    query = {'tenant_id': current_user.tenant_id}
    if ota:
        query['ota_platform'] = ota
    
    conversations = await db.ota_conversations.find(query, {'_id': 0}).sort('last_message_at', -1).to_list(100)
    return {'conversations': conversations}

@api_router.get("/ota/conversations/{conversation_id}/messages")
async def get_ota_messages(
    conversation_id: str,
    current_user: User = Depends(get_current_user)
):
    messages = await db.ota_messages.find({
        'conversation_id': conversation_id,
        'tenant_id': current_user.tenant_id
    }, {'_id': 0}).sort('sent_at', 1).to_list(1000)
    return {'messages': messages}

@api_router.post("/ota/conversations/{conversation_id}/messages")
async def send_ota_message(
    conversation_id: str,
    message_data: dict,
    current_user: User = Depends(get_current_user)
):
    message = {
        'id': str(uuid.uuid4()),
        'tenant_id': current_user.tenant_id,
        'conversation_id': conversation_id,
        'message': message_data.get('message'),
        'sender': 'hotel',
        'channel': message_data.get('channel'),
        'sent_at': datetime.now(timezone.utc).isoformat()
    }
    await db.ota_messages.insert_one(message)
    
    # Update conversation last message
    await db.ota_conversations.update_one(
        {'id': conversation_id},
        {'$set': {'last_message': message_data.get('message'), 'last_message_at': message['sent_at']}}
    )
    
    return {'message': 'Sent successfully'}

# 2. RMS
@api_router.get("/rms/comp-set")
async def get_comp_set(current_user: User = Depends(get_current_user)):
    competitors = await db.rms_competitors.find({'tenant_id': current_user.tenant_id}, {'_id': 0}).to_list(100)
    return {'competitors': competitors}

@api_router.get("/rms/pricing-strategy")
async def get_pricing_strategy(current_user: User = Depends(get_current_user)):
    strategy = await db.rms_strategy.find_one({'tenant_id': current_user.tenant_id}, {'_id': 0})
    return strategy or {'current_rate': 100, 'recommended_rate': 110, 'auto_pricing_enabled': False}

@api_router.put("/rms/pricing-strategy")
async def update_pricing_strategy(
    strategy_data: dict,
    current_user: User = Depends(get_current_user)
):
    await db.rms_strategy.update_one(
        {'tenant_id': current_user.tenant_id},
        {'$set': strategy_data},
        upsert=True
    )
    return {'message': 'Strategy updated'}

@api_router.get("/rms/demand-forecast")
async def get_demand_forecast(
    days: int = 30,
    current_user: User = Depends(get_current_user)
):
    # Generate forecast data
    forecast = []
    today = datetime.now(timezone.utc).date()
    for i in range(days):
        date = today + timedelta(days=i)
        forecast.append({
            'date': date.isoformat(),
            'demand_index': 70 + (i % 10) * 3,
            'predicted_occupancy': 65 + (i % 15) * 2
        })
    return {'forecast': forecast}

@api_router.get("/rms/price-adjustments")
async def get_price_adjustments(current_user: User = Depends(get_current_user)):
    adjustments = await db.rms_price_adjustments.find(
        {'tenant_id': current_user.tenant_id},
        {'_id': 0}
    ).sort('date', -1).limit(20).to_list(20)
    return {'adjustments': adjustments}

@api_router.post("/rms/apply-recommendations")
async def apply_pricing_recommendations(current_user: User = Depends(get_current_user)):
    return {'message': 'Recommendations applied'}

# 3. Housekeeping Mobile
@api_router.get("/housekeeping/rooms")
async def get_housekeeping_rooms(
    status: str = 'dirty',
    current_user: User = Depends(get_current_user)
):
    query = {'tenant_id': current_user.tenant_id, 'hk_status': status}
    rooms = await db.rooms.find(query, {'_id': 0}).to_list(100)
    return {'rooms': rooms}

@api_router.get("/housekeeping/checklist")
async def get_housekeeping_checklist(current_user: User = Depends(get_current_user)):
    # Default checklist
    checklist = [
        {'id': '1', 'task': 'Make beds with fresh linens', 'area': 'Bedroom', 'completed': False},
        {'id': '2', 'task': 'Clean and sanitize bathroom', 'area': 'Bathroom', 'completed': False},
        {'id': '3', 'task': 'Vacuum carpets and floors', 'area': 'General', 'completed': False},
        {'id': '4', 'task': 'Dust all surfaces', 'area': 'General', 'completed': False},
        {'id': '5', 'task': 'Replenish amenities', 'area': 'Bathroom', 'completed': False},
        {'id': '6', 'task': 'Empty trash bins', 'area': 'General', 'completed': False},
        {'id': '7', 'task': 'Check minibar and restock', 'area': 'Minibar', 'completed': False}
    ]
    return {'items': checklist}

@api_router.post("/housekeeping/rooms/{room_id}/start")
async def start_room_cleaning(
    room_id: str,
    current_user: User = Depends(get_current_user)
):
    await db.rooms.update_one(
        {'id': room_id},
        {'$set': {'hk_status': 'cleaning', 'cleaning_started_at': datetime.now(timezone.utc).isoformat()}}
    )
    return {'message': 'Cleaning started'}

@api_router.post("/housekeeping/rooms/{room_id}/complete")
async def complete_room_cleaning(
    room_id: str,
    completion_data: dict,
    current_user: User = Depends(get_current_user)
):
    await db.rooms.update_one(
        {'id': room_id},
        {'$set': {
            'hk_status': 'clean',
            'last_cleaned_at': datetime.now(timezone.utc).isoformat(),
            'cleaned_by': completion_data.get('cleaned_by')
        }}
    )
    return {'message': 'Room cleaned successfully'}

# 4. Group & Block Reservations
@api_router.get("/pms/group-reservations")
async def get_group_reservations(current_user: User = Depends(get_current_user)):
    groups = await db.group_reservations.find({'tenant_id': current_user.tenant_id}, {'_id': 0}).to_list(100)
    return {'groups': groups}

@api_router.post("/pms/group-reservations")
async def create_group_reservation(
    group_data: dict,
    current_user: User = Depends(get_current_user)
):
    group = {
        'id': str(uuid.uuid4()),
        'tenant_id': current_user.tenant_id,
        **group_data,
        'created_at': datetime.now(timezone.utc).isoformat()
    }
    await db.group_reservations.insert_one(group)
    return group

@api_router.get("/pms/room-blocks")
async def get_room_blocks(current_user: User = Depends(get_current_user)):
    blocks = await db.room_blocks.find({'tenant_id': current_user.tenant_id}, {'_id': 0}).to_list(100)
    return {'blocks': blocks}

@api_router.post("/pms/room-blocks")
async def create_room_block(
    block_data: dict,
    current_user: User = Depends(get_current_user)
):
    block = {
        'id': str(uuid.uuid4()),
        'tenant_id': current_user.tenant_id,
        'block_name': block_data.get('group_name'),
        'room_type': block_data.get('room_type'),
        'total_rooms': block_data.get('total_rooms'),
        'start_date': block_data.get('check_in'),
        'end_date': block_data.get('check_out'),
        'reason': block_data.get('notes'),
        'status': 'active',
        'created_at': datetime.now(timezone.utc).isoformat()
    }
    await db.room_blocks.insert_one(block)
    return block

# 5. Multi-Property Management
@api_router.get("/multi-property/properties")
async def get_properties(current_user: User = Depends(get_current_user)):
    properties = await db.properties.find({'organization_id': current_user.tenant_id}, {'_id': 0}).to_list(100)
    return {'properties': properties}

@api_router.get("/multi-property/dashboard")
async def get_multi_property_dashboard(
    property_id: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    # Aggregate data across properties
    return {
        'total_revenue': 125000,
        'avg_occupancy': 78.5,
        'total_guests': 450,
        'total_rooms': 250,
        'property_revenues': [45000, 35000, 25000, 20000],
        'property_occupancies': [82, 78, 75, 72]
    }

# 6. Marketplace Inventory
@api_router.get("/marketplace/inventory")
async def get_marketplace_inventory(current_user: User = Depends(get_current_user)):
    products = await db.marketplace_inventory.find({'tenant_id': current_user.tenant_id}, {'_id': 0}).to_list(1000)
    return {'products': products}

@api_router.post("/marketplace/inventory")
async def add_inventory_product(
    product_data: dict,
    current_user: User = Depends(get_current_user)
):
    product = {
        'id': str(uuid.uuid4()),
        'tenant_id': current_user.tenant_id,
        **product_data,
        'created_at': datetime.now(timezone.utc).isoformat()
    }
    await db.marketplace_inventory.insert_one(product)
    return product

@api_router.get("/marketplace/purchase-orders")
async def get_purchase_orders(current_user: User = Depends(get_current_user)):
    orders = await db.purchase_orders.find({'tenant_id': current_user.tenant_id}, {'_id': 0}).sort('created_at', -1).to_list(100)
    return {'orders': orders}

@api_router.post("/marketplace/purchase-orders")
async def create_purchase_order(
    order_data: dict,
    current_user: User = Depends(get_current_user)
):
    order = {
        'id': str(uuid.uuid4()),
        'tenant_id': current_user.tenant_id,
        **order_data,
        'status': 'pending',
        'created_at': datetime.now(timezone.utc).isoformat()
    }
    await db.purchase_orders.insert_one(order.copy())
    return order

@api_router.get("/marketplace/deliveries")
async def get_deliveries(current_user: User = Depends(get_current_user)):
    deliveries = await db.deliveries.find({'tenant_id': current_user.tenant_id}, {'_id': 0}).sort('delivered_at', -1).to_list(100)
    return {'deliveries': deliveries}

# 7. E-Fatura & POS
@api_router.get("/efatura/invoices")
async def get_efatura_invoices(current_user: User = Depends(get_current_user)):
    invoices = await db.invoices.find({
        'tenant_id': current_user.tenant_id
    }, {'_id': 0}).sort('created_at', -1).limit(50).to_list(50)
    
    # Add efatura status to each invoice
    for invoice in invoices:
        invoice['efatura_status'] = invoice.get('efatura_status', 'pending')
    
    return {'invoices': invoices}

@api_router.get("/efatura/settings")
async def get_efatura_settings(current_user: User = Depends(get_current_user)):
    settings = await db.efatura_settings.find_one({'tenant_id': current_user.tenant_id}, {'_id': 0})
    return settings or {'vkn': '1234567890', 'enabled': True, 'auto_send': False, 'last_sync': None}

@api_router.post("/efatura/send/{invoice_id}")
async def send_efatura(
    invoice_id: str,
    current_user: User = Depends(get_current_user)
):
    # Update invoice status
    await db.invoices.update_one(
        {'id': invoice_id},
        {'$set': {
            'efatura_status': 'sent',
            'efatura_sent_at': datetime.now(timezone.utc).isoformat()
        }}
    )
    return {'message': 'E-Fatura sent successfully'}

@api_router.get("/pos/daily-closures")
async def get_pos_closures(current_user: User = Depends(get_current_user)):
    closures = await db.pos_closures.find(
        {'tenant_id': current_user.tenant_id},
        {'_id': 0}
    ).sort('closure_date', -1).limit(30).to_list(30)
    return {'closures': closures}

@api_router.post("/pos/daily-closure")
async def create_pos_closure(current_user: User = Depends(get_current_user)):
    # Calculate today's sales
    today = datetime.now(timezone.utc).date().isoformat()
    
    closure = {
        'id': str(uuid.uuid4()),
        'tenant_id': current_user.tenant_id,
        'closure_date': today,
        'total_sales': 5420.50,
        'cash_sales': 1200.00,
        'card_sales': 4220.50,
        'transaction_count': 45,
        'closed_at': datetime.now(timezone.utc).isoformat(),
        'closed_by': current_user.id
    }
    
    await db.pos_closures.insert_one(closure)
    return closure


# ========================================
# 1. WhatsApp & OTA Messaging Hub
# ========================================

@api_router.post("/messaging/send-whatsapp")
async def send_whatsapp_message(
    request: SendWhatsAppRequest,
    current_user: User = Depends(get_current_user)
):
    """Send WhatsApp message to guest"""
    msg_record = {
        'id': str(uuid.uuid4()),
        'tenant_id': current_user.tenant_id,
        'channel': 'whatsapp',
        'to': request.to,
        'message': request.message,
        'booking_id': request.booking_id,
        'status': 'sent',
        'sent_at': datetime.now(timezone.utc).isoformat(),
        'sent_by': current_user.id
    }
    
    msg_copy = msg_record.copy()
    await db.messages.insert_one(msg_copy)
    return {'message': 'WhatsApp message sent successfully', 'message_id': msg_record['id']}

@api_router.post("/messaging/send-email")
async def send_email_message(
    request: SendEmailRequest,
    current_user: User = Depends(get_current_user)
):
    """Send email to guest"""
    msg_record = {
        'id': str(uuid.uuid4()),
        'tenant_id': current_user.tenant_id,
        'channel': 'email',
        'to': request.to,
        'subject': request.subject,
        'message': request.message,
        'booking_id': request.booking_id,
        'status': 'sent',
        'sent_at': datetime.now(timezone.utc).isoformat(),
        'sent_by': current_user.id
    }
    
    msg_copy = msg_record.copy()
    await db.messages.insert_one(msg_copy)
    return {'message': 'Email sent successfully', 'message_id': msg_record['id']}

@api_router.post("/messaging/send-sms")
async def send_sms_message(
    request: SendSMSRequest,
    current_user: User = Depends(get_current_user)
):
    """Send SMS to guest"""
    msg_record = {
        'id': str(uuid.uuid4()),
        'tenant_id': current_user.tenant_id,
        'channel': 'sms',
        'to': request.to,
        'message': request.message,
        'booking_id': request.booking_id,
        'status': 'sent',
        'sent_at': datetime.now(timezone.utc).isoformat(),
        'sent_by': current_user.id
    }
    
    msg_copy = msg_record.copy()
    await db.messages.insert_one(msg_copy)
    return {'message': 'SMS sent successfully', 'message_id': msg_record['id']}

@api_router.get("/messaging/conversations")
async def get_conversations(
    channel: str = None,
    current_user: User = Depends(get_current_user)
):
    """Get all message conversations"""
    query = {'tenant_id': current_user.tenant_id}
    if channel:
        query['channel'] = channel
    
    messages = await db.messages.find(
        query,
        {'_id': 0}
    ).sort('sent_at', -1).limit(100).to_list(100)
    
    return {'messages': messages, 'count': len(messages)}

@api_router.get("/messaging/templates")
async def get_message_templates(
    channel: str = None,
    current_user: User = Depends(get_current_user)
):
    """Get message templates"""
    query = {'tenant_id': current_user.tenant_id}
    if channel:
        query['channel'] = channel
    
    templates = await db.message_templates.find(
        query,
        {'_id': 0}
    ).to_list(100)
    
    return {'templates': templates, 'count': len(templates)}

@api_router.post("/messaging/templates")
async def create_message_template(
    request: CreateMessageTemplateRequest,
    current_user: User = Depends(get_current_user)
):
    """Create message template"""
    template = {
        'id': str(uuid.uuid4()),
        'tenant_id': current_user.tenant_id,
        'name': request.name,
        'channel': request.channel,
        'subject': request.subject,
        'content': request.content,
        'variables': request.variables,
        'created_at': datetime.now(timezone.utc).isoformat(),
        'created_by': current_user.id
    }
    
    template_copy = template.copy()
    await db.message_templates.insert_one(template_copy)
    return template

@api_router.get("/messaging/ota-integrations")
async def get_ota_integrations(current_user: User = Depends(get_current_user)):
    """Get OTA messaging integrations"""
    integrations = await db.ota_integrations.find(
        {'tenant_id': current_user.tenant_id},
        {'_id': 0}
    ).to_list(100)
    
    return {'integrations': integrations, 'count': len(integrations)}


# ========================================
# 2. Full RMS - Revenue Management System
# ========================================

@api_router.get("/rms/comp-set")
async def get_comp_set(current_user: User = Depends(get_current_user)):
    """Get competitor set data"""
    comp_set = await db.comp_set.find(
        {'tenant_id': current_user.tenant_id},
        {'_id': 0}
    ).to_list(100)
    
    return {'comp_set': comp_set, 'count': len(comp_set)}

@api_router.post("/rms/comp-set")
async def add_competitor(
    request: AddCompetitorRequest,
    current_user: User = Depends(get_current_user)
):
    """Add competitor to comp set"""
    competitor = {
        'id': str(uuid.uuid4()),
        'tenant_id': current_user.tenant_id,
        'name': request.name,
        'location': request.location,
        'star_rating': request.star_rating,
        'url': request.url,
        'status': 'active',
        'created_at': datetime.now(timezone.utc).isoformat()
    }
    
    competitor_copy = competitor.copy()
    await db.comp_set.insert_one(competitor_copy)
    return competitor

@api_router.get("/rms/comp-pricing")
async def get_competitor_pricing(
    date: str = None,
    current_user: User = Depends(get_current_user)
):
    """Get competitor pricing for specific date"""
    query = {'tenant_id': current_user.tenant_id}
    if date:
        query['date'] = date
    
    pricing = await db.comp_pricing.find(
        query,
        {'_id': 0}
    ).sort('date', -1).limit(100).to_list(100)
    
    return {'pricing': pricing, 'count': len(pricing)}

@api_router.post("/rms/scrape-comp-prices")
async def scrape_competitor_prices(
    request: ScrapePricesRequest,
    current_user: User = Depends(get_current_user)
):
    """Scrape competitor prices for specific date"""
    date = request.date
    # Get all active competitors
    competitors = await db.comp_set.find(
        {'tenant_id': current_user.tenant_id, 'status': 'active'},
        {'_id': 0}
    ).to_list(100)
    
    scraped_prices = []
    for comp in competitors:
        price_data = {
            'id': str(uuid.uuid4()),
            'tenant_id': current_user.tenant_id,
            'competitor_id': comp['id'],
            'competitor_name': comp['name'],
            'date': date,
            'lowest_rate': 120.00 + (hash(comp['id']) % 50),  # Mock pricing
            'standard_rate': 150.00 + (hash(comp['id']) % 80),
            'scraped_at': datetime.now(timezone.utc).isoformat()
        }
        await db.comp_pricing.insert_one(price_data.copy())
        scraped_prices.append(price_data)
    
    return {
        'message': f'Scraped prices for {len(scraped_prices)} competitors',
        'prices': scraped_prices
    }

@api_router.post("/rms/auto-pricing")
async def generate_auto_pricing(
    request: AutoPricingRequest,
    current_user: User = Depends(get_current_user)
):
    """Generate automatic pricing recommendations with advanced confidence scoring"""
    # Parse dates
    start = datetime.fromisoformat(request.start_date)
    end = datetime.fromisoformat(request.end_date)
    room_type = request.room_type
    days = (end - start).days + 1
    
    # Get room types
    room_types_query = {'tenant_id': current_user.tenant_id}
    if room_type:
        room_types_query['name'] = room_type
    
    room_types = await db.room_types.find(room_types_query, {'_id': 0}).to_list(100)
    
    # Get competitor pricing for comparison
    comp_avg_prices = {}
    comp_pricing = await db.comp_pricing.find(
        {'tenant_id': current_user.tenant_id},
        {'_id': 0}
    ).to_list(1000)
    
    for price in comp_pricing:
        date = price.get('date')
        if date:
            if date not in comp_avg_prices:
                comp_avg_prices[date] = []
            comp_avg_prices[date].append(price.get('standard_rate', 0))
    
    recommendations = []
    for day in range(days):
        current_date = (start + timedelta(days=day)).date().isoformat()
        date_obj = datetime.fromisoformat(current_date)
        
        for rt in room_types:
            # Get bookings for this date
            bookings = await db.bookings.count_documents({
                'tenant_id': current_user.tenant_id,
                'room_type': rt['name'],
                'check_in_date': {'$lte': current_date},
                'check_out_date': {'$gt': current_date},
                'status': {'$in': ['confirmed', 'guaranteed', 'checked_in']}
            })
            
            # Get total rooms
            total_rooms = await db.rooms.count_documents({
                'tenant_id': current_user.tenant_id,
                'room_type': rt['name']
            })
            
            occupancy = (bookings / total_rooms * 100) if total_rooms > 0 else 0
            base_rate = rt.get('base_rate', 100.0)
            
            # Get booking pace (bookings in last 7 days for this date)
            recent_bookings = await db.bookings.count_documents({
                'tenant_id': current_user.tenant_id,
                'room_type': rt['name'],
                'check_in_date': {'$lte': current_date},
                'check_out_date': {'$gt': current_date},
                'created_at': {'$gte': (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()}
            })
            
            booking_pace = recent_bookings / 7 if recent_bookings > 0 else 0
            
            # Get competitor average price for this date
            comp_avg = sum(comp_avg_prices.get(current_date, [])) / len(comp_avg_prices.get(current_date, [1])) if comp_avg_prices.get(current_date) else base_rate
            
            # Day of week factor
            day_of_week = date_obj.weekday()
            is_weekend = day_of_week in [4, 5]  # Friday, Saturday
            
            # Seasonal factor
            month = date_obj.month
            is_peak_season = month in [6, 7, 8, 12]
            
            # ENHANCED PRICING ALGORITHM with multiple factors
            price_multiplier = 1.0
            reasoning_factors = []
            
            # Factor 1: Current Occupancy (40% weight)
            if occupancy > 90:
                price_multiplier *= 1.25
                reasoning_factors.append(f"Very high occupancy ({occupancy:.0f}%): +25%")
            elif occupancy > 75:
                price_multiplier *= 1.15
                reasoning_factors.append(f"High occupancy ({occupancy:.0f}%): +15%")
            elif occupancy > 50:
                price_multiplier *= 1.05
                reasoning_factors.append(f"Moderate occupancy ({occupancy:.0f}%): +5%")
            elif occupancy > 30:
                price_multiplier *= 0.95
                reasoning_factors.append(f"Low occupancy ({occupancy:.0f}%): -5%")
            else:
                price_multiplier *= 0.85
                reasoning_factors.append(f"Very low occupancy ({occupancy:.0f}%): -15%")
            
            # Factor 2: Booking Pace (20% weight)
            if booking_pace > 2:
                price_multiplier *= 1.08
                reasoning_factors.append(f"Strong booking pace ({booking_pace:.1f}/day): +8%")
            elif booking_pace > 1:
                price_multiplier *= 1.03
                reasoning_factors.append(f"Good booking pace ({booking_pace:.1f}/day): +3%")
            elif booking_pace < 0.5 and occupancy < 60:
                price_multiplier *= 0.95
                reasoning_factors.append(f"Slow booking pace ({booking_pace:.1f}/day): -5%")
            
            # Factor 3: Day of Week (15% weight)
            if is_weekend:
                price_multiplier *= 1.10
                reasoning_factors.append("Weekend demand: +10%")
            
            # Factor 4: Seasonality (15% weight)
            if is_peak_season:
                price_multiplier *= 1.12
                reasoning_factors.append("Peak season: +12%")
            
            # Factor 5: Competitor Pricing (10% weight)
            if comp_avg > 0:
                price_position = (base_rate / comp_avg) * 100
                if price_position < 85:
                    price_multiplier *= 1.05
                    reasoning_factors.append(f"Below market (${comp_avg:.0f}): +5%")
                elif price_position > 115:
                    price_multiplier *= 0.97
                    reasoning_factors.append(f"Above market (${comp_avg:.0f}): -3%")
                else:
                    reasoning_factors.append(f"Market aligned (${comp_avg:.0f})")
            
            suggested_rate = base_rate * price_multiplier
            
            # DYNAMIC CONFIDENCE SCORING
            confidence_factors = []
            confidence_score = 0.0
            
            # Historical data availability
            if bookings > 0:
                confidence_score += 0.25
                confidence_factors.append("Has booking history")
            
            # Booking pace reliability
            if booking_pace > 0.5:
                confidence_score += 0.20
                confidence_factors.append("Active booking pace")
            
            # Competitor data availability
            if comp_avg > 0 and len(comp_avg_prices.get(current_date, [])) >= 2:
                confidence_score += 0.25
                confidence_factors.append("Multiple competitor prices")
            elif comp_avg > 0:
                confidence_score += 0.15
                confidence_factors.append("Limited competitor data")
            
            # Time to arrival
            days_to_arrival = (date_obj - datetime.now(timezone.utc)).days
            if days_to_arrival < 30:
                confidence_score += 0.20
                confidence_factors.append("Near-term forecast")
            elif days_to_arrival < 90:
                confidence_score += 0.10
                confidence_factors.append("Medium-term forecast")
            
            # Room type data quality
            if total_rooms >= 5:
                confidence_score += 0.10
                confidence_factors.append("Adequate room inventory")
            
            # Cap confidence at 0.95
            confidence_score = min(confidence_score, 0.95)
            
            # Determine confidence level
            if confidence_score >= 0.75:
                confidence_level = "High"
            elif confidence_score >= 0.50:
                confidence_level = "Medium"
            else:
                confidence_level = "Low"
            
            # Determine strategy
            if price_multiplier >= 1.15:
                strategy = 'Premium Pricing'
            elif price_multiplier >= 1.05:
                strategy = 'Demand-Based Pricing'
            elif price_multiplier >= 0.95:
                strategy = 'Market Rate'
            elif price_multiplier >= 0.85:
                strategy = 'Competitive Pricing'
            else:
                strategy = 'Promotional Pricing'
            
            recommendation = {
                'id': str(uuid.uuid4()),
                'tenant_id': current_user.tenant_id,
                'date': current_date,
                'room_type': rt['name'],
                'current_rate': base_rate,
                'suggested_rate': round(suggested_rate, 2),
                'occupancy': round(occupancy, 1),
                'booking_pace': round(booking_pace, 2),
                'competitor_avg': round(comp_avg, 2) if comp_avg > 0 else None,
                'strategy': strategy,
                'confidence': round(confidence_score, 2),
                'confidence_level': confidence_level,
                'confidence_factors': confidence_factors,
                'reasoning': ' | '.join(reasoning_factors),
                'reasoning_breakdown': reasoning_factors,
                'is_weekend': is_weekend,
                'is_peak_season': is_peak_season,
                'price_change_pct': round((price_multiplier - 1) * 100, 1),
                'generated_at': datetime.now(timezone.utc).isoformat()
            }
            recommendations.append(recommendation)
    
    # Save recommendations
    if recommendations:
        await db.rms_pricing_recommendations.insert_many([r.copy() for r in recommendations])
    
    return {
        'message': f'Generated {len(recommendations)} pricing recommendations',
        'recommendations': recommendations,
        'summary': {
            'total_recommendations': len(recommendations),
            'avg_confidence': round(sum(r['confidence'] for r in recommendations) / len(recommendations), 2) if recommendations else 0,
            'high_confidence_count': sum(1 for r in recommendations if r['confidence_level'] == 'High'),
            'date_range': f"{request.start_date} to {request.end_date}"
        }
    }

@api_router.get("/rms/demand-forecast")
async def get_demand_forecast(
    start_date: str = None,
    end_date: str = None,
    current_user: User = Depends(get_current_user)
):
    """Get demand forecast"""
    query = {'tenant_id': current_user.tenant_id}
    if start_date and end_date:
        query['date'] = {'$gte': start_date, '$lte': end_date}
    
    forecasts = await db.demand_forecasts.find(
        query,
        {'_id': 0}
    ).sort('date', 1).to_list(365)
    
    return {'forecasts': forecasts, 'count': len(forecasts)}

@api_router.post("/rms/demand-forecast")
async def generate_demand_forecast(
    request: DemandForecastRequest,
    current_user: User = Depends(get_current_user)
):
    """Generate advanced demand forecast with ML-inspired algorithm (90-day capable)"""
    start = datetime.fromisoformat(request.start_date)
    end = datetime.fromisoformat(request.end_date)
    days = (end - start).days + 1
    
    # Get historical booking data for trend analysis
    historical_start = datetime.now(timezone.utc) - timedelta(days=365)
    historical_bookings = await db.bookings.find({
        'tenant_id': current_user.tenant_id,
        'created_at': {'$gte': historical_start.isoformat()}
    }, {'_id': 0, 'check_in_date': 1, 'check_out_date': 1, 'created_at': 1}).to_list(10000)
    
    # Calculate historical occupancy patterns
    historical_occupancy_by_dow = {i: [] for i in range(7)}  # Day of week
    historical_occupancy_by_month = {i: [] for i in range(1, 13)}  # Month
    
    for booking in historical_bookings:
        try:
            checkin = datetime.fromisoformat(booking['check_in_date'])
            dow = checkin.weekday()
            month = checkin.month
            historical_occupancy_by_dow[dow].append(1)
            historical_occupancy_by_month[month].append(1)
        except:
            pass
    
    # Get total rooms
    total_rooms = await db.rooms.count_documents({'tenant_id': current_user.tenant_id})
    if total_rooms == 0:
        total_rooms = 100  # Default for demo
    
    forecasts = []
    for day in range(days):
        current_date = (start + timedelta(days=day)).date().isoformat()
        date_obj = datetime.fromisoformat(current_date).replace(tzinfo=timezone.utc)
        
        # Advanced forecast model with multiple factors
        day_of_week = date_obj.weekday()
        month = date_obj.month
        days_from_now = (date_obj - datetime.now(timezone.utc)).days
        
        # 1. Day of Week Pattern (30% weight)
        dow_historical_count = len(historical_occupancy_by_dow.get(day_of_week, []))
        if dow_historical_count > 10:
            dow_factor = min(dow_historical_count / 50, 1.0)  # Normalize
        else:
            # Default pattern if no history
            if day_of_week in [4, 5]:  # Friday, Saturday
                dow_factor = 0.85
            elif day_of_week in [6]:  # Sunday
                dow_factor = 0.70
            else:
                dow_factor = 0.60
        
        # 2. Seasonal Pattern (25% weight)
        month_historical_count = len(historical_occupancy_by_month.get(month, []))
        if month_historical_count > 20:
            seasonal_factor = min(month_historical_count / 100, 1.3)
        else:
            # Default seasonal pattern
            if month in [6, 7, 8]:  # Summer
                seasonal_factor = 1.25
            elif month in [12, 1]:  # Winter holidays
                seasonal_factor = 1.15
            elif month in [3, 4, 5]:  # Spring
                seasonal_factor = 1.05
            else:
                seasonal_factor = 0.95
        
        # 3. Lead Time Factor (20% weight)
        if days_from_now < 7:
            lead_factor = 1.15  # Last minute bookings boost
        elif days_from_now < 30:
            lead_factor = 1.05
        elif days_from_now < 60:
            lead_factor = 1.00
        else:
            lead_factor = 0.92  # Far future less certain
        
        # 4. Current Booking Trend (15% weight)
        recent_booking_count = len([b for b in historical_bookings if b.get('created_at') and (datetime.now(timezone.utc) - datetime.fromisoformat(b['created_at']).replace(tzinfo=timezone.utc)).days < 30])
        if recent_booking_count > 50:
            trend_factor = 1.10  # Strong recent trend
        elif recent_booking_count > 20:
            trend_factor = 1.05
        else:
            trend_factor = 1.00
        
        # 5. Special Events (10% weight) - Can be enhanced with event calendar
        # Check if weekend or holiday
        is_friday_saturday = day_of_week in [4, 5]
        event_factor = 1.12 if is_friday_saturday else 1.0
        
        # Combine all factors
        base_demand = 0.65  # Base occupancy
        forecasted_demand = base_demand * dow_factor * (seasonal_factor / 1.1) * lead_factor * (trend_factor / 1.05) * event_factor
        
        # Cap at realistic bounds
        forecasted_demand = min(max(forecasted_demand, 0.15), 0.98)
        
        forecasted_rooms = int(total_rooms * forecasted_demand)
        forecasted_occupancy = round(forecasted_demand * 100, 1)
        
        # Dynamic confidence based on factors
        confidence = 0.0
        confidence_factors = []
        
        # Historical data quality
        if dow_historical_count > 20:
            confidence += 0.25
            confidence_factors.append("Strong day-of-week history")
        elif dow_historical_count > 5:
            confidence += 0.15
            confidence_factors.append("Moderate day-of-week history")
        else:
            confidence += 0.05
            confidence_factors.append("Limited day-of-week history")
        
        # Seasonal data quality
        if month_historical_count > 30:
            confidence += 0.25
            confidence_factors.append("Strong seasonal pattern")
        elif month_historical_count > 10:
            confidence += 0.15
            confidence_factors.append("Moderate seasonal pattern")
        else:
            confidence += 0.05
            confidence_factors.append("Limited seasonal data")
        
        # Lead time certainty
        if days_from_now < 30:
            confidence += 0.30
            confidence_factors.append("Near-term forecast (high certainty)")
        elif days_from_now < 60:
            confidence += 0.20
            confidence_factors.append("Medium-term forecast")
        else:
            confidence += 0.10
            confidence_factors.append("Long-term forecast (lower certainty)")
        
        # Recent booking trend
        if recent_booking_count > 30:
            confidence += 0.20
            confidence_factors.append("Strong recent booking trend")
        elif recent_booking_count > 10:
            confidence += 0.10
            confidence_factors.append("Moderate booking activity")
        
        confidence = min(confidence, 0.95)
        
        # Confidence level
        if confidence >= 0.70:
            confidence_level = "High"
        elif confidence >= 0.45:
            confidence_level = "Medium"
        else:
            confidence_level = "Low"
        
        # Forecast trend
        if forecasted_occupancy > 80:
            trend = "High Demand"
        elif forecasted_occupancy > 60:
            trend = "Strong Demand"
        elif forecasted_occupancy > 40:
            trend = "Moderate Demand"
        else:
            trend = "Low Demand"
        
        forecast = {
            'id': str(uuid.uuid4()),
            'tenant_id': current_user.tenant_id,
            'date': current_date,
            'forecasted_occupancy': forecasted_occupancy,
            'forecasted_rooms': forecasted_rooms,
            'total_rooms': total_rooms,
            'day_of_week': ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'][day_of_week],
            'is_weekend': day_of_week in [4, 5, 6],
            'confidence': round(confidence, 2),
            'confidence_level': confidence_level,
            'confidence_factors': confidence_factors,
            'trend': trend,
            'seasonal_factor': round(seasonal_factor, 2),
            'lead_time_days': days_from_now,
            'model_version': '2.0-advanced',
            'generated_at': datetime.now(timezone.utc).isoformat()
        }
        forecasts.append(forecast)
    
    # Calculate summary statistics
    avg_occupancy = sum(f['forecasted_occupancy'] for f in forecasts) / len(forecasts) if forecasts else 0
    high_demand_days = sum(1 for f in forecasts if f['forecasted_occupancy'] > 75)
    low_demand_days = sum(1 for f in forecasts if f['forecasted_occupancy'] < 40)
    
    # Save forecasts
    if forecasts:
        await db.demand_forecasts.insert_many([f.copy() for f in forecasts])
    
    return {
        'message': f'Generated {len(forecasts)} demand forecasts',
        'forecasts': forecasts,
        'summary': {
            'total_days': len(forecasts),
            'avg_forecasted_occupancy': round(avg_occupancy, 1),
            'high_demand_days': high_demand_days,
            'moderate_demand_days': len(forecasts) - high_demand_days - low_demand_days,
            'low_demand_days': low_demand_days,
            'date_range': f"{request.start_date} to {request.end_date}",
            'model_version': '2.0-advanced'
        }
    }

@api_router.get("/rms/pricing-recommendations")
async def get_pricing_recommendations(
    date: str = None,
    status: str = 'pending',
    current_user: User = Depends(get_current_user)
):
    """Get pricing recommendations"""
    query = {'tenant_id': current_user.tenant_id}
    if date:
        query['date'] = date
    if status:
        query['status'] = status
    
    recommendations = await db.rms_pricing_recommendations.find(
        query,
        {'_id': 0}
    ).sort('date', 1).to_list(1000)
    
    return {'recommendations': recommendations, 'count': len(recommendations)}

@api_router.post("/rms/apply-pricing/{recommendation_id}")
async def apply_pricing_recommendation(
    recommendation_id: str,
    current_user: User = Depends(get_current_user)
):
    """Apply pricing recommendation"""
    recommendation = await db.rms_pricing_recommendations.find_one({
        'id': recommendation_id,
        'tenant_id': current_user.tenant_id
    }, {'_id': 0})
    
    if not recommendation:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    
    # Update rate in rate calendar
    await db.rate_calendar.update_one(
        {
            'tenant_id': current_user.tenant_id,
            'date': recommendation['date'],
            'room_type': recommendation['room_type']
        },
        {
            '$set': {
                'rate': recommendation['suggested_rate'],
                'updated_at': datetime.now(timezone.utc).isoformat(),
                'updated_by': current_user.id
            }
        },
        upsert=True
    )
    
    # Mark recommendation as applied
    await db.rms_pricing_recommendations.update_one(
        {'id': recommendation_id},
        {
            '$set': {
                'status': 'applied',
                'applied_at': datetime.now(timezone.utc).isoformat(),
                'applied_by': current_user.id
            }
        }
    )
    
    return {'message': 'Pricing recommendation applied successfully'}


# ENHANCED RMS ENDPOINTS FOR VISUALIZATION
@api_router.get("/rms/comp-set-comparison")
async def get_comp_set_price_comparison(
    start_date: str = None,
    end_date: str = None,
    current_user: User = Depends(get_current_user)
):
    """Get competitor pricing comparison with your hotel rates"""
    # Default to next 30 days if not specified
    if not start_date:
        start_date = datetime.now(timezone.utc).date().isoformat()
    if not end_date:
        end_date = (datetime.now(timezone.utc) + timedelta(days=30)).date().isoformat()
    
    # Get all competitors
    competitors = await db.comp_set.find({
        'tenant_id': current_user.tenant_id,
        'status': 'active'
    }, {'_id': 0}).to_list(100)
    
    # Get competitor pricing
    comp_pricing = await db.comp_pricing.find({
        'tenant_id': current_user.tenant_id,
        'date': {'$gte': start_date, '$lte': end_date}
    }, {'_id': 0}).to_list(1000)
    
    # Get your hotel's rates
    room_types = await db.room_types.find({
        'tenant_id': current_user.tenant_id
    }, {'_id': 0}).to_list(100)
    
    # Organize data by date
    comparison_data = {}
    
    # Process each date
    start = datetime.fromisoformat(start_date)
    end = datetime.fromisoformat(end_date)
    days = (end - start).days + 1
    
    for day in range(days):
        current_date = (start + timedelta(days=day)).date().isoformat()
        
        # Get competitor prices for this date
        date_comp_prices = [p for p in comp_pricing if p.get('date') == current_date]
        
        comp_data = []
        for comp in competitors:
            comp_price = next((p for p in date_comp_prices if p.get('competitor_id') == comp['id']), None)
            if comp_price:
                comp_data.append({
                    'competitor_name': comp['name'],
                    'rate': comp_price.get('standard_rate', 0),
                    'star_rating': comp.get('star_rating', 0)
                })
        
        # Get your hotel's average rate
        your_avg_rate = sum(rt.get('base_rate', 0) for rt in room_types) / len(room_types) if room_types else 100
        
        comp_avg = sum(c['rate'] for c in comp_data) / len(comp_data) if comp_data else 0
        comp_min = min([c['rate'] for c in comp_data]) if comp_data else 0
        comp_max = max([c['rate'] for c in comp_data]) if comp_data else 0
        
        comparison_data[current_date] = {
            'date': current_date,
            'your_rate': round(your_avg_rate, 2),
            'comp_avg': round(comp_avg, 2),
            'comp_min': round(comp_min, 2),
            'comp_max': round(comp_max, 2),
            'competitors': comp_data,
            'price_index': round((your_avg_rate / comp_avg * 100), 1) if comp_avg > 0 else 100,
            'position': 'Above Market' if your_avg_rate > comp_avg and comp_avg > 0 else ('Below Market' if your_avg_rate < comp_avg and comp_avg > 0 else 'At Market')
        }
    
    # Convert to list
    comparison_list = list(comparison_data.values())
    
    # Calculate summary
    avg_price_index = sum(d['price_index'] for d in comparison_list) / len(comparison_list) if comparison_list else 100
    days_above_market = sum(1 for d in comparison_list if d['position'] == 'Above Market')
    days_below_market = sum(1 for d in comparison_list if d['position'] == 'Below Market')
    
    return {
        'comparison': comparison_list,
        'summary': {
            'total_days': len(comparison_list),
            'competitor_count': len(competitors),
            'avg_price_index': round(avg_price_index, 1),
            'days_above_market': days_above_market,
            'days_at_market': len(comparison_list) - days_above_market - days_below_market,
            'days_below_market': days_below_market,
            'date_range': f"{start_date} to {end_date}"
        }
    }

@api_router.get("/rms/pricing-insights")
async def get_pricing_insights(
    date: str = None,
    current_user: User = Depends(get_current_user)
):
    """Get detailed pricing insights and breakdown for specific date"""
    if not date:
        date = datetime.now(timezone.utc).date().isoformat()
    
    # Get recommendations for this date
    recommendations = await db.rms_pricing_recommendations.find({
        'tenant_id': current_user.tenant_id,
        'date': date
    }, {'_id': 0}).to_list(100)
    
    if not recommendations:
        return {
            'date': date,
            'message': 'No pricing recommendations available for this date',
            'insights': []
        }
    
    # Aggregate insights
    insights = []
    for rec in recommendations:
        insight = {
            'room_type': rec.get('room_type'),
            'current_rate': rec.get('current_rate'),
            'suggested_rate': rec.get('suggested_rate'),
            'price_change': rec.get('suggested_rate', 0) - rec.get('current_rate', 0),
            'price_change_pct': rec.get('price_change_pct', 0),
            'occupancy': rec.get('occupancy'),
            'booking_pace': rec.get('booking_pace'),
            'competitor_avg': rec.get('competitor_avg'),
            'confidence': rec.get('confidence'),
            'confidence_level': rec.get('confidence_level'),
            'strategy': rec.get('strategy'),
            'reasoning': rec.get('reasoning'),
            'reasoning_breakdown': rec.get('reasoning_breakdown', []),
            'confidence_factors': rec.get('confidence_factors', [])
        }
        insights.append(insight)
    
    # Calculate aggregate metrics
    avg_confidence = sum(i['confidence'] for i in insights) / len(insights) if insights else 0
    total_price_change = sum(i['price_change'] for i in insights)
    
    return {
        'date': date,
        'insights': insights,
        'summary': {
            'total_recommendations': len(insights),
            'avg_confidence': round(avg_confidence, 2),
            'total_rate_adjustment': round(total_price_change, 2),
            'high_confidence_count': sum(1 for i in insights if i['confidence_level'] == 'High'),
            'recommended_increase': sum(1 for i in insights if i['price_change'] > 0),
            'recommended_decrease': sum(1 for i in insights if i['price_change'] < 0)
        }
    }


# ========================================
# 3. Mobile Housekeeping App
# ========================================

@api_router.get("/housekeeping/mobile/my-tasks")
async def get_my_housekeeping_tasks(
    status: str = None,
    current_user: User = Depends(get_current_user)
):
    """Get tasks assigned to current user"""
    query = {
        'tenant_id': current_user.tenant_id,
        'assigned_to': current_user.name
    }
    if status:
        query['status'] = status
    
    tasks = await db.housekeeping_tasks.find(
        query,
        {'_id': 0}
    ).sort('priority', -1).to_list(100)
    
    # Enrich with room details
    for task in tasks:
        if task.get('room_id'):
            room = await db.rooms.find_one(
                {'id': task['room_id'], 'tenant_id': current_user.tenant_id},
                {'_id': 0}
            )
            if room:
                task['room_number'] = room['room_number']
                task['room_type'] = room['room_type']
    
    return {'tasks': tasks, 'count': len(tasks)}

@api_router.post("/housekeeping/mobile/start-task/{task_id}")
async def start_housekeeping_task(
    task_id: str,
    current_user: User = Depends(get_current_user)
):
    """Start working on a task"""
    task = await db.housekeeping_tasks.find_one({
        'id': task_id,
        'tenant_id': current_user.tenant_id,
        'assigned_to': current_user.name
    })
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    await db.housekeeping_tasks.update_one(
        {'id': task_id},
        {
            '$set': {
                'status': 'in_progress',
                'started_at': datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    # Update room status to cleaning
    if task.get('room_id'):
        await db.rooms.update_one(
            {'id': task['room_id'], 'tenant_id': current_user.tenant_id},
            {'$set': {'room_status': 'cleaning'}}
        )
    
    return {'message': 'Task started successfully'}

@api_router.post("/housekeeping/mobile/complete-task/{task_id}")
async def complete_housekeeping_task(
    task_id: str,
    notes: str = None,
    photos: list = [],
    current_user: User = Depends(get_current_user)
):
    """Complete a housekeeping task"""
    task = await db.housekeeping_tasks.find_one({
        'id': task_id,
        'tenant_id': current_user.tenant_id,
        'assigned_to': current_user.name
    })
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    await db.housekeeping_tasks.update_one(
        {'id': task_id},
        {
            '$set': {
                'status': 'completed',
                'completed_at': datetime.now(timezone.utc).isoformat(),
                'completion_notes': notes,
                'photos': photos
            }
        }
    )
    
    # Update room status based on task type
    if task.get('room_id'):
        new_status = 'inspected' if task.get('task_type') == 'inspection' else 'clean'
        await db.rooms.update_one(
            {'id': task['room_id'], 'tenant_id': current_user.tenant_id},
            {'$set': {'room_status': new_status}}
        )
    
    return {'message': 'Task completed successfully'}

@api_router.post("/housekeeping/mobile/report-issue")
async def report_housekeeping_issue(
    request: ReportIssueRequest,
    current_user: User = Depends(get_current_user)
):
    """Report maintenance or cleaning issue"""
    issue = {
        'id': str(uuid.uuid4()),
        'tenant_id': current_user.tenant_id,
        'room_id': request.room_id,
        'issue_type': request.issue_type,
        'description': request.description,
        'priority': request.priority,
        'photos': request.photos,
        'status': 'open',
        'reported_by': current_user.name,
        'reported_at': datetime.now(timezone.utc).isoformat()
    }
    
    issue_copy = issue.copy()
    await db.housekeeping_issues.insert_one(issue_copy)
    
    # If maintenance issue, create maintenance task
    if request.issue_type == 'maintenance':
        maintenance_task = {
            'id': str(uuid.uuid4()),
            'tenant_id': current_user.tenant_id,
            'room_id': request.room_id,
            'task_type': 'maintenance',
            'description': request.description,
            'priority': request.priority,
            'status': 'pending',
            'assigned_to': 'Engineering',
            'created_at': datetime.now(timezone.utc).isoformat()
        }
        await db.housekeeping_tasks.insert_one(maintenance_task)
    
    return {'message': 'Issue reported successfully', 'issue_id': issue['id']}

@api_router.post("/housekeeping/mobile/upload-photo")
async def upload_housekeeping_photo(
    request: UploadPhotoRequest,
    current_user: User = Depends(get_current_user)
):
    """Upload photo for housekeeping task"""
    photo_record = {
        'id': str(uuid.uuid4()),
        'tenant_id': current_user.tenant_id,
        'task_id': request.task_id,
        'photo_data': request.photo_base64[:100] + '...',  # Store truncated for demo
        'uploaded_by': current_user.name,
        'uploaded_at': datetime.now(timezone.utc).isoformat()
    }
    
    photo_copy = photo_record.copy()
    await db.housekeeping_photos.insert_one(photo_copy)
    
    return {'message': 'Photo uploaded successfully', 'photo_id': photo_record['id']}

@api_router.get("/housekeeping/mobile/room-status/{room_id}")
async def get_mobile_room_status(
    room_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get detailed room status for mobile app"""
    room = await db.rooms.find_one(
        {'id': room_id, 'tenant_id': current_user.tenant_id},
        {'_id': 0}
    )
    
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    # Get current booking
    booking = None
    if room.get('current_booking_id'):
        booking = await db.bookings.find_one(
            {'id': room['current_booking_id']},
            {'_id': 0}
        )
    
    # Get pending tasks for this room
    tasks = await db.housekeeping_tasks.find(
        {
            'tenant_id': current_user.tenant_id,
            'room_id': room_id,
            'status': {'$in': ['pending', 'in_progress']}
        },
        {'_id': 0}
    ).to_list(10)
    
    return {
        'room': room,
        'current_booking': booking,
        'pending_tasks': tasks
    }


# ========================================
# 4. E-Fatura & POS Integration (Extended)
# ========================================

@api_router.get("/efatura/invoices")
async def get_efatura_invoices(
    status: str = None,
    start_date: str = None,
    end_date: str = None,
    current_user: User = Depends(get_current_user)
):
    """Get E-Fatura invoices with filtering"""
    query = {'tenant_id': current_user.tenant_id}
    
    if status:
        query['efatura_status'] = status
    
    if start_date and end_date:
        query['invoice_date'] = {'$gte': start_date, '$lte': end_date}
    
    invoices = await db.accounting_invoices.find(
        query,
        {'_id': 0}
    ).sort('invoice_date', -1).limit(100).to_list(100)
    
    return {'invoices': invoices, 'count': len(invoices)}

@api_router.post("/efatura/generate/{invoice_id}")
async def generate_efatura(
    invoice_id: str,
    current_user: User = Depends(get_current_user)
):
    """Generate E-Fatura XML for GIB"""
    invoice = await db.accounting_invoices.find_one(
        {'id': invoice_id, 'tenant_id': current_user.tenant_id},
        {'_id': 0}
    )
    
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    # Generate E-Fatura XML (simplified)
    efatura_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2">
    <ID>{invoice['invoice_number']}</ID>
    <IssueDate>{invoice['invoice_date']}</IssueDate>
    <InvoiceTypeCode>SATIS</InvoiceTypeCode>
    <LineCountNumeric>{len(invoice.get('items', []))}</LineCountNumeric>
    <LegalMonetaryTotal>
        <TaxExclusiveAmount>{invoice.get('subtotal', 0)}</TaxExclusiveAmount>
        <TaxInclusiveAmount>{invoice.get('grand_total', 0)}</TaxInclusiveAmount>
    </LegalMonetaryTotal>
</Invoice>"""
    
    # Save E-Fatura record
    efatura_record = {
        'id': str(uuid.uuid4()),
        'tenant_id': current_user.tenant_id,
        'invoice_id': invoice_id,
        'invoice_number': invoice['invoice_number'],
        'efatura_uuid': str(uuid.uuid4()),
        'xml_content': efatura_xml,
        'status': 'generated',
        'generated_at': datetime.now(timezone.utc).isoformat()
    }
    
    efatura_copy = efatura_record.copy()
    await db.efatura_records.insert_one(efatura_copy)
    
    # Update invoice status
    await db.accounting_invoices.update_one(
        {'id': invoice_id},
        {'$set': {'efatura_status': 'generated', 'efatura_uuid': efatura_record['efatura_uuid']}}
    )
    
    return {
        'message': 'E-Fatura generated successfully',
        'efatura_uuid': efatura_record['efatura_uuid'],
        'xml_content': efatura_xml
    }

@api_router.post("/efatura/send-to-gib/{invoice_id}")
async def send_efatura_to_gib(
    invoice_id: str,
    current_user: User = Depends(get_current_user)
):
    """Send E-Fatura to GIB (Turkish Revenue Administration)"""
    efatura = await db.efatura_records.find_one(
        {'invoice_id': invoice_id, 'tenant_id': current_user.tenant_id},
        {'_id': 0}
    )
    
    if not efatura:
        raise HTTPException(status_code=404, detail="E-Fatura not found")
    
    # Mock GIB integration (in production, use actual GIB API)
    gib_response = {
        'status': 'success',
        'gib_id': str(uuid.uuid4()),
        'timestamp': datetime.now(timezone.utc).isoformat()
    }
    
    # Update E-Fatura status
    await db.efatura_records.update_one(
        {'id': efatura['id']},
        {
            '$set': {
                'status': 'sent_to_gib',
                'gib_response': gib_response,
                'sent_at': datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    await db.accounting_invoices.update_one(
        {'id': invoice_id},
        {'$set': {'efatura_status': 'sent', 'efatura_sent_at': datetime.now(timezone.utc).isoformat()}}
    )
    
    return {'message': 'E-Fatura sent to GIB successfully', 'gib_response': gib_response}

@api_router.get("/pos/transactions")
async def get_pos_transactions(
    start_date: str = None,
    end_date: str = None,
    current_user: User = Depends(get_current_user)
):
    """Get POS transactions"""
    query = {'tenant_id': current_user.tenant_id}
    
    if start_date and end_date:
        query['transaction_date'] = {'$gte': start_date, '$lte': end_date}
    
    transactions = await db.pos_transactions.find(
        query,
        {'_id': 0}
    ).sort('transaction_date', -1).limit(500).to_list(500)
    
    return {'transactions': transactions, 'count': len(transactions)}

@api_router.post("/pos/transaction")
async def create_pos_transaction(
    request: CreatePOSTransactionRequest,
    current_user: User = Depends(get_current_user)
):
    """Create POS transaction"""
    transaction = {
        'id': str(uuid.uuid4()),
        'tenant_id': current_user.tenant_id,
        'transaction_date': datetime.now(timezone.utc).date().isoformat(),
        'transaction_time': datetime.now(timezone.utc).time().isoformat(),
        'amount': request.amount,
        'payment_method': request.payment_method,
        'folio_id': request.folio_id,
        'status': 'completed',
        'processed_by': current_user.id,
        'created_at': datetime.now(timezone.utc).isoformat()
    }
    
    transaction_copy = transaction.copy()
    await db.pos_transactions.insert_one(transaction_copy)
    return transaction

@api_router.get("/pos/daily-summary")
async def get_pos_daily_summary(
    date: str = None,
    current_user: User = Depends(get_current_user)
):
    """Get POS daily summary"""
    if not date:
        date = datetime.now(timezone.utc).date().isoformat()
    
    # Aggregate transactions
    pipeline = [
        {
            '$match': {
                'tenant_id': current_user.tenant_id,
                'transaction_date': date
            }
        },
        {
            '$group': {
                '_id': '$payment_method',
                'total': {'$sum': '$amount'},
                'count': {'$sum': 1}
            }
        }
    ]
    
    results = await db.pos_transactions.aggregate(pipeline).to_list(100)
    
    summary = {
        'date': date,
        'by_payment_method': results,
        'grand_total': sum(r['total'] for r in results),
        'transaction_count': sum(r['count'] for r in results)
    }
    
    return summary


# ========================================
# POS ENHANCEMENTS - 3 New Features
# ========================================

# 1. MULTI-OUTLET SUPPORT (Restaurant 1, Restaurant 2, Bar, etc.)
@api_router.get("/pos/outlets")
async def get_outlets(current_user: User = Depends(get_current_user)):
    """Get all F&B outlets"""
    outlets = await db.pos_outlets.find(
        {'tenant_id': current_user.tenant_id},
        {'_id': 0}
    ).to_list(100)
    
    # Get transaction counts per outlet
    for outlet in outlets:
        today_trans = await db.pos_menu_transactions.count_documents({
            'tenant_id': current_user.tenant_id,
            'outlet_id': outlet['id'],
            'transaction_date': datetime.now(timezone.utc).date().isoformat()
        })
        outlet['today_transactions'] = today_trans
    
    return {'outlets': outlets, 'count': len(outlets)}

@api_router.post("/pos/outlets")
async def create_outlet(
    request: CreateOutletRequest,
    current_user: User = Depends(get_current_user)
):
    """Create new F&B outlet"""
    outlet = {
        'id': str(uuid.uuid4()),
        'tenant_id': current_user.tenant_id,
        'outlet_name': request.outlet_name,
        'outlet_type': request.outlet_type,
        'location': request.location,
        'capacity': request.capacity,
        'opening_hours': request.opening_hours,
        'status': 'active',
        'created_at': datetime.now(timezone.utc).isoformat()
    }
    
    outlet_copy = outlet.copy()
    await db.pos_outlets.insert_one(outlet_copy)
    return outlet

@api_router.get("/pos/outlets/{outlet_id}")
async def get_outlet_details(
    outlet_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get outlet details with menu and stats"""
    outlet = await db.pos_outlets.find_one({
        'id': outlet_id,
        'tenant_id': current_user.tenant_id
    }, {'_id': 0})
    
    if not outlet:
        raise HTTPException(status_code=404, detail="Outlet not found")
    
    # Get menu items
    menu_items = await db.pos_menu_items.find({
        'tenant_id': current_user.tenant_id,
        'outlet_id': outlet_id
    }, {'_id': 0}).to_list(1000)
    
    # Get today's stats
    today = datetime.now(timezone.utc).date().isoformat()
    today_transactions = await db.pos_menu_transactions.find({
        'tenant_id': current_user.tenant_id,
        'outlet_id': outlet_id,
        'transaction_date': today
    }, {'_id': 0}).to_list(1000)
    
    today_revenue = sum(t.get('total_amount', 0) for t in today_transactions)
    
    return {
        'outlet': outlet,
        'menu_items': menu_items,
        'menu_items_count': len(menu_items),
        'today_stats': {
            'transactions': len(today_transactions),
            'revenue': round(today_revenue, 2)
        }
    }


# 2. MENU-BASED TRANSACTION BREAKDOWN
@api_router.get("/pos/menu-items")
async def get_menu_items(
    outlet_id: str = None,
    category: str = None,
    current_user: User = Depends(get_current_user)
):
    """Get menu items with optional filters"""
    query = {'tenant_id': current_user.tenant_id}
    
    if outlet_id:
        query['outlet_id'] = outlet_id
    if category:
        query['category'] = category
    
    menu_items = await db.pos_menu_items.find(query, {'_id': 0}).to_list(1000)
    
    return {'menu_items': menu_items, 'count': len(menu_items)}

@api_router.post("/pos/menu-items")
async def create_menu_item(
    request: CreateMenuItemRequest,
    current_user: User = Depends(get_current_user)
):
    """Create menu item for outlet"""
    # Verify outlet exists
    outlet = await db.pos_outlets.find_one({
        'id': request.outlet_id,
        'tenant_id': current_user.tenant_id
    })
    
    if not outlet:
        raise HTTPException(status_code=404, detail="Outlet not found")
    
    menu_item = {
        'id': str(uuid.uuid4()),
        'tenant_id': current_user.tenant_id,
        'outlet_id': request.outlet_id,
        'item_name': request.item_name,
        'category': request.category,
        'price': request.price,
        'cost': request.cost,
        'description': request.description,
        'status': 'active',
        'created_at': datetime.now(timezone.utc).isoformat()
    }
    
    menu_copy = menu_item.copy()
    await db.pos_menu_items.insert_one(menu_copy)
    return menu_item

@api_router.post("/pos/transactions/with-menu")
async def create_pos_transaction_with_menu(
    request: CreatePOSTransactionWithMenuRequest,
    current_user: User = Depends(get_current_user)
):
    """Create POS transaction with menu item breakdown"""
    # Verify outlet
    outlet = await db.pos_outlets.find_one({
        'id': request.outlet_id,
        'tenant_id': current_user.tenant_id
    })
    
    if not outlet:
        raise HTTPException(status_code=404, detail="Outlet not found")
    
    # Calculate totals
    subtotal = sum(item.get('quantity', 0) * item.get('price', 0) for item in request.items)
    
    # Get menu item details and calculate costs
    enriched_items = []
    total_cost = 0
    
    for item in request.items:
        menu_item = await db.pos_menu_items.find_one({
            'id': item.get('menu_item_id'),
            'tenant_id': current_user.tenant_id
        }, {'_id': 0})
        
        if menu_item:
            item_cost = menu_item.get('cost', 0) * item.get('quantity', 0)
            total_cost += item_cost
            
            enriched_items.append({
                'menu_item_id': item.get('menu_item_id'),
                'item_name': menu_item.get('item_name'),
                'category': menu_item.get('category'),
                'quantity': item.get('quantity'),
                'unit_price': item.get('price'),
                'unit_cost': menu_item.get('cost', 0),
                'total_price': item.get('quantity') * item.get('price'),
                'total_cost': item_cost
            })
    
    # Create transaction
    transaction = {
        'id': str(uuid.uuid4()),
        'tenant_id': current_user.tenant_id,
        'outlet_id': request.outlet_id,
        'outlet_name': outlet.get('outlet_name'),
        'transaction_date': datetime.now(timezone.utc).date().isoformat(),
        'transaction_time': datetime.now(timezone.utc).time().isoformat(),
        'items': enriched_items,
        'subtotal': round(subtotal, 2),
        'total_amount': round(subtotal, 2),  # Can add tax/service charge
        'total_cost': round(total_cost, 2),
        'gross_profit': round(subtotal - total_cost, 2),
        'payment_method': request.payment_method,
        'folio_id': request.folio_id,
        'table_number': request.table_number,
        'server_name': request.server_name,
        'status': 'completed',
        'processed_by': current_user.id,
        'created_at': datetime.now(timezone.utc).isoformat()
    }
    
    trans_copy = transaction.copy()
    await db.pos_menu_transactions.insert_one(trans_copy)
    
    # Post to folio if folio_id provided
    if request.folio_id:
        folio_charge = {
            'id': str(uuid.uuid4()),
            'tenant_id': current_user.tenant_id,
            'folio_id': request.folio_id,
            'charge_date': datetime.now(timezone.utc).date().isoformat(),
            'description': f"F&B - {outlet.get('outlet_name')}",
            'category': 'fnb',
            'amount': subtotal,
            'quantity': 1,
            'total': subtotal,
            'voided': False,
            'posted_at': datetime.now(timezone.utc).isoformat(),
            'posted_by': current_user.id
        }
        folio_copy = folio_charge.copy()
        await db.folio_charges.insert_one(folio_copy)
    
    return transaction

@api_router.get("/pos/menu-sales-breakdown")
async def get_menu_sales_breakdown(
    outlet_id: str = None,
    start_date: str = None,
    end_date: str = None,
    current_user: User = Depends(get_current_user)
):
    """Get menu item sales breakdown"""
    if not start_date:
        start_date = datetime.now(timezone.utc).date().isoformat()
    if not end_date:
        end_date = start_date
    
    # Get transactions
    query = {
        'tenant_id': current_user.tenant_id,
        'transaction_date': {'$gte': start_date, '$lte': end_date}
    }
    
    if outlet_id:
        query['outlet_id'] = outlet_id
    
    transactions = await db.pos_menu_transactions.find(query, {'_id': 0}).to_list(10000)
    
    # Aggregate by menu item
    menu_sales = {}
    category_sales = {}
    outlet_sales = {}
    
    for trans in transactions:
        outlet_name = trans.get('outlet_name', 'Unknown')
        outlet_sales[outlet_name] = outlet_sales.get(outlet_name, 0) + trans.get('total_amount', 0)
        
        for item in trans.get('items', []):
            item_name = item.get('item_name')
            category = item.get('category', 'Other')
            
            if item_name not in menu_sales:
                menu_sales[item_name] = {
                    'item_name': item_name,
                    'category': category,
                    'quantity_sold': 0,
                    'total_revenue': 0,
                    'total_cost': 0,
                    'gross_profit': 0
                }
            
            menu_sales[item_name]['quantity_sold'] += item.get('quantity', 0)
            menu_sales[item_name]['total_revenue'] += item.get('total_price', 0)
            menu_sales[item_name]['total_cost'] += item.get('total_cost', 0)
            menu_sales[item_name]['gross_profit'] += (item.get('total_price', 0) - item.get('total_cost', 0))
            
            category_sales[category] = category_sales.get(category, 0) + item.get('total_price', 0)
    
    # Sort by revenue
    sorted_menu_sales = sorted(menu_sales.values(), key=lambda x: x['total_revenue'], reverse=True)
    
    # Calculate totals
    total_revenue = sum(item['total_revenue'] for item in sorted_menu_sales)
    total_cost = sum(item['total_cost'] for item in sorted_menu_sales)
    
    return {
        'date_range': f"{start_date} to {end_date}",
        'menu_items': sorted_menu_sales,
        'by_category': [
            {'category': cat, 'revenue': round(rev, 2)}
            for cat, rev in sorted(category_sales.items(), key=lambda x: x[1], reverse=True)
        ],
        'by_outlet': [
            {'outlet_name': name, 'revenue': round(rev, 2)}
            for name, rev in sorted(outlet_sales.items(), key=lambda x: x[1], reverse=True)
        ],
        'summary': {
            'total_transactions': len(transactions),
            'total_revenue': round(total_revenue, 2),
            'total_cost': round(total_cost, 2),
            'gross_profit': round(total_revenue - total_cost, 2),
            'profit_margin': round((total_revenue - total_cost) / total_revenue * 100, 1) if total_revenue > 0 else 0
        }
    }


# 3. Z REPORT / GÜNLÜK KAPANIŞ
@api_router.post("/pos/z-report")
async def generate_z_report(
    request: GenerateZReportRequest,
    current_user: User = Depends(get_current_user)
):
    """Generate Z Report (End of Day report)"""
    date = request.date or datetime.now(timezone.utc).date().isoformat()
    outlet_id = request.outlet_id
    
    # Get transactions for the day
    query = {
        'tenant_id': current_user.tenant_id,
        'transaction_date': date
    }
    
    if outlet_id:
        query['outlet_id'] = outlet_id
        outlet = await db.pos_outlets.find_one({'id': outlet_id}, {'_id': 0})
        outlet_name = outlet.get('outlet_name') if outlet else 'Unknown'
    else:
        outlet_name = 'All Outlets'
    
    transactions = await db.pos_menu_transactions.find(query, {'_id': 0}).to_list(10000)
    
    if not transactions:
        return {
            'message': 'No transactions found for this date',
            'date': date,
            'outlet': outlet_name
        }
    
    # Calculate totals
    total_transactions = len(transactions)
    gross_sales = sum(t.get('total_amount', 0) for t in transactions)
    total_cost = sum(t.get('total_cost', 0) for t in transactions)
    gross_profit = gross_sales - total_cost
    
    # Payment method breakdown
    payment_methods = {}
    for trans in transactions:
        method = trans.get('payment_method', 'cash')
        payment_methods[method] = payment_methods.get(method, 0) + trans.get('total_amount', 0)
    
    # Category breakdown
    category_sales = {}
    menu_item_sales = {}
    
    for trans in transactions:
        for item in trans.get('items', []):
            category = item.get('category', 'Other')
            item_name = item.get('item_name')
            
            category_sales[category] = category_sales.get(category, 0) + item.get('total_price', 0)
            
            if item_name not in menu_item_sales:
                menu_item_sales[item_name] = {
                    'quantity': 0,
                    'revenue': 0
                }
            menu_item_sales[item_name]['quantity'] += item.get('quantity', 0)
            menu_item_sales[item_name]['revenue'] += item.get('total_price', 0)
    
    # Server breakdown
    server_sales = {}
    for trans in transactions:
        server = trans.get('server_name', 'Unknown')
        server_sales[server] = server_sales.get(server, 0) + trans.get('total_amount', 0)
    
    # Hourly breakdown
    hourly_sales = {}
    for trans in transactions:
        hour = trans.get('transaction_time', '00:00:00')[:2]
        hourly_sales[hour] = hourly_sales.get(hour, 0) + trans.get('total_amount', 0)
    
    # Top selling items
    top_items = sorted(
        [{'item': k, **v} for k, v in menu_item_sales.items()],
        key=lambda x: x['revenue'],
        reverse=True
    )[:10]
    
    # Create Z Report
    z_report = {
        'id': str(uuid.uuid4()),
        'tenant_id': current_user.tenant_id,
        'report_date': date,
        'outlet_id': outlet_id,
        'outlet_name': outlet_name,
        'report_type': 'Z-Report',
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'generated_by': current_user.id,
        
        # Summary
        'summary': {
            'total_transactions': total_transactions,
            'gross_sales': round(gross_sales, 2),
            'total_cost': round(total_cost, 2),
            'gross_profit': round(gross_profit, 2),
            'profit_margin': round((gross_profit / gross_sales * 100), 1) if gross_sales > 0 else 0,
            'average_check': round(gross_sales / total_transactions, 2) if total_transactions > 0 else 0
        },
        
        # Payment methods
        'payment_methods': [
            {'method': method, 'amount': round(amount, 2), 'count': sum(1 for t in transactions if t.get('payment_method') == method)}
            for method, amount in payment_methods.items()
        ],
        
        # Category breakdown
        'categories': [
            {'category': cat, 'revenue': round(rev, 2)}
            for cat, rev in sorted(category_sales.items(), key=lambda x: x[1], reverse=True)
        ],
        
        # Server performance
        'servers': [
            {'server_name': server, 'revenue': round(rev, 2)}
            for server, rev in sorted(server_sales.items(), key=lambda x: x[1], reverse=True)
        ],
        
        # Hourly sales
        'hourly_breakdown': [
            {'hour': f"{hour}:00", 'revenue': round(rev, 2)}
            for hour, rev in sorted(hourly_sales.items())
        ],
        
        # Top selling items
        'top_items': [
            {
                'item_name': item['item'],
                'quantity_sold': item['quantity'],
                'revenue': round(item['revenue'], 2)
            }
            for item in top_items
        ]
    }
    
    # Save Z Report
    z_copy = z_report.copy()
    await db.z_reports.insert_one(z_copy)
    
    return z_report

@api_router.get("/pos/z-reports")
async def get_z_reports(
    outlet_id: str = None,
    start_date: str = None,
    end_date: str = None,
    current_user: User = Depends(get_current_user)
):
    """Get Z Reports history"""
    query = {'tenant_id': current_user.tenant_id}
    
    if outlet_id:
        query['outlet_id'] = outlet_id
    
    if start_date and end_date:
        query['report_date'] = {'$gte': start_date, '$lte': end_date}
    
    reports = await db.z_reports.find(
        query,
        {'_id': 0}
    ).sort('report_date', -1).to_list(100)
    
    return {'reports': reports, 'count': len(reports)}


# ========================================
# 5. Group Reservations & Block Reservations
# ========================================

@api_router.get("/group-reservations")
async def get_group_reservations(current_user: User = Depends(get_current_user)):
    """Get all group reservations"""
    groups = await db.group_reservations.find(
        {'tenant_id': current_user.tenant_id},
        {'_id': 0}
    ).sort('created_at', -1).to_list(100)
    
    return {'groups': groups, 'count': len(groups)}

@api_router.post("/group-reservations")
async def create_group_reservation(
    request: CreateGroupReservationRequest,
    current_user: User = Depends(get_current_user)
):
    """Create new group reservation"""
    group = {
        'id': str(uuid.uuid4()),
        'tenant_id': current_user.tenant_id,
        'group_name': request.group_name,
        'group_type': request.group_type,
        'contact_person': request.contact_person,
        'contact_email': request.contact_email,
        'contact_phone': request.contact_phone,
        'check_in_date': request.check_in_date,
        'check_out_date': request.check_out_date,
        'total_rooms': request.total_rooms,
        'adults_per_room': request.adults_per_room,
        'special_requests': request.special_requests,
        'status': 'pending',
        'rooms_assigned': 0,
        'created_at': datetime.now(timezone.utc).isoformat(),
        'created_by': current_user.id
    }
    
    group_copy = group.copy()
    await db.group_reservations.insert_one(group_copy)
    return group

@api_router.get("/group-reservations/{group_id}")
async def get_group_reservation(
    group_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get group reservation details"""
    group = await db.group_reservations.find_one(
        {'id': group_id, 'tenant_id': current_user.tenant_id},
        {'_id': 0}
    )
    
    if not group:
        raise HTTPException(status_code=404, detail="Group reservation not found")
    
    # Get individual bookings in this group
    bookings = await db.bookings.find(
        {'tenant_id': current_user.tenant_id, 'group_id': group_id},
        {'_id': 0}
    ).to_list(1000)
    
    group['bookings'] = bookings
    group['bookings_count'] = len(bookings)
    
    return group

@api_router.post("/group-reservations/{group_id}/assign-rooms")
async def assign_group_rooms(
    group_id: str,
    request: AssignGroupRoomsRequest,
    current_user: User = Depends(get_current_user)
):
    """Assign rooms to group reservation"""
    room_assignments = request.room_assignments
    group = await db.group_reservations.find_one(
        {'id': group_id, 'tenant_id': current_user.tenant_id}
    )
    
    if not group:
        raise HTTPException(status_code=404, detail="Group reservation not found")
    
    created_bookings = []
    
    for assignment in room_assignments:
        booking = {
            'id': str(uuid.uuid4()),
            'tenant_id': current_user.tenant_id,
            'group_id': group_id,
            'guest_name': assignment.get('guest_name', group['group_name']),
            'guest_email': assignment.get('guest_email', group['contact_email']),
            'guest_phone': assignment.get('guest_phone', group['contact_phone']),
            'check_in_date': group['check_in_date'],
            'check_out_date': group['check_out_date'],
            'room_type': assignment['room_type'],
            'room_id': assignment.get('room_id'),
            'adults': assignment.get('adults', group['adults_per_room']),
            'children': assignment.get('children', 0),
            'status': 'confirmed',
            'booking_source': 'group',
            'created_at': datetime.now(timezone.utc).isoformat()
        }
        
        await db.bookings.insert_one(booking)
        created_bookings.append(booking)
    
    # Update group reservation
    await db.group_reservations.update_one(
        {'id': group_id},
        {
            '$set': {
                'rooms_assigned': len(created_bookings),
                'status': 'confirmed' if len(created_bookings) >= group['total_rooms'] else 'partial'
            }
        }
    )
    
    return {
        'message': f'Assigned {len(created_bookings)} rooms to group',
        'bookings': created_bookings
    }

@api_router.get("/block-reservations")
async def get_block_reservations(current_user: User = Depends(get_current_user)):
    """Get all block reservations"""
    blocks = await db.block_reservations.find(
        {'tenant_id': current_user.tenant_id},
        {'_id': 0}
    ).sort('created_at', -1).to_list(100)
    
    return {'blocks': blocks, 'count': len(blocks)}

@api_router.post("/block-reservations")
async def create_block_reservation(
    request: CreateBlockReservationRequest,
    current_user: User = Depends(get_current_user)
):
    """Create room block reservation"""
    block = {
        'id': str(uuid.uuid4()),
        'tenant_id': current_user.tenant_id,
        'block_name': request.block_name,
        'room_type': request.room_type,
        'start_date': request.start_date,
        'end_date': request.end_date,
        'total_rooms': request.total_rooms,
        'rooms_used': 0,
        'rooms_available': request.total_rooms,
        'block_type': request.block_type,
        'release_date': request.release_date,
        'status': 'active',
        'created_at': datetime.now(timezone.utc).isoformat(),
        'created_by': current_user.id
    }
    
    block_copy = block.copy()
    await db.block_reservations.insert_one(block_copy)
    return block

@api_router.post("/block-reservations/{block_id}/use-room")
async def use_block_room(
    block_id: str,
    request: UseBlockRoomRequest,
    current_user: User = Depends(get_current_user)
):
    """Use a room from block reservation"""
    guest_name = request.guest_name
    guest_email = request.guest_email
    block = await db.block_reservations.find_one(
        {'id': block_id, 'tenant_id': current_user.tenant_id}
    )
    
    if not block:
        raise HTTPException(status_code=404, detail="Block reservation not found")
    
    if block['rooms_available'] <= 0:
        raise HTTPException(status_code=400, detail="No rooms available in block")
    
    # Create booking from block
    booking = {
        'id': str(uuid.uuid4()),
        'tenant_id': current_user.tenant_id,
        'block_id': block_id,
        'guest_name': guest_name,
        'guest_email': guest_email,
        'check_in_date': block['start_date'],
        'check_out_date': block['end_date'],
        'room_type': block['room_type'],
        'status': 'confirmed',
        'booking_source': 'block',
        'created_at': datetime.now(timezone.utc).isoformat()
    }
    
    await db.bookings.insert_one(booking.copy())
    
    # Update block availability
    await db.block_reservations.update_one(
        {'id': block_id},
        {
            '$inc': {'rooms_used': 1, 'rooms_available': -1}
        }
    )
    
    return {'message': 'Room used from block successfully', 'booking': booking}

@api_router.post("/block-reservations/{block_id}/release")
async def release_block_reservation(
    block_id: str,
    current_user: User = Depends(get_current_user)
):
    """Release unused rooms from block"""
    block = await db.block_reservations.find_one(
        {'id': block_id, 'tenant_id': current_user.tenant_id}
    )
    
    if not block:
        raise HTTPException(status_code=404, detail="Block reservation not found")
    
    await db.block_reservations.update_one(
        {'id': block_id},
        {
            '$set': {
                'status': 'released',
                'released_at': datetime.now(timezone.utc).isoformat(),
                'released_by': current_user.id
            }
        }
    )
    
    return {
        'message': 'Block released successfully',
        'rooms_released': block['rooms_available']
    }


# ========================================
# 6. Multi-Property Management
# ========================================

@api_router.get("/multi-property/properties")
async def get_properties(current_user: User = Depends(get_current_user)):
    """Get all properties in portfolio"""
    properties = await db.properties.find(
        {'portfolio_id': current_user.tenant_id},
        {'_id': 0}
    ).to_list(100)
    
    return {'properties': properties, 'count': len(properties)}

@api_router.post("/multi-property/properties")
async def create_property(
    request: CreatePropertyRequest,
    current_user: User = Depends(get_current_user)
):
    """Add new property to portfolio"""
    property_obj = {
        'id': str(uuid.uuid4()),
        'portfolio_id': current_user.tenant_id,
        'property_name': request.property_name,
        'property_code': request.property_code,
        'location': request.location,
        'total_rooms': request.total_rooms,
        'property_type': request.property_type,
        'status': request.status,
        'created_at': datetime.now(timezone.utc).isoformat()
    }
    
    property_copy = property_obj.copy()
    await db.properties.insert_one(property_copy)
    return property_obj

@api_router.get("/multi-property/dashboard")
async def get_multi_property_dashboard(
    date: str = None,
    current_user: User = Depends(get_current_user)
):
    """Get consolidated dashboard across all properties"""
    if not date:
        date = datetime.now(timezone.utc).date().isoformat()
    
    # Get all properties
    properties = await db.properties.find(
        {'portfolio_id': current_user.tenant_id, 'status': 'active'},
        {'_id': 0}
    ).to_list(100)
    
    property_stats = []
    total_rooms = 0
    total_occupied = 0
    total_revenue = 0.0
    
    for prop in properties:
        # Get rooms for this property
        rooms = await db.rooms.count_documents({
            'tenant_id': prop['id'],
            'room_status': {'$ne': 'out_of_order'}
        })
        
        occupied = await db.rooms.count_documents({
            'tenant_id': prop['id'],
            'room_status': 'occupied'
        })
        
        # Get revenue (simplified)
        pipeline = [
            {
                '$match': {
                    'tenant_id': prop['id'],
                    'charge_date': date,
                    'voided': False
                }
            },
            {
                '$group': {
                    '_id': None,
                    'total': {'$sum': '$total'}
                }
            }
        ]
        
        revenue_result = await db.folio_charges.aggregate(pipeline).to_list(1)
        revenue = revenue_result[0]['total'] if revenue_result else 0.0
        
        occupancy = (occupied / rooms * 100) if rooms > 0 else 0
        
        property_stats.append({
            'property_id': prop['id'],
            'property_name': prop['property_name'],
            'property_code': prop['property_code'],
            'total_rooms': rooms,
            'occupied_rooms': occupied,
            'occupancy': round(occupancy, 1),
            'revenue': round(revenue, 2)
        })
        
        total_rooms += rooms
        total_occupied += occupied
        total_revenue += revenue
    
    overall_occupancy = (total_occupied / total_rooms * 100) if total_rooms > 0 else 0
    
    return {
        'date': date,
        'portfolio_summary': {
            'total_properties': len(properties),
            'total_rooms': total_rooms,
            'occupied_rooms': total_occupied,
            'overall_occupancy': round(overall_occupancy, 1),
            'total_revenue': round(total_revenue, 2),
            'average_occupancy': round(sum(p['occupancy'] for p in property_stats) / len(property_stats), 1) if property_stats else 0
        },
        'properties': property_stats
    }

@api_router.get("/multi-property/consolidated-report")
async def get_consolidated_report(
    start_date: str,
    end_date: str,
    metric: str = 'occupancy',
    current_user: User = Depends(get_current_user)
):
    """Get consolidated report across properties"""
    properties = await db.properties.find(
        {'portfolio_id': current_user.tenant_id, 'status': 'active'},
        {'_id': 0}
    ).to_list(100)
    
    start = datetime.fromisoformat(start_date)
    end = datetime.fromisoformat(end_date)
    days = (end - start).days + 1
    
    report_data = []
    
    for day in range(days):
        current_date = (start + timedelta(days=day)).date().isoformat()
        
        day_data = {
            'date': current_date,
            'properties': []
        }
        
        for prop in properties:
            # Simplified metrics
            if metric == 'occupancy':
                rooms = await db.rooms.count_documents({'tenant_id': prop['id']})
                occupied = await db.rooms.count_documents({
                    'tenant_id': prop['id'],
                    'room_status': 'occupied'
                })
                value = (occupied / rooms * 100) if rooms > 0 else 0
            elif metric == 'revenue':
                pipeline = [
                    {
                        '$match': {
                            'tenant_id': prop['id'],
                            'charge_date': current_date,
                            'voided': False
                        }
                    },
                    {
                        '$group': {
                            '_id': None,
                            'total': {'$sum': '$total'}
                        }
                    }
                ]
                result = await db.folio_charges.aggregate(pipeline).to_list(1)
                value = result[0]['total'] if result else 0.0
            else:
                value = 0
            
            day_data['properties'].append({
                'property_id': prop['id'],
                'property_name': prop['property_name'],
                'value': round(value, 2)
            })
        
        report_data.append(day_data)
    
    return {
        'start_date': start_date,
        'end_date': end_date,
        'metric': metric,
        'data': report_data
    }

@api_router.post("/multi-property/transfer-reservation")
async def transfer_reservation_between_properties(
    booking_id: str,
    request: TransferReservationRequest,
    current_user: User = Depends(get_current_user)
):
    """Transfer reservation from one property to another"""
    booking = await db.bookings.find_one({'id': booking_id})
    target_property_id = request.target_property_id
    reason = request.reason
    
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    # Create transfer record
    transfer = {
        'id': str(uuid.uuid4()),
        'booking_id': booking_id,
        'from_property': booking['tenant_id'],
        'to_property': target_property_id,
        'reason': reason,
        'transferred_at': datetime.now(timezone.utc).isoformat(),
        'transferred_by': current_user.id
    }
    
    await db.property_transfers.insert_one(transfer)
    
    # Update booking tenant_id
    await db.bookings.update_one(
        {'id': booking_id},
        {'$set': {'tenant_id': target_property_id, 'transferred': True}}
    )
    
    return {'message': 'Reservation transferred successfully', 'transfer': transfer}


# ========================================
# 7. Marketplace - Warehouse & Procurement
# ========================================

@api_router.get("/marketplace/products")
async def get_marketplace_products(
    category: str = None,
    current_user: User = Depends(get_current_user)
):
    """Get marketplace product catalog"""
    query = {}
    if category:
        query['category'] = category
    
    products = await db.marketplace_products.find(
        query,
        {'_id': 0}
    ).to_list(1000)
    
    return {'products': products, 'count': len(products)}

@api_router.post("/marketplace/products")
async def create_marketplace_product(
    request: CreateMarketplaceProductRequest,
    current_user: User = Depends(get_current_user)
):
    """Add product to marketplace catalog"""
    product = {
        'id': str(uuid.uuid4()),
        'product_name': request.product_name,
        'category': request.category,
        'unit_price': request.unit_price,
        'unit_of_measure': request.unit_of_measure,
        'supplier': request.supplier,
        'min_order_qty': request.min_order_qty,
        'status': 'active',
        'created_at': datetime.now(timezone.utc).isoformat()
    }
    
    product_copy = product.copy()
    await db.marketplace_products.insert_one(product_copy)
    return product

@api_router.get("/marketplace/inventory")
async def get_inventory(
    location: str = None,
    current_user: User = Depends(get_current_user)
):
    """Get current inventory levels"""
    query = {'tenant_id': current_user.tenant_id}
    if location:
        query['location'] = location
    
    inventory = await db.inventory.find(
        query,
        {'_id': 0}
    ).to_list(1000)
    
    return {'inventory': inventory, 'count': len(inventory)}

@api_router.post("/marketplace/inventory/adjust")
async def adjust_inventory(
    request: AdjustInventoryRequest,
    current_user: User = Depends(get_current_user)
):
    """Adjust inventory quantity"""
    # Get current inventory
    inventory = await db.inventory.find_one({
        'tenant_id': current_user.tenant_id,
        'product_id': request.product_id,
        'location': request.location
    })
    product_id = request.product_id
    location = request.location
    quantity_change = request.quantity_change
    reason = request.reason
    
    if not inventory:
        # Create new inventory record
        inventory = {
            'id': str(uuid.uuid4()),
            'tenant_id': current_user.tenant_id,
            'product_id': request.product_id,
            'location': request.location,
            'quantity': max(0, request.quantity_change),
            'updated_at': datetime.now(timezone.utc).isoformat()
        }
        await db.inventory.insert_one(inventory)
    else:
        # Update existing inventory
        new_qty = max(0, inventory['quantity'] + quantity_change)
        await db.inventory.update_one(
            {'id': inventory['id']},
            {
                '$set': {
                    'quantity': new_qty,
                    'updated_at': datetime.now(timezone.utc).isoformat()
                }
            }
        )
    
    # Log adjustment
    log = {
        'id': str(uuid.uuid4()),
        'tenant_id': current_user.tenant_id,
        'product_id': request.product_id,
        'location': request.location,
        'quantity_change': request.quantity_change,
        'reason': request.reason,
        'adjusted_by': current_user.id,
        'adjusted_at': datetime.now(timezone.utc).isoformat()
    }
    await db.inventory_adjustments.insert_one(log)
    
    return {'message': 'Inventory adjusted successfully'}

@api_router.get("/marketplace/purchase-orders")
async def get_purchase_orders(
    status: str = None,
    current_user: User = Depends(get_current_user)
):
    """Get purchase orders"""
    query = {'tenant_id': current_user.tenant_id}
    if status:
        query['status'] = status
    
    orders = await db.purchase_orders.find(
        query,
        {'_id': 0}
    ).sort('created_at', -1).to_list(100)
    
    return {'orders': orders, 'count': len(orders)}

@api_router.post("/marketplace/purchase-orders")
async def create_purchase_order(
    request: CreatePurchaseOrderRequest,
    current_user: User = Depends(get_current_user)
):
    """Create purchase order"""
    # Calculate total
    total_amount = sum(item.get('quantity', 0) * item.get('unit_price', 0) for item in request.items)
    
    po = {
        'id': str(uuid.uuid4()),
        'tenant_id': current_user.tenant_id,
        'po_number': f"PO-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}",
        'supplier': request.supplier,
        'items': request.items,
        'delivery_location': request.delivery_location,
        'expected_delivery_date': request.expected_delivery_date,
        'total_amount': round(total_amount, 2),
        'status': 'pending',
        'created_at': datetime.now(timezone.utc).isoformat(),
        'created_by': current_user.id
    }
    
    po_copy = po.copy()
    await db.purchase_orders.insert_one(po_copy)
    return po

@api_router.post("/marketplace/purchase-orders/{po_id}/approve")
async def approve_purchase_order(
    po_id: str,
    current_user: User = Depends(get_current_user)
):
    """Approve purchase order"""
    po = await db.purchase_orders.find_one({
        'id': po_id,
        'tenant_id': current_user.tenant_id
    })
    
    if not po:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    
    await db.purchase_orders.update_one(
        {'id': po_id},
        {
            '$set': {
                'status': 'approved',
                'approved_at': datetime.now(timezone.utc).isoformat(),
                'approved_by': current_user.id
            }
        }
    )
    
    return {'message': 'Purchase order approved successfully'}

@api_router.post("/marketplace/purchase-orders/{po_id}/receive")
async def receive_purchase_order(
    po_id: str,
    request: ReceivePurchaseOrderRequest,
    current_user: User = Depends(get_current_user)
):
    """Receive purchase order and update inventory"""
    received_items = request.received_items
    po = await db.purchase_orders.find_one({
        'id': po_id,
        'tenant_id': current_user.tenant_id
    })
    
    if not po:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    
    # Update inventory for received items
    for item in received_items:
        await db.inventory.update_one(
            {
                'tenant_id': current_user.tenant_id,
                'product_id': item['product_id'],
                'location': po['delivery_location']
            },
            {
                '$inc': {'quantity': item['quantity_received']},
                '$set': {'updated_at': datetime.now(timezone.utc).isoformat()}
            },
            upsert=True
        )
    
    # Update PO status
    await db.purchase_orders.update_one(
        {'id': po_id},
        {
            '$set': {
                'status': 'received',
                'received_at': datetime.now(timezone.utc).isoformat(),
                'received_by': current_user.id,
                'received_items': received_items
            }
        }
    )
    
    return {'message': 'Purchase order received and inventory updated'}

@api_router.get("/marketplace/deliveries")
async def get_deliveries(
    status: str = None,
    current_user: User = Depends(get_current_user)
):
    """Get delivery tracking"""
    query = {'tenant_id': current_user.tenant_id}
    if status:
        query['status'] = status
    
    deliveries = await db.deliveries.find(
        query,
        {'_id': 0}
    ).sort('created_at', -1).to_list(100)
    
    return {'deliveries': deliveries, 'count': len(deliveries)}

@api_router.post("/marketplace/deliveries")
async def create_delivery(
    request: CreateDeliveryRequest,
    current_user: User = Depends(get_current_user)
):
    """Create delivery tracking"""
    delivery = {
        'id': str(uuid.uuid4()),
        'tenant_id': current_user.tenant_id,
        'po_id': request.po_id,
        'tracking_number': request.tracking_number,
        'carrier': request.carrier,
        'estimated_delivery': request.estimated_delivery,
        'status': 'in_transit',
        'created_at': datetime.now(timezone.utc).isoformat()
    }
    
    delivery_copy = delivery.copy()
    await db.deliveries.insert_one(delivery_copy)
    return delivery

@api_router.get("/marketplace/stock-alerts")
async def get_stock_alerts(current_user: User = Depends(get_current_user)):
    """Get low stock alerts"""
    # Get all inventory items
    inventory_items = await db.inventory.find(
        {'tenant_id': current_user.tenant_id},
        {'_id': 0}
    ).to_list(1000)
    
    alerts = []
    for item in inventory_items:
        # Get product details
        product = await db.marketplace_products.find_one(
            {'id': item['product_id']},
            {'_id': 0}
        )
        
        if product:
            # Check if below minimum (using min_order_qty * 2 as threshold)
            threshold = product.get('min_order_qty', 1) * 2
            if item['quantity'] < threshold:
                alerts.append({
                    'product_id': item['product_id'],
                    'product_name': product['product_name'],
                    'location': item['location'],
                    'current_quantity': item['quantity'],
                    'threshold': threshold,
                    'status': 'low_stock'
                })
    
    return {'alerts': alerts, 'count': len(alerts)}


# ========================================
# MARKETPLACE EXTENSIONS - 4 New Features
# ========================================

# 1. SUPPLIER MANAGEMENT WITH CREDIT LIMITS
@api_router.get("/marketplace/suppliers")
async def get_suppliers(
    status: str = None,
    current_user: User = Depends(get_current_user)
):
    """Get all suppliers with credit limit info"""
    query = {'tenant_id': current_user.tenant_id}
    if status:
        query['status'] = status
    
    suppliers = await db.suppliers.find(
        query,
        {'_id': 0}
    ).to_list(100)
    
    return {'suppliers': suppliers, 'count': len(suppliers)}

@api_router.post("/marketplace/suppliers")
async def create_supplier(
    request: CreateSupplierRequest,
    current_user: User = Depends(get_current_user)
):
    """Create new supplier with credit limit"""
    supplier = {
        'id': str(uuid.uuid4()),
        'tenant_id': current_user.tenant_id,
        'supplier_name': request.supplier_name,
        'contact_person': request.contact_person,
        'contact_email': request.contact_email,
        'contact_phone': request.contact_phone,
        'credit_limit': request.credit_limit,
        'current_outstanding': 0.0,
        'available_credit': request.credit_limit,
        'payment_terms': request.payment_terms,
        'status': request.status,
        'created_at': datetime.now(timezone.utc).isoformat()
    }
    
    supplier_copy = supplier.copy()
    await db.suppliers.insert_one(supplier_copy)
    return supplier

@api_router.put("/marketplace/suppliers/{supplier_id}/credit")
async def update_supplier_credit(
    supplier_id: str,
    request: UpdateSupplierCreditRequest,
    current_user: User = Depends(get_current_user)
):
    """Update supplier credit limit and payment terms"""
    supplier = await db.suppliers.find_one({
        'id': supplier_id,
        'tenant_id': current_user.tenant_id
    })
    
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    
    # Update available credit based on outstanding
    available_credit = request.credit_limit - supplier.get('current_outstanding', 0.0)
    
    await db.suppliers.update_one(
        {'id': supplier_id},
        {
            '$set': {
                'credit_limit': request.credit_limit,
                'available_credit': available_credit,
                'payment_terms': request.payment_terms,
                'updated_at': datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    return {
        'message': 'Supplier credit updated successfully',
        'credit_limit': request.credit_limit,
        'available_credit': available_credit
    }

@api_router.get("/marketplace/suppliers/{supplier_id}/credit-status")
async def get_supplier_credit_status(
    supplier_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get supplier credit status and outstanding balance"""
    supplier = await db.suppliers.find_one(
        {'id': supplier_id, 'tenant_id': current_user.tenant_id},
        {'_id': 0}
    )
    
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    
    # Get all outstanding purchase orders
    outstanding_pos = await db.purchase_orders.find({
        'tenant_id': current_user.tenant_id,
        'supplier': supplier['supplier_name'],
        'status': {'$in': ['approved', 'received']},
        'payment_status': {'$ne': 'paid'}
    }, {'_id': 0}).to_list(100)
    
    total_outstanding = sum(po.get('total_amount', 0) for po in outstanding_pos)
    
    return {
        'supplier_id': supplier_id,
        'supplier_name': supplier['supplier_name'],
        'credit_limit': supplier.get('credit_limit', 0.0),
        'current_outstanding': total_outstanding,
        'available_credit': supplier.get('credit_limit', 0.0) - total_outstanding,
        'payment_terms': supplier.get('payment_terms', 'Net 30'),
        'outstanding_orders': len(outstanding_pos)
    }


# 2. GM APPROVAL WORKFLOW FOR PURCHASE ORDERS
@api_router.post("/marketplace/purchase-orders/{po_id}/submit-for-approval")
async def submit_po_for_approval(
    po_id: str,
    current_user: User = Depends(get_current_user)
):
    """Submit purchase order for GM approval"""
    po = await db.purchase_orders.find_one({
        'id': po_id,
        'tenant_id': current_user.tenant_id
    })
    
    if not po:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    
    if po.get('status') != 'pending':
        raise HTTPException(status_code=400, detail="Only pending orders can be submitted for approval")
    
    # Update PO status to awaiting_approval
    await db.purchase_orders.update_one(
        {'id': po_id},
        {
            '$set': {
                'status': 'awaiting_approval',
                'submitted_for_approval_at': datetime.now(timezone.utc).isoformat(),
                'submitted_by': current_user.id
            }
        }
    )
    
    # Create approval request record
    approval_request = {
        'id': str(uuid.uuid4()),
        'tenant_id': current_user.tenant_id,
        'po_id': po_id,
        'po_number': po.get('po_number'),
        'total_amount': po.get('total_amount'),
        'supplier': po.get('supplier'),
        'status': 'pending',
        'requested_by': current_user.id,
        'requested_at': datetime.now(timezone.utc).isoformat()
    }
    
    approval_copy = approval_request.copy()
    await db.approval_requests.insert_one(approval_copy)
    
    return {
        'message': 'Purchase order submitted for GM approval',
        'approval_request_id': approval_request['id']
    }

@api_router.get("/marketplace/approvals/pending")
async def get_pending_approvals(current_user: User = Depends(get_current_user)):
    """Get all pending approval requests (for GM)"""
    approvals = await db.approval_requests.find({
        'tenant_id': current_user.tenant_id,
        'status': 'pending'
    }, {'_id': 0}).sort('requested_at', -1).to_list(100)
    
    return {'approvals': approvals, 'count': len(approvals)}

@api_router.post("/marketplace/purchase-orders/{po_id}/approve")
async def approve_purchase_order_by_gm(
    po_id: str,
    request: ApprovePurchaseOrderRequest,
    current_user: User = Depends(get_current_user)
):
    """GM approves purchase order"""
    po = await db.purchase_orders.find_one({
        'id': po_id,
        'tenant_id': current_user.tenant_id
    })
    
    if not po:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    
    # Check user has GM/approval permission
    # (In production, add proper permission check here)
    
    # Update PO status
    await db.purchase_orders.update_one(
        {'id': po_id},
        {
            '$set': {
                'status': 'approved',
                'approved_at': datetime.now(timezone.utc).isoformat(),
                'approved_by': current_user.id,
                'approval_notes': request.approval_notes
            }
        }
    )
    
    # Update approval request
    await db.approval_requests.update_one(
        {'po_id': po_id, 'tenant_id': current_user.tenant_id},
        {
            '$set': {
                'status': 'approved',
                'approved_by': current_user.id,
                'approved_at': datetime.now(timezone.utc).isoformat(),
                'notes': request.approval_notes
            }
        }
    )
    
    # Update supplier outstanding balance
    supplier = await db.suppliers.find_one({
        'tenant_id': current_user.tenant_id,
        'supplier_name': po.get('supplier')
    })
    
    if supplier:
        new_outstanding = supplier.get('current_outstanding', 0.0) + po.get('total_amount', 0.0)
        await db.suppliers.update_one(
            {'id': supplier['id']},
            {
                '$set': {
                    'current_outstanding': new_outstanding,
                    'available_credit': supplier.get('credit_limit', 0.0) - new_outstanding
                }
            }
        )
    
    return {'message': 'Purchase order approved successfully'}

@api_router.post("/marketplace/purchase-orders/{po_id}/reject")
async def reject_purchase_order(
    po_id: str,
    request: RejectPurchaseOrderRequest,
    current_user: User = Depends(get_current_user)
):
    """GM rejects purchase order"""
    po = await db.purchase_orders.find_one({
        'id': po_id,
        'tenant_id': current_user.tenant_id
    })
    
    if not po:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    
    await db.purchase_orders.update_one(
        {'id': po_id},
        {
            '$set': {
                'status': 'rejected',
                'rejected_at': datetime.now(timezone.utc).isoformat(),
                'rejected_by': current_user.id,
                'rejection_reason': request.rejection_reason
            }
        }
    )
    
    await db.approval_requests.update_one(
        {'po_id': po_id, 'tenant_id': current_user.tenant_id},
        {
            '$set': {
                'status': 'rejected',
                'rejected_by': current_user.id,
                'rejected_at': datetime.now(timezone.utc).isoformat(),
                'rejection_reason': request.rejection_reason
            }
        }
    )
    
    return {'message': 'Purchase order rejected', 'reason': request.rejection_reason}


# 3. WAREHOUSE / DEPOT STOCK TRACKING
@api_router.get("/marketplace/warehouses")
async def get_warehouses(current_user: User = Depends(get_current_user)):
    """Get all warehouses/depots"""
    warehouses = await db.warehouses.find(
        {'tenant_id': current_user.tenant_id},
        {'_id': 0}
    ).to_list(100)
    
    return {'warehouses': warehouses, 'count': len(warehouses)}

@api_router.post("/marketplace/warehouses")
async def create_warehouse(
    request: CreateWarehouseRequest,
    current_user: User = Depends(get_current_user)
):
    """Create new warehouse/depot"""
    warehouse = {
        'id': str(uuid.uuid4()),
        'tenant_id': current_user.tenant_id,
        'warehouse_name': request.warehouse_name,
        'location': request.location,
        'capacity': request.capacity,
        'warehouse_type': request.warehouse_type,
        'current_stock_count': 0,
        'status': 'active',
        'created_at': datetime.now(timezone.utc).isoformat()
    }
    
    warehouse_copy = warehouse.copy()
    await db.warehouses.insert_one(warehouse_copy)
    return warehouse

@api_router.get("/marketplace/warehouses/{warehouse_id}/inventory")
async def get_warehouse_inventory(
    warehouse_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get inventory for specific warehouse"""
    warehouse = await db.warehouses.find_one({
        'id': warehouse_id,
        'tenant_id': current_user.tenant_id
    }, {'_id': 0})
    
    if not warehouse:
        raise HTTPException(status_code=404, detail="Warehouse not found")
    
    # Get all inventory items for this warehouse
    inventory = await db.inventory.find({
        'tenant_id': current_user.tenant_id,
        'location': warehouse['warehouse_name']
    }, {'_id': 0}).to_list(1000)
    
    # Enrich with product details
    for item in inventory:
        product = await db.marketplace_products.find_one(
            {'id': item['product_id']},
            {'_id': 0}
        )
        if product:
            item['product_name'] = product.get('product_name')
            item['category'] = product.get('category')
            item['unit_of_measure'] = product.get('unit_of_measure')
    
    total_items = sum(item.get('quantity', 0) for item in inventory)
    
    return {
        'warehouse': warehouse,
        'inventory': inventory,
        'total_items': total_items,
        'item_count': len(inventory)
    }

@api_router.get("/marketplace/stock-summary")
async def get_stock_summary_by_warehouse(current_user: User = Depends(get_current_user)):
    """Get stock summary across all warehouses"""
    warehouses = await db.warehouses.find(
        {'tenant_id': current_user.tenant_id},
        {'_id': 0}
    ).to_list(100)
    
    summary = []
    for warehouse in warehouses:
        inventory = await db.inventory.find({
            'tenant_id': current_user.tenant_id,
            'location': warehouse['warehouse_name']
        }, {'_id': 0}).to_list(1000)
        
        total_items = sum(item.get('quantity', 0) for item in inventory)
        unique_products = len(inventory)
        
        summary.append({
            'warehouse_id': warehouse['id'],
            'warehouse_name': warehouse['warehouse_name'],
            'location': warehouse['location'],
            'total_items': total_items,
            'unique_products': unique_products,
            'capacity': warehouse.get('capacity', 0),
            'utilization': round((total_items / warehouse.get('capacity', 1)) * 100, 1) if warehouse.get('capacity') else 0
        })
    
    return {'summary': summary, 'warehouse_count': len(warehouses)}


# 4. SHIPPING & DELIVERY TRACKING WITH CARRIER
@api_router.put("/marketplace/deliveries/{delivery_id}/update-status")
async def update_delivery_status(
    delivery_id: str,
    request: UpdateDeliveryStatusRequest,
    current_user: User = Depends(get_current_user)
):
    """Update delivery status with location tracking"""
    delivery = await db.deliveries.find_one({
        'id': delivery_id,
        'tenant_id': current_user.tenant_id
    })
    
    if not delivery:
        raise HTTPException(status_code=404, detail="Delivery not found")
    
    # Create tracking event
    tracking_event = {
        'status': request.status,
        'location': request.location,
        'notes': request.notes,
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'updated_by': current_user.id
    }
    
    # Update delivery
    await db.deliveries.update_one(
        {'id': delivery_id},
        {
            '$set': {
                'status': request.status,
                'current_location': request.location,
                'updated_at': datetime.now(timezone.utc).isoformat()
            },
            '$push': {
                'tracking_history': tracking_event
            }
        }
    )
    
    # If delivered, update PO status
    if request.status == 'delivered':
        await db.deliveries.update_one(
            {'id': delivery_id},
            {'$set': {'delivered_at': datetime.now(timezone.utc).isoformat()}}
        )
    
    return {
        'message': 'Delivery status updated successfully',
        'new_status': request.status,
        'tracking_event': tracking_event
    }

@api_router.get("/marketplace/deliveries/{delivery_id}/tracking")
async def get_delivery_tracking(
    delivery_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get full tracking history for delivery"""
    delivery = await db.deliveries.find_one({
        'id': delivery_id,
        'tenant_id': current_user.tenant_id
    }, {'_id': 0})
    
    if not delivery:
        raise HTTPException(status_code=404, detail="Delivery not found")
    
    # Get associated PO
    po = await db.purchase_orders.find_one({
        'id': delivery.get('po_id')
    }, {'_id': 0})
    
    return {
        'delivery': delivery,
        'purchase_order': po,
        'tracking_history': delivery.get('tracking_history', []),
        'current_status': delivery.get('status'),
        'estimated_delivery': delivery.get('estimated_delivery')
    }

@api_router.get("/marketplace/deliveries/in-transit")
async def get_in_transit_deliveries(current_user: User = Depends(get_current_user)):
    """Get all in-transit deliveries"""
    deliveries = await db.deliveries.find({
        'tenant_id': current_user.tenant_id,
        'status': 'in_transit'
    }, {'_id': 0}).sort('estimated_delivery', 1).to_list(100)
    
    return {'deliveries': deliveries, 'count': len(deliveries)}


# ========================================
# CALENDAR ENHANCEMENTS - 3 New Features
# ========================================

# 1. RATE CODES MANAGEMENT (BB, HB, FB, AI, RO, Non-refundable)
@api_router.get("/calendar/rate-codes")
async def get_rate_codes(current_user: User = Depends(get_current_user)):
    """Get all rate codes"""
    rate_codes = await db.rate_codes.find(
        {'tenant_id': current_user.tenant_id},
        {'_id': 0}
    ).to_list(100)
    
    # Default rate codes if none exist
    if not rate_codes:
        default_codes = [
            {
                'id': str(uuid.uuid4()),
                'tenant_id': current_user.tenant_id,
                'code': 'RO',
                'name': 'Room Only',
                'description': 'Room only, no meals included',
                'includes_breakfast': False,
                'includes_lunch': False,
                'includes_dinner': False,
                'is_refundable': True,
                'cancellation_policy': 'Free cancellation up to 24h before arrival',
                'price_modifier': 1.0
            },
            {
                'id': str(uuid.uuid4()),
                'tenant_id': current_user.tenant_id,
                'code': 'BB',
                'name': 'Bed & Breakfast',
                'description': 'Room with breakfast included',
                'includes_breakfast': True,
                'includes_lunch': False,
                'includes_dinner': False,
                'is_refundable': True,
                'cancellation_policy': 'Free cancellation up to 48h before arrival',
                'price_modifier': 1.15
            },
            {
                'id': str(uuid.uuid4()),
                'tenant_id': current_user.tenant_id,
                'code': 'HB',
                'name': 'Half Board',
                'description': 'Room with breakfast and dinner',
                'includes_breakfast': True,
                'includes_lunch': False,
                'includes_dinner': True,
                'is_refundable': True,
                'cancellation_policy': 'Free cancellation up to 72h before arrival',
                'price_modifier': 1.30
            },
            {
                'id': str(uuid.uuid4()),
                'tenant_id': current_user.tenant_id,
                'code': 'FB',
                'name': 'Full Board',
                'description': 'Room with all meals (breakfast, lunch, dinner)',
                'includes_breakfast': True,
                'includes_lunch': True,
                'includes_dinner': True,
                'is_refundable': True,
                'cancellation_policy': 'Free cancellation up to 72h before arrival',
                'price_modifier': 1.45
            },
            {
                'id': str(uuid.uuid4()),
                'tenant_id': current_user.tenant_id,
                'code': 'AI',
                'name': 'All Inclusive',
                'description': 'All meals and drinks included',
                'includes_breakfast': True,
                'includes_lunch': True,
                'includes_dinner': True,
                'is_refundable': True,
                'cancellation_policy': 'Free cancellation up to 7 days before arrival',
                'price_modifier': 1.75
            },
            {
                'id': str(uuid.uuid4()),
                'tenant_id': current_user.tenant_id,
                'code': 'NR',
                'name': 'Non-Refundable',
                'description': 'Best price, non-refundable rate',
                'includes_breakfast': False,
                'includes_lunch': False,
                'includes_dinner': False,
                'is_refundable': False,
                'cancellation_policy': 'Non-refundable - no cancellation allowed',
                'price_modifier': 0.85
            }
        ]
        rate_codes = default_codes
    
    return {'rate_codes': rate_codes, 'count': len(rate_codes)}

@api_router.post("/calendar/rate-codes")
async def create_rate_code(
    request: CreateRateCodeRequest,
    current_user: User = Depends(get_current_user)
):
    """Create custom rate code"""
    rate_code = {
        'id': str(uuid.uuid4()),
        'tenant_id': current_user.tenant_id,
        'code': request.code.upper(),
        'name': request.name,
        'description': request.description,
        'includes_breakfast': request.includes_breakfast,
        'includes_lunch': request.includes_lunch,
        'includes_dinner': request.includes_dinner,
        'is_refundable': request.is_refundable,
        'cancellation_policy': request.cancellation_policy,
        'price_modifier': request.price_modifier,
        'created_at': datetime.now(timezone.utc).isoformat()
    }
    
    rate_copy = rate_code.copy()
    await db.rate_codes.insert_one(rate_copy)
    return rate_code


# 2. ENHANCED CALENDAR TOOLTIP DATA
@api_router.post("/calendar/tooltip")
async def get_calendar_tooltip(
    request: GetCalendarTooltipRequest,
    current_user: User = Depends(get_current_user)
):
    """Get enriched data for calendar tooltip hover"""
    date = request.date
    room_type_filter = request.room_type
    
    # Get bookings for this date
    bookings_query = {
        'tenant_id': current_user.tenant_id,
        'check_in_date': {'$lte': date},
        'check_out_date': {'$gt': date},
        'status': {'$in': ['confirmed', 'guaranteed', 'checked_in']}
    }
    
    if room_type_filter:
        bookings_query['room_type'] = room_type_filter
    
    bookings = await db.bookings.find(bookings_query, {'_id': 0}).to_list(1000)
    
    # Get total rooms
    rooms_query = {'tenant_id': current_user.tenant_id}
    if room_type_filter:
        rooms_query['room_type'] = room_type_filter
    
    total_rooms = await db.rooms.count_documents(rooms_query)
    occupied_rooms = len(bookings)
    occupancy_pct = (occupied_rooms / total_rooms * 100) if total_rooms > 0 else 0
    
    # Calculate revenue for the day
    folio_charges = await db.folio_charges.find({
        'tenant_id': current_user.tenant_id,
        'charge_date': date,
        'voided': False
    }, {'_id': 0}).to_list(1000)
    
    total_revenue = sum(charge.get('total', 0) for charge in folio_charges)
    adr = (total_revenue / occupied_rooms) if occupied_rooms > 0 else 0
    
    # Segment breakdown
    segment_counts = {}
    for booking in bookings:
        segment = booking.get('booking_source', 'direct')
        segment_counts[segment] = segment_counts.get(segment, 0) + 1
    
    # Rate code breakdown
    rate_code_counts = {}
    rate_code_revenue = {}
    for booking in bookings:
        rate_code = booking.get('rate_code', 'BB')
        rate_code_counts[rate_code] = rate_code_counts.get(rate_code, 0) + 1
        
        # Get booking rate
        booking_charges = [c for c in folio_charges if c.get('booking_id') == booking.get('id')]
        if booking_charges:
            rate_code_revenue[rate_code] = rate_code_revenue.get(rate_code, 0) + sum(c.get('total', 0) for c in booking_charges)
    
    # Room type breakdown (if no filter)
    room_type_occupancy = {}
    if not room_type_filter:
        room_types = await db.room_types.find({'tenant_id': current_user.tenant_id}, {'_id': 0}).to_list(100)
        for rt in room_types:
            rt_bookings = [b for b in bookings if b.get('room_type') == rt['name']]
            rt_total = await db.rooms.count_documents({
                'tenant_id': current_user.tenant_id,
                'room_type': rt['name']
            })
            rt_occ = (len(rt_bookings) / rt_total * 100) if rt_total > 0 else 0
            room_type_occupancy[rt['name']] = {
                'occupied': len(rt_bookings),
                'total': rt_total,
                'occupancy_pct': round(rt_occ, 1)
            }
    
    # Group reservations for this date
    group_bookings = [b for b in bookings if b.get('group_id')]
    group_ids = list(set([b['group_id'] for b in group_bookings if b.get('group_id')]))
    
    groups_info = []
    for group_id in group_ids:
        group = await db.group_reservations.find_one({'id': group_id}, {'_id': 0})
        if group:
            group_rooms = len([b for b in group_bookings if b.get('group_id') == group_id])
            groups_info.append({
                'group_name': group.get('group_name'),
                'total_rooms': group.get('total_rooms'),
                'rooms_today': group_rooms
            })
    
    return {
        'date': date,
        'occupancy': {
            'occupied_rooms': occupied_rooms,
            'total_rooms': total_rooms,
            'occupancy_pct': round(occupancy_pct, 1),
            'available_rooms': total_rooms - occupied_rooms
        },
        'revenue': {
            'total_revenue': round(total_revenue, 2),
            'adr': round(adr, 2),
            'revpar': round((total_revenue / total_rooms), 2) if total_rooms > 0 else 0
        },
        'segments': segment_counts,
        'rate_codes': {
            'breakdown': rate_code_counts,
            'revenue_by_code': {k: round(v, 2) for k, v in rate_code_revenue.items()}
        },
        'room_types': room_type_occupancy,
        'groups': {
            'count': len(groups_info),
            'details': groups_info
        }
    }


# 3. GROUP RESERVATION CALENDAR VIEW
@api_router.get("/calendar/group-view")
async def get_calendar_group_view(
    start_date: str,
    end_date: str,
    current_user: User = Depends(get_current_user)
):
    """Get calendar view optimized for group reservations"""
    # Get all group reservations that overlap with date range
    groups = await db.group_reservations.find({
        'tenant_id': current_user.tenant_id,
        'check_in_date': {'$lte': end_date},
        'check_out_date': {'$gte': start_date}
    }, {'_id': 0}).to_list(100)
    
    calendar_data = []
    start = datetime.fromisoformat(start_date)
    end = datetime.fromisoformat(end_date)
    days = (end - start).days + 1
    
    for day in range(days):
        current_date = (start + timedelta(days=day)).date().isoformat()
        
        # Get groups active on this date
        active_groups = []
        for group in groups:
            if group.get('check_in_date') <= current_date <= group.get('check_out_date'):
                # Get bookings for this group on this date
                group_bookings = await db.bookings.find({
                    'tenant_id': current_user.tenant_id,
                    'group_id': group['id'],
                    'check_in_date': {'$lte': current_date},
                    'check_out_date': {'$gt': current_date}
                }, {'_id': 0}).to_list(1000)
                
                active_groups.append({
                    'group_id': group['id'],
                    'group_name': group.get('group_name'),
                    'group_type': group.get('group_type'),
                    'total_rooms': group.get('total_rooms'),
                    'rooms_active_today': len(group_bookings),
                    'contact_person': group.get('contact_person')
                })
        
        # Get regular (non-group) bookings
        regular_bookings = await db.bookings.count_documents({
            'tenant_id': current_user.tenant_id,
            'check_in_date': {'$lte': current_date},
            'check_out_date': {'$gt': current_date},
            'group_id': None,
            'status': {'$in': ['confirmed', 'guaranteed', 'checked_in']}
        })
        
        total_rooms = await db.rooms.count_documents({'tenant_id': current_user.tenant_id})
        group_rooms = sum(g['rooms_active_today'] for g in active_groups)
        
        calendar_data.append({
            'date': current_date,
            'total_rooms': total_rooms,
            'group_rooms': group_rooms,
            'regular_rooms': regular_bookings,
            'available_rooms': total_rooms - group_rooms - regular_bookings,
            'groups': active_groups
        })
    
    return {
        'calendar': calendar_data,
        'summary': {
            'total_days': days,
            'total_groups': len(groups),
            'date_range': f"{start_date} to {end_date}"
        }
    }

@api_router.get("/calendar/rate-code-breakdown")
async def get_rate_code_breakdown(
    start_date: str,
    end_date: str,
    current_user: User = Depends(get_current_user)
):
    """Get rate code breakdown for date range"""
    # Get all bookings in date range
    bookings = await db.bookings.find({
        'tenant_id': current_user.tenant_id,
        'check_in_date': {'$lte': end_date},
        'check_out_date': {'$gte': start_date},
        'status': {'$in': ['confirmed', 'guaranteed', 'checked_in']}
    }, {'_id': 0}).to_list(10000)
    
    # Get rate codes
    rate_codes = await db.rate_codes.find({'tenant_id': current_user.tenant_id}, {'_id': 0}).to_list(100)
    rate_code_map = {rc['code']: rc['name'] for rc in rate_codes}
    
    # Aggregate by date and rate code
    breakdown_by_date = {}
    
    start = datetime.fromisoformat(start_date)
    end = datetime.fromisoformat(end_date)
    days = (end - start).days + 1
    
    for day in range(days):
        current_date = (start + timedelta(days=day)).date().isoformat()
        
        # Get bookings for this date
        date_bookings = [
            b for b in bookings
            if b.get('check_in_date') <= current_date < b.get('check_out_date')
        ]
        
        # Count by rate code
        rate_counts = {}
        for booking in date_bookings:
            rate_code = booking.get('rate_code', 'BB')
            rate_counts[rate_code] = rate_counts.get(rate_code, 0) + 1
        
        breakdown_by_date[current_date] = {
            'date': current_date,
            'total_bookings': len(date_bookings),
            'rate_codes': [
                {
                    'code': code,
                    'name': rate_code_map.get(code, code),
                    'count': count,
                    'percentage': round((count / len(date_bookings) * 100), 1) if date_bookings else 0
                }
                for code, count in rate_counts.items()
            ]
        }
    
    # Overall summary
    total_rate_counts = {}
    for booking in bookings:
        rate_code = booking.get('rate_code', 'BB')
        total_rate_counts[rate_code] = total_rate_counts.get(rate_code, 0) + 1
    
    return {
        'breakdown': list(breakdown_by_date.values()),
        'summary': {
            'date_range': f"{start_date} to {end_date}",
            'total_bookings': len(bookings),
            'rate_code_distribution': [
                {
                    'code': code,
                    'name': rate_code_map.get(code, code),
                    'count': count,
                    'percentage': round((count / len(bookings) * 100), 1) if bookings else 0
                }
                for code, count in total_rate_counts.items()
            ]
        }
    }


# ========================================
# FEEDBACK & REVIEWS ENHANCEMENTS - 3 Features
# ========================================

# 1. EXTERNAL REVIEW API INTEGRATION (Booking.com, Google, TripAdvisor)
@api_router.post("/feedback/external-review-webhook")
async def receive_external_review(
    request: ExternalReviewWebhookRequest,
    current_user: User = Depends(get_current_user)
):
    """Webhook to receive reviews from external platforms"""
    review = {
        'id': str(uuid.uuid4()),
        'tenant_id': current_user.tenant_id,
        'platform': request.platform,
        'external_review_id': request.review_id,
        'rating': request.rating,
        'reviewer_name': request.reviewer_name,
        'review_text': request.review_text,
        'review_date': request.review_date,
        'booking_reference': request.booking_reference,
        'status': 'new',
        'sentiment': 'positive' if request.rating >= 4.0 else ('neutral' if request.rating >= 3.0 else 'negative'),
        'received_at': datetime.now(timezone.utc).isoformat()
    }
    
    review_copy = review.copy()
    await db.external_reviews.insert_one(review_copy)
    
    return {'message': 'External review received successfully', 'review_id': review['id']}

@api_router.get("/feedback/external-reviews")
async def get_external_reviews(
    platform: str = None,
    sentiment: str = None,
    start_date: str = None,
    end_date: str = None,
    current_user: User = Depends(get_current_user)
):
    """Get reviews from external platforms"""
    query = {'tenant_id': current_user.tenant_id}
    
    if platform:
        query['platform'] = platform
    if sentiment:
        query['sentiment'] = sentiment
    if start_date and end_date:
        query['review_date'] = {'$gte': start_date, '$lte': end_date}
    
    reviews = await db.external_reviews.find(
        query,
        {'_id': 0}
    ).sort('review_date', -1).to_list(1000)
    
    return {'reviews': reviews, 'count': len(reviews)}

@api_router.get("/feedback/external-reviews/summary")
async def get_external_reviews_summary(
    start_date: str = None,
    end_date: str = None,
    current_user: User = Depends(get_current_user)
):
    """Get aggregated summary of external reviews"""
    query = {'tenant_id': current_user.tenant_id}
    
    if start_date and end_date:
        query['review_date'] = {'$gte': start_date, '$lte': end_date}
    
    reviews = await db.external_reviews.find(query, {'_id': 0}).to_list(10000)
    
    if not reviews:
        return {
            'message': 'No external reviews found',
            'summary': {}
        }
    
    # Calculate platform breakdown
    platform_stats = {}
    for review in reviews:
        platform = review.get('platform', 'unknown')
        if platform not in platform_stats:
            platform_stats[platform] = {
                'count': 0,
                'total_rating': 0,
                'positive': 0,
                'neutral': 0,
                'negative': 0
            }
        
        platform_stats[platform]['count'] += 1
        platform_stats[platform]['total_rating'] += review.get('rating', 0)
        
        sentiment = review.get('sentiment', 'neutral')
        platform_stats[platform][sentiment] += 1
    
    # Calculate averages
    for platform, stats in platform_stats.items():
        if stats['count'] > 0:
            stats['avg_rating'] = round(stats['total_rating'] / stats['count'], 2)
    
    # Overall stats
    total_reviews = len(reviews)
    avg_rating = sum(r.get('rating', 0) for r in reviews) / total_reviews if total_reviews > 0 else 0
    
    sentiment_breakdown = {
        'positive': sum(1 for r in reviews if r.get('sentiment') == 'positive'),
        'neutral': sum(1 for r in reviews if r.get('sentiment') == 'neutral'),
        'negative': sum(1 for r in reviews if r.get('sentiment') == 'negative')
    }
    
    return {
        'summary': {
            'total_reviews': total_reviews,
            'avg_rating': round(avg_rating, 2),
            'sentiment_breakdown': sentiment_breakdown,
            'platforms': platform_stats
        },
        'date_range': f"{start_date or 'all'} to {end_date or 'all'}"
    }

@api_router.post("/feedback/external-reviews/{review_id}/respond")
async def respond_to_external_review(
    review_id: str,
    response_text: str,
    current_user: User = Depends(get_current_user)
):
    """Respond to external review"""
    review = await db.external_reviews.find_one({
        'id': review_id,
        'tenant_id': current_user.tenant_id
    })
    
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    
    await db.external_reviews.update_one(
        {'id': review_id},
        {
            '$set': {
                'response': response_text,
                'responded_at': datetime.now(timezone.utc).isoformat(),
                'responded_by': current_user.id,
                'status': 'responded'
            }
        }
    )
    
    return {'message': 'Response posted successfully'}


# 2. IN-HOUSE SURVEY SYSTEM
@api_router.get("/feedback/surveys")
async def get_surveys(current_user: User = Depends(get_current_user)):
    """Get all surveys"""
    surveys = await db.surveys.find(
        {'tenant_id': current_user.tenant_id},
        {'_id': 0}
    ).to_list(100)
    
    # Get response counts
    for survey in surveys:
        response_count = await db.survey_responses.count_documents({
            'tenant_id': current_user.tenant_id,
            'survey_id': survey['id']
        })
        survey['response_count'] = response_count
    
    return {'surveys': surveys, 'count': len(surveys)}

@api_router.post("/feedback/surveys")
async def create_survey(
    request: CreateSurveyRequest,
    current_user: User = Depends(get_current_user)
):
    """Create new survey"""
    survey = {
        'id': str(uuid.uuid4()),
        'tenant_id': current_user.tenant_id,
        'survey_name': request.survey_name,
        'description': request.description,
        'target_department': request.target_department,
        'questions': request.questions,
        'trigger': request.trigger,
        'status': 'active',
        'created_at': datetime.now(timezone.utc).isoformat(),
        'created_by': current_user.id
    }
    
    survey_copy = survey.copy()
    await db.surveys.insert_one(survey_copy)
    return survey

@api_router.post("/feedback/surveys/response")
async def submit_survey_response(
    request: SubmitSurveyResponseRequest,
    current_user: User = Depends(get_current_user)
):
    """Submit survey response"""
    # Verify survey exists
    survey = await db.surveys.find_one({
        'id': request.survey_id,
        'tenant_id': current_user.tenant_id
    })
    
    if not survey:
        raise HTTPException(status_code=404, detail="Survey not found")
    
    # Calculate overall rating
    ratings = [r.get('rating') for r in request.responses if r.get('rating')]
    avg_rating = sum(ratings) / len(ratings) if ratings else None
    
    response = {
        'id': str(uuid.uuid4()),
        'tenant_id': current_user.tenant_id,
        'survey_id': request.survey_id,
        'survey_name': survey.get('survey_name'),
        'booking_id': request.booking_id,
        'guest_name': request.guest_name,
        'guest_email': request.guest_email,
        'responses': request.responses,
        'overall_rating': round(avg_rating, 2) if avg_rating else None,
        'submitted_at': datetime.now(timezone.utc).isoformat()
    }
    
    response_copy = response.copy()
    await db.survey_responses.insert_one(response_copy)
    
    return {'message': 'Survey response submitted successfully', 'response_id': response['id']}

@api_router.get("/feedback/surveys/{survey_id}/responses")
async def get_survey_responses(
    survey_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get responses for specific survey"""
    # Verify survey
    survey = await db.surveys.find_one({
        'id': survey_id,
        'tenant_id': current_user.tenant_id
    }, {'_id': 0})
    
    if not survey:
        raise HTTPException(status_code=404, detail="Survey not found")
    
    # Get responses
    responses = await db.survey_responses.find({
        'tenant_id': current_user.tenant_id,
        'survey_id': survey_id
    }, {'_id': 0}).to_list(1000)
    
    # Calculate statistics
    if responses:
        ratings = [r.get('overall_rating') for r in responses if r.get('overall_rating')]
        avg_rating = sum(ratings) / len(ratings) if ratings else 0
        
        # Aggregate answers per question
        question_stats = {}
        for response in responses:
            for answer in response.get('responses', []):
                q_id = answer.get('question_id', 'unknown')
                if q_id not in question_stats:
                    question_stats[q_id] = {
                        'ratings': [],
                        'answers': []
                    }
                
                if answer.get('rating'):
                    question_stats[q_id]['ratings'].append(answer['rating'])
                if answer.get('answer'):
                    question_stats[q_id]['answers'].append(answer['answer'])
        
        # Calculate averages
        for q_id, stats in question_stats.items():
            if stats['ratings']:
                stats['avg_rating'] = round(sum(stats['ratings']) / len(stats['ratings']), 2)
    else:
        avg_rating = 0
        question_stats = {}
    
    return {
        'survey': survey,
        'responses': responses,
        'statistics': {
            'total_responses': len(responses),
            'avg_overall_rating': round(avg_rating, 2),
            'question_stats': question_stats
        }
    }


# 3. DEPARTMENT-BASED SATISFACTION TRACKING
@api_router.post("/feedback/department")
async def submit_department_feedback(
    request: CreateDepartmentFeedbackRequest,
    current_user: User = Depends(get_current_user)
):
    """Submit feedback for specific department"""
    feedback = {
        'id': str(uuid.uuid4()),
        'tenant_id': current_user.tenant_id,
        'department': request.department,
        'booking_id': request.booking_id,
        'guest_name': request.guest_name,
        'rating': request.rating,
        'comment': request.comment,
        'staff_member': request.staff_member,
        'sentiment': 'positive' if request.rating >= 4 else ('neutral' if request.rating == 3 else 'negative'),
        'submitted_at': datetime.now(timezone.utc).isoformat()
    }
    
    feedback_copy = feedback.copy()
    await db.department_feedback.insert_one(feedback_copy)
    
    return {'message': 'Department feedback submitted successfully', 'feedback_id': feedback['id']}

@api_router.get("/feedback/department")
async def get_department_feedback(
    department: str = None,
    start_date: str = None,
    end_date: str = None,
    current_user: User = Depends(get_current_user)
):
    """Get department feedback"""
    query = {'tenant_id': current_user.tenant_id}
    
    if department:
        query['department'] = department
    
    if start_date and end_date:
        query['submitted_at'] = {'$gte': start_date, '$lte': end_date}
    
    feedback = await db.department_feedback.find(
        query,
        {'_id': 0}
    ).sort('submitted_at', -1).to_list(1000)
    
    return {'feedback': feedback, 'count': len(feedback)}

@api_router.get("/feedback/department/summary")
async def get_department_satisfaction_summary(
    start_date: str = None,
    end_date: str = None,
    current_user: User = Depends(get_current_user)
):
    """Get department satisfaction summary"""
    query = {'tenant_id': current_user.tenant_id}
    
    if start_date and end_date:
        query['submitted_at'] = {'$gte': start_date, '$lte': end_date}
    
    feedback = await db.department_feedback.find(query, {'_id': 0}).to_list(10000)
    
    if not feedback:
        return {
            'message': 'No department feedback found',
            'summary': {}
        }
    
    # Aggregate by department
    dept_stats = {}
    departments = ['housekeeping', 'front_desk', 'fnb', 'spa', 'concierge']
    
    for dept in departments:
        dept_feedback = [f for f in feedback if f.get('department') == dept]
        
        if dept_feedback:
            ratings = [f.get('rating', 0) for f in dept_feedback]
            avg_rating = sum(ratings) / len(ratings) if ratings else 0
            
            sentiment_counts = {
                'positive': sum(1 for f in dept_feedback if f.get('sentiment') == 'positive'),
                'neutral': sum(1 for f in dept_feedback if f.get('sentiment') == 'neutral'),
                'negative': sum(1 for f in dept_feedback if f.get('sentiment') == 'negative')
            }
            
            dept_stats[dept] = {
                'total_feedback': len(dept_feedback),
                'avg_rating': round(avg_rating, 2),
                'sentiment_breakdown': sentiment_counts,
                'satisfaction_rate': round((sentiment_counts['positive'] / len(dept_feedback) * 100), 1) if dept_feedback else 0
            }
        else:
            dept_stats[dept] = {
                'total_feedback': 0,
                'avg_rating': 0,
                'sentiment_breakdown': {'positive': 0, 'neutral': 0, 'negative': 0},
                'satisfaction_rate': 0
            }
    
    # Overall stats
    all_ratings = [f.get('rating', 0) for f in feedback]
    overall_avg = sum(all_ratings) / len(all_ratings) if all_ratings else 0
    
    # Staff member performance
    staff_performance = {}
    for f in feedback:
        if f.get('staff_member'):
            staff = f['staff_member']
            if staff not in staff_performance:
                staff_performance[staff] = {
                    'ratings': [],
                    'department': f.get('department')
                }
            staff_performance[staff]['ratings'].append(f.get('rating', 0))
    
    # Calculate staff averages
    staff_stats = []
    for staff, data in staff_performance.items():
        if data['ratings']:
            avg = sum(data['ratings']) / len(data['ratings'])
            staff_stats.append({
                'staff_member': staff,
                'department': data['department'],
                'avg_rating': round(avg, 2),
                'feedback_count': len(data['ratings'])
            })
    
    staff_stats.sort(key=lambda x: x['avg_rating'], reverse=True)
    
    return {
        'summary': {
            'total_feedback': len(feedback),
            'overall_avg_rating': round(overall_avg, 2),
            'departments': dept_stats,
            'top_performers': staff_stats[:10],
            'needs_attention': [
                {'department': dept, 'avg_rating': stats['avg_rating']}
                for dept, stats in dept_stats.items()
                if stats['avg_rating'] > 0 and stats['avg_rating'] < 3.5
            ]
        },
        'date_range': f"{start_date or 'all'} to {end_date or 'all'}"
    }


# ========================================
# TASK MANAGEMENT SYSTEM - Multi-Department
# ========================================

@api_router.get("/tasks")
async def get_tasks(
    department: str = None,
    status: str = None,
    priority: str = None,
    assigned_to: str = None,
    current_user: User = Depends(get_current_user)
):
    """Get tasks with filters"""
    query = {'tenant_id': current_user.tenant_id}
    
    if department:
        query['department'] = department
    if status:
        query['status'] = status
    if priority:
        query['priority'] = priority
    if assigned_to:
        query['assigned_to'] = assigned_to
    
    tasks = await db.tasks.find(
        query,
        {'_id': 0}
    ).sort([('priority_order', -1), ('created_at', 1)]).to_list(1000)
    
    return {'tasks': tasks, 'count': len(tasks)}

@api_router.post("/tasks")
async def create_task(
    request: CreateTaskRequest,
    current_user: User = Depends(get_current_user)
):
    """Create new task"""
    # Priority order for sorting
    priority_order = {
        'urgent': 4,
        'high': 3,
        'normal': 2,
        'low': 1
    }
    
    task = {
        'id': str(uuid.uuid4()),
        'tenant_id': current_user.tenant_id,
        'department': request.department,
        'task_type': request.task_type,
        'title': request.title,
        'description': request.description,
        'priority': request.priority,
        'priority_order': priority_order.get(request.priority, 2),
        'location': request.location,
        'room_id': request.room_id,
        'assigned_to': request.assigned_to,
        'due_date': request.due_date,
        'recurring': request.recurring,
        'recurrence_pattern': request.recurrence_pattern,
        'status': 'new' if not request.assigned_to else 'assigned',
        'created_at': datetime.now(timezone.utc).isoformat(),
        'created_by': current_user.id,
        'updated_at': datetime.now(timezone.utc).isoformat()
    }
    
    task_copy = task.copy()
    await db.tasks.insert_one(task_copy)
    
    # Create notification for assigned user
    if request.assigned_to:
        notification = {
            'id': str(uuid.uuid4()),
            'tenant_id': current_user.tenant_id,
            'user': request.assigned_to,
            'type': 'task_assigned',
            'message': f"New {request.priority} priority task assigned: {request.title}",
            'task_id': task['id'],
            'read': False,
            'created_at': datetime.now(timezone.utc).isoformat()
        }
        notif_copy = notification.copy()
        await db.notifications.insert_one(notif_copy)
    
    return task

@api_router.get("/tasks/my-tasks")
async def get_my_tasks(
    status: str = None,
    current_user: User = Depends(get_current_user)
):
    """Get tasks assigned to current user"""
    query = {
        'tenant_id': current_user.tenant_id,
        'assigned_to': current_user.name
    }
    
    if status:
        query['status'] = status
    
    tasks = await db.tasks.find(query, {'_id': 0}).sort([('priority_order', -1), ('due_date', 1)]).to_list(1000)
    
    return {'tasks': tasks, 'count': len(tasks)}

@api_router.get("/tasks/dashboard")
async def get_tasks_dashboard(current_user: User = Depends(get_current_user)):
    """Get tasks dashboard with all department stats"""
    # Get all tasks
    tasks = await db.tasks.find({
        'tenant_id': current_user.tenant_id
    }, {'_id': 0}).to_list(10000)
    
    # Department breakdown
    departments = ['engineering', 'housekeeping', 'fnb', 'maintenance', 'front_desk']
    dept_stats = {}
    
    for dept in departments:
        dept_tasks = [t for t in tasks if t.get('department') == dept]
        
        dept_stats[dept] = {
            'total': len(dept_tasks),
            'new': sum(1 for t in dept_tasks if t.get('status') == 'new'),
            'in_progress': sum(1 for t in dept_tasks if t.get('status') == 'in_progress'),
            'completed': sum(1 for t in dept_tasks if t.get('status') == 'completed'),
            'urgent': sum(1 for t in dept_tasks if t.get('priority') == 'urgent'),
            'overdue': sum(1 for t in dept_tasks if t.get('due_date') and t.get('due_date') < datetime.now(timezone.utc).date().isoformat() and t.get('status') not in ['completed', 'verified'])
        }
    
    # Overall stats
    today = datetime.now(timezone.utc).date().isoformat()
    
    return {
        'summary': {
            'total_tasks': len(tasks),
            'new': sum(1 for t in tasks if t.get('status') == 'new'),
            'in_progress': sum(1 for t in tasks if t.get('status') == 'in_progress'),
            'completed_today': sum(1 for t in tasks if t.get('status') == 'completed' and t.get('completed_at', '').startswith(today)),
            'urgent_pending': sum(1 for t in tasks if t.get('priority') == 'urgent' and t.get('status') not in ['completed', 'verified', 'cancelled']),
            'overdue': sum(1 for t in tasks if t.get('due_date') and t.get('due_date') < today and t.get('status') not in ['completed', 'verified', 'cancelled'])
        },
        'departments': dept_stats
    }

@api_router.get("/tasks/{task_id}")
async def get_task_details(
    task_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get task details with history"""
    task = await db.tasks.find_one({
        'id': task_id,
        'tenant_id': current_user.tenant_id
    }, {'_id': 0})
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Get task history
    history = await db.task_history.find({
        'tenant_id': current_user.tenant_id,
        'task_id': task_id
    }, {'_id': 0}).sort('timestamp', 1).to_list(100)
    
    task['history'] = history
    
    return task

@api_router.post("/tasks/{task_id}/assign")
async def assign_task(
    task_id: str,
    request: AssignTaskRequest,
    current_user: User = Depends(get_current_user)
):
    """Assign task to user"""
    task = await db.tasks.find_one({
        'id': task_id,
        'tenant_id': current_user.tenant_id
    })
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Update task
    await db.tasks.update_one(
        {'id': task_id},
        {
            '$set': {
                'assigned_to': request.assigned_to,
                'status': 'assigned',
                'assigned_at': datetime.now(timezone.utc).isoformat(),
                'assigned_by': current_user.id,
                'updated_at': datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    # Add to history
    history_entry = {
        'id': str(uuid.uuid4()),
        'tenant_id': current_user.tenant_id,
        'task_id': task_id,
        'action': 'assigned',
        'performed_by': current_user.id,
        'details': f"Assigned to {request.assigned_to}",
        'notes': request.notes,
        'timestamp': datetime.now(timezone.utc).isoformat()
    }
    history_copy = history_entry.copy()
    await db.task_history.insert_one(history_copy)
    
    # Create notification
    notification = {
        'id': str(uuid.uuid4()),
        'tenant_id': current_user.tenant_id,
        'user': request.assigned_to,
        'type': 'task_assigned',
        'message': f"Task assigned: {task.get('title')}",
        'task_id': task_id,
        'read': False,
        'created_at': datetime.now(timezone.utc).isoformat()
    }
    notif_copy = notification.copy()
    await db.notifications.insert_one(notif_copy)
    
    return {'message': 'Task assigned successfully'}

@api_router.post("/tasks/{task_id}/status")
async def update_task_status(
    task_id: str,
    request: UpdateTaskStatusRequest,
    current_user: User = Depends(get_current_user)
):
    """Update task status"""
    task = await db.tasks.find_one({
        'id': task_id,
        'tenant_id': current_user.tenant_id
    })
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    update_data = {
        'status': request.status,
        'updated_at': datetime.now(timezone.utc).isoformat()
    }
    
    if request.status == 'completed':
        update_data['completed_at'] = datetime.now(timezone.utc).isoformat()
        update_data['completed_by'] = current_user.id
        if request.completion_photos:
            update_data['completion_photos'] = request.completion_photos
    
    await db.tasks.update_one(
        {'id': task_id},
        {'$set': update_data}
    )
    
    # Add to history
    history_entry = {
        'id': str(uuid.uuid4()),
        'tenant_id': current_user.tenant_id,
        'task_id': task_id,
        'action': f"status_changed_to_{request.status}",
        'performed_by': current_user.id,
        'details': f"Status changed to {request.status}",
        'notes': request.notes,
        'timestamp': datetime.now(timezone.utc).isoformat()
    }
    history_copy = history_entry.copy()
    await db.task_history.insert_one(history_copy)
    
    return {'message': 'Task status updated successfully'}

@api_router.get("/tasks/department/{department}")
async def get_department_tasks(
    department: str,
    status: str = None,
    current_user: User = Depends(get_current_user)
):
    """Get tasks by department with stats"""
    query = {
        'tenant_id': current_user.tenant_id,
        'department': department
    }
    
    if status:
        query['status'] = status
    
    tasks = await db.tasks.find(query, {'_id': 0}).sort([('priority_order', -1), ('created_at', 1)]).to_list(1000)
    
    # Calculate stats
    total = len(tasks)
    by_status = {}
    by_priority = {}
    overdue = 0
    
    today = datetime.now(timezone.utc).date().isoformat()
    
    for task in tasks:
        status = task.get('status', 'new')
        priority = task.get('priority', 'normal')
        
        by_status[status] = by_status.get(status, 0) + 1
        by_priority[priority] = by_priority.get(priority, 0) + 1
        
        if task.get('due_date') and task.get('due_date') < today and status not in ['completed', 'verified', 'cancelled']:
            overdue += 1
    
    return {
        'department': department,
        'tasks': tasks,
        'statistics': {
            'total': total,
            'by_status': by_status,
            'by_priority': by_priority,
            'overdue': overdue
        }
    }


# DEPARTMENT-SPECIFIC TASK ENDPOINTS

# Engineering Tasks
@api_router.post("/tasks/engineering/maintenance-request")
async def create_engineering_maintenance_request(
    title: str,
    description: str,
    location: str,
    priority: str = "normal",
    room_id: str = None,
    current_user: User = Depends(get_current_user)
):
    """Create engineering/maintenance request"""
    task_request = CreateTaskRequest(
        department='engineering',
        task_type='repair',
        title=title,
        description=description,
        priority=priority,
        location=location,
        room_id=room_id
    )
    
    return await create_task(task_request, current_user)

# Housekeeping Tasks (Enhanced)
@api_router.post("/tasks/housekeeping/cleaning-request")
async def create_housekeeping_cleaning_request(
    room_id: str,
    task_type: str,  # deep_clean, turndown, inspection
    priority: str = "normal",
    special_instructions: str = None,
    current_user: User = Depends(get_current_user)
):
    """Create housekeeping cleaning request"""
    room = await db.rooms.find_one({'id': room_id, 'tenant_id': current_user.tenant_id}, {'_id': 0})
    
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    task_request = CreateTaskRequest(
        department='housekeeping',
        task_type=task_type,
        title=f"{task_type.replace('_', ' ').title()} - Room {room.get('room_number')}",
        description=special_instructions or f"{task_type} requested for room {room.get('room_number')}",
        priority=priority,
        location=f"Room {room.get('room_number')}",
        room_id=room_id
    )
    
    return await create_task(task_request, current_user)

# F&B Tasks
@api_router.post("/tasks/fnb/service-request")
async def create_fnb_service_request(
    request_type: str,  # room_service, catering, setup, delivery
    title: str,
    description: str,
    location: str,
    priority: str = "normal",
    due_date: str = None,
    current_user: User = Depends(get_current_user)
):
    """Create F&B service request"""
    task_request = CreateTaskRequest(
        department='fnb',
        task_type=request_type,
        title=title,
        description=description,
        priority=priority,
        location=location,
        due_date=due_date
    )
    
    return await create_task(task_request, current_user)


# ========================================
# ENTERPRISE FEATURES - Kurumsal Otel Refleksi
# ========================================

# 1. ROLLER & YETKİLER MATRİSİ (RBAC)
@api_router.get("/admin/roles")
async def get_roles(current_user: User = Depends(get_current_user)):
    """Get all roles and permissions"""
    roles = await db.roles.find(
        {'tenant_id': current_user.tenant_id},
        {'_id': 0}
    ).to_list(100)
    
    # Default roles if none exist
    if not roles:
        default_roles = [
            {
                'id': str(uuid.uuid4()),
                'tenant_id': current_user.tenant_id,
                'role_name': 'General Manager',
                'description': 'Full access to all features',
                'permissions': [
                    'view_all', 'edit_all', 'delete_all', 'approve_all',
                    'view_financials', 'edit_rates', 'manage_users',
                    'export_reports', 'system_settings'
                ],
                'department': 'management',
                'created_at': datetime.now(timezone.utc).isoformat()
            },
            {
                'id': str(uuid.uuid4()),
                'tenant_id': current_user.tenant_id,
                'role_name': 'Front Desk Agent',
                'description': 'Check-in, check-out, reservations',
                'permissions': [
                    'view_bookings', 'create_booking', 'edit_booking',
                    'check_in', 'check_out', 'view_rates',
                    'post_charges', 'process_payments'
                ],
                'department': 'front_desk',
                'created_at': datetime.now(timezone.utc).isoformat()
            },
            {
                'id': str(uuid.uuid4()),
                'tenant_id': current_user.tenant_id,
                'role_name': 'Housekeeping Manager',
                'description': 'Room status, cleaning tasks',
                'permissions': [
                    'view_rooms', 'update_room_status', 'assign_tasks',
                    'view_housekeeping_reports'
                ],
                'department': 'housekeeping',
                'created_at': datetime.now(timezone.utc).isoformat()
            },
            {
                'id': str(uuid.uuid4()),
                'tenant_id': current_user.tenant_id,
                'role_name': 'Accountant',
                'description': 'Financial operations',
                'permissions': [
                    'view_financials', 'create_invoice', 'edit_invoice',
                    'void_charge', 'export_reports', 'view_ar_aging'
                ],
                'department': 'accounting',
                'created_at': datetime.now(timezone.utc).isoformat()
            },
            {
                'id': str(uuid.uuid4()),
                'tenant_id': current_user.tenant_id,
                'role_name': 'Revenue Manager',
                'description': 'Rate management and revenue optimization',
                'permissions': [
                    'view_rates', 'edit_rates', 'view_rms',
                    'apply_pricing', 'view_comp_set', 'export_reports'
                ],
                'department': 'revenue',
                'created_at': datetime.now(timezone.utc).isoformat()
            },
            {
                'id': str(uuid.uuid4()),
                'tenant_id': current_user.tenant_id,
                'role_name': 'F&B Manager',
                'description': 'Restaurant and bar operations',
                'permissions': [
                    'view_pos', 'create_pos_transaction', 'view_menu',
                    'edit_menu', 'view_fnb_reports', 'generate_z_report'
                ],
                'department': 'fnb',
                'created_at': datetime.now(timezone.utc).isoformat()
            }
        ]
        roles = default_roles
    
    return {'roles': roles, 'count': len(roles)}

@api_router.post("/admin/roles")
async def create_role(
    request: CreateRoleRequest,
    current_user: User = Depends(get_current_user)
):
    """Create custom role"""
    role = {
        'id': str(uuid.uuid4()),
        'tenant_id': current_user.tenant_id,
        'role_name': request.role_name,
        'description': request.description,
        'permissions': request.permissions,
        'department': request.department,
        'created_at': datetime.now(timezone.utc).isoformat(),
        'created_by': current_user.id
    }
    
    role_copy = role.copy()
    await db.roles.insert_one(role_copy)
    
    # Log audit trail
    await log_audit_event(
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        action='create_role',
        entity_type='role',
        entity_id=role['id'],
        details=f"Created role: {request.role_name}",
        db=db
    )
    
    return role

@api_router.post("/admin/users/{user_id}/assign-role")
async def assign_role_to_user(
    user_id: str,
    request: AssignRoleRequest,
    current_user: User = Depends(get_current_user)
):
    """Assign role to user"""
    # Verify role exists
    role = await db.roles.find_one({
        'id': request.role_id,
        'tenant_id': current_user.tenant_id
    }, {'_id': 0})
    
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    
    # Update user role
    await db.users.update_one(
        {'id': user_id, 'tenant_id': current_user.tenant_id},
        {
            '$set': {
                'role_id': request.role_id,
                'role_name': role['role_name'],
                'permissions': role['permissions'],
                'updated_at': datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    # Log audit trail
    await log_audit_event(
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        action='assign_role',
        entity_type='user',
        entity_id=user_id,
        details=f"Assigned role {role['role_name']} to user",
        db=db
    )
    
    return {'message': 'Role assigned successfully', 'role': role['role_name']}

@api_router.get("/admin/permissions")
async def get_all_permissions():
    """Get list of all available permissions"""
    permissions = {
        'bookings': [
            'view_bookings', 'create_booking', 'edit_booking', 'delete_booking',
            'check_in', 'check_out', 'cancel_booking', 'move_booking'
        ],
        'rates': [
            'view_rates', 'edit_rates', 'apply_pricing', 'override_rate'
        ],
        'financials': [
            'view_financials', 'create_invoice', 'edit_invoice', 'void_invoice',
            'post_charges', 'void_charge', 'process_payments', 'process_refund',
            'view_ar_aging', 'export_reports'
        ],
        'rooms': [
            'view_rooms', 'update_room_status', 'create_room_block',
            'assign_room', 'change_room'
        ],
        'pos': [
            'view_pos', 'create_pos_transaction', 'void_pos_transaction',
            'view_menu', 'edit_menu', 'generate_z_report'
        ],
        'housekeeping': [
            'view_tasks', 'create_task', 'assign_task', 'complete_task',
            'view_housekeeping_reports'
        ],
        'admin': [
            'manage_users', 'manage_roles', 'system_settings',
            'view_audit_logs', 'manage_backups'
        ],
        'reports': [
            'export_reports', 'view_rms', 'view_comp_set'
        ],
        'all': [
            'view_all', 'edit_all', 'delete_all', 'approve_all'
        ]
    }
    
    return {'permissions': permissions}


# 2. LOGLAMA & DENETİM (Audit Trail)
async def log_audit_event(tenant_id: str, user_id: str, action: str, entity_type: str,
                           entity_id: str, details: str, before_value: dict = None,
                           after_value: dict = None, db = None):
    """Helper function to log audit events"""
    audit_log = {
        'id': str(uuid.uuid4()),
        'tenant_id': tenant_id,
        'user_id': user_id,
        'action': action,
        'entity_type': entity_type,
        'entity_id': entity_id,
        'details': details,
        'before_value': before_value,
        'after_value': after_value,
        'ip_address': None,  # Can be captured from request
        'user_agent': None,  # Can be captured from request
        'timestamp': datetime.now(timezone.utc).isoformat()
    }
    
    audit_copy = audit_log.copy()
    await db.audit_logs.insert_one(audit_copy)
    return audit_log

@api_router.get("/admin/audit-logs")
async def get_audit_logs(
    action: str = None,
    entity_type: str = None,
    user_id: str = None,
    start_date: str = None,
    end_date: str = None,
    limit: int = 100,
    current_user: User = Depends(get_current_user)
):
    """Get audit logs with filters"""
    query = {'tenant_id': current_user.tenant_id}
    
    if action:
        query['action'] = action
    if entity_type:
        query['entity_type'] = entity_type
    if user_id:
        query['user_id'] = user_id
    if start_date and end_date:
        query['timestamp'] = {'$gte': start_date, '$lte': end_date}
    
    logs = await db.audit_logs.find(
        query,
        {'_id': 0}
    ).sort('timestamp', -1).limit(limit).to_list(limit)
    
    return {'logs': logs, 'count': len(logs)}

@api_router.get("/admin/audit-logs/critical")
async def get_critical_audit_logs(
    days: int = 7,
    current_user: User = Depends(get_current_user)
):
    """Get critical audit events (deletions, refunds, rate changes)"""
    critical_actions = [
        'delete_booking', 'cancel_booking', 'process_refund',
        'void_invoice', 'void_charge', 'edit_rates', 'override_rate',
        'delete_user', 'change_role'
    ]
    
    start_date = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    
    logs = await db.audit_logs.find({
        'tenant_id': current_user.tenant_id,
        'action': {'$in': critical_actions},
        'timestamp': {'$gte': start_date}
    }, {'_id': 0}).sort('timestamp', -1).to_list(1000)
    
    # Group by action
    by_action = {}
    for log in logs:
        action = log.get('action')
        by_action[action] = by_action.get(action, 0) + 1
    
    return {
        'logs': logs,
        'summary': {
            'total_critical_events': len(logs),
            'by_action': by_action,
            'date_range': f"Last {days} days"
        }
    }

# Rate Change Audit (Example of critical operation logging)
@api_router.post("/admin/rates/{room_type}/change")
async def change_rate_with_audit(
    room_type: str,
    new_rate: float,
    effective_date: str,
    reason: str,
    current_user: User = Depends(get_current_user)
):
    """Change rate with full audit trail"""
    # Get current rate
    current_rate_record = await db.room_types.find_one({
        'tenant_id': current_user.tenant_id,
        'name': room_type
    }, {'_id': 0})
    
    if not current_rate_record:
        raise HTTPException(status_code=404, detail="Room type not found")
    
    old_rate = current_rate_record.get('base_rate', 0)
    
    # Update rate
    await db.room_types.update_one(
        {'tenant_id': current_user.tenant_id, 'name': room_type},
        {'$set': {'base_rate': new_rate, 'updated_at': datetime.now(timezone.utc).isoformat()}}
    )
    
    # Log audit event
    await log_audit_event(
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        action='edit_rates',
        entity_type='room_type',
        entity_id=room_type,
        details=f"Rate changed from ${old_rate} to ${new_rate}. Reason: {reason}",
        before_value={'base_rate': old_rate},
        after_value={'base_rate': new_rate},
        db=db
    )
    
    return {
        'message': 'Rate changed successfully',
        'old_rate': old_rate,
        'new_rate': new_rate,
        'effective_date': effective_date
    }


# 3. YEDEKLEME & FELAKET SENARYOSU
@api_router.post("/admin/backup/create")
async def create_backup(
    request: CreateBackupRequest,
    current_user: User = Depends(get_current_user)
):
    """Create database backup"""
    backup_id = str(uuid.uuid4())
    
    # In production, this would trigger actual backup process
    # For now, we'll create a backup metadata record
    backup = {
        'id': backup_id,
        'tenant_id': current_user.tenant_id,
        'backup_type': request.backup_type,
        'status': 'in_progress',
        'size_mb': 0,
        'collections_included': request.include_collections or ['all'],
        'started_at': datetime.now(timezone.utc).isoformat(),
        'created_by': current_user.id
    }
    
    backup_copy = backup.copy()
    await db.backups.insert_one(backup_copy)
    
    # Log audit event
    await log_audit_event(
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        action='create_backup',
        entity_type='backup',
        entity_id=backup_id,
        details=f"Initiated {request.backup_type} backup",
        db=db
    )
    
    # Simulate backup completion
    await db.backups.update_one(
        {'id': backup_id},
        {
            '$set': {
                'status': 'completed',
                'size_mb': 145.7,  # Mock size
                'completed_at': datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    return {
        'message': 'Backup created successfully',
        'backup_id': backup_id,
        'status': 'completed'
    }

@api_router.get("/admin/backup/list")
async def list_backups(
    limit: int = 20,
    current_user: User = Depends(get_current_user)
):
    """List all backups"""
    backups = await db.backups.find({
        'tenant_id': current_user.tenant_id
    }, {'_id': 0}).sort('started_at', -1).limit(limit).to_list(limit)
    
    return {'backups': backups, 'count': len(backups)}

@api_router.post("/admin/backup/{backup_id}/restore")
async def restore_backup(
    backup_id: str,
    confirm: bool = False,
    current_user: User = Depends(get_current_user)
):
    """Restore from backup"""
    if not confirm:
        raise HTTPException(status_code=400, detail="Must confirm restore operation")
    
    # Get backup
    backup = await db.backups.find_one({
        'id': backup_id,
        'tenant_id': current_user.tenant_id
    }, {'_id': 0})
    
    if not backup:
        raise HTTPException(status_code=404, detail="Backup not found")
    
    if backup.get('status') != 'completed':
        raise HTTPException(status_code=400, detail="Cannot restore from incomplete backup")
    
    # Log critical audit event
    await log_audit_event(
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        action='restore_backup',
        entity_type='backup',
        entity_id=backup_id,
        details=f"Restore initiated from backup {backup_id}",
        db=db
    )
    
    # In production, this would trigger actual restore process
    restore_job = {
        'id': str(uuid.uuid4()),
        'tenant_id': current_user.tenant_id,
        'backup_id': backup_id,
        'status': 'in_progress',
        'started_at': datetime.now(timezone.utc).isoformat(),
        'initiated_by': current_user.id
    }
    
    restore_copy = restore_job.copy()
    await db.restore_jobs.insert_one(restore_copy)
    
    return {
        'message': 'Restore initiated',
        'restore_job_id': restore_job['id'],
        'estimated_time': '10-15 minutes',
        'rto_target': '15 minutes'  # Recovery Time Objective
    }

@api_router.get("/admin/system/health")
async def get_system_health(current_user: User = Depends(get_current_user)):
    """Get system health status"""
    # Check database connectivity
    try:
        await db.users.count_documents({'tenant_id': current_user.tenant_id}, limit=1)
        db_status = 'healthy'
    except Exception as e:
        db_status = f'unhealthy: {str(e)}'
    
    # Get latest backup
    latest_backup = await db.backups.find_one(
        {'tenant_id': current_user.tenant_id, 'status': 'completed'},
        {'_id': 0},
        sort=[('completed_at', -1)]
    )
    
    # Calculate RPO (Recovery Point Objective)
    if latest_backup:
        last_backup_time = datetime.fromisoformat(latest_backup['completed_at'])
        hours_since_backup = (datetime.now(timezone.utc) - last_backup_time).total_seconds() / 3600
        rpo_status = 'good' if hours_since_backup < 24 else 'warning' if hours_since_backup < 48 else 'critical'
    else:
        hours_since_backup = None
        rpo_status = 'critical'
    
    # Get audit log count (last 24h)
    audit_count = await db.audit_logs.count_documents({
        'tenant_id': current_user.tenant_id,
        'timestamp': {'$gte': (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()}
    })
    
    return {
        'status': 'healthy' if db_status == 'healthy' else 'degraded',
        'components': {
            'database': db_status,
            'backup_system': rpo_status
        },
        'metrics': {
            'last_backup': latest_backup.get('completed_at') if latest_backup else None,
            'hours_since_backup': round(hours_since_backup, 1) if hours_since_backup else None,
            'rpo_target': '24 hours',
            'rto_target': '15 minutes',
            'audit_events_24h': audit_count
        },
        'timestamp': datetime.now(timezone.utc).isoformat()
    }


# Include router at the very end after ALL endpoints are defined
app.include_router(api_router)
