from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from app.db import get_db


class BillingRepository:
  """Repository for billing_customers, billing_subscriptions, billing_plan_catalog, billing_webhook_events."""

  async def _db(self):
    return await get_db()

  # --- Customers ---

  async def get_customer(self, tenant_id: str) -> Optional[Dict[str, Any]]:
    db = await self._db()
    return await db.billing_customers.find_one({"tenant_id": tenant_id}, {"_id": 0})

  async def upsert_customer(self, tenant_id: str, provider: str, provider_customer_id: str, email: str, mode: str = "test") -> Dict[str, Any]:
    db = await self._db()
    now = datetime.now(timezone.utc)
    doc = {
      "tenant_id": tenant_id,
      "provider": provider,
      "provider_customer_id": provider_customer_id,
      "email": email,
      "mode": mode,
      "updated_at": now,
    }
    await db.billing_customers.update_one(
      {"tenant_id": tenant_id},
      {"$set": doc, "$setOnInsert": {"created_at": now}},
      upsert=True,
    )
    return await self.get_customer(tenant_id)

  # --- Subscriptions ---

  async def get_subscription(self, tenant_id: str) -> Optional[Dict[str, Any]]:
    db = await self._db()
    return await db.billing_subscriptions.find_one({"tenant_id": tenant_id}, {"_id": 0})

  async def upsert_subscription(
    self,
    tenant_id: str,
    provider: str,
    provider_subscription_id: str,
    plan: str,
    status: str,
    current_period_end: Optional[str] = None,
    cancel_at_period_end: bool = False,
    mode: str = "test",
    grace_period_until: Optional[str] = None,
  ) -> Dict[str, Any]:
    db = await self._db()
    now = datetime.now(timezone.utc)
    doc = {
      "tenant_id": tenant_id,
      "provider": provider,
      "provider_subscription_id": provider_subscription_id,
      "plan": plan,
      "status": status,
      "current_period_end": current_period_end,
      "cancel_at_period_end": cancel_at_period_end,
      "mode": mode,
      "grace_period_until": grace_period_until,
      "updated_at": now,
    }
    await db.billing_subscriptions.update_one(
      {"tenant_id": tenant_id},
      {"$set": doc, "$setOnInsert": {"created_at": now}},
      upsert=True,
    )
    return await self.get_subscription(tenant_id)

  async def update_subscription_status(self, tenant_id: str, status: str, cancel_at_period_end: Optional[bool] = None) -> Optional[Dict[str, Any]]:
    db = await self._db()
    update: Dict[str, Any] = {"status": status, "updated_at": datetime.now(timezone.utc)}
    if cancel_at_period_end is not None:
      update["cancel_at_period_end"] = cancel_at_period_end
    await db.billing_subscriptions.update_one({"tenant_id": tenant_id}, {"$set": update})
    return await self.get_subscription(tenant_id)

  # --- Plan Catalog ---

  async def get_plan_catalog(self, active_only: bool = True) -> List[Dict[str, Any]]:
    db = await self._db()
    flt = {"active": True} if active_only else {}
    cursor = db.billing_plan_catalog.find(flt, {"_id": 0})
    return await cursor.to_list(length=100)

  async def get_plan_price(self, plan: str, interval: str = "monthly", currency: str = "TRY") -> Optional[Dict[str, Any]]:
    db = await self._db()
    return await db.billing_plan_catalog.find_one(
      {"plan": plan, "interval": interval, "currency": currency, "active": True},
      {"_id": 0},
    )

  async def upsert_plan_price(self, plan: str, interval: str, currency: str, amount: float, provider_price_id: str, provider: str = "stripe") -> Dict[str, Any]:
    db = await self._db()
    now = datetime.now(timezone.utc)
    doc = {
      "plan": plan,
      "interval": interval,
      "currency": currency,
      "amount": amount,
      "provider": provider,
      "provider_price_id": provider_price_id,
      "active": True,
      "updated_at": now,
    }
    await db.billing_plan_catalog.update_one(
      {"plan": plan, "interval": interval, "currency": currency},
      {"$set": doc, "$setOnInsert": {"created_at": now}},
      upsert=True,
    )
    return doc

  # --- Webhook Events (idempotency) ---

  async def webhook_event_exists(self, provider_event_id: str) -> bool:
    db = await self._db()
    return await db.billing_webhook_events.find_one({"provider_event_id": provider_event_id}) is not None

  async def record_webhook_event(self, provider_event_id: str, event_type: str, provider: str, payload: Optional[Dict] = None) -> None:
    db = await self._db()
    now = datetime.now(timezone.utc)
    await db.billing_webhook_events.update_one(
      {"provider_event_id": provider_event_id},
      {"$setOnInsert": {
        "provider_event_id": provider_event_id,
        "event_type": event_type,
        "provider": provider,
        "payload": payload or {},
        "created_at": now,
      }},
      upsert=True,
    )

  # --- Indexes ---

  async def ensure_indexes(self) -> None:
    db = await self._db()
    await db.billing_customers.create_index("tenant_id", unique=True)
    await db.billing_subscriptions.create_index("tenant_id", unique=True)
    await db.billing_subscriptions.create_index("provider_subscription_id")
    await db.billing_plan_catalog.create_index([("plan", 1), ("interval", 1), ("currency", 1)], unique=True)
    await db.billing_webhook_events.create_index("provider_event_id", unique=True)


billing_repo = BillingRepository()
