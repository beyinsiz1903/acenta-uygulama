from __future__ import annotations

from datetime import datetime, date
from typing import Optional, List, Dict, Any, Literal

from pydantic import BaseModel, Field


ProductType = Literal["hotel", "tour", "transfer", "activity"]
ProductStatus = Literal["active", "inactive", "archived"]

VersionStatus = Literal["draft", "published", "archived"]


class LocalizedText(BaseModel):
    tr: Optional[str] = None
    en: Optional[str] = None


class ProductLocation(BaseModel):
    city: str
    country: str


class ProductCreateRequest(BaseModel):
    type: ProductType
    code: str = Field(min_length=2, max_length=64)
    name: LocalizedText
    default_currency: str = Field(min_length=3, max_length=3)
    status: ProductStatus = "inactive"
    location: Optional[ProductLocation] = None


class ProductUpdateRequest(BaseModel):
    type: Optional[ProductType] = None
    code: Optional[str] = Field(default=None, min_length=2, max_length=64)
    name: Optional[LocalizedText] = None
    default_currency: Optional[str] = Field(default=None, min_length=3, max_length=3)
    status: Optional[ProductStatus] = None
    location: Optional[ProductLocation] = None


class ProductResponse(BaseModel):
    product_id: str
    organization_id: str
    type: ProductType
    code: str
    name: LocalizedText
    status: ProductStatus
    default_currency: str
    created_at: datetime
    updated_at: datetime


class ProductListItem(BaseModel):
    product_id: str
    type: ProductType
    code: str
    status: ProductStatus
    name_tr: Optional[str] = None
    name_en: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    published_version: Optional[int] = None


class ProductListResponse(BaseModel):
    items: List[ProductListItem]
    next_cursor: Optional[str] = None


class RoomTypeCreateRequest(BaseModel):
    product_id: str
    code: str = Field(min_length=1, max_length=32)
    name: LocalizedText
    max_occupancy: int = Field(ge=1, le=20)
    attributes: Dict[str, Any] = Field(default_factory=dict)


class RoomTypeResponse(BaseModel):
    room_type_id: str
    product_id: str
    code: str
    name: LocalizedText
    max_occupancy: int
    attributes: Dict[str, Any]


class CancellationRule(BaseModel):
    days_before: int = Field(ge=0, le=3650)
    penalty_type: Literal["none", "nights", "percent", "fixed"]
    nights: Optional[int] = Field(default=None, ge=1, le=30)
    percent: Optional[float] = Field(default=None, ge=0, le=100)
    amount: Optional[float] = Field(default=None, ge=0)


class CancellationPolicyCreateRequest(BaseModel):
    code: str = Field(min_length=2, max_length=64)
    name: str = Field(min_length=2, max_length=128)
    rules: List[CancellationRule]


class CancellationPolicyResponse(BaseModel):
    cancellation_policy_id: str
    code: str
    name: str
    rules: List[CancellationRule]


class RatePlanCreateRequest(BaseModel):
    product_id: str
    code: str = Field(min_length=1, max_length=32)
    name: LocalizedText
    board: Literal["RO", "BB", "HB", "FB", "AI"]
    cancellation_policy_id: Optional[str] = None
    payment_type: Literal["prepay", "postpay", "mixed"] = "postpay"
    min_stay: int = Field(default=1, ge=1, le=365)
    max_stay: int = Field(default=30, ge=1, le=365)


class RatePlanResponse(BaseModel):
    rate_plan_id: str
    product_id: str
    code: str
    name: LocalizedText
    board: str
    cancellation_policy_id: Optional[str] = None
    payment_type: str
    min_stay: int
    max_stay: int


class ProductVersionContent(BaseModel):
    description: LocalizedText = Field(default_factory=LocalizedText)
    images: List[Dict[str, str]] = Field(default_factory=list)
    amenities: List[str] = Field(default_factory=list)
    room_type_ids: List[str] = Field(default_factory=list)
    rate_plan_ids: List[str] = Field(default_factory=list)
    extra: Dict[str, Any] = Field(default_factory=dict)


class ProductVersionCreateRequest(BaseModel):
    valid_from: Optional[date] = None
    valid_to: Optional[date] = None
    content: ProductVersionContent = Field(default_factory=ProductVersionContent)


class ProductVersionResponse(BaseModel):
    version_id: str
    product_id: str
    version: int
    status: VersionStatus
    valid_from: Optional[date] = None
    valid_to: Optional[date] = None
    content: ProductVersionContent
    created_at: datetime
    updated_at: datetime
    published_at: Optional[datetime] = None
    published_by_email: Optional[str] = None


class ProductVersionListResponse(BaseModel):
    items: List[ProductVersionResponse]


class PublishResponse(BaseModel):
    product_id: str
    published_version: int
    version_id: str
    status: str = "published"
