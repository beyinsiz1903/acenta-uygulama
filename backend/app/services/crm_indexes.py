from __future__ import annotations

import logging
import os

from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo.errors import OperationFailure

logger = logging.getLogger("acenta-master.crm-indexes")


# Mongo can return a couple of different codes for index conflicts depending on
# version/cluster configuration. We treat these as *non-fatal* and simply skip
# re-creating the index so that deployments are idempotent across environments.
_INDEX_CONFLICT_CODES = {85, 86}


async def _safe_create_index(
    collection,
    keys,
    *,
    name: str,
    **kwargs,
) -> None:
    """Create an index in a deployment-safe, idempotent way.

    - If the index already exists (or has a compatible spec), Mongo/Atlas may
      raise OperationFailure with an IndexKeySpecsConflict code (e.g. 85/86).
      In that case we log at INFO level and continue without failing startup.
    - Any other error is logged and re-raised so it can be investigated.
    """

    try:
        await collection.create_index(keys, name=name, **kwargs)
    except OperationFailure as exc:  # pragma: no cover - depends on Atlas state
        if exc.code in _INDEX_CONFLICT_CODES:
            logger.info(
                "Index %s already exists or has a conflicting spec (code=%s); "
                "skipping create_index.",
                name,
                exc.code,
            )
            return
        logger.exception("OperationFailure while creating index %s", name)
        raise
    except Exception:  # pragma: no cover - unexpected
        logger.exception("Unexpected error while creating index %s", name)
        raise


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

    logger.info(
        "Ensuring CRM indexes for hotel_contacts, hotel_crm_notes, hotel_crm_tasks..."
    )

    try:
        # hotel_contacts
        await _safe_create_index(
            db.hotel_contacts,
            [("organization_id", 1), ("hotel_id", 1)],
            name="hc_org_hotel_idx",
        )

        await _safe_create_index(
            db.hotel_contacts,
            [("organization_id", 1), ("email", 1)],
            name="hc_org_email_idx",
            unique=False,
            sparse=True,
        )

        await _safe_create_index(
            db.hotel_contacts,
            [("organization_id", 1), ("hotel_id", 1), ("is_primary", 1)],
            name="hc_org_hotel_primary_idx",
        )

        # hotel_crm_notes
        await _safe_create_index(
            db.hotel_crm_notes,
            [
                ("organization_id", 1),
                ("hotel_id", 1),
                ("agency_id", 1),
                ("created_at", -1),
            ],
            name="hnotes_org_hotel_agency_created_idx",
        )

        await _safe_create_index(
            db.hotel_crm_notes,
            [
                ("organization_id", 1),
                ("created_by_user_id", 1),
                ("created_at", -1),
            ],
            name="hnotes_org_creator_created_idx",
        )

        # hotel_crm_tasks
        await _safe_create_index(
            db.hotel_crm_tasks,
            [
                ("organization_id", 1),
                ("assignee_user_id", 1),
                ("status", 1),
                ("due_date", 1),
            ],
            name="htasks_org_assignee_status_due_idx",
        )

        await _safe_create_index(
            db.hotel_crm_tasks,
            [
                ("organization_id", 1),
                ("hotel_id", 1),
                ("agency_id", 1),
                ("status", 1),
            ],
            name="htasks_org_hotel_agency_status_idx",
        )

        # match_outcomes (soft outcome events for match risk reports)
        try:
            await _safe_create_index(
                db.match_outcomes,
                [("organization_id", 1), ("match_id", 1), ("marked_at", -1)],
                name="mo_org_match_marked_idx",
            )

            await _safe_create_index(
                db.match_outcomes,
                [("organization_id", 1), ("marked_at", -1)],
                name="mo_org_marked_idx",
            )

            await _safe_create_index(
                db.match_outcomes,
                [
                    ("organization_id", 1),
                    ("to_hotel_id", 1),
                    ("marked_at", -1),
                ],
                name="mo_org_to_hotel_marked_idx",
            )
        except Exception:
            # Match outcomes indexes are non-critical; log but never fail startup.
            logger.exception("Failed to ensure match_outcomes indexes")

        logger.info("CRM indexes ensured successfully")
    except Exception:
        # Do not crash the app on index errors; just log for investigation.
        logger.exception("Failed to ensure CRM indexes")
