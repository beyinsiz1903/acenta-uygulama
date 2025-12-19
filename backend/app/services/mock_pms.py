from __future__ import annotations

import uuid
from typing import Any, Optional

from app.db import get_db
from app.services.hotel_availability import compute_availability
from app.services.pms_client import PmsClient, PmsError
from app.services.rate_pricing import compute_rate_for_stay
from app.utils import now_utc


class MockPmsClient(PmsClient):
    """Mock PMS adapter backed by the local DB.

    Behaves like an external system:
    - quote uses current local availability + rate pricing
    - create_booking re-checks quote to prevent overbooking/price mismatch
    - idempotent create using idempotency_key (draft_id)

    Collections used:
    - pms_idempotency: {_id, organization_id, idempotency_key, pms_booking_id, created_at}
    - pms_bookings: {_id, organization_id, status, ...}
    """

    async def quote(self, *, organization_id: str, channel: str, payload: dict[str, Any]) -> dict[str, Any]:
        hotel_id = payload.get("hotel_id")
        check_in = payload.get("check_in")
        check_out = payload.get("check_out")
        occupancy = payload.get("occupancy") or {"adults": 2, "children": 0}
        currency = payload.get("currency") or "TRY"

        if not hotel_id or not check_in or not check_out:
            raise PmsError(code="VALIDATION_ERROR", message="missing hotel_id/check_in/check_out", http_status=409)

        availability = await compute_availability(
            hotel_id=hotel_id,
            check_in=check_in,
            check_out=check_out,
            occupancy=occupancy,
            organization_id=organization_id,
            channel=channel,
        )

        # Attach rate plans per room type
        nights = int((availability.get("nights") or 0) or 0)
        rooms_out: list[dict[str, Any]] = []
        for r in availability.get("rooms") or []:
            room_type_id = r.get("room_type")
            room_type_name = r.get("room_type_name")
            max_occupancy = r.get("max_occupancy")

            # compute rates for this room type
            rates = await compute_rate_for_stay(
                tenant_id=hotel_id,
                room_type=room_type_id,
                check_in=check_in,
                check_out=check_out,
                nights=nights,
                organization_id=organization_id,
                currency=currency,
            )

            rooms_out.append(
                {
                    "room_type_id": room_type_id,
                    "name": room_type_name,
                    "max_occupancy": max_occupancy,
                    "inventory_left": r.get("available_rooms", 0),
                    "rate_plans": rates,
                }
            )

        # Response mirrors /api/agency/search output
        search_id = payload.get("search_id") or f"srch_{uuid.uuid4().hex[:16]}"
        return {
            "search_id": search_id,
            "hotel_id": hotel_id,
            "check_in": check_in,
            "check_out": check_out,
            "nights": nights,
            "currency": currency,
            "rooms": rooms_out,
            "source": "pms",
        }

    async def create_booking(
        self,
        *,
        organization_id: str,
        channel: str,
        idempotency_key: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        db = await get_db()

        # Idempotency
        idem = await db.pms_idempotency.find_one(
            {"organization_id": organization_id, "idempotency_key": idempotency_key}
        )
        if idem:
            return {"pms_booking_id": str(idem["pms_booking_id"]), "status": "created"}

        hotel_id = payload.get("hotel_id")
        agency_id = payload.get("agency_id")
        stay = payload.get("stay") or {}
        check_in = stay.get("check_in")
        check_out = stay.get("check_out")
        rate_snapshot = payload.get("rate_snapshot") or {}

        if not hotel_id or not agency_id or not check_in or not check_out:
            raise PmsError(code="VALIDATION_ERROR", message="missing fields", http_status=409)

        # Deterministic PRICE_CHANGED simulation (stable by idempotency key)
        try:
            if int(idempotency_key.replace("-", "")[-1], 16) % 20 == 0:
                raise PmsError(code="PRICE_CHANGED", message="price changed", http_status=409)
        except PmsError:
            raise
        except Exception:
            # ignore parse issues
            pass

        # Re-quote to prevent overbooking / price mismatch
        quote = await self.quote(
            organization_id=organization_id,
            channel=channel,
            payload={
                "hotel_id": hotel_id,
                "check_in": check_in,
                "check_out": check_out,
                "currency": (rate_snapshot.get("price") or {}).get("currency") or "TRY",
                "occupancy": payload.get("occupancy") or {"adults": 2, "children": 0},
            },
        )

        room_type_id = rate_snapshot.get("room_type_id")
        rate_plan_id = rate_snapshot.get("rate_plan_id")
        expected_total = float((rate_snapshot.get("price") or {}).get("total") or 0)

        room = next((x for x in quote.get("rooms") or [] if x.get("room_type_id") == room_type_id), None)
        if not room or int(room.get("inventory_left") or 0) <= 0:
            raise PmsError(code="NO_INVENTORY", message="no inventory", http_status=409)

        rp = next((x for x in room.get("rate_plans") or [] if x.get("rate_plan_id") == rate_plan_id), None)
        if not rp:
            raise PmsError(code="VALIDATION_ERROR", message="rate_plan not found", http_status=409)

        actual_total = float((rp.get("price") or {}).get("total") or 0)
        if round(actual_total, 2) != round(expected_total, 2):
            raise PmsError(code="PRICE_CHANGED", message="price changed", http_status=409)

        pms_booking_id = f"pms_{uuid.uuid4().hex[:16]}"

        await db.pms_bookings.insert_one(
            {
                "_id": pms_booking_id,
                "organization_id": organization_id,
                "hotel_id": hotel_id,
                "agency_id": agency_id,
                "status": "confirmed",
                "channel": channel,
                "stay": stay,
                "rate_snapshot": rate_snapshot,
                "created_at": now_utc(),
                "updated_at": now_utc(),
            }
        )

        await db.pms_idempotency.insert_one(
            {
                "_id": str(uuid.uuid4()),
                "organization_id": organization_id,
                "idempotency_key": idempotency_key,
                "pms_booking_id": pms_booking_id,
                "created_at": now_utc(),
            }
        )

        return {"pms_booking_id": pms_booking_id, "status": "created"}

    async def cancel_booking(
        self,
        *,
        organization_id: str,
        channel: str,
        pms_booking_id: str,
        reason: Optional[str] = None,
    ) -> dict[str, Any]:
        db = await get_db()
        doc = await db.pms_bookings.find_one({"organization_id": organization_id, "_id": pms_booking_id})
        if not doc:
            raise PmsError(code="NOT_FOUND", message="pms booking not found", http_status=404)

        await db.pms_bookings.update_one(
            {"_id": pms_booking_id},
            {"$set": {"status": "cancelled", "cancel_reason": reason, "updated_at": now_utc()}},
        )

        return {"pms_booking_id": pms_booking_id, "status": "cancelled"}
