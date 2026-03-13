"""Real Supplier Adapter Bridges.

Wraps the HTTP-based adapters (RateHawk, TBO, Paximum, WWTatil)
into the canonical SupplierAdapter contract interface used by
the orchestrator, registry, and failover engine.

Architecture:
  RealRateHawkBridge -> contracts/base.SupplierAdapter
    internally uses -> adapters/ratehawk_adapter.RateHawkAdapter (HTTP client)

Each bridge:
  1. Implements search/confirm/cancel via the canonical interface
  2. Normalizes raw supplier responses into canonical schemas
  3. Transforms canonical requests into supplier-specific payloads
  4. Reports capability metadata (supports_hold, etc.)
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, date, timezone
from typing import Any, Dict, Optional

from app.suppliers.contracts.base import SupplierAdapter, SupplierType, LifecycleMethod
from app.suppliers.contracts.schemas import (
    AvailabilityRequest, AvailabilityResult,
    CancelRequest, CancelResult,
    ConfirmRequest, ConfirmResult,
    HoldRequest, HoldResult,
    HotelSearchItem, TourSearchItem, FlightSearchItem,
    TransferSearchItem, ActivitySearchItem,
    PriceBreakdown,
    PricingRequest, PricingResult,
    SearchRequest, SearchResult,
    SupplierContext, SupplierProductType,
    SupplierCapabilityInfo,
)
from app.suppliers.contracts.errors import (
    SupplierAuthError, SupplierError, SupplierTimeoutError, SupplierUnavailableError,
)

logger = logging.getLogger("suppliers.bridges")


def _now():
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# RateHawk Bridge (Hotel)
# ---------------------------------------------------------------------------

class RealRateHawkBridge(SupplierAdapter):
    supplier_code = "ratehawk"
    supplier_type = SupplierType.HOTEL
    display_name = "RateHawk Hotel API"
    supported_methods = {
        LifecycleMethod.HEALTHCHECK,
        LifecycleMethod.SEARCH,
        LifecycleMethod.CONFIRM,
        LifecycleMethod.CANCEL,
    }

    capability = SupplierCapabilityInfo(
        supplier_code="ratehawk",
        product_types=["hotel"],
        supports_hold=False,
        supports_direct_confirm=True,
        supports_cancel=True,
        supports_pricing_check=True,
        requires_precheck=False,
    )

    def __init__(self, db=None):
        self.db = db

    async def _get_adapter(self, ctx: SupplierContext):
        from app.suppliers.adapters.ratehawk_adapter import RateHawkAdapter
        from app.domain.suppliers.supplier_credentials_service import get_decrypted_credentials, get_cached_token
        db = self.db
        if db is None:
            from app.db import get_db_sync
            db = get_db_sync()
        creds = await get_decrypted_credentials(db, ctx.organization_id, "ratehawk")
        if not creds:
            raise SupplierAuthError("No RateHawk credentials configured", supplier_code="ratehawk")
        token = await get_cached_token(db, ctx.organization_id, "ratehawk")
        adapter = RateHawkAdapter(creds.get("base_url", ""), token)
        if not token:
            auth = await adapter.authenticate(creds)
            if not auth.get("success"):
                raise SupplierAuthError(f"RateHawk auth failed: {auth.get('error')}", supplier_code="ratehawk")
            adapter.token = auth.get("token", "")
        return adapter, creds

    async def search(self, ctx: SupplierContext, request: SearchRequest) -> SearchResult:
        adapter, creds = await self._get_adapter(ctx)
        raw = await adapter.search_hotels({
            "checkin": request.check_in.isoformat() if request.check_in else "",
            "checkout": request.check_out.isoformat() if request.check_out else "",
            "destination": request.destination or "",
            "guests": [{"adults": request.adults, "children": request.children}],
            "currency": ctx.currency,
        })
        items = []
        if raw.get("success") and raw.get("products"):
            for p in raw["products"]:
                items.append(HotelSearchItem(
                    item_id=str(uuid.uuid4()),
                    supplier_code="ratehawk",
                    supplier_item_id=str(p.get("external_id", "")),
                    name=p.get("name", ""),
                    hotel_name=p.get("name", ""),
                    star_rating=p.get("star_rating", 0),
                    currency=p.get("currency", ctx.currency),
                    supplier_price=float(p.get("price", 0)),
                    sell_price=float(p.get("price", 0)) * 1.12,
                    address=p.get("location", ""),
                    available=True,
                    check_in=request.check_in,
                    check_out=request.check_out,
                    fetched_at=_now(),
                    supplier_metadata={"raw": p.get("raw", {})},
                ))
        elif not raw.get("success"):
            raise SupplierError(raw.get("error", "Search failed"), supplier_code="ratehawk", retryable=True)
        return SearchResult(
            request_id=ctx.request_id,
            product_type=SupplierProductType.HOTEL,
            total_items=len(items),
            items=items,
            suppliers_queried=["ratehawk"],
        )

    async def confirm_booking(self, ctx: SupplierContext, request: ConfirmRequest) -> ConfirmResult:
        adapter, _ = await self._get_adapter(ctx)
        raw = await adapter.create_booking({"partner_order_id": request.hold_id, "payment_reference": request.payment_reference})
        if raw.get("success"):
            bk = raw.get("booking", raw.get("data", {}))
            return ConfirmResult(
                supplier_code="ratehawk", supplier_booking_id=str(bk.get("external_booking_id", request.hold_id)),
                status="confirmed", confirmation_code=str(bk.get("external_booking_id", "")),
                confirmed_at=_now(), supplier_metadata=bk,
            )
        raise SupplierError(raw.get("error", "Booking failed"), supplier_code="ratehawk")

    async def cancel_booking(self, ctx: SupplierContext, request: CancelRequest) -> CancelResult:
        adapter, _ = await self._get_adapter(ctx)
        raw = await adapter.cancel_booking({"booking_id": request.supplier_booking_id})
        return CancelResult(
            supplier_code="ratehawk", supplier_booking_id=request.supplier_booking_id,
            status="cancelled" if raw.get("success") else "failed",
            cancelled_at=_now() if raw.get("success") else None,
        )


# ---------------------------------------------------------------------------
# TBO Bridge (Hotel + Flight + Tour)
# ---------------------------------------------------------------------------

class RealTBOBridge(SupplierAdapter):
    supplier_code = "tbo"
    supplier_type = SupplierType.HOTEL  # primary type
    display_name = "TBO Holidays API"
    supported_methods = {
        LifecycleMethod.HEALTHCHECK,
        LifecycleMethod.SEARCH,
        LifecycleMethod.CONFIRM,
        LifecycleMethod.CANCEL,
    }

    capability = SupplierCapabilityInfo(
        supplier_code="tbo",
        product_types=["hotel", "flight", "tour"],
        supports_hold=False,
        supports_direct_confirm=True,
        supports_cancel=True,
        supports_pricing_check=False,
        requires_precheck=False,
    )

    def __init__(self, db=None):
        self.db = db

    async def _get_adapter(self, ctx: SupplierContext):
        from app.suppliers.adapters.tbo_adapter import TBOAdapter
        from app.domain.suppliers.supplier_credentials_service import get_decrypted_credentials, get_cached_token
        db = self.db
        if db is None:
            from app.db import get_db_sync
            db = get_db_sync()
        creds = await get_decrypted_credentials(db, ctx.organization_id, "tbo")
        if not creds:
            raise SupplierAuthError("No TBO credentials configured", supplier_code="tbo")
        token = await get_cached_token(db, ctx.organization_id, "tbo")
        adapter = TBOAdapter(creds.get("base_url", ""), token)
        if not token:
            auth = await adapter.authenticate(creds)
            if not auth.get("success"):
                raise SupplierAuthError(f"TBO auth failed: {auth.get('error')}", supplier_code="tbo")
            adapter.token = auth.get("token", "")
        return adapter, creds

    async def search(self, ctx: SupplierContext, request: SearchRequest) -> SearchResult:
        adapter, _ = await self._get_adapter(ctx)
        pt = request.product_type.value if request.product_type else "hotel"
        items = []
        if pt == "hotel":
            raw = await adapter.search_hotels({
                "checkin": request.check_in.isoformat() if request.check_in else "",
                "checkout": request.check_out.isoformat() if request.check_out else "",
                "destination": request.destination or "",
                "rooms": [{"Adults": request.adults, "Children": request.children}],
            })
            if raw.get("success") and raw.get("products"):
                for p in raw["products"]:
                    items.append(HotelSearchItem(
                        item_id=str(uuid.uuid4()), supplier_code="tbo",
                        supplier_item_id=str(p.get("external_id", "")),
                        name=p.get("name", ""), hotel_name=p.get("name", ""),
                        star_rating=p.get("star_rating", 0),
                        currency=p.get("currency", ctx.currency),
                        supplier_price=float(p.get("price", 0)),
                        sell_price=float(p.get("price", 0)) * 1.12,
                        address=p.get("location", ""),
                        available=True, check_in=request.check_in, check_out=request.check_out,
                        fetched_at=_now(), supplier_metadata={"raw": p.get("raw", {})},
                    ))
        elif pt == "flight":
            raw = await adapter.search_flights({
                "origin": request.origin or "",
                "destination": request.destination or "",
                "departure_date": request.departure_date.isoformat() if request.departure_date else "",
                "return_date": request.return_date.isoformat() if request.return_date else "",
                "adults": request.adults, "children": request.children,
            })
            if raw.get("success") and raw.get("products"):
                for p in raw["products"]:
                    items.append(FlightSearchItem(
                        item_id=str(uuid.uuid4()), supplier_code="tbo",
                        supplier_item_id=str(p.get("external_id", "")),
                        name=p.get("name", ""), airline=p.get("airline", ""),
                        currency=p.get("currency", ctx.currency),
                        supplier_price=float(p.get("price", 0)),
                        sell_price=float(p.get("price", 0)) * 1.10,
                        available=True, fetched_at=_now(),
                        supplier_metadata={"raw": p.get("raw", {})},
                    ))
        elif pt == "tour":
            raw = await adapter.search_tours({
                "destination": request.destination or "",
                "start_date": request.check_in.isoformat() if request.check_in else "",
                "end_date": request.check_out.isoformat() if request.check_out else "",
                "adults": request.adults, "children": request.children,
            })
            if raw.get("success") and raw.get("products"):
                for p in raw["products"]:
                    items.append(TourSearchItem(
                        item_id=str(uuid.uuid4()), supplier_code="tbo",
                        supplier_item_id=str(p.get("external_id", "")),
                        name=p.get("name", ""),
                        currency=p.get("currency", ctx.currency),
                        supplier_price=float(p.get("price", 0)),
                        sell_price=float(p.get("price", 0)) * 1.12,
                        available=True, fetched_at=_now(),
                        supplier_metadata={"raw": p.get("raw", {})},
                    ))
        return SearchResult(
            request_id=ctx.request_id,
            product_type=request.product_type or SupplierProductType.HOTEL,
            total_items=len(items), items=items, suppliers_queried=["tbo"],
        )

    async def confirm_booking(self, ctx: SupplierContext, request: ConfirmRequest) -> ConfirmResult:
        adapter, _ = await self._get_adapter(ctx)
        raw = await adapter.create_booking({"BookingId": request.hold_id, "PaymentRef": request.payment_reference})
        if raw.get("success"):
            bk = raw.get("booking", raw.get("data", {}))
            return ConfirmResult(
                supplier_code="tbo", supplier_booking_id=str(bk.get("external_booking_id", request.hold_id)),
                status="confirmed", confirmed_at=_now(), supplier_metadata=bk,
            )
        raise SupplierError(raw.get("error", "TBO booking failed"), supplier_code="tbo")

    async def cancel_booking(self, ctx: SupplierContext, request: CancelRequest) -> CancelResult:
        adapter, _ = await self._get_adapter(ctx)
        raw = await adapter.cancel_booking({"booking_id": request.supplier_booking_id})
        return CancelResult(
            supplier_code="tbo", supplier_booking_id=request.supplier_booking_id,
            status="cancelled" if raw.get("success") else "failed",
            cancelled_at=_now() if raw.get("success") else None,
        )


# ---------------------------------------------------------------------------
# Paximum Bridge (Hotel + Transfer + Activity)
# ---------------------------------------------------------------------------

class RealPaximumBridge(SupplierAdapter):
    supplier_code = "paximum"
    supplier_type = SupplierType.HOTEL
    display_name = "Paximum Travel API"
    supported_methods = {
        LifecycleMethod.HEALTHCHECK,
        LifecycleMethod.SEARCH,
        LifecycleMethod.CONFIRM,
        LifecycleMethod.CANCEL,
    }

    capability = SupplierCapabilityInfo(
        supplier_code="paximum",
        product_types=["hotel", "transfer", "activity"],
        supports_hold=False,
        supports_direct_confirm=True,
        supports_cancel=True,
        supports_pricing_check=True,
        requires_precheck=False,
    )

    def __init__(self, db=None):
        self.db = db

    async def _get_adapter(self, ctx: SupplierContext):
        from app.suppliers.adapters.paximum_adapter import PaximumAdapter
        from app.domain.suppliers.supplier_credentials_service import get_decrypted_credentials, get_cached_token
        db = self.db
        if db is None:
            from app.db import get_db_sync
            db = get_db_sync()
        creds = await get_decrypted_credentials(db, ctx.organization_id, "paximum")
        if not creds:
            raise SupplierAuthError("No Paximum credentials configured", supplier_code="paximum")
        token = await get_cached_token(db, ctx.organization_id, "paximum")
        adapter = PaximumAdapter(creds.get("base_url", ""), token)
        if not token:
            auth = await adapter.authenticate(creds)
            if not auth.get("success"):
                raise SupplierAuthError(f"Paximum auth failed: {auth.get('error')}", supplier_code="paximum")
            adapter.token = auth.get("token", "")
        return adapter, creds

    async def search(self, ctx: SupplierContext, request: SearchRequest) -> SearchResult:
        adapter, _ = await self._get_adapter(ctx)
        pt = request.product_type.value if request.product_type else "hotel"
        items = []
        if pt == "hotel":
            raw = await adapter.search_hotels({
                "checkin": request.check_in.isoformat() if request.check_in else "",
                "checkout": request.check_out.isoformat() if request.check_out else "",
                "destination": request.destination or "",
                "currency": ctx.currency,
            })
            if raw.get("success") and raw.get("products"):
                for p in raw["products"]:
                    items.append(HotelSearchItem(
                        item_id=str(uuid.uuid4()), supplier_code="paximum",
                        supplier_item_id=str(p.get("external_id", "")),
                        name=p.get("name", ""), hotel_name=p.get("name", ""),
                        star_rating=p.get("star_rating", 0),
                        currency=p.get("currency", ctx.currency),
                        supplier_price=float(p.get("price", 0)),
                        sell_price=float(p.get("price", 0)) * 1.12,
                        available=True, check_in=request.check_in, check_out=request.check_out,
                        fetched_at=_now(), supplier_metadata={"raw": p.get("raw", {})},
                    ))
        elif pt == "transfer":
            raw = await adapter.search_transfers({
                "date": request.check_in.isoformat() if request.check_in else "",
                "from_location": request.origin or request.destination or "",
                "to_location": request.destination or "",
                "adults": request.adults, "children": request.children,
            })
            if raw.get("success") and raw.get("products"):
                for p in raw["products"]:
                    items.append(TransferSearchItem(
                        item_id=str(uuid.uuid4()), supplier_code="paximum",
                        supplier_item_id=str(p.get("external_id", "")),
                        name=p.get("name", ""),
                        currency=p.get("currency", ctx.currency),
                        supplier_price=float(p.get("price", 0)),
                        sell_price=float(p.get("price", 0)) * 1.10,
                        pickup_location=request.origin or "", dropoff_location=request.destination or "",
                        available=True, fetched_at=_now(),
                        supplier_metadata={"raw": p.get("raw", {})},
                    ))
        elif pt == "activity":
            raw = await adapter.search_activities({
                "destination": request.destination or "",
                "start_date": request.check_in.isoformat() if request.check_in else "",
                "adults": request.adults, "children": request.children,
            })
            if raw.get("success") and raw.get("products"):
                for p in raw["products"]:
                    items.append(ActivitySearchItem(
                        item_id=str(uuid.uuid4()), supplier_code="paximum",
                        supplier_item_id=str(p.get("external_id", "")),
                        name=p.get("name", ""),
                        currency=p.get("currency", ctx.currency),
                        supplier_price=float(p.get("price", 0)),
                        sell_price=float(p.get("price", 0)) * 1.12,
                        available=True, fetched_at=_now(),
                        supplier_metadata={"raw": p.get("raw", {})},
                    ))
        return SearchResult(
            request_id=ctx.request_id,
            product_type=request.product_type or SupplierProductType.HOTEL,
            total_items=len(items), items=items, suppliers_queried=["paximum"],
        )

    async def confirm_booking(self, ctx: SupplierContext, request: ConfirmRequest) -> ConfirmResult:
        adapter, _ = await self._get_adapter(ctx)
        raw = await adapter.create_booking({"offerId": request.hold_id})
        if raw.get("success"):
            bk = raw.get("booking", raw.get("data", {}))
            return ConfirmResult(
                supplier_code="paximum", supplier_booking_id=str(bk.get("external_booking_id", request.hold_id)),
                status="confirmed", confirmed_at=_now(), supplier_metadata=bk,
            )
        raise SupplierError(raw.get("error", "Paximum booking failed"), supplier_code="paximum")

    async def cancel_booking(self, ctx: SupplierContext, request: CancelRequest) -> CancelResult:
        adapter, _ = await self._get_adapter(ctx)
        raw = await adapter.cancel_booking({"booking_id": request.supplier_booking_id})
        return CancelResult(
            supplier_code="paximum", supplier_booking_id=request.supplier_booking_id,
            status="cancelled" if raw.get("success") else "failed",
            cancelled_at=_now() if raw.get("success") else None,
        )


# ---------------------------------------------------------------------------
# WWTatil Bridge (Tour)
# ---------------------------------------------------------------------------

class RealWWTatilBridge(SupplierAdapter):
    supplier_code = "wwtatil"
    supplier_type = SupplierType.TOUR
    display_name = "WWTatil Tour API"
    supported_methods = {
        LifecycleMethod.HEALTHCHECK,
        LifecycleMethod.SEARCH,
        LifecycleMethod.CONFIRM,
        LifecycleMethod.CANCEL,
    }

    capability = SupplierCapabilityInfo(
        supplier_code="wwtatil",
        product_types=["tour"],
        supports_hold=True,  # basket = hold
        supports_direct_confirm=False,
        supports_cancel=True,
        supports_pricing_check=False,
        requires_precheck=False,
    )

    def __init__(self, db=None):
        self.db = db

    async def _get_adapter(self, ctx: SupplierContext):
        from app.suppliers.adapters.wwtatil_adapter import WWTatilAdapter
        from app.domain.suppliers.supplier_credentials_service import get_decrypted_credentials, get_cached_token
        db = self.db
        if db is None:
            from app.db import get_db_sync
            db = get_db_sync()
        creds = await get_decrypted_credentials(db, ctx.organization_id, "wwtatil")
        if not creds:
            raise SupplierAuthError("No WWTatil credentials configured", supplier_code="wwtatil")
        token = await get_cached_token(db, ctx.organization_id, "wwtatil")
        adapter = WWTatilAdapter(creds.get("base_url", ""), token)
        if not token:
            auth = await adapter.authenticate(creds)
            if not auth.get("success"):
                raise SupplierAuthError(f"WWTatil auth failed: {auth.get('error')}", supplier_code="wwtatil")
            adapter.token = auth.get("token", "")
        return adapter, creds

    async def search(self, ctx: SupplierContext, request: SearchRequest) -> SearchResult:
        adapter, creds = await self._get_adapter(ctx)
        agency_id = int(creds.get("agency_id", 0))
        raw = await adapter.search_tours({
            "agency_id": agency_id,
            "start_date": request.check_in.isoformat() if request.check_in else "",
            "end_date": request.check_out.isoformat() if request.check_out else "",
            "adults": request.adults, "children": request.children,
        })
        items = []
        if raw.get("success") and raw.get("products"):
            for p in raw["products"]:
                items.append(TourSearchItem(
                    item_id=str(uuid.uuid4()), supplier_code="wwtatil",
                    supplier_item_id=str(p.get("external_id", "")),
                    name=p.get("name", ""),
                    currency=p.get("currency", "TRY"),
                    supplier_price=float(p.get("price", 0)),
                    sell_price=float(p.get("price", 0)) * 1.10,
                    available=True, departure_date=request.check_in, return_date=request.check_out,
                    fetched_at=_now(), supplier_metadata={"raw": p.get("raw", {})},
                ))
        return SearchResult(
            request_id=ctx.request_id,
            product_type=SupplierProductType.TOUR,
            total_items=len(items), items=items, suppliers_queried=["wwtatil"],
        )

    async def create_hold(self, ctx: SupplierContext, request: HoldRequest) -> HoldResult:
        """WWTatil uses basket as hold mechanism."""
        adapter, creds = await self._get_adapter(ctx)
        agency_id = int(creds.get("agency_id", 0))
        # The hold_id in wwtatil = basket_id returned after add_basket_item
        # For the bridge, we create a basket with minimal info
        raw = await adapter.add_basket_item(
            agency_id=agency_id, reference_number=str(uuid.uuid4())[:8],
            product_id=int(request.supplier_item_id) if request.supplier_item_id.isdigit() else 0,
            product_type_id=1, product_period_id=0,
            price=str(request.pricing_snapshot.total) if request.pricing_snapshot else "0",
            currency_code="TRY", customers=[], billing_details={},
        )
        if raw.get("success"):
            basket_data = raw.get("data", {})
            basket_id = str(basket_data.get("BasketId", basket_data.get("Id", "")))
            return HoldResult(
                supplier_code="wwtatil", hold_id=basket_id,
                status="held", supplier_metadata=basket_data,
            )
        raise SupplierError(raw.get("error", "WWTatil basket creation failed"), supplier_code="wwtatil")

    async def confirm_booking(self, ctx: SupplierContext, request: ConfirmRequest) -> ConfirmResult:
        adapter, creds = await self._get_adapter(ctx)
        agency_id = int(creds.get("agency_id", 0))
        raw = await adapter.create_booking({
            "agency_id": agency_id,
            "basket_id": int(request.hold_id) if request.hold_id.isdigit() else 0,
            "tracking_number": request.idempotency_key[:20],
            "price": request.payment_reference or "0",
        })
        if raw.get("success"):
            bk = raw.get("booking", raw.get("data", {}))
            return ConfirmResult(
                supplier_code="wwtatil",
                supplier_booking_id=str(bk.get("external_booking_id", bk.get("BookingId", ""))),
                status="confirmed", confirmed_at=_now(), supplier_metadata=bk,
            )
        raise SupplierError(raw.get("error", "WWTatil booking failed"), supplier_code="wwtatil")

    async def cancel_booking(self, ctx: SupplierContext, request: CancelRequest) -> CancelResult:
        adapter, _ = await self._get_adapter(ctx)
        raw = await adapter.cancel_booking({
            "BookingId": int(request.supplier_booking_id) if request.supplier_booking_id.isdigit() else 0,
            "CancelTypeId": 1,
        })
        return CancelResult(
            supplier_code="wwtatil", supplier_booking_id=request.supplier_booking_id,
            status="cancelled" if raw.get("success") else "failed",
            cancelled_at=_now() if raw.get("success") else None,
        )
