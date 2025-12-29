from __future__ import annotations

from typing import Any


def draft_to_pms_create_payload(*, draft: dict[str, Any], agency_id: str) -> dict[str, Any]:
    """Map booking draft -> PMS create_booking payload (adapter contract)."""
    return {
        "hotel_id": draft.get("hotel_id"),
        "agency_id": agency_id,
        "stay": draft.get("stay"),
        "occupancy": draft.get("occupancy"),
        "guest": draft.get("guest"),
        "special_requests": draft.get("special_requests"),
        "rate_snapshot": draft.get("rate_snapshot"),
        "channel": "agency_extranet",
    }
