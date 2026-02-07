"""SMS provider abstraction (B).

ABC interface + MockSMSProvider.
"""
from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class SMSProvider(ABC):
    """Abstract SMS provider interface."""

    @abstractmethod
    async def send_sms(self, to: str, message: str, sender_id: str = "") -> Dict[str, Any]:
        """Send single SMS. Returns {message_id, status}."""
        ...

    @abstractmethod
    async def send_bulk(self, recipients: List[str], message: str, sender_id: str = "") -> Dict[str, Any]:
        """Send bulk SMS. Returns {batch_id, count, status}."""
        ...

    @abstractmethod
    async def get_status(self, message_id: str) -> Dict[str, Any]:
        """Get delivery status."""
        ...

    @abstractmethod
    async def get_balance(self) -> Dict[str, Any]:
        """Get account balance/credits."""
        ...


class MockSMSProvider(SMSProvider):
    """Mock SMS provider for development/testing.

    Logs all messages to MongoDB instead of sending real SMS.
    """

    def __init__(self):
        self._sent: List[Dict] = []

    async def send_sms(self, to: str, message: str, sender_id: str = "") -> Dict[str, Any]:
        msg_id = f"sms_{uuid.uuid4().hex[:12]}"
        entry = {
            "message_id": msg_id,
            "to": to,
            "message": message,
            "sender_id": sender_id,
            "status": "delivered",
            "provider": "mock",
        }
        self._sent.append(entry)
        return entry

    async def send_bulk(self, recipients: List[str], message: str, sender_id: str = "") -> Dict[str, Any]:
        batch_id = f"batch_{uuid.uuid4().hex[:8]}"
        results = []
        for phone in recipients:
            r = await self.send_sms(phone, message, sender_id)
            results.append(r)
        return {
            "batch_id": batch_id,
            "count": len(results),
            "status": "completed",
            "results": results,
        }

    async def get_status(self, message_id: str) -> Dict[str, Any]:
        for entry in self._sent:
            if entry["message_id"] == message_id:
                return {"message_id": message_id, "status": "delivered"}
        return {"message_id": message_id, "status": "not_found"}

    async def get_balance(self) -> Dict[str, Any]:
        return {"credits": 9999, "currency": "TRY", "provider": "mock"}


_providers: Dict[str, SMSProvider] = {}


def get_sms_provider(name: str = "mock") -> SMSProvider:
    if name not in _providers:
        if name == "mock":
            _providers[name] = MockSMSProvider()
        else:
            _providers[name] = MockSMSProvider()
    return _providers[name]
