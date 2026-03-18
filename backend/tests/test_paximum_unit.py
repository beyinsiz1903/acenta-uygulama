"""Unit tests for Paximum models, mapping, and adapter (no live API calls)."""
from __future__ import annotations

import pytest
from datetime import datetime, timezone
from decimal import Decimal

from app.services.suppliers.paximum_models import (
    Money,
    Offer,
    Hotel,
    SearchResult,
    PaximumBooking,
    CancellationPolicy,
    Room,
    Traveller,
    parse_dt,
)
from app.services.suppliers.paximum_mapping import (
    map_offer,
    map_hotel,
    map_search_result,
    map_booking,
)
from app.services.suppliers.paximum_adapter import (
    PaximumAdapter,
    PaximumValidationError,
)


# ── parse_dt ──

class TestParseDt:
    def test_none_input(self):
        assert parse_dt(None) is None

    def test_empty_string(self):
        assert parse_dt("") is None

    def test_iso_with_z(self):
        dt = parse_dt("2026-05-01T12:00:00Z")
        assert dt is not None
        assert dt.year == 2026
        assert dt.month == 5

    def test_iso_with_offset(self):
        dt = parse_dt("2026-05-01T12:00:00+03:00")
        assert dt is not None

    def test_invalid_string(self):
        assert parse_dt("not-a-date") is None


# ── Money ──

class TestMoney:
    def test_creation(self):
        m = Money(amount=Decimal("100.50"), currency="EUR")
        assert m.amount == Decimal("100.50")
        assert m.currency == "EUR"


# ── Offer ──

class TestOffer:
    def test_is_expired_no_expiry(self):
        offer = Offer(
            offer_id="1", search_id=None, hotel_id="h1",
            expires_on=None, board=None, board_id=None,
            board_categories=[], rooms=[],
            price=Money(amount=Decimal("100"), currency="EUR"),
            minimum_sale_price=None,
            is_b2c_price=False, is_special=False, is_available=True,
            cancellation_policies=[], restrictions=[],
            warnings=[], notes=[], supplements=[],
        )
        assert offer.is_expired() is False

    def test_is_expired_future(self):
        offer = Offer(
            offer_id="1", search_id=None, hotel_id="h1",
            expires_on=datetime(2099, 1, 1, tzinfo=timezone.utc),
            board=None, board_id=None,
            board_categories=[], rooms=[],
            price=Money(amount=Decimal("100"), currency="EUR"),
            minimum_sale_price=None,
            is_b2c_price=False, is_special=False, is_available=True,
            cancellation_policies=[], restrictions=[],
            warnings=[], notes=[], supplements=[],
        )
        assert offer.is_expired() is False

    def test_is_expired_past(self):
        offer = Offer(
            offer_id="1", search_id=None, hotel_id="h1",
            expires_on=datetime(2020, 1, 1, tzinfo=timezone.utc),
            board=None, board_id=None,
            board_categories=[], rooms=[],
            price=Money(amount=Decimal("100"), currency="EUR"),
            minimum_sale_price=None,
            is_b2c_price=False, is_special=False, is_available=True,
            cancellation_policies=[], restrictions=[],
            warnings=[], notes=[], supplements=[],
        )
        assert offer.is_expired() is True


# ── Mapping ──

class TestMapOffer:
    def test_basic_mapping(self):
        raw = {
            "id": "offer-123",
            "hotelId": "h-456",
            "expiresOn": "2026-06-01T10:00:00Z",
            "board": "All Inclusive",
            "boardId": "AI",
            "boardCategories": ["all_inclusive"],
            "rooms": [
                {"id": "r1", "type": "Standard", "typeId": "std"}
            ],
            "price": {"amount": 250.0, "currency": "TRY"},
            "minimumSalePrice": {"amount": 200.0, "currency": "TRY"},
            "isB2CPrice": True,
            "isSpecial": False,
            "isAvailable": True,
            "cancellationPolicies": [
                {
                    "permittedDate": "2026-05-25T00:00:00Z",
                    "fee": {"amount": 50.0, "currency": "TRY"},
                }
            ],
            "restrictions": [],
            "warnings": ["test warning"],
            "notes": [],
            "supplements": [],
        }
        offer = map_offer(raw, search_id="search-1")
        assert offer.offer_id == "offer-123"
        assert offer.hotel_id == "h-456"
        assert offer.search_id == "search-1"
        assert offer.price.amount == Decimal("250.0")
        assert offer.price.currency == "TRY"
        assert offer.is_b2c_price is True
        assert len(offer.rooms) == 1
        assert offer.rooms[0].room_id == "r1"
        assert len(offer.cancellation_policies) == 1
        assert offer.cancellation_policies[0].fee.amount == Decimal("50.0")
        assert offer.warnings == ["test warning"]


class TestMapHotel:
    def test_basic_mapping(self):
        raw = {
            "id": "h-789",
            "name": "Grand Hotel",
            "description": "A grand hotel",
            "city": {"id": 42, "name": "Istanbul"},
            "country": {"id": 1, "name": "Turkey"},
            "stars": 5,
            "rating": 8.5,
            "photos": ["photo1.jpg"],
            "themes": ["luxury"],
            "facilities": [],
            "content": [],
            "address": {"line1": "Main St"},
            "geolocation": {"lat": 41.0, "lon": 29.0},
            "offers": [
                {
                    "id": "o1",
                    "hotelId": "h-789",
                    "price": {"amount": 100, "currency": "EUR"},
                    "isAvailable": True,
                    "rooms": [],
                    "boardCategories": [],
                }
            ],
        }
        hotel = map_hotel(raw, search_id="s1")
        assert hotel.hotel_id == "h-789"
        assert hotel.name == "Grand Hotel"
        assert hotel.city_name == "Istanbul"
        assert hotel.stars == 5.0
        assert len(hotel.offers) == 1
        assert hotel.offers[0].offer_id == "o1"


class TestMapSearchResult:
    def test_basic_mapping(self):
        payload = {
            "searchId": "search-abc",
            "expiresOn": "2026-06-01T10:00:00Z",
            "hotels": [
                {
                    "id": "h1",
                    "name": "Hotel A",
                    "offers": [],
                    "city": {},
                    "country": {},
                    "address": {},
                    "geolocation": {},
                    "photos": [],
                    "themes": [],
                    "facilities": [],
                    "content": [],
                }
            ],
        }
        result = map_search_result(payload)
        assert result.search_id == "search-abc"
        assert len(result.hotels) == 1
        assert result.hotels[0].hotel_id == "h1"


class TestMapBooking:
    def test_basic_mapping(self):
        raw = {
            "bookingInfo": {
                "id": "bk-100",
                "bookingNumber": "BN-001",
                "orderNumber": "ON-001",
                "supplierBookingNumber": "SBN-001",
                "status": "Confirmed",
                "serviceType": "Hotel",
                "totalBuyingAmount": {"amount": 500, "currency": "TRY"},
                "totalSellingAmount": {"amount": 600, "currency": "TRY"},
            },
            "checkin": "2026-06-01T14:00:00Z",
            "checkout": "2026-06-05T11:00:00Z",
            "hotelId": "h-789",
            "notes": ["VIP guest"],
            "nationality": "TR",
        }
        booking = map_booking(raw)
        assert booking.booking_id == "bk-100"
        assert booking.booking_number == "BN-001"
        assert booking.status == "Confirmed"
        assert booking.total_buying_amount.amount == Decimal("500")


# ── Adapter Validation ──

class TestAdapterValidation:
    def test_max_rooms_validation(self):
        adapter = PaximumAdapter(base_url="http://localhost", token="test")
        with pytest.raises(PaximumValidationError, match="Maximum 4 rooms"):
            import asyncio
            asyncio.get_event_loop().run_until_complete(
                adapter.search_hotels(
                    destinations=[{"type": "city", "id": "1"}],
                    rooms=[{"adults": 2}] * 5,
                    check_in_date="2026-05-01",
                    check_out_date="2026-05-03",
                    currency="EUR",
                    customer_nationality="TR",
                )
            )

    def test_max_adults_validation(self):
        adapter = PaximumAdapter(base_url="http://localhost", token="test")
        with pytest.raises(PaximumValidationError, match="Maximum 20 adults"):
            import asyncio
            asyncio.get_event_loop().run_until_complete(
                adapter.search_hotels(
                    destinations=[{"type": "city", "id": "1"}],
                    rooms=[{"adults": 21}],
                    check_in_date="2026-05-01",
                    check_out_date="2026-05-03",
                    currency="EUR",
                    customer_nationality="TR",
                )
            )



# ── Status Mapping ──

from app.services.suppliers.status_mapping import (
    resolve_all,
    resolve_supplier_booking_status,
    resolve_oms_order_status,
    resolve_settlement_status,
    is_terminal_supplier_status,
    should_post_ledger,
    should_reverse_ledger,
    ResolvedStatus,
)


class TestStatusMapping:
    """Tests for Paximum → OMS three-domain status mapping."""

    def test_confirmed_mapping(self):
        r = resolve_all("Confirmed")
        assert r.supplier_booking_status == "confirmed"
        assert r.oms_order_status == "confirmed"
        assert r.settlement_status == "not_settled"
        assert r.raw_supplier_status == "Confirmed"

    def test_pending_mapping(self):
        r = resolve_all("Pending")
        assert r.supplier_booking_status == "pending"
        assert r.oms_order_status == "pending_confirmation"
        assert r.settlement_status == "not_settled"

    def test_onrequest_mapping(self):
        r = resolve_all("OnRequest")
        assert r.supplier_booking_status == "pending"
        assert r.oms_order_status == "pending_confirmation"
        assert r.settlement_status == "not_settled"

    def test_rejected_mapping(self):
        r = resolve_all("Rejected")
        assert r.supplier_booking_status == "failed"
        assert r.oms_order_status == "cancelled"
        assert r.settlement_status == "not_settled"

    def test_cancelled_mapping(self):
        r = resolve_all("Cancelled")
        assert r.supplier_booking_status == "cancelled"
        assert r.oms_order_status == "cancelled"
        assert r.settlement_status == "reversed"

    def test_unknown_mapping_defaults(self):
        r = resolve_all("SomeRandomStatus")
        assert r.supplier_booking_status == "not_started"
        assert r.oms_order_status == "pending_confirmation"
        assert r.settlement_status == "not_settled"

    def test_case_insensitive(self):
        for raw in ("confirmed", "CONFIRMED", "Confirmed", "  confirmed  "):
            r = resolve_all(raw)
            assert r.supplier_booking_status == "confirmed"
            assert r.oms_order_status == "confirmed"

    def test_individual_resolvers(self):
        assert resolve_supplier_booking_status("OnRequest") == "pending"
        assert resolve_oms_order_status("OnRequest") == "pending_confirmation"
        assert resolve_settlement_status("Cancelled") == "reversed"

    def test_terminal_status(self):
        assert is_terminal_supplier_status("Confirmed") is True
        assert is_terminal_supplier_status("Rejected") is True
        assert is_terminal_supplier_status("Cancelled") is True
        assert is_terminal_supplier_status("Pending") is False
        assert is_terminal_supplier_status("OnRequest") is False

    def test_ledger_decisions(self):
        assert should_post_ledger("Confirmed") is True
        assert should_post_ledger("Pending") is False
        assert should_reverse_ledger("Cancelled") is True
        assert should_reverse_ledger("Rejected") is True
        assert should_reverse_ledger("Confirmed") is False

    def test_resolved_status_is_frozen(self):
        r = resolve_all("Confirmed")
        with pytest.raises(AttributeError):
            r.oms_order_status = "hacked"

    def test_three_domains_are_distinct(self):
        """supplier_status != oms_status != settlement_status for non-trivial states."""
        r = resolve_all("Pending")
        assert r.supplier_booking_status == "pending"
        assert r.oms_order_status == "pending_confirmation"
        assert r.settlement_status == "not_settled"
        # All three are different
        assert len({r.supplier_booking_status, r.oms_order_status, r.settlement_status}) == 3


# ── Offer Cache ──

from app.services.suppliers.offer_cache import RedisOfferCache


class TestOfferCacheTTL:
    """Unit tests for TTL computation (no Redis needed)."""

    def test_ttl_with_no_expiry(self):
        cache = RedisOfferCache()
        ttl = cache._compute_ttl(None)
        assert ttl == cache.DEFAULT_TTL_SECONDS

    def test_ttl_with_future_expiry(self):
        cache = RedisOfferCache()
        future = datetime(2099, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        ttl = cache._compute_ttl(future)
        assert ttl > 0

    def test_ttl_with_past_expiry(self):
        cache = RedisOfferCache()
        past = datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        ttl = cache._compute_ttl(past)
        assert ttl == 0

    def test_ttl_subtracts_safety_buffer(self):
        from datetime import timedelta
        cache = RedisOfferCache()
        # Offer expires 120 seconds from now
        exp = datetime.now(timezone.utc) + timedelta(seconds=120)
        ttl = cache._compute_ttl(exp)
        # Should be approximately 120 - 30 = 90
        assert 85 <= ttl <= 95

    def test_ttl_too_short_returns_zero(self):
        from datetime import timedelta
        cache = RedisOfferCache()
        # Offer expires 20 seconds from now (less than safety buffer)
        exp = datetime.now(timezone.utc) + timedelta(seconds=20)
        ttl = cache._compute_ttl(exp)
        assert ttl == 0

    def test_ttl_with_naive_datetime(self):
        """Naive datetime should be treated as UTC."""
        cache = RedisOfferCache()
        future = datetime(2099, 1, 1, 0, 0, 0)
        ttl = cache._compute_ttl(future)
        assert ttl > 0
