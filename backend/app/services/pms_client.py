from __future__ import annotations

import abc
from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class PmsError(Exception):
    code: str
    message: str
    http_status: int = 503
    meta: Optional[dict[str, Any]] = None


class PmsClient(abc.ABC):
    """PMS adapter interface.

    MVP contract:
    - quote(): availability + rate snapshot
    - create_booking(): create reservation in PMS (idempotent)
    - cancel_booking(): cancel reservation in PMS
    """

    @abc.abstractmethod
    async def quote(self, *, organization_id: str, channel: str, payload: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError

    @abc.abstractmethod
    async def create_booking(
        self,
        *,
        organization_id: str,
        channel: str,
        idempotency_key: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        raise NotImplementedError

    @abc.abstractmethod
    async def cancel_booking(
        self,
        *,
        organization_id: str,
        channel: str,
        pms_booking_id: str,
        reason: Optional[str] = None,
    ) -> dict[str, Any]:
        raise NotImplementedError
