"""
Finance OS Phase 1.5: Booking Integration Helpers
Credit check + auto-posting for booking lifecycle
"""
from __future__ import annotations

from typing import Optional, Dict, Any
from datetime import datetime
from bson import ObjectId


from app.errors import AppError
from app.services.ledger_posting import LedgerPostingService, PostingMatrixConfig
from app.utils import now_utc


class BookingFinanceService:
    """
    Finance integration for booking lifecycle:
    - Credit check before booking creation
    - Auto-posting on booking confirmation
    - Refund posting on cancellation
    """
    
    def __init__(self, db):
        self.db = db
    
    async def check_credit_and_get_flags(
        self,
        organization_id: str,
        agency_id: str,
        sell_amount: float,
        currency: str,
    ) -> Dict[str, Any]:
        """
        Check agency credit limit before booking creation.
        
        Returns:
            {
                "allowed": bool,
                "error": Optional[dict],  # if not allowed
                "flags": {
                    "near_limit": bool,
                    "over_limit_after_post": bool,  # post-check flag for race conditions
                }
            }
        
        Raises:
            AppError: If credit limit exceeded or other validation fails
        """
        
        # Get agency finance account
        agency_account = await self.db.finance_accounts.find_one({
            "organization_id": organization_id,
            "type": "agency",
            "owner_id": agency_id,
        })
        
        if not agency_account:
            raise AppError(
                status_code=404,
                code="finance_account_not_found",
                message=f"Finance account not found for agency {agency_id}",
            )
        
        account_id = agency_account["_id"]
        account_currency = agency_account["currency"]
        
        # Currency mismatch check
        if account_currency != currency:
            raise AppError(
                status_code=409,
                code="currency_mismatch",
                message=f"Account currency {account_currency} != booking currency {currency}",
            )
        
        # Get credit profile
        credit_profile = await self.db.credit_profiles.find_one({
            "organization_id": organization_id,
            "agency_id": agency_id,
        })
        
        if not credit_profile:
            raise AppError(
                status_code=404,
                code="credit_profile_not_found",
                message=f"Credit profile not found for agency {agency_id}",
            )
        
        limit = credit_profile["limit"]
        soft_limit = credit_profile.get("soft_limit")
        
        # Get current exposure (balance)
        balance = await self.db.account_balances.find_one({
            "organization_id": organization_id,
            "account_id": account_id,
            "currency": currency,
        })
        
        exposure = balance["balance"] if balance else 0.0
        
        # Calculate projected exposure
        projected = exposure + sell_amount
        
        # Hard limit check (> limit blocks booking)
        if projected > limit:
            raise AppError(
                status_code=409,
                code="credit_limit_exceeded",
                message="Credit limit exceeded",
                details={
                    "exposure": exposure,
                    "sell_amount": sell_amount,
                    "projected": projected,
                    "limit": limit,
                    "currency": currency,
                    "agency_id": agency_id,
                },
            )
        
        # Soft limit check (>= soft_limit is warning)
        near_limit = False
        if soft_limit and projected >= soft_limit:
            near_limit = True
        
        return {
            "allowed": True,
            "error": None,
            "flags": {
                "near_limit": near_limit,
                "over_limit_after_post": False,  # will be checked post-booking
            },
            "finance_context": {
                "account_id": account_id,
                "exposure": exposure,
                "projected": projected,
                "limit": limit,
                "soft_limit": soft_limit,
            }
        }
    
    async def post_booking_confirmed(
        self,
        organization_id: str,
        booking_id: str,
        agency_id: str,
        sell_amount: float,
        currency: str,
        occurred_at: Optional[datetime] = None,
    ) -> str:
        """Create EUR-denominated posting for BOOKING_CONFIRMED.

        - For EUR bookings: uses amounts.sell (and ensures sell_eur matches).
        - For non-EUR bookings: requires amounts.sell_eur to be present
          (set by Phase 2C FX integration). If missing, raises
          fx_snapshot_missing and does NOT create any posting.
        """

        # Load booking to derive EUR amount
        booking = await self.db.bookings.find_one(
            {"_id": ObjectId(booking_id), "organization_id": organization_id}
        )
        if not booking:
            raise AppError(404, "booking_not_found", "Booking not found")

        booking_currency = booking.get("currency") or currency
        amounts = booking.get("amounts") or {}
        sell = float(amounts.get("sell", sell_amount))
        sell_eur = amounts.get("sell_eur")

        if booking_currency == "EUR":
            # Backwards compatible: sell_eur may be missing for legacy bookings
            if sell_eur is None:
                sell_eur = sell
        else:
            if sell_eur is None:
                raise AppError(
                    500,
                    "fx_snapshot_missing",
                    "Non-EUR booking is missing FX snapshot / sell_eur",
                )

        amount_eur = float(sell_eur)

        # Get agency account
        agency_account = await self.db.finance_accounts.find_one({
            "organization_id": organization_id,
            "type": "agency",
            "owner_id": agency_id,
        })

        if not agency_account:
            raise AppError(
                status_code=404,
                code="finance_account_not_found",
                message=f"Finance account not found for agency {agency_id}",
            )

        # Get platform account
        platform_account = await self.db.finance_accounts.find_one({
            "organization_id": organization_id,
            "type": "platform",
        })

        if not platform_account:
            raise AppError(
                status_code=404,
                code="finance_account_not_found",
                message="Platform finance account not found",
            )

        # Create posting lines (EUR)
        lines = PostingMatrixConfig.get_booking_confirmed_lines(
            agency_account_id=agency_account["_id"],
            platform_account_id=platform_account["_id"],
            sell_amount=amount_eur,
        )

        # Post to ledger (EUR)
        posting = await LedgerPostingService.post_event(
            organization_id=organization_id,
            source_type="booking",
            source_id=booking_id,
            event="BOOKING_CONFIRMED",
            currency="EUR",
            lines=lines,
            occurred_at=occurred_at,
            created_by="system",
            meta={"booking_id": booking_id, "agency_id": agency_id},
        )

        return posting["_id"]
    

    async def post_booking_cancelled(
        self,
        organization_id: str,
        booking_id: str,
        agency_id: str,
        occurred_at: Optional[datetime] = None,
    ) -> Optional[str]:
        """Create EUR-denominated posting for BOOKING_CANCELLED.

        - Uses booking.amounts.sell_eur as canonical EUR amount.
        - If a BOOKING_CANCELLED posting already exists for this booking,
          behaves idempotently and returns without creating a new posting.
        """

        booking = await self.db.bookings.find_one(
            {"_id": ObjectId(booking_id), "organization_id": organization_id}
        )
        if not booking:
            raise AppError(404, "booking_not_found", "Booking not found")

        # Idempotency: if a BOOKING_CANCELLED posting already exists, do nothing
        existing = await self.db.ledger_postings.find_one(
            {
                "organization_id": organization_id,
                "source.type": "booking",
                "source.id": booking_id,
                "event": "BOOKING_CANCELLED",
            }
        )
        if existing:
            return None

        amounts = booking.get("amounts") or {}
        sell_eur = amounts.get("sell_eur")
        if sell_eur is None:
            raise AppError(
                500,
                "fx_snapshot_missing",
                "Booking is missing sell_eur for cancellation",
            )

        amount_eur = float(sell_eur)

        # Get agency account
        agency_account = await self.db.finance_accounts.find_one(
            {
                "organization_id": organization_id,
                "type": "agency",
                "owner_id": agency_id,
            }
        )
        if not agency_account:
            raise AppError(
                status_code=404,
                code="finance_account_not_found",
                message=f"Finance account not found for agency {agency_id}",
            )

        # Get platform account
        platform_account = await self.db.finance_accounts.find_one(
            {"organization_id": organization_id, "type": "platform"}
        )
        if not platform_account:
            raise AppError(
                status_code=404,
                code="finance_account_not_found",
                message="Platform finance account not found",
            )

        lines = PostingMatrixConfig.get_booking_cancelled_lines(
            agency_account_id=agency_account["_id"],
            platform_account_id=platform_account["_id"],
            sell_amount=amount_eur,
        )

        posting = await LedgerPostingService.post_event(
            organization_id=organization_id,
            source_type="booking",
            source_id=booking_id,
            event="BOOKING_CANCELLED",
            currency="EUR",
            lines=lines,
            occurred_at=occurred_at,
            created_by="system",
            meta={"booking_id": booking_id, "agency_id": agency_id},
        )

        return posting["_id"]

    async def post_refund_approved(
        self,
        organization_id: str,
        booking_id: str,
        case_id: str,
        agency_id: str,
        refund_amount: float,
        currency: str,
        occurred_at: Optional[datetime] = None,
    ) -> str:
        """Create EUR-denominated posting for REFUND_APPROVED event.

        `refund_amount` is expected to be in EUR already (approved.amount_eur).
        Accounts are still keyed by currency code for AR structure, but
        ledger currency is always EUR in Phase 2C.
        """

        eur_currency = "EUR"

        # Get or create agency AR account (AGENCY_AR_{agency_id}_{currency})
        agency_code = f"AGENCY_AR_{agency_id}_{eur_currency}"
        agency_filter = {
            "organization_id": organization_id,
            "type": "agency",
            "owner_id": agency_id,
            "code": agency_code,
            "currency": eur_currency,
        }
        now = now_utc()
        await self.db.finance_accounts.update_one(
            agency_filter,
            {
                "$setOnInsert": {
                    "organization_id": organization_id,
                    "type": "agency",
                    "owner_id": agency_id,
                    "code": agency_code,
                    "name": f"Agency AR {agency_id} {eur_currency}",
                    "currency": eur_currency,
                    "status": "active",
                    "created_at": now,
                    "updated_at": now,
                }
            },
            upsert=True,
        )
        agency_account = await self.db.finance_accounts.find_one(agency_filter)

        # Get or create platform AR account (PLATFORM_AR_{EUR})
        platform_code = f"PLATFORM_AR_{eur_currency}"
        platform_filter = {
            "organization_id": organization_id,
            "code": platform_code,
        }
        now = now_utc()
        await self.db.finance_accounts.update_one(
            platform_filter,
            {
                "$setOnInsert": {
                    "organization_id": organization_id,
                    "type": "platform",
                    "owner_id": "platform",
                    "code": platform_code,
                    "name": f"Platform AR {eur_currency}",
                    "currency": eur_currency,
                    "status": "active",
                    "created_at": now,
                    "updated_at": now,
                }
            },
            upsert=True,
        )
        platform_account = await self.db.finance_accounts.find_one(platform_filter)

        # Create posting lines (EUR)
        lines = PostingMatrixConfig.get_refund_approved_lines(
            agency_account_id=str(agency_account["_id"]),
            platform_ar_account_id=str(platform_account["_id"]),
            refund_amount=refund_amount,
        )

        # Post to ledger (EUR)
        posting = await LedgerPostingService.post_event(
            organization_id=organization_id,
            source_type="booking",
            source_id=booking_id,
            event="REFUND_APPROVED",
            currency=eur_currency,
            lines=lines,
            occurred_at=occurred_at,
            created_by="system",
            meta={"booking_id": booking_id, "agency_id": agency_id},
        )

        return posting["_id"]
