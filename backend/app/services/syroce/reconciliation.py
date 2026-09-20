"""Read-only PMS recovery of ambiguous marketplace bookings; never resubmit."""

from __future__ import annotations

import asyncio
import logging
import math
import os
import uuid
from datetime import datetime, timedelta, timezone

from pymongo import ReturnDocument

from app.services.syroce.agent import SyroceAgentClient

logger = logging.getLogger(__name__)
COLLECTION = "agency_reservations"


def _matches(summary, local, agency_id):
    return (
        isinstance(summary, dict)
        and isinstance(summary.get("id"), str)
        and bool(summary["id"].strip())
        and summary.get("agency_id") == agency_id
        and summary.get("tenant_id") == local.get("syroce_tenant_id")
        and summary.get("external_reference") == local.get("external_reference")
        and all(
            summary.get(k) == local.get(k)
            for k in ("check_in", "check_out", "guest_name")
        )
    )


async def verified_update(client, local):
    """None means unknown, never rejection. Require two consistent PMS reads."""
    if not client.syroce_agency_id or not all(
        local.get(k)
        for k in (
            "external_reference",
            "syroce_tenant_id",
            "check_in",
            "check_out",
            "guest_name",
        )
    ):
        return None
    response = await client.list_reservations_for_reconciliation(
        tenant_id=local["syroce_tenant_id"],
        check_in=local["check_in"],
    )
    rows = response.get("reservations")
    # The existing PMS endpoint has no pagination. At its cap completeness is
    # unknown: even a visible match must not hide a second matching booking.
    if (
        not isinstance(rows, list)
        or len(rows) >= 500
        or response.get("total") != len(rows)
    ):
        return None
    if any(not isinstance(row, dict) for row in rows):
        return None
    matches = [
        r for r in rows if r.get("external_reference") == local["external_reference"]
    ]
    if len(matches) != 1 or not _matches(matches[0], local, client.syroce_agency_id):
        return None
    detail = await client.get_reservation(matches[0]["id"])
    summary, booking = detail.get("summary"), detail.get("booking")
    if not _matches(summary, local, client.syroce_agency_id) or not isinstance(
        booking, dict
    ):
        return None
    if summary["id"] != matches[0]["id"] or booking.get("id") != summary["id"]:
        return None
    status = summary.get("status")
    if status not in {"confirmed", "cancelled"} or booking.get("status") != status:
        return None
    if booking.get("marketplace_agency_id") != client.syroce_agency_id:
        return None
    if booking.get("external_reference") != local["external_reference"]:
        return None
    for key in ("guest_name", "guest_email", "guest_phone"):
        if booking.get(key) != str(local.get(key) or "").strip():
            return None
    for key in ("room_type", "adults", "children"):
        if booking.get(key) != local.get(key):
            return None
    if (booking.get("special_requests") or "") != (local.get("special_requests") or ""):
        return None
    for key in ("check_in", "check_out"):
        value = booking.get(key)
        if not isinstance(value, str) or value.split("T")[0] != local[key]:
            return None
    amounts = {}
    for source, target, booking_key in (
        ("total_amount", "total_amount", "total_amount"),
        ("commission_pct", "commission_rate", "agency_commission_rate"),
        ("commission_amount", "commission_amount", "agency_commission_amount"),
        ("net_to_hotel", "net_to_hotel", "net_to_hotel"),
    ):
        value = summary.get(source)
        if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
            return None
        if booking.get(booking_key) != value:
            return None
        amounts[target] = value
    return {
        **amounts,
        "status": status,
        "syroce_reservation_id": summary["id"],
        "syroce_confirmation_code": summary.get("confirmation_code"),
        "room_number": booking.get("room_number"),
        "reconciliation_required": False,
    }


async def reconcile_one(db, *, now=None, client_factory=None):
    now = now or datetime.now(timezone.utc)
    collection = db[COLLECTION]
    token = uuid.uuid4().hex
    # Expiring claim survives process crashes and serializes concurrent workers.
    local = await collection.find_one_and_update(
        {
            "channel": "syroce_marketplace",
            "status": "pending",
            "created_at": {"$lte": now - timedelta(minutes=2)},
            "$and": [
                {
                    "$or": [
                        {"reconciliation_next_at": {"$exists": False}},
                        {"reconciliation_next_at": {"$lte": now}},
                    ]
                },
                {
                    "$or": [
                        {"reconciliation_lease_until": {"$exists": False}},
                        {"reconciliation_lease_until": {"$lte": now}},
                    ]
                },
            ],
        },
        {
            "$set": {
                "reconciliation_token": token,
                "reconciliation_lease_until": now + timedelta(minutes=2),
            }
        },
        sort=[("reconciliation_next_at", 1), ("created_at", 1)],
        return_document=ReturnDocument.AFTER,
    )
    if not local:
        return False
    outcome, update = "unresolved", None
    try:
        if local.get("organization_id"):
            factory = client_factory or SyroceAgentClient.from_organization_id
            client = await factory(local["organization_id"])
            update = await verified_update(client, local)
    except Exception:
        # Do not persist response bodies, guest data, or credentials in errors.
        outcome = "lookup_failed"
    finished = datetime.now(timezone.utc)
    fields = {
        "reconciliation_required": True,
        "reconciliation_checked_at": finished,
        "reconciliation_next_at": finished + timedelta(minutes=5),
        "reconciliation_outcome": outcome,
    }
    if update:
        fields.update(update, updated_at=finished, reconciliation_outcome="verified")
    await collection.update_one(
        {
            "id": local["id"],
            "organization_id": local.get("organization_id"),
            "status": "pending",
            "reconciliation_token": token,
            "reconciliation_lease_until": {"$gt": finished},
        },
        {
            "$set": fields,
            "$unset": {"reconciliation_token": "", "reconciliation_lease_until": ""},
            "$inc": {"reconciliation_attempts": 1},
            "$push": {
                "reconciliation_history": {
                    "$each": [
                        {
                            "at": finished,
                            "outcome": fields["reconciliation_outcome"],
                        }
                    ],
                    "$slice": -20,
                }
            },
        },
    )
    return True


async def run():
    from app.db import get_db

    indexed = False
    while True:
        try:
            if os.environ.get("SYROCE_BASE_URL"):
                db = await get_db()
                if not indexed:
                    await db[COLLECTION].create_index(
                        [
                            ("channel", 1),
                            ("status", 1),
                            ("reconciliation_next_at", 1),
                            ("created_at", 1),
                        ],
                        name="marketplace_reconciliation_due",
                    )
                    indexed = True
                for _ in range(50):
                    if not await reconcile_one(db):
                        break
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.warning("Marketplace reconciliation cycle failed; retrying later")
        await asyncio.sleep(60)
