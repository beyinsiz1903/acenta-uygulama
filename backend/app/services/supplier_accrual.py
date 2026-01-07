"""
Supplier Accrual Service (Phase 2A.2)
Creates supplier_accruals and posts SUPPLIER_ACCRUED ledger event

CONTRACTS ENFORCED:
1. Accrual trigger: CONFIRMED → VOUCHERED (state-transition)
2. Source-of-truth: supplier_accruals (unique per booking)
3. supplier_id REQUIRED (hard fail)
4. Net amount snapshot from booking
5. Exactly-once ledger posting
6. Platform AP ≠ AR (separate accounts)
"""
from __future__ import annotations

from bson import ObjectId
from typing import Optional
from datetime import datetime

from app.errors import AppError
from app.utils import now_utc
from app.services.ledger_posting import LedgerPostingService, PostingMatrixConfig
from app.services.supplier_finance import SupplierFinanceService, ensure_platform_ap_clearing_account
import logging

logger = logging.getLogger(__name__)


class SupplierAccrualService:
    """
    Manages supplier accruals with production-grade guarantees:
    - Exactly-once accrual per booking
    - Double-entry ledger posting
    - State transition enforcement
    - Hard validation (supplier_id, commission)
    """
    
    def __init__(self, db):
        self.db = db
        self.ledger = LedgerPostingService()
        self.supp_fin = SupplierFinanceService(db)

    async def _load_booking(self, organization_id: str, booking_id: str) -> dict:
        """Load booking by ID with support for ObjectId/string _id."""
        # Try ObjectId first (normal case)
        try:
            oid = ObjectId(booking_id)
            booking = await self.db.bookings.find_one({
                "_id": oid,
                "organization_id": organization_id,
            })
        except Exception:
            # Fallback: some tests may use string _id
            booking = await self.db.bookings.find_one({
                "_id": booking_id,
                "organization_id": organization_id,
            })

        if not booking:
            raise AppError(
                status_code=404,
                code="not_found",
                message=f"Booking {booking_id} not found",
            )

        return booking


    
    async def post_accrual_for_booking(
        self,
        organization_id: str,
        booking_id: str,
        triggered_by: str,
        trigger: str = "voucher_generate",
    ) -> dict:
        """
        Creates supplier_accruals (unique per booking) and posts SUPPLIER_ACCRUED exactly-once.
        
        Args:
            organization_id: Organization ID
            booking_id: Booking ID (must be VOUCHERED)
            triggered_by: Email or "system"
            trigger: Meta info (voucher_generate, manual, etc.)
            
        Returns:
            {
                "accrual_id": str,
                "posting_id": str,
                "supplier_id": str,
                "supplier_account_id": str,
                "platform_ap_account_id": str,
                "currency": str,
                "net_amount": float,
            }
            
        Raises:
            AppError: 404 not_found, 409 invalid_booking_state, 409 supplier_id_missing, 409 invalid_commission
        """
        
        # Step 0: Booking lookup + scope (support both ObjectId and string _id)
        try:
            from bson import ObjectId as _ObjectId

            booking_oid = _ObjectId(booking_id)
            booking = await self.db.bookings.find_one(
                {"_id": booking_oid, "organization_id": organization_id}
            )
        except Exception:
            booking = await self.db.bookings.find_one(
                {"_id": booking_id, "organization_id": organization_id}
            )
        
        if not booking:
            raise AppError(
                status_code=404,
                code="not_found",
                message=f"Booking {booking_id} not found",
            )
        
        # Step 1: Trigger guard (booking must be VOUCHERED)
        if booking.get("status") != "VOUCHERED":
            raise AppError(
                status_code=409,
                code="invalid_booking_state",
                message="Accrual requires booking VOUCHERED",
                details={"booking_id": booking_id, "current_status": booking.get("status")},
            )
        
        # Step 2: supplier_id guard (HARD FAIL if missing)
        supplier_id = booking.get("supplier_id")
        if not supplier_id and booking.get("items"):
            supplier_id = booking["items"][0].get("supplier_id")
        
        if not supplier_id:
            raise AppError(
                status_code=409,
                code="supplier_id_missing",
                message="Booking missing supplier_id for accrual",
                details={"booking_id": booking_id},
            )
        
        # Step 3: Amounts snapshot
        currency = booking.get("currency", "EUR")
        gross_sell = booking.get("amounts", {}).get("sell", 0.0)
        commission = booking.get("commission", {}).get("amount", 0.0)
        net_payable = gross_sell - commission
        
        # Validation: net must be >= 0
        if net_payable < 0:
            raise AppError(
                status_code=409,
                code="invalid_commission",
                message="Commission cannot exceed gross sell amount",
                details={
                    "gross_sell": gross_sell,
                    "commission": commission,
                    "net_payable": net_payable,
                },
            )
        
        # Step 4: Ensure accounts exist
        supplier_account_id = await self.supp_fin.get_or_create_supplier_account(
            organization_id, supplier_id, currency
        )
        
        platform_ap_account_id = await ensure_platform_ap_clearing_account(
            self.db, organization_id, currency
        )
        
        # Step 5: Create accrual doc (unique per booking)
        now = now_utc()
        accrual_id = ObjectId()
        
        accrual_doc = {
            "_id": accrual_id,
            "organization_id": organization_id,
            "booking_id": booking_id,
            "supplier_id": supplier_id,
            "currency": currency,
            "amounts": {
                "gross_sell": gross_sell,
                "commission": commission,
                "net_payable": net_payable,
            },
            "status": "accrued",
            "accrued_at": now,
            "accrual_posting_id": None,  # will be set after posting
            "settlement_id": None,
            "settled_at": None,
            "created_at": now,
            "updated_at": now,
            "meta": {
                "trigger": trigger,
                "booking_status_at_accrual": "VOUCHERED",
                "triggered_by": triggered_by,
            },
        }
        
        try:
            await self.db.supplier_accruals.insert_one(accrual_doc)
            logger.info(f"Created supplier accrual: {accrual_id} for booking {booking_id}")
        except Exception as e:
            # Check if duplicate (race condition or idempotency replay)
            if "duplicate key" in str(e).lower():
                existing = await self.db.supplier_accruals.find_one({
                    "organization_id": organization_id,
                    "booking_id": booking_id,
                })
                if existing:
                    logger.info(f"Accrual already exists for booking {booking_id}, replaying posting")
                    accrual_id = existing["_id"]
                    # Continue to posting replay
                else:
                    raise
            else:
                raise
        
        # Step 6: Ledger posting (exactly-once)
        lines = PostingMatrixConfig.get_supplier_accrued_lines(
            supplier_account_id=supplier_account_id,
            platform_ap_clearing_account_id=platform_ap_account_id,
            net_amount=net_payable,
        )
        
        posting = await self.ledger.post_event(
            organization_id=organization_id,
            source_type="booking",
            source_id=booking_id,
            event="SUPPLIER_ACCRUED",
            currency=currency,
            lines=lines,
            occurred_at=now,
            created_by=triggered_by,
            meta={
                "supplier_id": supplier_id,
                "accrual_id": str(accrual_id),
                "trigger": trigger,
            },
        )
        
        posting_id = posting["_id"]
        
        # Step 7: Persist posting_id in accrual
        await self.db.supplier_accruals.update_one(
            {"_id": accrual_id},
            {
                "$set": {
                    "accrual_posting_id": posting_id,
                    "updated_at": now_utc(),
                }
            },
        )
        
        # Step 7b: Update booking with supplier_finance fields
        await self.db.bookings.update_one(
            {"_id": booking_id},
            {
                "$set": {
                    "supplier_finance": {
                        "accrual_id": str(accrual_id),
                        "posting_id": posting_id,
                        "net_amount": net_payable,
                        "currency": currency,
                    },
                    "updated_at": now_utc(),
                }
            },
        )
        
        logger.info(f"Completed accrual posting: {posting_id} for booking {booking_id}")
        
        return {
            "accrual_id": str(accrual_id),
            "posting_id": posting_id,
            "supplier_id": supplier_id,
            "supplier_account_id": supplier_account_id,
            "platform_ap_account_id": platform_ap_account_id,
            "currency": currency,
            "net_amount": net_payable,
        }
