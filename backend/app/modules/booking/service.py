"""Booking State Transition Service — THE SINGLE POINT for all booking status changes.

No router, no other service may change booking.status directly.
Everything flows through BookingTransitionService.transition().

Responsibilities per transition:
1. Read booking
2. Tenant check
3. Optimistic lock / version check
4. Command → target status resolution
5. Transition validation (structural)
6. Policy validation (business rules)
7. Booking update (atomic with version increment)
8. Booking history append
9. Outbox event write
10. Audit log write
11. Return updated booking
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from typing import Any

from bson import ObjectId

from app.modules.booking.errors import (
    BookingNotFoundError,
    InvalidTransitionError,
    VersionConflictError,
)
from app.modules.booking.models import (
    COMMAND_TO_EVENT,
    COMMAND_TO_TARGET,
    is_valid_transition,
)
from app.modules.booking.policies import BookingPolicyService
from app.utils import now_utc

logger = logging.getLogger("booking.transition")


@dataclass
class ActorContext:
    user_id: str = ""
    email: str = ""
    actor_type: str = "user"  # user | system | supplier


class BookingTransitionService:
    """Central, atomic booking state transition service."""

    def __init__(self, db):
        self.db = db
        self.policy = BookingPolicyService()

    # ── Public API ────────────────────────────────────────────

    async def transition(
        self,
        booking_id: str,
        command: str,
        actor: ActorContext,
        *,
        tenant_id: str = "",
        organization_id: str = "",
        payload: dict[str, Any] | None = None,
        reason: str = "",
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        """Execute a booking command (the ONLY way to change booking status).

        Returns the updated booking document (without _id).
        """
        payload = payload or {}
        now = now_utc()

        # 1. Read booking
        booking = await self._read_booking(booking_id, organization_id)

        # 2. Tenant check — organization_id is the primary isolation.
        #    tenant_id is a secondary subdivision; only enforce when both
        #    the booking and request have meaningful, non-org tenant IDs.
        booking_tenant = booking.get("tenant_id", "")
        if (
            tenant_id
            and booking_tenant
            and tenant_id != booking_tenant
            and booking_tenant != organization_id
        ):
            raise BookingNotFoundError(booking_id)

        # 3. Idempotency check
        if idempotency_key:
            existing = await self.db.booking_history.find_one(
                {
                    "booking_id": booking_id,
                    "command": command,
                    "idempotency_key": idempotency_key,
                },
                {"_id": 0},
            )
            if existing:
                # Return current booking state — operation already applied
                return await self._read_booking_clean(booking_id, organization_id)

        current_status = booking.get("status", "draft")
        current_version = booking.get("version", 0)
        target_status = COMMAND_TO_TARGET.get(command)

        # 4. For fulfillment commands (mark_ticketed, mark_vouchered)
        if target_status is None:
            return await self._handle_fulfillment_command(
                booking, booking_id, command, actor, organization_id, payload, reason, idempotency_key, now
            )

        # 5. Structural validation
        if not is_valid_transition(current_status, target_status):
            raise InvalidTransitionError(current_status, target_status)

        # 6. Business policy validation
        self.policy.validate_command(command, booking)

        # 7. Atomic update with optimistic lock
        event_type = COMMAND_TO_EVENT.get(command, f"booking.{command}")
        event_id = str(uuid.uuid4())

        update_fields: dict[str, Any] = {
            "status": target_status,
            "status_changed_at": now,
            "status_changed_by": {
                "user_id": actor.user_id,
                "email": actor.email,
                "type": actor.actor_type,
            },
            "updated_at": now,
        }

        # Set timestamp fields for specific transitions
        ts_field = f"{target_status}_at"
        update_fields[ts_field] = now

        # Apply any extra payload fields
        for key in ("cancellation_reason", "notes", "metadata"):
            if key in payload:
                update_fields[key] = payload[key]
        if reason:
            update_fields["last_transition_reason"] = reason

        try:
            oid = ObjectId(booking_id)
        except Exception:
            raise BookingNotFoundError(booking_id)

        result = await self.db.bookings.update_one(
            {
                "_id": oid,
                "organization_id": organization_id,
                "version": current_version,
            },
            {
                "$set": update_fields,
                "$inc": {"version": 1},
            },
        )

        if result.matched_count == 0:
            raise VersionConflictError(booking_id, current_version)

        # 8. History
        await self._write_history(
            booking_id=booking_id,
            organization_id=organization_id,
            tenant_id=tenant_id or booking.get("tenant_id", ""),
            from_status=current_status,
            to_status=target_status,
            command=command,
            reason=reason,
            actor=actor,
            metadata=payload,
            idempotency_key=idempotency_key,
            now=now,
        )

        # 9. Outbox event
        await self._write_outbox(
            event_id=event_id,
            event_type=event_type,
            booking_id=booking_id,
            organization_id=organization_id,
            tenant_id=tenant_id or booking.get("tenant_id", ""),
            version=current_version + 1,
            actor=actor,
            data={
                "status": target_status,
                "from_status": current_status,
                "payment_status": booking.get("payment_status", "unpaid"),
                "fulfillment_status": booking.get("fulfillment_status", "none"),
            },
            now=now,
        )

        # 10. Audit log
        await self._write_audit(
            booking_id=booking_id,
            organization_id=organization_id,
            actor=actor,
            action=f"booking.{command}",
            before={"status": current_status},
            after={"status": target_status},
            now=now,
        )

        logger.info(
            "Booking %s: %s -> %s [command=%s, actor=%s]",
            booking_id, current_status, target_status, command, actor.email or actor.user_id,
        )

        # 11. Return clean document
        return await self._read_booking_clean(booking_id, organization_id)

    # ── Fulfillment commands ──────────────────────────────────

    async def _handle_fulfillment_command(
        self,
        booking: dict,
        booking_id: str,
        command: str,
        actor: ActorContext,
        organization_id: str,
        payload: dict,
        reason: str,
        idempotency_key: str | None,
        now,
    ) -> dict[str, Any]:
        """Handle mark_ticketed / mark_vouchered without changing main status."""
        current_fulfillment = booking.get("fulfillment_status", "none")

        if command == "mark_ticketed":
            new_fulfillment = "both" if current_fulfillment == "vouchered" else "ticketed"
        elif command == "mark_vouchered":
            new_fulfillment = "both" if current_fulfillment == "ticketed" else "vouchered"
        else:
            new_fulfillment = current_fulfillment

        current_version = booking.get("version", 0)
        event_type = COMMAND_TO_EVENT.get(command, f"booking.{command}")
        event_id = str(uuid.uuid4())

        try:
            oid = ObjectId(booking_id)
        except Exception:
            raise BookingNotFoundError(booking_id)

        result = await self.db.bookings.update_one(
            {
                "_id": oid,
                "organization_id": organization_id,
                "version": current_version,
            },
            {
                "$set": {
                    "fulfillment_status": new_fulfillment,
                    "updated_at": now,
                },
                "$inc": {"version": 1},
            },
        )

        if result.matched_count == 0:
            raise VersionConflictError(booking_id, current_version)

        # History
        await self._write_history(
            booking_id=booking_id,
            organization_id=organization_id,
            tenant_id=booking.get("tenant_id", ""),
            from_status=booking.get("status", "draft"),
            to_status=booking.get("status", "draft"),
            command=command,
            reason=reason,
            actor=actor,
            metadata={"fulfillment_from": current_fulfillment, "fulfillment_to": new_fulfillment},
            idempotency_key=idempotency_key,
            now=now,
        )

        # Outbox
        await self._write_outbox(
            event_id=event_id,
            event_type=event_type,
            booking_id=booking_id,
            organization_id=organization_id,
            tenant_id=booking.get("tenant_id", ""),
            version=current_version + 1,
            actor=actor,
            data={
                "status": booking.get("status", "draft"),
                "fulfillment_status": new_fulfillment,
            },
            now=now,
        )

        logger.info(
            "Booking %s fulfillment: %s -> %s [command=%s]",
            booking_id, current_fulfillment, new_fulfillment, command,
        )

        return await self._read_booking_clean(booking_id, organization_id)

    # ── Internals ─────────────────────────────────────────────

    async def _read_booking(self, booking_id: str, organization_id: str) -> dict:
        try:
            oid = ObjectId(booking_id)
        except Exception:
            raise BookingNotFoundError(booking_id)

        booking = await self.db.bookings.find_one(
            {"_id": oid, "organization_id": organization_id},
        )
        if not booking:
            raise BookingNotFoundError(booking_id)
        return booking

    async def _read_booking_clean(self, booking_id: str, organization_id: str) -> dict:
        """Read booking without _id for safe serialization."""
        try:
            oid = ObjectId(booking_id)
        except Exception:
            raise BookingNotFoundError(booking_id)

        booking = await self.db.bookings.find_one(
            {"_id": oid, "organization_id": organization_id},
            {"_id": 0},
        )
        if not booking:
            raise BookingNotFoundError(booking_id)
        # Inject booking_id as string for convenience
        booking["booking_id"] = booking_id
        return booking

    async def _write_history(
        self,
        *,
        booking_id: str,
        organization_id: str,
        tenant_id: str,
        from_status: str,
        to_status: str,
        command: str,
        reason: str,
        actor: ActorContext,
        metadata: dict | None,
        idempotency_key: str | None,
        now,
    ) -> None:
        doc = {
            "booking_id": booking_id,
            "organization_id": organization_id,
            "tenant_id": tenant_id,
            "from_status": from_status,
            "to_status": to_status,
            "command": command,
            "reason": reason,
            "metadata": metadata or {},
            "actor": {
                "user_id": actor.user_id,
                "email": actor.email,
                "type": actor.actor_type,
            },
            "idempotency_key": idempotency_key,
            "occurred_at": now,
        }
        try:
            await self.db.booking_history.insert_one(doc)
        except Exception as e:
            logger.warning("Failed to write booking history for %s: %s", booking_id, e)

    async def _write_outbox(
        self,
        *,
        event_id: str,
        event_type: str,
        booking_id: str,
        organization_id: str,
        tenant_id: str,
        version: int,
        actor: ActorContext,
        data: dict,
        now,
    ) -> None:
        doc = {
            "_id": event_id,
            "aggregate_type": "booking",
            "aggregate_id": booking_id,
            "organization_id": organization_id,
            "tenant_id": tenant_id,
            "event_type": event_type,
            "payload": {
                "event_id": event_id,
                "event_type": event_type,
                "occurred_at": now.isoformat() if hasattr(now, "isoformat") else str(now),
                "tenant_id": tenant_id,
                "booking_id": booking_id,
                "version": version,
                "actor": {
                    "user_id": actor.user_id,
                    "email": actor.email,
                    "type": actor.actor_type,
                },
                "data": data,
            },
            "status": "pending",
            "retry_count": 0,
            "created_at": now,
            "published_at": None,
        }
        try:
            await self.db.outbox_events.insert_one(doc)
        except Exception as e:
            logger.warning("Failed to write outbox event for booking %s: %s", booking_id, e)

    async def _write_audit(
        self,
        *,
        booking_id: str,
        organization_id: str,
        actor: ActorContext,
        action: str,
        before: dict,
        after: dict,
        now,
    ) -> None:
        try:
            from app.services.audit import write_audit_log
            await write_audit_log(
                self.db,
                organization_id=organization_id,
                actor={"id": actor.user_id, "email": actor.email, "type": actor.actor_type},
                request=None,
                action=action,
                target_type="booking",
                target_id=booking_id,
                before=before,
                after=after,
                meta={},
            )
        except Exception as e:
            logger.warning("Failed to write audit for booking %s: %s", booking_id, e)
