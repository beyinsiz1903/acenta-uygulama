"""Stripe checkout — session lifecycle mixin (T009 / Task #3).

Owns the Checkout Session lifecycle:
- `create_checkout_session`     — create a hosted Stripe Checkout Session.
- `_apply_successful_checkout`  — mirror a paid session into our billing
  collections (idempotent via `fulfillment_status`).
- `sync_checkout_status`        — refresh a session's status from Stripe
  and trigger fulfilment when payment becomes paid.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta
from typing import Any

import stripe

from app.db import get_db
from app.errors import AppError
from app.repositories.billing_repository import billing_repo
from app.services.audit_log_service import append_audit_log
from app.services.feature_service import feature_service
from app.services.stripe_checkout_helpers import (
    _billing_mode,
    _is_missing_stripe_resource_error,
    _is_real_customer_id,
    _is_real_subscription_id,
    _now,
)

logger = logging.getLogger(__name__)


class StripeSessionMixin:
    async def create_checkout_session(
        self,
        http_request=None,
        *,
        tenant_id: str,
        organization_id: str,
        user_id: str,
        user_email: str,
        plan: str,
        interval: str,
        origin_url: str,
        cancel_path: str | None,
        current_plan: str | None,
    ) -> dict[str, Any]:
        config = self._plan_config(plan, interval)
        amount = float(config["amount"])
        origin = self._validate_origin(origin_url)
        cancel_url = f"{origin}{self._normalize_path(cancel_path, '/pricing')}"
        success_url = f"{origin}/payment-success?session_id={{CHECKOUT_SESSION_ID}}"
        catalog_entry = await self._ensure_recurring_price(plan, interval)
        metadata = {
            "tenant_id": str(tenant_id),
            "organization_id": str(organization_id),
            "user_id": str(user_id),
            "user_email": str(user_email),
            "plan": plan,
            "interval": interval,
            "source": "saas_billing_checkout",
            "current_plan": str(current_plan or "trial"),
        }
        customer_id = await self._get_real_customer_id(tenant_id)

        create_kwargs = {
            "payment_method_types": ["card"],
            "line_items": [{"price": catalog_entry["provider_price_id"], "quantity": 1}],
            "mode": "subscription",
            "success_url": success_url,
            "cancel_url": cancel_url,
            "metadata": metadata,
            "subscription_data": {"metadata": metadata},
        }
        if customer_id:
            create_kwargs["customer"] = customer_id
        elif user_email:
            create_kwargs["customer_email"] = user_email

        try:
            session = await self._stripe_call(stripe.checkout.Session.create, **create_kwargs)
        except Exception as exc:
            if customer_id and _is_missing_stripe_resource_error(exc):
                # Stale customer reference - clear it and retry with customer_email
                await self._clear_stale_customer_reference(tenant_id)
                del create_kwargs["customer"]
                if user_email:
                    create_kwargs["customer_email"] = user_email
                session = await self._stripe_call(stripe.checkout.Session.create, **create_kwargs)
            else:
                raise

        now = _now()
        db = await get_db()
        await db.payment_transactions.update_one(
            {"session_id": session.id},
            {
                "$setOnInsert": {
                    "_id": str(uuid.uuid4()),
                    "provider": "stripe",
                    "tenant_id": tenant_id,
                    "organization_id": organization_id,
                    "user_id": user_id,
                    "user_email": user_email,
                    "plan": plan,
                    "interval": interval,
                    "plan_label": config["label"],
                    "amount": amount,
                    "amount_total": int(amount * 100),
                    "currency": str(config["currency"]),
                    "session_id": session.id,
                    "payment_id": session.id,
                    "payment_status": "pending",
                    "status": "initiated",
                    "fulfillment_status": "pending",
                    "checkout_url": session.url,
                    "provider_price_id": catalog_entry.get("provider_price_id"),
                    "metadata": metadata,
                    "created_at": now,
                },
                "$set": {"updated_at": now},
            },
            upsert=True,
        )

        return {
            "url": session.url,
            "session_id": session.id,
            "plan": plan,
            "interval": interval,
            "amount": amount,
            "currency": str(config["currency"]),
        }

    async def _apply_successful_checkout(self, session_id: str, tx_doc: dict[str, Any]) -> bool:
        db = await get_db()
        now = _now()
        lock = await db.payment_transactions.update_one(
            {
                "session_id": session_id,
                "fulfillment_status": {"$in": [None, "pending", "initiated", "processing_failed"]},
            },
            {
                "$set": {
                    "fulfillment_status": "processing",
                    "processing_started_at": now,
                    "updated_at": now,
                }
            },
        )
        if lock.modified_count == 0:
            existing = await db.payment_transactions.find_one({"session_id": session_id}, {"_id": 0, "fulfillment_status": 1})
            return bool(existing and existing.get("fulfillment_status") == "processed")

        tenant_id = str(tx_doc.get("tenant_id") or "")
        organization_id = str(tx_doc.get("organization_id") or "")
        user_id = str(tx_doc.get("user_id") or "")
        user_email = str(tx_doc.get("user_email") or "")
        plan = str(tx_doc.get("plan") or "")
        interval = str(tx_doc.get("interval") or "monthly")

        try:
            session = await self._retrieve_checkout_session(session_id)
            customer_id = session.customer if isinstance(session.customer, str) else getattr(session.customer, "id", None)
            subscription_id = session.subscription if isinstance(session.subscription, str) else getattr(session.subscription, "id", None)

            current_period_end = None
            current_period_start = None
            schedule_id = None
            subscription_status = "active"

            if customer_id and _is_real_customer_id(customer_id):
                await billing_repo.upsert_customer(
                    tenant_id=tenant_id,
                    provider="stripe",
                    provider_customer_id=customer_id,
                    email=user_email,
                    mode=_billing_mode(),
                )

            if subscription_id and _is_real_subscription_id(subscription_id):
                synced = await self._sync_subscription_document(
                    tenant_id,
                    subscription_id,
                    customer_id=customer_id,
                    plan_hint=plan,
                    interval_hint=interval,
                    user_email=user_email,
                    organization_id=organization_id,
                )
                current_period_end = synced.get("current_period_end")
                current_period_start = synced.get("current_period_start")
                schedule_id = synced.get("schedule_id")
                subscription_status = str(synced.get("status") or "active")
            else:
                fallback_period_end = now + timedelta(days=365 if interval == "yearly" else 30)
                current_period_end = fallback_period_end.isoformat()
                current_period_start = now.isoformat()
                await billing_repo.upsert_customer(
                    tenant_id=tenant_id,
                    provider="stripe",
                    provider_customer_id=customer_id or f"checkout:{session_id}",
                    email=user_email,
                    mode=_billing_mode(),
                )
                await billing_repo.upsert_subscription(
                    tenant_id=tenant_id,
                    provider="stripe",
                    provider_subscription_id=session_id,
                    plan=plan,
                    status="active",
                    current_period_end=current_period_end,
                    cancel_at_period_end=False,
                    mode=_billing_mode(),
                    interval=interval,
                    provider_price_id=str(tx_doc.get("provider_price_id") or ""),
                    provider_customer_id=customer_id or f"checkout:{session_id}",
                    current_period_start=current_period_start,
                )
                await feature_service.set_plan(tenant_id, plan)

            period_end_dt = datetime.fromisoformat(current_period_end) if current_period_end else now + timedelta(days=30)
            period_start_dt = datetime.fromisoformat(current_period_start) if current_period_start else now
            await db.subscriptions.update_one(
                {"org_id": organization_id},
                {
                    "$set": {
                        "org_id": organization_id,
                        "tenant_id": tenant_id,
                        "plan": plan,
                        "status": subscription_status,
                        "billing_cycle": interval,
                        "billing_enabled": True,
                        "provider": "stripe",
                        "provider_subscription_id": subscription_id or session_id,
                        "provider_customer_id": customer_id or f"checkout:{session_id}",
                        "checkout_session_id": session_id,
                        "trial_end": None,
                        "period_start": period_start_dt,
                        "period_end": period_end_dt,
                        "updated_at": now,
                    },
                    "$setOnInsert": {
                        "_id": str(uuid.uuid4()),
                        "created_at": now,
                    },
                },
                upsert=True,
            )
            await db.payment_transactions.update_one(
                {"session_id": session_id},
                {
                    "$set": {
                        "fulfillment_status": "processed",
                        "processed_at": now,
                        "activated_plan": plan,
                        "current_period_end": current_period_end,
                        "provider_customer_id": customer_id,
                        "provider_subscription_id": subscription_id,
                        "schedule_id": schedule_id,
                        "updated_at": now,
                    }
                },
            )
            await append_audit_log(
                scope="billing",
                tenant_id=tenant_id,
                actor_user_id=user_id,
                actor_email=user_email,
                action="billing.checkout_completed",
                before={"plan": tx_doc.get("metadata", {}).get("current_plan")},
                after={"plan": plan, "interval": interval, "session_id": session_id},
                metadata={"source": "stripe_checkout"},
            )
            return True
        except Exception as exc:
            logger.exception("checkout fulfillment failed for session %s", session_id)
            await db.payment_transactions.update_one(
                {"session_id": session_id},
                {
                    "$set": {
                        "fulfillment_status": "processing_failed",
                        "fulfillment_error": str(exc)[:500],
                        "updated_at": now,
                    }
                },
            )
            raise

    async def sync_checkout_status(self, http_request, session_id: str) -> dict[str, Any]:
        session = await self._retrieve_checkout_session(session_id)
        now = _now()
        db = await get_db()
        tx_doc = await db.payment_transactions.find_one({"session_id": session_id}, {"_id": 0})
        if not tx_doc:
            raise AppError(404, "checkout_session_not_found", "Checkout oturumu bulunamadı.", {"session_id": session_id})

        metadata = {**(tx_doc.get("metadata") or {}), **dict(getattr(session, "metadata", {}) or {})}
        await db.payment_transactions.update_one(
            {"session_id": session_id},
            {
                "$set": {
                    "status": str(getattr(session, "status", "open") or "open"),
                    "payment_status": str(getattr(session, "payment_status", "unpaid") or "unpaid"),
                    "amount_total": int(getattr(session, "amount_total", tx_doc.get("amount_total", 0)) or 0),
                    "currency": str(getattr(session, "currency", tx_doc.get("currency", "try")) or tx_doc.get("currency", "try")),
                    "metadata": metadata,
                    "last_checked_at": now,
                    "updated_at": now,
                }
            },
        )

        activated = False
        if str(getattr(session, "payment_status", "")) == "paid":
            activated = await self._apply_successful_checkout(session_id, tx_doc)

        refreshed = await db.payment_transactions.find_one({"session_id": session_id}, {"_id": 0}) or tx_doc
        return {
            "session_id": session_id,
            "status": str(getattr(session, "status", "open") or "open"),
            "payment_status": str(getattr(session, "payment_status", "unpaid") or "unpaid"),
            "amount_total": int(getattr(session, "amount_total", refreshed.get("amount_total", 0)) or 0),
            "currency": str(getattr(session, "currency", refreshed.get("currency", "try")) or refreshed.get("currency", "try")),
            "plan": refreshed.get("plan"),
            "interval": refreshed.get("interval"),
            "activated": activated or refreshed.get("fulfillment_status") == "processed",
            "fulfillment_status": refreshed.get("fulfillment_status"),
        }
