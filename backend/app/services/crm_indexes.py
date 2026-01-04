from __future__ import annotations

import logging
import os
from typing import Any

from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger("acenta-master.crm-indexes")


async def ensure_crm_indexes(db: AsyncIOMotorDatabase) -> None:
    """Ensure MongoDB indexes for CRM collections (contacts, notes, tasks).

    Controlled by ENSURE_CRM_INDEXES env flag (default: true).
    - ENSURE_CRM_INDEXES in ["false", "0", "no", "off"] (case-insensitive) → NOOP
    - Otherwise: create indexes idempotently with fixed names.
    """

    flag = os.getenv("ENSURE_CRM_INDEXES", "true").strip().lower()
    if flag in {"false", "0", "no", "off"}:
        logger.info("ENSURE_CRM_INDEXES disabled; skipping CRM index creation")
        return

    logger.info("Ensuring CRM indexes for hotel_contacts, hotel_crm_notes, hotel_crm_tasks...")

    try:
        # hotel_contacts
        await db.hotel_contacts.create_index(
            [("organization_id", 1), ("hotel_id", 1)],
            name="hc_org_hotel_idx",
        )

        await db.hotel_contacts.create_index(
            [("organization_id", 1), ("email", 1)],
            name="hc_org_email_idx",
            unique=False,
            sparse=True,
        )

        await db.hotel_contacts.create_index(
            [("organization_id", 1), ("hotel_id", 1), ("is_primary", 1)],
            name="hc_org_hotel_primary_idx",
        )

        # hotel_crm_notes
        await db.hotel_crm_notes.create_index(
            [("organization_id", 1), ("hotel_id", 1), ("agency_id", 1), ("created_at", -1)],
            name="hnotes_org_hotel_agency_created_idx",
        )

        await db.hotel_crm_notes.create_index(
            [("organization_id", 1), ("created_by_user_id", 1), ("created_at", -1)],
            name="hnotes_org_creator_created_idx",
        )

        # hotel_crm_tasks
        await db.hotel_crm_tasks.create_index(
            [("organization_id", 1), ("assignee_user_id", 1), ("status", 1), ("due_date", 1)],
            name="htasks_org_assignee_status_due_idx",
        )

        await db.hotel_crm_tasks.create_index(
            [("organization_id", 1), ("hotel_id", 1), ("agency_id", 1), ("status", 1)],
            name="htasks_org_hotel_agency_status_idx",
        )

        # match_outcomes (soft outcome events for match risk reports)
        try:
            await db.match_outcomes.create_index(
                [("organization_id", 1), ("match_id", 1), ("marked_at", -1)],
                name="mo_org_match_marked_idx",
            )

            await db.match_outcomes.create_index(
                [("organization_id", 1), ("marked_at", -1)],
                name="mo_org_marked_idx",
            )

            await db.match_outcomes.create_index(
                [("organization_id", 1), ("to_hotel_id", 1), ("marked_at", -1)],
                name="mo_org_to_hotel_marked_idx",
            )
        except Exception:
            logger.exception("Failed to ensure match_outcomes indexes")

        logger.info("CRM indexes ensured successfully")
    except Exception:
        # Do not crash the app on index errors; just log for investigation.
        logger.exception("Failed to ensure CRM indexes")
