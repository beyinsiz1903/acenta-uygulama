from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional
from datetime import datetime, timezone
import asyncio



class ConfirmStatus(str, Enum):
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    PENDING = "pending"
    NOT_SUPPORTED = "not_supported"


@dataclass
class SupplierContext:
    request_id: str
    organization_id: str
    tenant_id: Optional[str] = None
    user_id: Optional[str] = None
    timeout_ms: int = 8000
    deadline_at: Optional["datetime"] = None


@dataclass
class ConfirmResult:
    supplier_code: str
    supplier_booking_id: Optional[str]
    status: ConfirmStatus
    raw: Dict[str, Any]
    supplier_terms: Optional[Dict[str, Any]] = None


class SupplierAdapterError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        retryable: bool = False,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.retryable = retryable
        self.details = details or {}


class SupplierAdapter:
    async def pre_reserve(self, ctx: SupplierContext, booking: Dict[str, Any]) -> None:  # pragma: no cover - v1 no-op
        return None

    async def confirm_booking(self, ctx: SupplierContext, booking: Dict[str, Any]) -> ConfirmResult:
        raise NotImplementedError

    async def cancel_booking(self, ctx: SupplierContext, booking: Dict[str, Any]) -> None:  # pragma: no cover - v1 stub
        return None

    async def healthcheck(self, ctx: SupplierContext) -> Dict[str, Any]:  # pragma: no cover - v1 stub
        return {"status": "ok"}
