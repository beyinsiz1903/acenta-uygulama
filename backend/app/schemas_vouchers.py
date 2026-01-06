from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class VoucherGenerateResponse(BaseModel):
    booking_id: str
    voucher_id: str
    version: int
    status: str = Field(..., description="Voucher status (e.g. active, void)")
    html_url: str
    pdf_url: str


class VoucherHistoryItem(BaseModel):
    voucher_id: str
    version: int
    status: str
    created_at: datetime
    created_by_email: Optional[str] = None


class VoucherHistoryResponse(BaseModel):
    items: list[VoucherHistoryItem]


class VoucherResendRequest(BaseModel):
    to_email: str
    message: Optional[str] = None


class VoucherResendResponse(BaseModel):
    voucher_id: str
    status: str

