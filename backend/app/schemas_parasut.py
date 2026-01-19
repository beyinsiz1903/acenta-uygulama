from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


class ParasutPushStatusResponse(BaseModel):
    status: Literal["success", "skipped", "failed"]
    log_id: str
    parasut_contact_id: Optional[str] = None
    parasut_invoice_id: Optional[str] = None
    reason: Optional[str] = None


class ParasutPushLogItem(BaseModel):
    id: str = Field(..., alias="_id")
    booking_id: str
    push_type: str
    status: Literal["pending", "success", "failed"]
    parasut_contact_id: Optional[str] = None
    parasut_invoice_id: Optional[str] = None
    attempt_count: int
    last_error: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class ParasutPushLogListResponse(BaseModel):
    items: list[ParasutPushLogItem]

