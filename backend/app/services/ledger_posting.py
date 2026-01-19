"""
Finance OS Phase 1.3: Ledger Core Logic
Double-entry posting service with exactly-once guarantees
"""
from __future__ import annotations

import hashlib
import json
import uuid
from typing import Literal, Optional, Any
from datetime import datetime
from pydantic import BaseModel
from pymongo.errors import DuplicateKeyError

from app.db import get_db
from app.errors import AppError
from app.utils import now_utc


class LedgerLine(BaseModel):
    """Single line in a ledger posting"""
    account_id: str
    direction: Literal["debit", "credit"]
    amount: float


class LedgerPostingService:
    """
    Core ledger posting service implementing:
    - Double-entry accounting
    - Exactly-once guarantees (idempotency)
    - Immutable entries
    - Balance cache updates
    """
    
    @staticmethod
    def _compute_checksum(source_type: str, source_id: str, event: str, lines: list[LedgerLine]) -> str:
        """Compute SHA256 checksum for posting integrity"""
        data = {
            "source_type": source_type,
            "source_id": source_id,
            "event": event,
            "lines": [
                {"account_id": line.account_id, "direction": line.direction, "amount": line.amount}
                for line in lines
            ]
        }
        payload = json.dumps(data, sort_keys=True)
        return hashlib.sha256(payload.encode()).hexdigest()
    
    @staticmethod
    def _validate_lines(lines: list[LedgerLine], currency: str):
        """Validate posting lines"""
        # Must have at least 2 lines (double-entry)
        if len(lines) < 2:
            raise AppError(
                status_code=422,
                code="ledger_posting_invalid",
                message="Posting must have at least 2 lines (double-entry)",
            )
        
        # All amounts must be positive
        for line in lines:
            if line.amount <= 0:
                raise AppError(
                    status_code=422,
                    code="ledger_posting_invalid",
                    message=f"Amount must be > 0, got {line.amount}",
                )
        
        # Debit total must equal credit total
        debit_total = sum(line.amount for line in lines if line.direction == "debit")
        credit_total = sum(line.amount for line in lines if line.direction == "credit")
        
        if abs(debit_total - credit_total) > 0.01:  # floating point tolerance
            raise AppError(
                status_code=409,
                code="ledger_unbalanced",
                message=f"Debit total ({debit_total}) must equal credit total ({credit_total})",
            )
    
    @staticmethod
    async def post_event(
        organization_id: str,
        source_type: str,
        source_id: str,
        event: str,
        currency: str,
        lines: list[LedgerLine],
        occurred_at: Optional[datetime] = None,
        created_by: str = "system",
        meta: Optional[dict] = None,
    ) -> dict:
        """Post a financial event to the ledger.

        - Non-booking: keep idempotent single-doc posting (multi-line).
        - Booking: per-line posting (N lines => N docs), idempotency bypassed.
        - posting_id/_id are strings: "post_<uuid>".
        - ledger_entries.posting_id uses same string.
        """
        db = await get_db()

        # Validation
        LedgerPostingService._validate_lines(lines, currency)

        if occurred_at is None:
            occurred_at = now_utc()
        meta = meta or {}

        src_id_str = str(source_id)
        now = now_utc()

        # ----------------------------
        # NON-BOOKING: old behavior
        # ----------------------------
        if source_type != "booking":
            existing_posting = await db.ledger_postings.find_one(
                {
                    "organization_id": organization_id,
                    "source.type": source_type,
                    "source.id": src_id_str,
                    "event": event,
                }
            )
            if existing_posting:
                return existing_posting

            posting_id = f"post_{uuid.uuid4()}"
            posting_lines: list[dict] = []
            debit_total = 0.0
            credit_total = 0.0
            entry_docs: list[dict] = []

            for line in lines:
                direction = (getattr(line, "direction", None) or "").lower()
                amount = float(getattr(line, "amount", 0.0) or 0.0)
                account_id = str(getattr(line, "account_id"))

                debit = amount if direction == "debit" else 0.0
                credit = amount if direction == "credit" else 0.0
                debit_total += debit
                credit_total += credit

                posting_lines.append(
                    {
                        "account_id": account_id,
                        "direction": getattr(line, "direction", None),
                        "amount": amount,
                        "debit": debit,
                        "credit": credit,
                    }
                )

                entry_docs.append(
                    {
                        "_id": f"le_{uuid.uuid4()}",
                        "organization_id": organization_id,
                        "posting_id": posting_id,
                        "account_id": account_id,
                        "currency": currency,
                        "direction": getattr(line, "direction", None),
                        "amount": amount,
                        "occurred_at": occurred_at,
                        "posted_at": now,
                        "source": {"type": source_type, "id": src_id_str},
                        "event": event,
                        "memo": f"{event} {source_type}/{src_id_str}",
                        "meta": meta or {},
                    }
                )

            posting_doc: dict[str, Any] = {
                "_id": posting_id,
                "organization_id": organization_id,
                "source": {"type": source_type, "id": src_id_str},
                "event": event,
                "currency": currency,
                "lines": posting_lines,
                "debit": float(debit_total),
                "credit": float(credit_total),
                "created_at": now,
                "created_by": created_by,
            }
            if meta:
                posting_doc["meta"] = meta

            await db.ledger_postings.insert_one(posting_doc)

            if entry_docs:
                await db.ledger_entries.insert_many(entry_docs)

            for line in lines:
                await LedgerPostingService._update_balance(
                    db,
                    organization_id,
                    str(getattr(line, "account_id")),
                    currency,
                    getattr(line, "direction", None),
                    float(getattr(line, "amount", 0.0) or 0.0),
                )

            return posting_doc

        # ----------------------------
        # BOOKING: per-line postings
        # ----------------------------
        # For booking events we want a single posting header with multiple
        # lines, so that uniq_posting_per_source_event (scoped by meta.amend_id)
        # can be used for idempotency.
        posting_id = f"post_{uuid.uuid4()}"
        posting_doc: dict[str, Any] = {
            "_id": posting_id,
            "organization_id": organization_id,
            "source": {"type": source_type, "id": src_id_str},
            "event": event,
            "currency": currency,
            "lines": [],
            "created_at": now,
            "created_by": created_by,
        }
        if meta:
            posting_doc["meta"] = meta

        entry_docs: list[dict[str, Any]] = []

        for line in lines:
            direction = (getattr(line, "direction", None) or "").lower()
            amount = float(getattr(line, "amount", 0.0) or 0.0)

            if direction == "debit":
                debit, credit = amount, 0.0
            elif direction == "credit":
                debit, credit = 0.0, amount
            else:
                debit, credit = 0.0, 0.0

            account_id = str(getattr(line, "account_id"))

            posting_doc["lines"].append(
                {
                    "account_id": account_id,
                    "direction": getattr(line, "direction", None),
                    "amount": float(amount),
                    "debit": float(debit),
                    "credit": float(credit),
                }
            )

            entry_docs.append(
                {
                    "_id": f"le_{uuid.uuid4()}",
                    "organization_id": organization_id,
                    "posting_id": posting_id,
                    "account_id": account_id,
                    "currency": currency,
                    "direction": getattr(line, "direction", None),
                    "amount": float(amount),
                    "occurred_at": occurred_at,
                    "posted_at": now,
                    "source": {"type": source_type, "id": src_id_str},
                    "event": event,
                    "memo": f"{event} {source_type}/{src_id_str}",
                    "meta": meta or {},
                }
            )

        # Persist header + entries with idempotency on (org, source, event, amend_id)
        try:
            await db.ledger_postings.insert_one(posting_doc)
        except DuplicateKeyError:
            amend_id = (meta or {}).get("amend_id") if meta else None
            if amend_id is None:
                # Non-amend events should not violate uniq_posting_per_source_event
                raise

            existing = await db.ledger_postings.find_one(
                {
                    "organization_id": organization_id,
                    "source.type": source_type,
                    "source.id": src_id_str,
                    "event": event,
                    "meta.amend_id": amend_id,
                }
            )
            if existing:
                return existing
            raise

        if entry_docs:
            await db.ledger_entries.insert_many(entry_docs)

        for line in lines:
            await LedgerPostingService._update_balance(
                db,
                organization_id,
                str(getattr(line, "account_id")),
                currency,
                getattr(line, "direction", None),
                float(getattr(line, "amount", 0.0) or 0.0),
            )

        return posting_doc
    
    @staticmethod
    async def _update_balance(
        db,
        organization_id: str,
        account_id: str,
        currency: str,
        direction: Literal["debit", "credit"],
        amount: float,
    ):
        """
        Update account balance cache atomically.
        
        Balance rules (Phase 1):
        - Agency account: balance = total_debit - total_credit (exposure)
        - Platform account: balance = total_credit - total_debit (receivables)
        """
        # Determine account type to apply correct balance rule
        # account_id may be string (most accounts) or stringified ObjectId
        account = await db.finance_accounts.find_one({"_id": account_id})
        if not account and isinstance(account_id, str) and len(account_id) == 24:
            # Fallback: try interpreting as ObjectId for supplier/platform accounts
            try:
                from bson import ObjectId as _ObjectId

                account = await db.finance_accounts.find_one({"_id": _ObjectId(account_id)})
            except Exception:
                account = None

        if not account:
            # Account not found, skip balance update (defensive)
            return
        
        account_type = account.get("type")
        
        # Apply balance rules
        if account_type == "agency":
            # Agency: balance = debit - credit (exposure increases with debit)
            delta = amount if direction == "debit" else -amount
        elif account_type == "platform":
            # Platform: balance = credit - debit (receivables increase with credit)
            delta = amount if direction == "credit" else -amount
        elif account_type == "supplier":
            # Supplier payable: balance = credit - debit (higher credit = more payable)
            delta = amount if direction == "credit" else -amount
        else:
            # Other: default to agency rule (debit - credit)
            delta = amount if direction == "debit" else -amount
        
        # Atomic update with upsert
        now = now_utc()
        await db.account_balances.update_one(
            {
                "organization_id": organization_id,
                "account_id": account_id,
                "currency": currency,
            },
            {
                "$inc": {"balance": delta},
                "$set": {"as_of": now, "updated_at": now},
            },
            upsert=True,
        )
    
    @staticmethod
    async def recalculate_balance(
        organization_id: str,
        account_id: str,
        currency: str,
    ) -> dict:
        """
        Recalculate balance from ledger entries (safety net / debug tool).
        
        This is a full scan and should only be used for:
        - Recovery from balance corruption
        - Ops debugging
        - Balance verification
        
        NOT for normal operations (balance cache is updated on each posting).
        """
        db = await get_db()
        
        # Get account type to apply correct balance rule
        account = await db.finance_accounts.find_one({"_id": account_id})
        if not account:
            raise AppError(
                status_code=404,
                code="account_not_found",
                message=f"Account {account_id} not found",
            )
        
        account_type = account.get("type")
        
        # Aggregate all entries for this account
        entries = await db.ledger_entries.find({
            "organization_id": organization_id,
            "account_id": account_id,
            "currency": currency,
        }).to_list(length=10000)
        
        # Calculate totals
        total_debit = sum(e["amount"] for e in entries if e["direction"] == "debit")
        total_credit = sum(e["amount"] for e in entries if e["direction"] == "credit")
        
        # Apply balance rules
        if account_type == "agency":
            balance = total_debit - total_credit
        elif account_type == "platform":
            balance = total_credit - total_debit
        else:
            balance = total_debit - total_credit
        
        # Update balance cache
        now = now_utc()
        await db.account_balances.update_one(
            {
                "organization_id": organization_id,
                "account_id": account_id,
                "currency": currency,
            },
            {
                "$set": {
                    "balance": balance,
                    "as_of": now,
                    "updated_at": now,
                }
            },
            upsert=True,
        )
        
        return {
            "account_id": account_id,
            "currency": currency,
            "balance": balance,
            "total_debit": total_debit,
            "total_credit": total_credit,
            "entry_count": len(entries),
            "recalculated_at": now,
        }


# ============================================================================
# Posting Event Matrix (Phase 1 configuration)
# ============================================================================

class PostingMatrixConfig:
    """
    Configuration for booking/payment/refund → ledger posting mapping.
    
    This is the "source of truth" for Phase 1 financial events.
    """
    
    @staticmethod
    def get_booking_confirmed_lines(
        agency_account_id: str,
        platform_account_id: str,
        sell_amount: float,
    ) -> list[LedgerLine]:
        """
        BOOKING_CONFIRMED event:
        - Agency owes platform (debit agency, credit platform)
        """
        return [
            LedgerLine(account_id=agency_account_id, direction="debit", amount=sell_amount),
            LedgerLine(account_id=platform_account_id, direction="credit", amount=sell_amount),
        ]
    @staticmethod
    def get_booking_cancelled_lines(
        agency_account_id: str,
        platform_account_id: str,
        sell_amount: float,
    ) -> list[LedgerLine]:
        """BOOKING_CANCELLED event.

        Implemented as an exact reversal of BOOKING_CONFIRMED so that
        BOOKING_CONFIRMED + BOOKING_CANCELLED is net-zero in EUR.
        """
        confirmed = PostingMatrixConfig.get_booking_confirmed_lines(
            agency_account_id=agency_account_id,
            platform_account_id=platform_account_id,
            sell_amount=sell_amount,
        )
        reversed_lines: list[LedgerLine] = []
        for line in confirmed:
            reversed_lines.append(
                LedgerLine(
                    account_id=line.account_id,
                    direction="credit" if line.direction == "debit" else "debit",
                    amount=line.amount,
                )
            )
        return reversed_lines

    @staticmethod
    def get_booking_cancelled_with_penalty_lines(
        agency_account_id: str,
        platform_account_id: str,
        sell_amount: float,
        penalty_amount: float,
    ) -> list[LedgerLine]:
        """BOOKING_CANCELLED with flat penalty.

        - First fully reverses BOOKING_CONFIRMED (net-zero),
        - Then adds a penalty line (agency debit, platform credit).
        """
        lines = PostingMatrixConfig.get_booking_cancelled_lines(
            agency_account_id=agency_account_id,
            platform_account_id=platform_account_id,
            sell_amount=sell_amount,
        )
        if penalty_amount > 0:
            lines.append(
                LedgerLine(
                    account_id=agency_account_id,
                    direction="debit",
                    amount=penalty_amount,
                )
            )
            lines.append(
                LedgerLine(
                    account_id=platform_account_id,
                    direction="credit",
                    amount=penalty_amount,
                )
            )
        return lines

    @staticmethod
    def get_booking_amended_delta_lines(
        agency_account_id: str,
        platform_account_id: str,
        delta_amount: float,
        increase: bool,
    ) -> list[LedgerLine]:
        """BOOKING_AMENDED event (delta-only posting).

        - delta_amount is always positive.
        - increase=True  -> exposure increases (similar to BOOKING_CONFIRMED)
        - increase=False -> exposure decreases (reverse directions)
        """
        if delta_amount <= 0:
            return []

        if increase:
            # Same pattern as BOOKING_CONFIRMED but with delta
            return [
                LedgerLine(account_id=agency_account_id, direction="debit", amount=delta_amount),
                LedgerLine(account_id=platform_account_id, direction="credit", amount=delta_amount),
            ]

        # Decrease exposure: reverse directions
        return [
            LedgerLine(account_id=agency_account_id, direction="credit", amount=delta_amount),
            LedgerLine(account_id=platform_account_id, direction="debit", amount=delta_amount),
        ]



    
    @staticmethod
    def get_payment_received_lines(
        agency_account_id: str,
        platform_account_id: str,
        payment_amount: float,
    ) -> list[LedgerLine]:
        """
        PAYMENT_RECEIVED event:
        - Agency pays platform (credit agency, debit platform)
        """
        return [
            LedgerLine(account_id=agency_account_id, direction="credit", amount=payment_amount),
            LedgerLine(account_id=platform_account_id, direction="debit", amount=payment_amount),
        ]
    
    @staticmethod
    def get_supplier_accrued_lines(
        supplier_account_id: str,
        platform_ap_clearing_account_id: str,
        net_amount: float,
    ) -> list[LedgerLine]:
        """
        SUPPLIER_ACCRUED event (Phase 2A.2):
        - Supplier payable increases (credit supplier)
        - Platform AP clearing increases (debit platform AP)
        
        Note: This is separate from Phase 1 platform AR account.
        """
        return [
            LedgerLine(account_id=platform_ap_clearing_account_id, direction="debit", amount=net_amount),
            LedgerLine(account_id=supplier_account_id, direction="credit", amount=net_amount),
        ]

    @staticmethod
    def get_supplier_accrual_reversed_lines(
        supplier_account_id: str,
        platform_ap_clearing_account_id: str,
        net_amount: float,
    ) -> list[LedgerLine]:
        """
        SUPPLIER_ACCRUAL_REVERSED event (Phase 2A.3):
        - Reverse of SUPPLIER_ACCRUED
        - Supplier payable decreases (debit supplier)
        - Platform AP clearing decreases (credit platform AP)
        """
        return [
            LedgerLine(account_id=supplier_account_id, direction="debit", amount=net_amount),
            LedgerLine(account_id=platform_ap_clearing_account_id, direction="credit", amount=net_amount),
        ]

    @staticmethod
    def get_supplier_accrual_adjusted_lines(
        supplier_account_id: str,
        platform_ap_clearing_account_id: str,
        delta: float,
    ) -> list[LedgerLine]:
        """
        SUPPLIER_ACCRUAL_ADJUSTED event (Phase 2A.3):
        - Adjustment of supplier payable based on net payable delta
        - delta > 0: supplier payable increases (credit supplier)
        - delta < 0: supplier payable decreases (debit supplier)
        """
        if delta == 0:
            return []

        amount = abs(delta)

        if delta > 0:
            # Platform AP clearing increases (debit), supplier payable increases (credit)
            return [
                LedgerLine(account_id=platform_ap_clearing_account_id, direction="debit", amount=amount),
                LedgerLine(account_id=supplier_account_id, direction="credit", amount=amount),
            ]

        # delta < 0: supplier payable decreases, platform AP clearing decreases
        return [
            LedgerLine(account_id=supplier_account_id, direction="debit", amount=amount),
            LedgerLine(account_id=platform_ap_clearing_account_id, direction="credit", amount=amount),
        ]

    @staticmethod
    def get_settlement_paid_lines(
        supplier_payable_account_id: str,
        platform_cash_account_id: str,
        total_amount: float,
    ) -> list[LedgerLine]:
        """SETTLEMENT_PAID event (Phase 2A.5):

        - Supplier payable decreases (debit supplier payable)
        - Platform cash/bank decreases (credit cash)
        """
        return [
            LedgerLine(account_id=supplier_payable_account_id, direction="debit", amount=total_amount),
            LedgerLine(account_id=platform_cash_account_id, direction="credit", amount=total_amount),
        ]

    @staticmethod
    def get_refund_approved_lines(
        agency_account_id: str,
        platform_ar_account_id: str,
        refund_amount: float,
    ) -> list[LedgerLine]:
        """REFUND_APPROVED event (Phase 2B.3):

        - Platform AR decreases (debit PLATFORM_AR_{CCY})
        - Agency AR decreases (credit AGENCY_AR_{agency_id}_{CCY})
        """
        return [
            LedgerLine(account_id=platform_ar_account_id, direction="debit", amount=refund_amount),
            LedgerLine(account_id=agency_account_id, direction="credit", amount=refund_amount),
        ]

