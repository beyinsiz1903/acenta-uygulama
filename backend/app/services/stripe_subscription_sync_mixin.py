"""Stripe checkout — subscription sync mixin (T009 / Task #3).

Owns:
- `_sync_subscription_document`  — pull a fresh Stripe Subscription, mirror
  it into `billing_subscriptions` and the legacy `subscriptions` collection.
- `_repair_customer_reference`   — backfill missing customer/subscription
  IDs from `payment_transactions` or by re-reading the original checkout
  session.
- `sync_provider_subscription_record` — public sync helper used by webhook
  handling and lifecycle ops; transparently demotes stale references.

Code paths are extracted verbatim from the original monolithic service —
no behavioural change.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import Any, Optional

from app.db import get_db
from app.repositories.billing_repository import billing_repo
from app.services.feature_service import feature_service
from app.services.stripe_checkout_helpers import (
    _billing_mode,
    _is_missing_stripe_resource_error,
    _is_real_customer_id,
    _is_real_subscription_id,
    _iso_from_unix,
    _now,
    _schedule_id,
    _stripe_value,
    _subscription_first_item,
)


class StripeSubscriptionSyncMixin:
    async def _sync_subscription_document(
        self,
        tenant_id: str,
        subscription_id: str,
        *,
        customer_id: Optional[str] = None,
        plan_hint: Optional[str] = None,
        interval_hint: Optional[str] = None,
        user_email: str = "",
        organization_id: str = "",
    ) -> dict[str, Any]:
        if not _is_real_subscription_id(subscription_id):
            return (await billing_repo.get_subscription(tenant_id)) or {}

        sub = await self._retrieve_subscription(subscription_id)
        item = _subscription_first_item(sub)
        price = _stripe_value(item, "price")
        price_id = _stripe_value(price, "id")
        price_doc = await billing_repo.get_plan_price_by_provider_price_id(price_id) if price_id else None
        existing = await billing_repo.get_subscription(tenant_id)
        plan = (price_doc or {}).get("plan") or plan_hint or (existing or {}).get("plan") or "starter"
        interval = (price_doc or {}).get("interval") or interval_hint or (existing or {}).get("interval") or "monthly"
        provider_customer_id = customer_id or (sub.customer if isinstance(sub.customer, str) else getattr(sub.customer, "id", None))
        current_period_end = _iso_from_unix(_stripe_value(sub, "current_period_end")) or _iso_from_unix(_stripe_value(item, "current_period_end")) or _iso_from_unix(_stripe_value(sub, "cancel_at"))
        current_period_start = _iso_from_unix(_stripe_value(sub, "current_period_start")) or _iso_from_unix(_stripe_value(item, "current_period_start")) or _iso_from_unix(_stripe_value(sub, "start_date"))
        schedule_id = _schedule_id(getattr(sub, "schedule", None))

        if provider_customer_id and _is_real_customer_id(provider_customer_id):
            customer_doc = await billing_repo.get_customer(tenant_id)
            await billing_repo.upsert_customer(
                tenant_id=tenant_id,
                provider="stripe",
                provider_customer_id=provider_customer_id,
                email=user_email or str((customer_doc or {}).get("email") or ""),
                mode=_billing_mode(),
            )

        synced = await billing_repo.upsert_subscription(
            tenant_id=tenant_id,
            provider="stripe",
            provider_subscription_id=subscription_id,
            plan=plan,
            status=str(getattr(sub, "status", "active") or "active"),
            current_period_end=current_period_end,
            cancel_at_period_end=bool(getattr(sub, "cancel_at_period_end", False)),
            mode=_billing_mode(),
            interval=interval,
            provider_price_id=price_id,
            provider_customer_id=provider_customer_id,
            current_period_start=current_period_start,
            schedule_id=schedule_id,
            clear_scheduled_change=bool(
                existing
                and existing.get("scheduled_plan") == plan
                and existing.get("scheduled_interval") == interval
            ),
        )

        await feature_service.set_plan(tenant_id, plan)

        org_id = organization_id or await self._resolve_org_id_for_tenant(tenant_id)
        if org_id:
            db = await get_db()
            period_end_dt = datetime.fromisoformat(current_period_end) if current_period_end else _now() + timedelta(days=30)
            period_start_dt = datetime.fromisoformat(current_period_start) if current_period_start else _now()
            await db.subscriptions.update_one(
                {"org_id": org_id},
                {
                    "$set": {
                        "org_id": org_id,
                        "tenant_id": tenant_id,
                        "plan": plan,
                        "status": synced.get("status") or "active",
                        "billing_cycle": interval,
                        "billing_enabled": True,
                        "provider": "stripe",
                        "provider_subscription_id": subscription_id,
                        "provider_customer_id": provider_customer_id,
                        "period_start": period_start_dt,
                        "period_end": period_end_dt,
                        "updated_at": _now(),
                    },
                    "$setOnInsert": {
                        "_id": str(uuid.uuid4()),
                        "created_at": _now(),
                    },
                },
                upsert=True,
            )

        return (await billing_repo.get_subscription(tenant_id)) or synced or {}

    async def _repair_customer_reference(self, tenant_id: str, user_email: str = "") -> dict[str, Any]:
        customer = await billing_repo.get_customer(tenant_id)
        subscription = await billing_repo.get_subscription(tenant_id)
        customer_id = str((customer or {}).get("provider_customer_id") or "")
        subscription_id = str((subscription or {}).get("provider_subscription_id") or "")
        if _is_real_customer_id(customer_id) and (
            not subscription or _is_real_subscription_id(subscription_id)
        ):
            return {
                "customer_id": customer_id,
                "subscription_id": subscription_id,
            }

        db = await get_db()
        tx = await db.payment_transactions.find_one(
            {"tenant_id": tenant_id},
            {
                "_id": 0,
                "session_id": 1,
                "plan": 1,
                "interval": 1,
                "organization_id": 1,
                "provider_customer_id": 1,
                "provider_subscription_id": 1,
            },
            sort=[("processed_at", -1), ("updated_at", -1)],
        )

        tx_customer_id = str((tx or {}).get("provider_customer_id") or "")
        tx_subscription_id = str((tx or {}).get("provider_subscription_id") or "")

        if not _is_real_customer_id(customer_id) and _is_real_customer_id(tx_customer_id):
            customer_id = tx_customer_id
            await billing_repo.upsert_customer(
                tenant_id=tenant_id,
                provider="stripe",
                provider_customer_id=customer_id,
                email=user_email or str((customer or {}).get("email") or ""),
                mode=_billing_mode(),
            )

        if not _is_real_subscription_id(subscription_id) and _is_real_subscription_id(tx_subscription_id):
            try:
                await self._sync_subscription_document(
                    tenant_id,
                    tx_subscription_id,
                    customer_id=customer_id or None,
                    plan_hint=str((tx or {}).get("plan") or (subscription or {}).get("plan") or "starter"),
                    interval_hint=str((tx or {}).get("interval") or (subscription or {}).get("interval") or "monthly"),
                    user_email=user_email,
                    organization_id=str((tx or {}).get("organization_id") or ""),
                )
                subscription_id = tx_subscription_id
            except Exception as exc:
                if not _is_missing_stripe_resource_error(exc):
                    raise

        if _is_real_customer_id(customer_id) and _is_real_subscription_id(subscription_id):
            return {"customer_id": customer_id, "subscription_id": subscription_id}

        session_id = str((tx or {}).get("session_id") or "")
        if not session_id.startswith("cs_"):
            return {
                "customer_id": customer_id,
                "subscription_id": subscription_id,
            }

        try:
            session = await self._retrieve_checkout_session(session_id)
        except Exception:
            return {
                "customer_id": customer_id,
                "subscription_id": subscription_id,
            }

        session_customer_id = session.customer if isinstance(session.customer, str) else getattr(session.customer, "id", None)
        session_subscription_id = session.subscription if isinstance(session.subscription, str) else getattr(session.subscription, "id", None)

        if _is_real_customer_id(session_customer_id):
            customer_id = session_customer_id

        if _is_real_subscription_id(session_subscription_id):
            subscription_id = session_subscription_id

        if _is_real_customer_id(customer_id):
            await billing_repo.upsert_customer(
                tenant_id=tenant_id,
                provider="stripe",
                provider_customer_id=customer_id,
                email=user_email or str((customer or {}).get("email") or ""),
                mode=_billing_mode(),
            )

        if _is_real_subscription_id(subscription_id):
            await self._sync_subscription_document(
                tenant_id,
                subscription_id,
                customer_id=customer_id or None,
                plan_hint=str((tx or {}).get("plan") or (subscription or {}).get("plan") or "starter"),
                interval_hint=str((tx or {}).get("interval") or (subscription or {}).get("interval") or "monthly"),
                user_email=user_email,
                organization_id=str((tx or {}).get("organization_id") or ""),
            )

        return {"customer_id": customer_id, "subscription_id": subscription_id}

    async def sync_provider_subscription_record(self, tenant_id: str, provider_subscription_id: str, *, user_email: str = "", organization_id: str = "") -> dict[str, Any]:
        try:
            return await self._sync_subscription_document(
                tenant_id,
                provider_subscription_id,
                user_email=user_email,
                organization_id=organization_id,
            )
        except Exception as exc:
            if _is_missing_stripe_resource_error(exc):
                return await self._demote_stale_subscription_reference(tenant_id)
            raise
