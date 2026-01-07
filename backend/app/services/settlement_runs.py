from __future__ import annotations

"""Settlement Run Engine (Phase 2A.4)

Implements supplier settlement runs over supplier_accruals with:
- State machine: draft -> approved -> paid, cancelled
- Accrual locking via settlement_id + status=in_settlement
- Approval snapshot + immutability

NOTE: Payment ledger posting is implemented in Phase 2A.5; here we only
manage settlement state and accrual locking.
"""

from datetime import datetime
from typing import Any, Optional

from bson import ObjectId

from app.errors import AppError
from app.utils import now_utc


class SettlementRunService:
    def __init__(self, db):
        self.db = db

    # ---------------------------------------------------------------------
    # Helpers
    # ---------------------------------------------------------------------

    async def _load_run(self, organization_id: str, settlement_id: str) -> dict:
        try:
            oid = ObjectId(settlement_id)
        except Exception:
            raise AppError(
                status_code=404,
                code="settlement_not_found",
                message="Settlement not found",
            )

        doc = await self.db.settlement_runs.find_one(
            {"_id": oid, "organization_id": organization_id}
        )
        if not doc:
            raise AppError(
                status_code=404,
                code="settlement_not_found",
                message="Settlement not found",
            )
        return doc

    @staticmethod
    def _serialize_run(doc: dict) -> dict:
        return {
            "settlement_id": str(doc["_id"]),
            "organization_id": doc["organization_id"],
            "supplier_id": doc["supplier_id"],
            "currency": doc["currency"],
            "status": doc["status"],
            "period": doc.get("period"),
            "line_items": doc.get("line_items", []),
            "totals": doc.get("totals", {"total_items": 0, "total_net_payable": 0.0}),
            "approved_at": doc.get("approved_at"),
            "approved_by_email": doc.get("approved_by_email"),
            "paid_at": doc.get("paid_at"),
            "paid_by_email": doc.get("paid_by_email"),
            "payment_reference": doc.get("payment_reference"),
            "payment_posting_id": doc.get("payment_posting_id"),
            "cancelled_at": doc.get("cancelled_at"),
            "cancelled_by_email": doc.get("cancelled_by_email"),
            "cancel_reason": doc.get("cancel_reason"),
            "created_at": doc.get("created_at"),
            "updated_at": doc.get("updated_at"),
        }

    # ---------------------------------------------------------------------
    # Public API
    # ---------------------------------------------------------------------

    async def create_run(
        self,
        organization_id: str,
        supplier_id: str,
        currency: str,
        period: Optional[dict[str, Any]],
        created_by: str,
    ) -> dict:
        """Create a new settlement run in DRAFT.

        Enforces one open (draft/approved) run per (org, supplier, currency).
        """
        # Check for existing open run (draft or approved)
        existing = await self.db.settlement_runs.find_one(
            {
                "organization_id": organization_id,
                "supplier_id": supplier_id,
                "currency": currency,
                "status": {"$in": ["draft", "approved"]},
            }
        )
        if existing:
            raise AppError(
                status_code=409,
                code="open_settlement_exists",
                message="An open settlement run already exists for this supplier and currency",
            )

        now = now_utc()
        run_id = ObjectId()
        doc = {
            "_id": run_id,
            "organization_id": organization_id,
            "supplier_id": supplier_id,
            "currency": currency,
            "status": "draft",
            "period": period or None,
            "line_items": [],
            "totals": {"total_items": 0, "total_net_payable": 0.0},
            "approved_at": None,
            "approved_by_email": None,
            "paid_at": None,
            "paid_by_email": None,
            "payment_reference": None,
            "payment_posting_id": None,
            "cancelled_at": None,
            "cancelled_by_email": None,
            "cancel_reason": None,
            "created_at": now,
            "updated_at": now,
            "created_by_email": created_by,
        }

        await self.db.settlement_runs.insert_one(doc)
        return self._serialize_run(doc)

    async def list_runs(
        self,
        organization_id: str,
        supplier_id: Optional[str],
        currency: Optional[str],
        status: Optional[str],
        limit: int = 50,
    ) -> dict:
        query: dict[str, Any] = {"organization_id": organization_id}
        if supplier_id:
            query["supplier_id"] = supplier_id
        if currency:
            query["currency"] = currency
        if status:
            query["status"] = status

        cursor = (
            self.db.settlement_runs.find(query)
            .sort("created_at", -1)
            .limit(limit)
        )
        docs = await cursor.to_list(length=limit)
        items = []
        for doc in docs:
            items.append(
                {
                    "settlement_id": str(doc["_id"]),
                    "supplier_id": doc["supplier_id"],
                    "currency": doc["currency"],
                    "status": doc["status"],
                    "totals": doc.get("totals", {}),
                    "created_at": doc.get("created_at"),
                    "approved_at": doc.get("approved_at"),
                    "paid_at": doc.get("paid_at"),
                }
            )
        return {"items": items}

    async def get_run(self, organization_id: str, settlement_id: str) -> dict:
        doc = await self._load_run(organization_id, settlement_id)
        return self._serialize_run(doc)

    async def add_items(
        self,
        organization_id: str,
        settlement_id: str,
        accrual_ids: list[str],
        triggered_by: str,
    ) -> dict:
        """Add eligible accruals to a DRAFT run and lock them.

        Eligibility:
        - status in {"accrued", "adjusted"}
        - settlement_id is None
        """
        if not accrual_ids:
            return await self.get_run(organization_id, settlement_id)

        run = await self._load_run(organization_id, settlement_id)
        if run["status"] != "draft":
            raise AppError(
                status_code=409,
                code="settlement_not_draft",
                message="Can only add items to a draft settlement",
            )

        run_id = run["_id"]
        now = now_utc()

        # Accruals already present in run (avoid duplicates)
        existing_ids = {item["accrual_id"] for item in run.get("line_items", [])}

        added = 0
        new_items: list[dict[str, Any]] = []

        for accrual_id in accrual_ids:
            try:
                accrual_oid = ObjectId(accrual_id)
            except Exception:
                raise AppError(
                    status_code=404,
                    code="accrual_not_eligible",
                    message="Accrual not found or invalid id",
                    details={"accrual_id": accrual_id},
                )

            if accrual_id in existing_ids:
                raise AppError(
                    status_code=409,
                    code="accrual_not_eligible",
                    message="Accrual already in this settlement",
                    details={"accrual_id": accrual_id},
                )

            accrual = await self.db.supplier_accruals.find_one(
                {
                    "_id": accrual_oid,
                    "organization_id": organization_id,
                    "settlement_id": None,
                    "status": {"$in": ["accrued", "adjusted"]},
                }
            )
            if not accrual:
                raise AppError(
                    status_code=409,
                    code="accrual_not_eligible",
                    message="Accrual is not eligible for settlement",
                    details={"accrual_id": accrual_id},
                )

            prev_status = accrual["status"]

            # Lock accrual into this settlement
            res = await self.db.supplier_accruals.update_one(
                {
                    "_id": accrual_oid,
                    "organization_id": organization_id,
                    "settlement_id": None,
                    "status": prev_status,
                },
                {
                    "$set": {
                        "settlement_id": run_id,
                        "status": "in_settlement",
                        "lock_prev_status": prev_status,
                        "updated_at": now,
                    }
                },
            )

            if res.matched_count == 0:
                # Lost race or no longer eligible
                raise AppError(
                    status_code=409,
                    code="accrual_not_eligible",
                    message="Accrual became ineligible during settlement add",
                    details={"accrual_id": accrual_id},
                )

            net_payable = (accrual.get("amounts") or {}).get("net_payable", 0.0)
            item = {
                "accrual_id": accrual_id,
                "booking_id": accrual.get("booking_id"),
                "net_payable": net_payable,
                "status_at_approval": None,
                "accrued_at": accrual.get("accrued_at"),
            }
            new_items.append(item)
            added += 1

        # Push new items and recompute totals
        if new_items:
            await self.db.settlement_runs.update_one(
                {"_id": run_id}, {"$push": {"line_items": {"$each": new_items}}, "$set": {"updated_at": now}}
            )

        run = await self._load_run(organization_id, settlement_id)
        line_items = run.get("line_items", [])
        total_items = len(line_items)
        total_net = sum(float(li.get("net_payable", 0.0)) for li in line_items)

        await self.db.settlement_runs.update_one(
            {"_id": run_id},
            {
                "$set": {
                    "totals": {
                        "total_items": total_items,
                        "total_net_payable": total_net,
                    },
                    "updated_at": now,
                }
            },
        )

        run = await self._load_run(organization_id, settlement_id)
        return {
            "settlement_id": str(run["_id"]),
            "added": added,
            "totals": run.get("totals", {}),
        }

    async def remove_items(
        self,
        organization_id: str,
        settlement_id: str,
        accrual_ids: list[str],
        triggered_by: str,
    ) -> dict:
        """Remove accruals from a DRAFT run and unlock them."""
        if not accrual_ids:
            return await self.get_run(organization_id, settlement_id)

        run = await self._load_run(organization_id, settlement_id)
        if run["status"] != "draft":
            raise AppError(
                status_code=409,
                code="settlement_not_draft",
                message="Can only remove items from a draft settlement",
            )

        run_id = run["_id"]
        now = now_utc()

        # Map of accrual_id -> lock_prev_status for this run
        line_items = run.get("line_items", [])
        items_by_id = {li["accrual_id"]: li for li in line_items}

        for accrual_id in accrual_ids:
            if accrual_id not in items_by_id:
                raise AppError(
                    status_code=409,
                    code="accrual_not_in_this_settlement",
                    message="Accrual is not in this settlement",
                    details={"accrual_id": accrual_id},
                )

            try:
                accrual_oid = ObjectId(accrual_id)
            except Exception:
                raise AppError(
                    status_code=404,
                    code="accrual_not_in_this_settlement",
                    message="Accrual not found",
                    details={"accrual_id": accrual_id},
                )

            accrual = await self.db.supplier_accruals.find_one(
                {
                    "_id": accrual_oid,
                    "organization_id": organization_id,
                    "settlement_id": run_id,
                    "status": "in_settlement",
                }
            )
            if not accrual:
                raise AppError(
                    status_code=409,
                    code="accrual_not_in_this_settlement",
                    message="Accrual is not locked by this settlement",
                    details={"accrual_id": accrual_id},
                )

            prev_status = accrual.get("lock_prev_status") or "accrued"

            res = await self.db.supplier_accruals.update_one(
                {
                    "_id": accrual_oid,
                    "organization_id": organization_id,
                    "settlement_id": run_id,
                    "status": "in_settlement",
                },
                {
                    "$set": {
                        "settlement_id": None,
                        "status": prev_status,
                        "lock_prev_status": None,
                        "updated_at": now,
                    }
                },
            )
            if res.matched_count == 0:
                raise AppError(
                    status_code=409,
                    code="accrual_not_in_this_settlement",
                    message="Accrual is not locked by this settlement",
                    details={"accrual_id": accrual_id},
                )

            # Pull from settlement line_items
            await self.db.settlement_runs.update_one(
                {"_id": run_id},
                {"$pull": {"line_items": {"accrual_id": accrual_id}}, "$set": {"updated_at": now}},
            )

        # Recompute totals
        run = await self._load_run(organization_id, settlement_id)
        line_items = run.get("line_items", [])
        total_items = len(line_items)
        total_net = sum(float(li.get("net_payable", 0.0)) for li in line_items)

        await self.db.settlement_runs.update_one(
            {"_id": run_id},
            {
                "$set": {
                    "totals": {
                        "total_items": total_items,
                        "total_net_payable": total_net,
                    },
                    "updated_at": now,
                }
            },
        )

        return await self.get_run(organization_id, settlement_id)

    async def approve(
        self,
        organization_id: str,
        settlement_id: str,
        approved_by: str,
        approved_at: Optional[datetime] = None,
    ) -> dict:
        """Approve a DRAFT settlement and snapshot line_items + totals."""
        run = await self._load_run(organization_id, settlement_id)
        if run["status"] != "draft":
            raise AppError(
                status_code=409,
                code="settlement_not_draft",
                message="Only draft settlements can be approved",
            )

        run_id = run["_id"]

        # Ensure there is at least one item
        line_items = run.get("line_items", [])
        if not line_items:
            raise AppError(
                status_code=409,
                code="settlement_empty",
                message="Cannot approve an empty settlement",
            )

        # Load locked accruals for snapshot
        locked = await self.db.supplier_accruals.find(
            {
                "organization_id": organization_id,
                "settlement_id": run_id,
                "status": "in_settlement",
            }
        ).to_list(length=None)

        snapshot_items: list[dict[str, Any]] = []
        total_net = 0.0

        for accrual in locked:
            accrual_id = str(accrual["_id"])
            net_payable = (accrual.get("amounts") or {}).get("net_payable", 0.0)
            prev_status = accrual.get("lock_prev_status") or "accrued"
            snapshot_items.append(
                {
                    "accrual_id": accrual_id,
                    "booking_id": accrual.get("booking_id"),
                    "net_payable": net_payable,
                    "status_at_approval": prev_status,
                    "accrued_at": accrual.get("accrued_at"),
                }
            )
            total_net += float(net_payable)

        approved_at = approved_at or now_utc()

        await self.db.settlement_runs.update_one(
            {"_id": run_id, "organization_id": organization_id},
            {
                "$set": {
                    "status": "approved",
                    "line_items": snapshot_items,
                    "totals": {
                        "total_items": len(snapshot_items),
                        "total_net_payable": total_net,
                    },
                    "approved_at": approved_at,
                    "approved_by_email": approved_by,
                    "updated_at": approved_at,
                }
            },
        )

        run = await self._load_run(organization_id, settlement_id)
        return {
            "settlement_id": str(run["_id"]),
            "status": run["status"],
            "totals": run.get("totals", {}),
        }

    async def cancel(
        self,
        organization_id: str,
        settlement_id: str,
        cancelled_by: str,
        reason: str,
    ) -> dict:
        """Cancel a DRAFT or APPROVED settlement and unlock accruals.

        PAID settlements cannot be cancelled.
        """
        run = await self._load_run(organization_id, settlement_id)
        status = run["status"]
        if status == "paid":
            raise AppError(
                status_code=409,
                code="settlement_already_paid",
                message="Paid settlements cannot be cancelled",
            )

        if status not in {"draft", "approved"}:
            # Nothing to unlock but we can still mark cancelled
            pass

        run_id = run["_id"]
        now = now_utc()

        # Unlock all accruals locked by this settlement
        await self.db.supplier_accruals.update_many(
            {
                "organization_id": organization_id,
                "settlement_id": run_id,
                "status": "in_settlement",
            },
            {
                "$set": {
                    "settlement_id": None,
                    "status": "accrued",  # fallback if lock_prev_status missing
                    "lock_prev_status": None,
                    "updated_at": now,
                }
            },
        )

        # If lock_prev_status is present, restore it in a second pass
        await self.db.supplier_accruals.update_many(
            {
                "organization_id": organization_id,
                "settlement_id": None,
                "lock_prev_status": {"$in": ["accrued", "adjusted"]},
            },
            {
                "$set": {
                    "status": "$lock_prev_status",
                    "lock_prev_status": None,
                    "updated_at": now,
                }
            },
        )

        await self.db.settlement_runs.update_one(
            {"_id": run_id, "organization_id": organization_id},
            {
                "$set": {
                    "status": "cancelled",
                    "cancelled_at": now,
                    "cancelled_by_email": cancelled_by,
                    "cancel_reason": reason,
                    "updated_at": now,
                }
            },
        )

        run = await self._load_run(organization_id, settlement_id)
        return self._serialize_run(run)

    async def mark_paid(
        self,
        organization_id: str,
        settlement_id: str,
        paid_by: str,
        paid_at: Optional[datetime] = None,
        payment_reference: Optional[str] = None,
    ) -> dict:
        """Mark an APPROVED settlement as paid.

        Does NOT create ledger postings (Phase 2A.5 will handle that).
        """
        run = await self._load_run(organization_id, settlement_id)
        if run["status"] != "approved":
            raise AppError(
                status_code=409,
                code="settlement_not_approved",
                message="Only approved settlements can be marked as paid",
            )

        run_id = run["_id"]
        paid_at = paid_at or now_utc()

        await self.db.settlement_runs.update_one(
            {"_id": run_id, "organization_id": organization_id},
            {
                "$set": {
                    "status": "paid",
                    "paid_at": paid_at,
                    "paid_by_email": paid_by,
                    "payment_reference": payment_reference,
                    # payment_posting_id remains None in Phase 2A.4
                    "updated_at": paid_at,
                }
            },
        )

        run = await self._load_run(organization_id, settlement_id)
        return self._serialize_run(run)
