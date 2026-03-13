"""Real Supplier Integration Skeletons — Production-ready adapter contracts.

Defines auth, mapping, rate limits, sandbox/prod config for:
- Paximum
- AviationStack
- Amadeus

These skeletons are ready for live integration in the next phase.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SupplierConfig:
    """Supplier connection configuration."""
    code: str
    name: str
    auth_method: str  # api_key, oauth2, basic, hmac
    base_url_sandbox: str
    base_url_production: str
    rate_limit_rps: int
    timeout_ms: int
    max_retries: int
    pagination_type: str  # offset, cursor, page
    request_signing: str  # none, hmac_sha256, jwt
    sandbox_mode: bool = True
    headers: dict = field(default_factory=dict)
    env_key_name: str = ""


# ============================================================================
# PAXIMUM — Hotel/Tour supplier
# ============================================================================

PAXIMUM_CONFIG = SupplierConfig(
    code="paximum",
    name="Paximum Travel API",
    auth_method="api_key",
    base_url_sandbox="https://service.stage.paximum.com/v2/api",
    base_url_production="https://service.paximum.com/v2/api",
    rate_limit_rps=30,
    timeout_ms=15000,
    max_retries=3,
    pagination_type="offset",
    request_signing="none",
    env_key_name="PAXIMUM_API_KEY",
    headers={"Content-Type": "application/json"},
)

PAXIMUM_MAPPING = {
    "search": {
        "endpoint": "/productservice/getproductinfo",
        "method": "POST",
        "request_map": {
            "destination": "body.arrivalLocations[0].id",
            "check_in": "body.checkIn",
            "check_out": "body.checkOut",
            "guests": "body.roomCriteria",
            "nationality": "body.nationality",
            "currency": "body.currency",
        },
        "response_map": {
            "items": "body.hotels",
            "item_id": "body.hotels[].id",
            "name": "body.hotels[].name",
            "price": "body.hotels[].offers[0].price.amount",
        },
    },
    "hold": {
        "endpoint": "/bookingservice/beginbooking",
        "method": "POST",
    },
    "confirm": {
        "endpoint": "/bookingservice/commitbooking",
        "method": "POST",
    },
    "cancel": {
        "endpoint": "/bookingservice/cancelbooking",
        "method": "POST",
    },
}


# ============================================================================
# AVIATIONSTACK — Flight data & search
# ============================================================================

AVIATIONSTACK_CONFIG = SupplierConfig(
    code="aviationstack",
    name="AviationStack Flight API",
    auth_method="api_key",
    base_url_sandbox="https://api.aviationstack.com/v1",
    base_url_production="https://api.aviationstack.com/v1",
    rate_limit_rps=5,
    timeout_ms=10000,
    max_retries=2,
    pagination_type="offset",
    request_signing="none",
    env_key_name="AVIATIONSTACK_API_KEY",
)

AVIATIONSTACK_MAPPING = {
    "search_flights": {
        "endpoint": "/flights",
        "method": "GET",
        "request_map": {
            "dep_iata": "params.dep_iata",
            "arr_iata": "params.arr_iata",
            "flight_date": "params.flight_date",
        },
        "response_map": {
            "items": "data",
            "flight_number": "data[].flight.iata",
            "departure": "data[].departure",
            "arrival": "data[].arrival",
            "airline": "data[].airline.name",
            "status": "data[].flight_status",
        },
    },
}


# ============================================================================
# AMADEUS — GDS flights, hotels, activities
# ============================================================================

AMADEUS_CONFIG = SupplierConfig(
    code="amadeus",
    name="Amadeus Travel API",
    auth_method="oauth2",
    base_url_sandbox="https://test.api.amadeus.com",
    base_url_production="https://api.amadeus.com",
    rate_limit_rps=10,
    timeout_ms=12000,
    max_retries=3,
    pagination_type="page",
    request_signing="none",
    env_key_name="AMADEUS_API_KEY",
    headers={"Content-Type": "application/vnd.amadeus+json"},
)

AMADEUS_MAPPING = {
    "auth": {
        "endpoint": "/v1/security/oauth2/token",
        "method": "POST",
        "note": "OAuth2 client_credentials flow. Token valid ~30min.",
    },
    "search_flights": {
        "endpoint": "/v2/shopping/flight-offers",
        "method": "GET",
        "request_map": {
            "origin": "params.originLocationCode",
            "destination": "params.destinationLocationCode",
            "departure_date": "params.departureDate",
            "adults": "params.adults",
            "currency": "params.currencyCode",
        },
    },
    "search_hotels": {
        "endpoint": "/v1/reference-data/locations/hotels/by-city",
        "method": "GET",
    },
    "confirm_flight": {
        "endpoint": "/v1/booking/flight-orders",
        "method": "POST",
    },
}


# ============================================================================
# Registry & Risk Matrix
# ============================================================================

SUPPLIER_CONFIGS = {
    "paximum": PAXIMUM_CONFIG,
    "aviationstack": AVIATIONSTACK_CONFIG,
    "amadeus": AMADEUS_CONFIG,
}

SUPPLIER_RISK_MATRIX = {
    "paximum": {
        "integration_complexity": "medium",
        "api_stability": "high",
        "rate_limit_risk": "low",
        "auth_complexity": "low",
        "rollout_priority": 1,
        "estimated_days": 5,
        "risks": [
            "XML-based responses in some endpoints",
            "Session-based auth requires token refresh",
            "Currency conversion edge cases",
        ],
    },
    "aviationstack": {
        "integration_complexity": "low",
        "api_stability": "high",
        "rate_limit_risk": "high",
        "auth_complexity": "low",
        "rollout_priority": 2,
        "estimated_days": 3,
        "risks": [
            "Strict rate limits on free tier",
            "Real-time data only (no booking)",
            "Limited pagination support",
        ],
    },
    "amadeus": {
        "integration_complexity": "high",
        "api_stability": "medium",
        "rate_limit_risk": "medium",
        "auth_complexity": "high",
        "rollout_priority": 3,
        "estimated_days": 8,
        "risks": [
            "OAuth2 token management complexity",
            "Complex GDS response formats",
            "Sandbox vs production data differences",
            "Multi-step booking flow",
        ],
    },
}

ROLLOUT_ORDER = [
    {"phase": 1, "supplier": "paximum", "scope": "hotel search + booking", "timeline": "Week 1-2"},
    {"phase": 2, "supplier": "aviationstack", "scope": "flight search (read-only)", "timeline": "Week 2-3"},
    {"phase": 3, "supplier": "amadeus", "scope": "flight search + booking", "timeline": "Week 3-5"},
]
