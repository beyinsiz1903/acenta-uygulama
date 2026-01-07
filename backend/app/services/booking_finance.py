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
        """
        Create ledger posting for BOOKING_CONFIRMED event.
        
        Returns:
            posting_id
        """
        
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
        
        # Create posting lines
        lines = PostingMatrixConfig.get_booking_confirmed_lines(
            agency_account_id=agency_account["_id"],
            platform_account_id=platform_account["_id"],
            sell_amount=sell_amount,
        )
        
        # Post to ledger
        posting = await LedgerPostingService.post_event(
            organization_id=organization_id,
            source_type="booking",
            source_id=booking_id,
            event="BOOKING_CONFIRMED",
            currency=currency,
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
        agency_id: str,
        refund_amount: float,
        currency: str,
        occurred_at: Optional[datetime] = None,
    ) -> str:
        """
        Create ledger posting for REFUND_APPROVED event.
        
        Returns:
            posting_id
        """
        
        # Get or create agency AR account (AGENCY_AR_{agency_id}_{currency})
        agency_code = f"AGENCY_AR_{agency_id}_{currency}"
        agency_account = await self.db.finance_accounts.find_one(
            {
                "organization_id": organization_id,
                "type": "agency",
                "owner_id": agency_id,
                "code": agency_code,
                "currency": currency,
            }
        )
        if not agency_account:
            now = datetime.utcnow()
            agency_account_id = ObjectId()
            agency_account = {
                "_id": agency_account_id,
                "organization_id": organization_id,
                "type": "agency",
                "owner_id": agency_id,
                "code": agency_code,
                "name": f"Agency AR {agency_id} {currency}",
                "currency": currency,
                "status": "active",
                "created_at": now,
                "updated_at": now,
            }
            await self.db.finance_accounts.insert_one(agency_account)

        # Get or create platform AR account (PLATFORM_AR_{currency})
        platform_code = f"PLATFORM_AR_{currency}"
        platform_account = await self.db.finance_accounts.find_one(
            {
                "organization_id": organization_id,
                "type": "platform",
                "owner_id": "platform",
                "code": platform_code,
                "currency": currency,
            }
        )
        if not platform_account:
            now = datetime.utcnow()
            platform_account_id = ObjectId()
            platform_account = {
                "_id": platform_account_id,
                "organization_id": organization_id,
                "type": "platform",
                "owner_id": "platform",
                "code": platform_code,
                "name": f"Platform AR {currency}",
                "currency": currency,
                "status": "active",
                "created_at": now,
                "updated_at": now,
            }
            await self.db.finance_accounts.insert_one(platform_account)
        
        # Create posting lines
        lines = PostingMatrixConfig.get_refund_approved_lines(
            agency_account_id=str(agency_account["_id"]),
            platform_ar_account_id=str(platform_account["_id"]),
            refund_amount=refund_amount,
        )
        
        # Post to ledger
        posting = await LedgerPostingService.post_event(
            organization_id=organization_id,
            source_type="booking",
            source_id=booking_id,
            event="REFUND_APPROVED",
            currency=currency,
            lines=lines,
            occurred_at=occurred_at,
            created_by="system",
            meta={"booking_id": booking_id, "agency_id": agency_id},
        )
        
        return posting["_id"]
