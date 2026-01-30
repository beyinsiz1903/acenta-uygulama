from __future__ import annotations

from typing import Any, Dict


async def search_mock_offers(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Deterministic mock supplier response for testing connector layer.

    The input payload is currently ignored for branching; we only require it
    structurally. For any valid request we return the same two mock offers in
    TRY to keep behavior fully deterministic.
    """

    return {
        "supplier": "mock_v1",
        "currency": "TRY",
        "items": [
            {
                "offer_id": "MOCK-IST-1",
                "hotel_name": "Mock Hotel 1",
                "total_price": 12000.0,
                "is_available": True,
            },
            {
                "offer_id": "MOCK-IST-2",
                "hotel_name": "Mock Hotel 2",
                "total_price": 18000.0,
                "is_available": True,
            },
        ],
    }
