"""Stripe checkout — base/foundation mixin (T009 / Task #3).

Holds the cross-cutting helpers that every other Stripe mixin depends on:
- Stripe SDK configuration & thread-pool wrapping (`_stripe_call`).
- Origin/path validation, plan→price lookup helpers.
- Customer / subscription reference repair primitives shared by the
  lifecycle, plan-change, and portal mixins.

Methods here are extracted verbatim from the original
`StripeCheckoutService` class so that signatures, error codes, audit log
calls, and stored field names remain bit-for-bit identical.
"""
from __future__ import annotations

import logging
import os
from typing import Any, Optional
from urllib.parse import urlparse

import anyio
import stripe

try:
    from emergentintegrations.payments.stripe.checkout import StripeCheckout
except ImportError:
    StripeCheckout = None  # type: ignore[misc,assignment]

from app.db import get_db
from app.errors import AppError
from app.repositories.billing_repository import billing_repo
from app.services.stripe_checkout_helpers import (
    _interval_label,
    _is_missing_stripe_resource_error,
    _is_real_customer_id,
    _is_real_price_id,
    _now,
)

logger = logging.getLogger(__name__)

PLAN_CHECKOUT_MATRIX = {
    "starter": {
        "monthly": {"amount": 990.0, "currency": "try", "label": "Starter"},
        "yearly": {"amount": 9900.0, "currency": "try", "label": "Starter"},
    },
    "pro": {
        "monthly": {"amount": 2490.0, "currency": "try", "label": "Pro"},
        "yearly": {"amount": 24900.0, "currency": "try", "label": "Pro"},
    },
}

STRIPE_PROXY_BASE = "https://api.stripe.com"
PORTAL_CONFIG_MARKER = {"app": "syroce", "managed_by": "billing_lifecycle"}


class StripeBaseMixin:
    def _api_key(self) -> str:
        api_key = (os.environ.get("STRIPE_API_KEY") or "").strip()
        if not api_key:
            raise AppError(500, "stripe_key_missing", "STRIPE_API_KEY tanımlı değil.", None)
        return api_key

    def _configure_stripe_sdk(self) -> None:
        stripe.api_key = self._api_key()
        if "sk_test_emergent" in stripe.api_key:
            stripe.api_base = STRIPE_PROXY_BASE

    async def _stripe_call(self, func, *args, **kwargs):
        self._configure_stripe_sdk()
        return await anyio.to_thread.run_sync(lambda: func(*args, **kwargs))

    def _checkout_client(self, http_request) -> "StripeCheckout":
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

    def _normalize_path(self, path: Optional[str], default_path: str) -> str:
        value = (path or default_path).strip() or default_path
        return value if value.startswith("/") else f"/{value}"

    def _plan_config(self, plan: str, interval: str) -> dict[str, Any]:
        config = PLAN_CHECKOUT_MATRIX.get(plan, {}).get(interval)
        if not config:
            raise AppError(422, "plan_not_checkout_enabled", "Bu plan için online ödeme aktif değil.", {"plan": plan, "interval": interval})
        return config

    async def _get_real_customer_id(self, tenant_id: str) -> Optional[str]:
        customer = await billing_repo.get_customer(tenant_id)
        customer_id = (customer or {}).get("provider_customer_id")
        return customer_id if _is_real_customer_id(customer_id) else None

    async def _resolve_org_id_for_tenant(self, tenant_id: str) -> str:
        db = await get_db()
        tenant = await db.tenants.find_one({"_id": tenant_id}, {"_id": 0, "organization_id": 1})
        return str((tenant or {}).get("organization_id") or "")

    async def _ensure_portal_configuration(self) -> str:
        configs = await self._stripe_call(stripe.billing_portal.Configuration.list, limit=20)
        for config in configs.data:
            metadata = dict(getattr(config, "metadata", {}) or {})
            if metadata.get("managed_by") == PORTAL_CONFIG_MARKER["managed_by"]:
                return config.id

        created = await self._stripe_call(
            stripe.billing_portal.Configuration.create,
            business_profile={"headline": "Syroce faturalama yönetimi"},
            features={
                "invoice_history": {"enabled": True},
                "payment_method_update": {"enabled": True},
            },
            metadata=PORTAL_CONFIG_MARKER,
        )
        return created.id

    async def _ensure_recurring_price(self, plan: str, interval: str) -> dict[str, Any]:
        config = self._plan_config(plan, interval)
        amount = float(config["amount"])
        existing = await billing_repo.get_plan_price(plan, interval=interval, currency="TRY")
        if existing and _is_real_price_id(existing.get("provider_price_id")):
            try:
                await self._stripe_call(stripe.Price.retrieve, existing["provider_price_id"])
                return existing
            except Exception as exc:
                if not _is_missing_stripe_resource_error(exc):
                    raise

        lookup_key = f"syroce_{plan}_{interval}_try"
        listed = await self._stripe_call(stripe.Price.list, lookup_keys=[lookup_key], active=True, limit=1)
        if listed.data:
            price = listed.data[0]
        else:
            product = await self._stripe_call(
                stripe.Product.create,
                name=f"Syroce {config['label']} {_interval_label(interval)}",
                metadata={"plan": plan, "interval": interval, "product_type": "saas_subscription"},
            )
            price = await self._stripe_call(
                stripe.Price.create,
                product=product.id,
                unit_amount=int(amount * 100),
                currency="try",
                recurring={"interval": "month" if interval == "monthly" else "year"},
                lookup_key=lookup_key,
                metadata={"plan": plan, "interval": interval},
            )

        await billing_repo.upsert_plan_price(
            plan=plan,
            interval=interval,
            currency="TRY",
            amount=amount,
            provider_price_id=price.id,
            provider="stripe",
        )
        return {
            "plan": plan,
            "interval": interval,
            "currency": "TRY",
            "amount": amount,
            "provider_price_id": price.id,
            "provider": "stripe",
        }

    async def _retrieve_checkout_session(self, session_id: str):
        return await self._stripe_call(
            stripe.checkout.Session.retrieve,
            session_id,
            expand=["customer", "subscription", "line_items.data.price"],
        )

    async def _retrieve_subscription(self, subscription_id: str):
        return await self._stripe_call(
            stripe.Subscription.retrieve,
            subscription_id,
            expand=["items.data.price"],
        )

    async def _release_schedule_if_present(self, schedule_id: Optional[str]) -> None:
        if not schedule_id:
            return
        try:
            await self._stripe_call(stripe.SubscriptionSchedule.release, schedule_id)
        except Exception:
            logger.warning("subscription schedule release failed", extra={"schedule_id": schedule_id})

    async def _clear_scheduled_change(self, tenant_id: str) -> None:
        db = await get_db()
        await db.billing_subscriptions.update_one(
            {"tenant_id": tenant_id},
            {
                "$unset": {
                    "scheduled_plan": "",
                    "scheduled_interval": "",
                    "change_effective_at": "",
                    "schedule_id": "",
                },
                "$set": {"updated_at": _now()},
            },
        )

    async def _demote_stale_subscription_reference(self, tenant_id: str) -> dict[str, Any]:
        db = await get_db()
        await db.billing_subscriptions.update_one(
            {"tenant_id": tenant_id},
            {
                "$unset": {
                    "provider_subscription_id": "",
                    "schedule_id": "",
                    "scheduled_plan": "",
                    "scheduled_interval": "",
                    "change_effective_at": "",
                },
                "$set": {"updated_at": _now()},
            },
        )
        return (await billing_repo.get_subscription(tenant_id)) or {}

    async def _clear_stale_customer_reference(self, tenant_id: str) -> dict[str, Any]:
        db = await get_db()
        await db.billing_customers.update_one(
            {"tenant_id": tenant_id},
            {
                "$unset": {"provider_customer_id": ""},
                "$set": {"updated_at": _now()},
            },
        )
        await db.billing_subscriptions.update_one(
            {"tenant_id": tenant_id},
            {
                "$unset": {"provider_customer_id": ""},
                "$set": {"updated_at": _now()},
            },
        )
        return (await billing_repo.get_customer(tenant_id)) or {}

    async def _find_tenant_by_subscription(self, subscription_id: str) -> Optional[str]:
        db = await get_db()
        doc = await db.billing_subscriptions.find_one(
            {"provider_subscription_id": subscription_id},
            {"_id": 0, "tenant_id": 1},
        )
        return str((doc or {}).get("tenant_id") or "") or None
