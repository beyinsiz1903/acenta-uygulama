from __future__ import annotations

from typing import Any, Dict

import httpx

from app.config import PAXIMUM_API_KEY, PAXIMUM_BASE_URL, PAXIMUM_TIMEOUT_SECONDS


class PaximumAdapter:
    """Thin HTTP client for Paximum search-only API.

    This adapter is intentionally minimal for Sprint 3:
    - POSTs to /v1/search/hotels with JSON payload
    - Does not know about org/user; purely upstream communication
    - Leaves error mapping to higher-level service
    """

    def __init__(self) -> None:
        self.base_url = PAXIMUM_BASE_URL.rstrip("/")
        self.api_key = PAXIMUM_API_KEY
        self.timeout = float(PAXIMUM_TIMEOUT_SECONDS or 10.0)

    async def search_hotels(self, payload: Dict[str, Any]) -> httpx.Response:
        """Call Paximum /v1/search/hotels and return raw httpx.Response.

        Higher-level services are responsible for mapping status codes and
        normalizing JSON bodies.
        """

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            return await client.post(
                f"{self.base_url}/v1/search/hotels",
                json=payload,
                headers=headers,
            )


paximum_adapter = PaximumAdapter()
