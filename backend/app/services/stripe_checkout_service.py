from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from urllib.parse import urlparse

from dotenv import load_dotenv
from emergentintegrations.payments.stripe.checkout import CheckoutSessionRequest, StripeCheckout

from app.db import get_db
from app.errors import AppError
from app.repositories.billing_repository import billing_repo
from app.services.audit_log_service import append_audit_log
from app.services.feature_service import feature_service

load_dotenv(override=False)

logger = logging.getLogger(__name__)

PLAN_CHECKOUT_MATRIX = {
    "starter": {
        "monthly": {"amount": 990.0, "currency": "try", "label": "Starter", "env_key": "STRIPE_PLAN_STARTER_MONTHLY"},
        "yearly": {"amount": 9900.0, "currency": "try", "label": "Starter", "env_key": "STRIPE_PLAN_STARTER_YEARLY"},
    },
    "pro": {
        "monthly": {"amount": 2490.0, "currency": "try", "label": "Pro", "env_key": "STRIPE_PLAN_PRO_MONTHLY"},
        "yearly": {"amount": 24900.0, "currency": "try", "label": "Pro", "env_key": "STRIPE_PLAN_PRO_YEARLY"},
    },
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _billing_mode() -> str:
    key = os.environ.get("STRIPE_API_KEY", "")
    return "live" if "live" in key else "test"


class StripeCheckoutService:
    def _api_key(self) -> str:
        api_key = (os.environ.get("STRIPE_API_KEY") or "").strip()
        if not api_key:
            raise AppError(500, "stripe_key_missing", "STRIPE_API_KEY tanımlı değil.", None)
        return api_key

    def _checkout_client(self, http_request) -> StripeCheckout:
        host_url = str(http_request.base_url).rstrip("/")
        webhook_url = f"{host_url}/api/webhook/stripe"
        return StripeCheckout(
            api_key=self._api_key(),
            webhook_secret=(os.environ.get("STRIPE_WEBHOOK_SECRET") or "").strip() or None,
            webhook_url=webhook_url,
        )

    def _validate_origin(self, origin_url: str) -> str:
        parsed = urlparse((origin_url or "").strip())
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise AppError(400, "invalid_origin_url", "Geçersiz origin bilgisi gönderildi.", {"origin_url": origin_url})
        return f"{parsed.scheme}://{parsed.netloc}"

    def _normalize_cancel_path(self, cancel_path: Optional[str]) -> str:
        path = (cancel_path or "/pricing").strip() or "/pricing"
        return path if path.startswith("/") else f"/{path}"

    def _plan_config(self, plan: str, interval: str) -> dict[str, Any]:
        config = PLAN_CHECKOUT_MATRIX.get(plan, {}).get(interval)
        if not config:
            raise AppError(422, "plan_not_checkout_enabled", "Bu plan için online ödeme aktif değil.", {"plan": plan, "interval": interval})
        return config

    async def _resolve_catalog_entry(self, plan: str, interval: str, amount: float, env_key: str) -> dict[str, Any]:
        price_id = (os.environ.get(env_key) or "").strip()
        if price_id:
            await billing_repo.upsert_plan_price(
                plan=plan,
                interval=interval,
                currency="TRY",
                amount=amount,
                provider_price_id=price_id,
                provider="stripe",
            )
            return {"provider_price_id": price_id, "amount": amount}

        existing = await billing_repo.get_plan_price(plan, interval=interval, currency="TRY")
        if existing:
            return existing

        synthetic_price_id = f"manual_{plan}_{interval}_try"
        await billing_repo.upsert_plan_price(
            plan=plan,
            interval=interval,
            currency="TRY",
            amount=amount,
            provider_price_id=synthetic_price_id,
            provider="stripe",
        )
        return {"provider_price_id": synthetic_price_id, "amount": amount}

    async def create_checkout_session(
        self,
        http_request,
        *,
        tenant_id: str,
        organization_id: str,
        user_id: str,
        user_email: str,
        plan: str,
        interval: str,
        origin_url: str,
        cancel_path: Optional[str],
        current_plan: Optional[str],
    ) -> dict[str, Any]:
        config = self._plan_config(plan, interval)
        amount = float(config["amount"])
        origin = self._validate_origin(origin_url)
        cancel_url = f"{origin}{self._normalize_cancel_path(cancel_path)}"
        success_url = f"{origin}/payment-success?session_id={{CHECKOUT_SESSION_ID}}"

        catalog_entry = await self._resolve_catalog_entry(plan, interval, amount, config["env_key"])
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

        checkout = self._checkout_client(http_request)
        session = await checkout.create_checkout_session(
            CheckoutSessionRequest(
                amount=amount,
                currency=str(config["currency"]),
                success_url=success_url,
                cancel_url=cancel_url,
                metadata=metadata,
                payment_methods=["card"],
            )
        )

        now = _now()
        db = await get_db()
        await db.payment_transactions.update_one(
            {"session_id": session.session_id},
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
                    "session_id": session.session_id,
                    "payment_id": session.session_id,
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
            "session_id": session.session_id,
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
        period_end = now + timedelta(days=365 if interval == "yearly" else 30)

        try:
            await feature_service.set_plan(tenant_id, plan)
            await billing_repo.upsert_customer(
                tenant_id=tenant_id,
                provider="stripe",
                provider_customer_id=f"checkout:{session_id}",
                email=user_email,
                mode=_billing_mode(),
            )
            await billing_repo.upsert_subscription(
                tenant_id=tenant_id,
                provider="stripe",
                provider_subscription_id=session_id,
                plan=plan,
                status="active",
                current_period_end=period_end.isoformat(),
                cancel_at_period_end=False,
                mode=_billing_mode(),
            )
            await db.subscriptions.update_one(
                {"org_id": organization_id},
                {
                    "$set": {
                        "org_id": organization_id,
                        "tenant_id": tenant_id,
                        "plan": plan,
                        "status": "active",
                        "billing_cycle": interval,
                        "billing_enabled": True,
                        "provider": "stripe",
                        "checkout_session_id": session_id,
                        "trial_end": None,
                        "period_start": now,
                        "period_end": period_end,
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
                        "current_period_end": period_end.isoformat(),
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
        checkout = self._checkout_client(http_request)
        checkout_status = await checkout.get_checkout_status(session_id)

        now = _now()
        db = await get_db()
        tx_doc = await db.payment_transactions.find_one({"session_id": session_id}, {"_id": 0})
        if not tx_doc:
            raise AppError(404, "checkout_session_not_found", "Checkout oturumu bulunamadı.", {"session_id": session_id})

        await db.payment_transactions.update_one(
            {"session_id": session_id},
            {
                "$set": {
                    "status": checkout_status.status,
                    "payment_status": checkout_status.payment_status,
                    "amount_total": checkout_status.amount_total,
                    "currency": checkout_status.currency,
                    "metadata": {**(tx_doc.get("metadata") or {}), **dict(checkout_status.metadata or {})},
                    "last_checked_at": now,
                    "updated_at": now,
                }
            },
        )

        activated = False
        if checkout_status.payment_status == "paid":
            activated = await self._apply_successful_checkout(session_id, tx_doc)

        refreshed = await db.payment_transactions.find_one({"session_id": session_id}, {"_id": 0})
        return {
            "session_id": session_id,
            "status": checkout_status.status,
            "payment_status": checkout_status.payment_status,
            "amount_total": checkout_status.amount_total,
            "currency": checkout_status.currency,
            "plan": refreshed.get("plan"),
            "interval": refreshed.get("interval"),
            "activated": activated or refreshed.get("fulfillment_status") == "processed",
            "fulfillment_status": refreshed.get("fulfillment_status"),
        }

    async def handle_webhook(self, http_request, payload: bytes, signature: Optional[str]) -> dict[str, Any]:
        checkout = self._checkout_client(http_request)
        webhook_response = await checkout.handle_webhook(payload, signature)
        if webhook_response.event_id:
            if await billing_repo.webhook_event_exists(webhook_response.event_id):
                return {"status": "already_processed", "event_id": webhook_response.event_id}
            await billing_repo.record_webhook_event(
                webhook_response.event_id,
                webhook_response.event_type,
                "stripe",
                {
                    "session_id": webhook_response.session_id,
                    "payment_status": webhook_response.payment_status,
                    "metadata": webhook_response.metadata,
                },
            )

        if webhook_response.session_id:
            await self.sync_checkout_status(http_request, webhook_response.session_id)

        return {
            "status": "ok",
            "event_id": webhook_response.event_id,
            "event_type": webhook_response.event_type,
            "session_id": webhook_response.session_id,
        }


stripe_checkout_service = StripeCheckoutService()