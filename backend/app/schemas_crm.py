from __future__ import annotations

from datetime import datetime
from typing import List, Optional, Literal, Dict

from pydantic import BaseModel, Field, constr


class CustomerContact(BaseModel):
    type: Literal["phone", "email"]
    value: constr(strip_whitespace=True, min_length=3)
    is_primary: bool = False


class CustomerBase(BaseModel):
    type: Literal["individual", "corporate"] = "individual"
    name: constr(strip_whitespace=True, min_length=2)
    tc_vkn: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    contacts: List[CustomerContact] = Field(default_factory=list)
    assigned_user_id: Optional[str] = None


class CustomerCreate(CustomerBase):
    pass


class CustomerPatch(BaseModel):
    type: Optional[Literal["individual", "corporate"]] = None
    name: Optional[constr(strip_whitespace=True, min_length=2)] = None
    tc_vkn: Optional[str] = None
    tags: Optional[List[str]] = None
    contacts: Optional[List[CustomerContact]] = None
    assigned_user_id: Optional[str] = None


class CustomerOut(CustomerBase):
    id: str
    organization_id: str
    created_at: datetime
    updated_at: datetime


class DealOut(BaseModel):
    id: str
    organization_id: str
    customer_id: Optional[str] = None
    title: Optional[str] = None
    stage: str = "lead"
    status: str = "open"
    amount: Optional[float] = None
    currency: Optional[str] = None
    owner_user_id: Optional[str] = None
    expected_close_date: Optional[datetime] = None
    next_action_at: Optional[datetime] = None
    won_booking_id: Optional[str] = None
    tenant_id: Optional[str] = None
    source: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class DealCreate(BaseModel):
    customer_id: Optional[str] = None
    title: Optional[constr(strip_whitespace=True, min_length=1)] = None
    stage: Optional[str] = "lead"
    amount: Optional[float] = None
    currency: Optional[str] = None
    owner_user_id: Optional[str] = None
    next_action_at: Optional[datetime] = None


class DealPatch(BaseModel):
    customer_id: Optional[str] = None
    title: Optional[constr(strip_whitespace=True, min_length=1)] = None
    stage: Optional[str] = None
    status: Optional[str] = None
    amount: Optional[float] = None
    currency: Optional[str] = None
    owner_user_id: Optional[str] = None
    expected_close_date: Optional[datetime] = None
    next_action_at: Optional[datetime] = None


class TaskOut(BaseModel):
    id: str
    organization_id: str
    owner_user_id: Optional[str] = None
    title: str
    status: Literal["open", "done"] = "open"
    priority: Literal["low", "normal", "high"] = "normal"
    due_date: Optional[datetime] = None
    related_type: Optional[Literal["customer", "deal", "booking"]] = None
    related_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class TaskCreate(BaseModel):
    title: constr(strip_whitespace=True, min_length=2)
    owner_user_id: Optional[str] = None
    priority: Literal["low", "normal", "high"] = "normal"
    due_date: Optional[datetime] = None
    related_type: Optional[Literal["customer", "deal", "booking"]] = None
    related_id: Optional[str] = None


class TaskPatch(BaseModel):
    title: Optional[constr(strip_whitespace=True, min_length=2)] = None
    owner_user_id: Optional[str] = None
    priority: Optional[Literal["low", "normal", "high"]] = None
    due_date: Optional[datetime] = None
    status: Optional[Literal["open", "done"]] = None


class ActivityOut(BaseModel):
    id: str
    organization_id: str
    created_by_user_id: Optional[str] = None
    type: Literal["note", "call", "email", "meeting"]
    body: str
    related_type: Optional[Literal["customer", "deal", "booking"]] = None
    related_id: Optional[str] = None
    created_at: datetime


class ActivityCreate(BaseModel):
    type: Literal["note", "call", "email", "meeting"]
    body: constr(strip_whitespace=True, min_length=1)
    related_type: Optional[Literal["customer", "deal", "booking"]] = None
    related_id: Optional[str] = None


class CustomerDetailOut(BaseModel):
    customer: CustomerOut
    recent_bookings: List[dict] = Field(default_factory=list)
    open_deals: List[dict] = Field(default_factory=list)
    open_tasks: List[dict] = Field(default_factory=list)



class DuplicateCustomerSummary(BaseModel):
    id: str
    name: Optional[str]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]


class DuplicateCustomerClusterOut(BaseModel):
    organization_id: str
    contact: Dict[str, str]  # {"type": "email"|"phone", "value": "..."}
    primary: DuplicateCustomerSummary
    duplicates: List[DuplicateCustomerSummary]



class CustomerMergeRequest(BaseModel):
    primary_id: str
    duplicate_ids: List[str]
    dry_run: bool = False


class CustomerMergeCounts(BaseModel):
    bookings: Dict[str, int]
    deals: Dict[str, int]
    tasks: Dict[str, int]
    activities: Dict[str, int]


class CustomerMergeResultOut(BaseModel):
    organization_id: str
    primary_id: str
    merged_ids: List[str]
    skipped_ids: List[str]
    rewired: CustomerMergeCounts
    dry_run: bool
