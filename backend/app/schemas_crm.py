from __future__ import annotations

from datetime import datetime
from typing import List, Optional, Literal

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


class CustomerDetailOut(BaseModel):
    customer: CustomerOut
    recent_bookings: List[dict] = Field(default_factory=list)
    open_deals: List[dict] = Field(default_factory=list)
    open_tasks: List[dict] = Field(default_factory=list)
