"""
Supplier Finance Service (Phase 2A.1)
Auto-creates and manages supplier finance accounts

CRITICAL FIXES APPLIED:
1. account_id = ObjectId (not string compose)
2. balance_id = ObjectId (not hash)
3. NO product_id fallback (explicit supplier_id required)
"""
from __future__ import annotations

from bson import ObjectId
from app.errors import AppError
from app.utils import now_utc
import logging

logger = logging.getLogger(__name__)


class SupplierFinanceService:
    """
    Manages supplier finance accounts with production-grade guarantees:
    - Auto-create on first booking
    - Currency-scoped accounts
    - Balance tracking (credit - debit for payables)
    """
    
    def __init__(self, db):
        self.db = db
    
    async def get_or_create_supplier_account(
        self,
        organization_id: str,
        supplier_id: str,
        currency: str,
    ) -> str:
        """
        Get supplier finance account or create if not exists.
        
        Unique constraint: (org, type="supplier", owner_id, currency)
        
        Returns:
            account_id (str representation of ObjectId)
        """
        # Check if account exists
        account = await self.db.finance_accounts.find_one({
            "organization_id": organization_id,
            "type": "supplier",
            "owner_id": supplier_id,
            "currency": currency,
        })
        
        if account:
            return str(account["_id"])
        
        # Get supplier details
        supplier = await self.db.suppliers.find_one({
            "_id": supplier_id,
            "organization_id": organization_id,
        })
        
        if not supplier:
            raise AppError(
                status_code=404,
                code="supplier_not_found",
                message=f"Supplier {supplier_id} not found",
            )
        
        # Create account with ObjectId
        account_id = ObjectId()
        account_code = f"SUPP_{supplier_id[:8]}_{currency}"
        now = now_utc()
        
        account_doc = {
            "_id": account_id,
            "organization_id": organization_id,
            "type": "supplier",
            "owner_id": supplier_id,
            "code": account_code,
            "name": f"{supplier.get('name', 'Supplier')} Payables ({currency})",
            "currency": currency,
            "status": "active",
            "created_at": now,
            "updated_at": now,
        }
        
        try:
            await self.db.finance_accounts.insert_one(account_doc)
            logger.info(f"Created supplier account: {account_id} for supplier {supplier_id}")
        except Exception as e:
            # Check if duplicate (race condition)
            existing = await self.db.finance_accounts.find_one({
                "organization_id": organization_id,
                "type": "supplier",
                "owner_id": supplier_id,
                "currency": currency,
            })
            if existing:
                logger.warning(f"Supplier account already exists (race condition): {existing['_id']}")
                return str(existing["_id"])
            raise
        
        # Initialize balance cache with ObjectId
        balance_id = ObjectId()
        balance_doc = {
            "_id": balance_id,
            "organization_id": organization_id,
            "account_id": str(account_id),
            "currency": currency,
            "balance": 0.0,
            "as_of": now,
            "updated_at": now,
        }
        
        try:
            await self.db.account_balances.insert_one(balance_doc)
        except Exception as e:
            # Balance insert failed, but account created - log and continue
            logger.error(f"Failed to create balance for account {account_id}: {e}")
        
        return str(account_id)
    
    async def get_supplier_accounts(
        self,
        organization_id: str,
        supplier_id: str,
    ) -> list:
        """Get all finance accounts for supplier (by currency)"""
        cursor = self.db.finance_accounts.find({
            "organization_id": organization_id,
            "type": "supplier",
            "owner_id": supplier_id,
        }).sort("currency", 1)
        
        docs = await cursor.to_list(length=100)
        
        # Convert ObjectId to string for JSON serialization
        for doc in docs:
            doc["account_id"] = str(doc["_id"])
        
        return docs
    
    async def get_supplier_balance(
        self,
        organization_id: str,
        supplier_id: str,
        currency: str,
    ) -> float:
        """
        Get supplier payable balance.
        
        Balance rule: credit - debit (higher credit = more payable)
        """
        account = await self.db.finance_accounts.find_one({
            "organization_id": organization_id,
            "type": "supplier",
            "owner_id": supplier_id,
            "currency": currency,
        })
        
        if not account:
            return 0.0
        
        balance = await self.db.account_balances.find_one({
            "organization_id": organization_id,
            "account_id": str(account["_id"]),
            "currency": currency,
        })
        
        return balance["balance"] if balance else 0.0
    
    async def get_all_supplier_balances(
        self,
        organization_id: str,
        currency: str = "EUR",
    ) -> list:
        """
        Get all supplier balances (for payable summary dashboard)
        
        Returns list of {supplier_id, supplier_name, balance}
        """
        # Get all supplier accounts for currency
        accounts_cursor = self.db.finance_accounts.find({
            "organization_id": organization_id,
            "type": "supplier",
            "currency": currency,
        })
        
        accounts = await accounts_cursor.to_list(length=1000)
        
        results = []
        for account in accounts:
            supplier_id = account["owner_id"]
            account_id = str(account["_id"])
            
            # Get balance
            balance = await self.db.account_balances.find_one({
                "organization_id": organization_id,
                "account_id": account_id,
                "currency": currency,
            })
            
            balance_amount = balance["balance"] if balance else 0.0
            
            # Only include if balance > 0 (outstanding payables)
            if balance_amount > 0:
                # Get supplier name
                supplier = await self.db.suppliers.find_one({"_id": supplier_id})
                supplier_name = supplier.get("name", "Unknown") if supplier else "Unknown"
                
                results.append({
                    "supplier_id": supplier_id,
                    "supplier_name": supplier_name,
                    "currency": currency,
                    "balance": balance_amount,
                })
        
        # Sort by balance desc (highest payables first)
        results.sort(key=lambda x: x["balance"], reverse=True)
        
        return results
