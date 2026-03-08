from __future__ import annotations

import logging
import os
import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from urllib.parse import urlparse

import anyio
import stripe
from dotenv import load_dotenv
from emergentintegrations.payments.stripe.checkout import StripeCheckout

from app.db import get_db
from app.errors import AppError
from app.repositories.billing_repository import billing_repo
from app.services.audit_log_service import append_audit_log
from app.services.feature_service import feature_service

load_dotenv(override=False)

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

PLAN_ORDER = {"trial": 0, "starter": 1, "pro": 2, "enterprise": 3}
STRIPE_PROXY_BASE = "https://integrations.emergentagent.com/stripe"
REAL_PRICE_PREFIX = "price_"
REAL_SUBSCRIPTION_PREFIX = "sub_"
REAL_CUSTOMER_PREFIX = "cus_"
PORTAL_CONFIG_MARKER = {"app": "syroce", "managed_by": "billing_lifecycle"}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _billing_mode() -> str:
    key = os.environ.get("STRIPE_API_KEY", "")
    return "live" if "live" in key else "test"


def _iso_from_unix(value: Any) -> Optional[str]:
    if value in (None, ""):
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat()
    try:
        return datetime.fromtimestamp(int(value), tz=timezone.utc).isoformat()
    except Exception:
        return None


def _is_real_price_id(value: Optional[str]) -> bool:
    return bool(value and value.startswith(REAL_PRICE_PREFIX))


def _is_real_subscription_id(value: Optional[str]) -> bool:
    return bool(value and value.startswith(REAL_SUBSCRIPTION_PREFIX))


def _is_real_customer_id(value: Optional[str]) -> bool:
    return bool(value and value.startswith(REAL_CUSTOMER_PREFIX))


def _schedule_id(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return getattr(value, "id", None)


def _subscription_first_item(subscription: Any) -> Any:
    if not subscription:
        return None
    items_container = subscription.get("items", {}) if hasattr(subscription, "get") else getattr(subscription, "items", {})
    if callable(items_container):
        items_container = {}
    data = items_container.get("data") if isinstance(items_container, dict) else getattr(items_container, "data", None)
    return (data or [None])[0]


def _stripe_value(obj: Any, key: str, default: Any = None) -> Any:
    if obj is None:
        return default
    if hasattr(obj, "get"):
        try:
            return obj.get(key, default)
        except Exception:
            pass
    return getattr(obj, key, default)


def _interval_label(interval: str) -> str:
    return "Yıllık" if interval == "yearly" else "Aylık"


def _plan_change_mode(current_plan: str, current_interval: str, target_plan: str, target_interval: str) -> str:
    current_rank = PLAN_ORDER.get(current_plan or "trial", 0)
    target_rank = PLAN_ORDER.get(target_plan, 0)
    if target_rank > current_rank:
        return "upgrade_now"
    if target_rank < current_rank:
        return "downgrade_later"
    if current_interval == target_interval:
        return "none"
    if current_interval == "monthly" and target_interval == "yearly":
        return "upgrade_now"
    return "downgrade_later"


class StripeCheckoutService:
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
            return existing

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

    async def _find_tenant_by_subscription(self, subscription_id: str) -> Optional[str]:
        db = await get_db()
        doc = await db.billing_subscriptions.find_one(
            {"provider_subscription_id": subscription_id},
            {"_id": 0, "tenant_id": 1},
        )
        return str((doc or {}).get("tenant_id") or "") or None

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
        if _is_real_customer_id((customer or {}).get("provider_customer_id")) and (
            not subscription or _is_real_subscription_id(subscription.get("provider_subscription_id"))
        ):
            return {
                "customer_id": customer.get("provider_customer_id"),
                "subscription_id": (subscription or {}).get("provider_subscription_id"),
            }

        db = await get_db()
        tx = await db.payment_transactions.find_one(
            {"tenant_id": tenant_id},
            {"_id": 0, "session_id": 1, "plan": 1, "interval": 1, "organization_id": 1},
            sort=[("processed_at", -1), ("updated_at", -1)],
        )
        session_id = str((tx or {}).get("session_id") or "")
        if not session_id.startswith("cs_"):
            return {
                "customer_id": (customer or {}).get("provider_customer_id"),
                "subscription_id": (subscription or {}).get("provider_subscription_id"),
            }

        try:
            session = await self._retrieve_checkout_session(session_id)
        except Exception:
            return {
                "customer_id": (customer or {}).get("provider_customer_id"),
                "subscription_id": (subscription or {}).get("provider_subscription_id"),
            }

        customer_id = session.customer if isinstance(session.customer, str) else getattr(session.customer, "id", None)
        subscription_id = session.subscription if isinstance(session.subscription, str) else getattr(session.subscription, "id", None)

        if customer_id and _is_real_customer_id(customer_id):
            await billing_repo.upsert_customer(
                tenant_id=tenant_id,
                provider="stripe",
                provider_customer_id=customer_id,
                email=user_email or str((customer or {}).get("email") or ""),
                mode=_billing_mode(),
            )

        if subscription_id and _is_real_subscription_id(subscription_id):
            await self._sync_subscription_document(
                tenant_id,
                subscription_id,
                customer_id=customer_id,
                plan_hint=str((tx or {}).get("plan") or (subscription or {}).get("plan") or "starter"),
                interval_hint=str((tx or {}).get("interval") or (subscription or {}).get("interval") or "monthly"),
                user_email=user_email,
                organization_id=str((tx or {}).get("organization_id") or ""),
            )

        return {"customer_id": customer_id, "subscription_id": subscription_id}

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
        cancel_path: Optional[str],
        current_plan: Optional[str],
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

        session = await self._stripe_call(stripe.checkout.Session.create, **create_kwargs)

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

    async def sync_provider_subscription_record(self, tenant_id: str, provider_subscription_id: str, *, user_email: str = "", organization_id: str = "") -> dict[str, Any]:
        return await self._sync_subscription_document(
            tenant_id,
            provider_subscription_id,
            user_email=user_email,
            organization_id=organization_id,
        )

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

    async def get_billing_overview(self, tenant_id: str, *, user_email: str = "") -> dict[str, Any]:
        await self._repair_customer_reference(tenant_id, user_email=user_email)
        subscription = await billing_repo.get_subscription(tenant_id)
        if subscription and _is_real_subscription_id(subscription.get("provider_subscription_id")):
            subscription = await self._sync_subscription_document(
                tenant_id,
                subscription["provider_subscription_id"],
                user_email=user_email,
            )

        customer = await billing_repo.get_customer(tenant_id)
        plan = str((subscription or {}).get("plan") or await feature_service.get_plan(tenant_id) or "trial")
        interval = str((subscription or {}).get("interval") or "monthly")
        status = str((subscription or {}).get("status") or ("trialing" if plan == "trial" else "active"))
        current_period_end = (subscription or {}).get("current_period_end")
        managed_subscription = _is_real_subscription_id((subscription or {}).get("provider_subscription_id"))
        portal_available = _is_real_customer_id((customer or {}).get("provider_customer_id")) or bool(user_email and plan != "trial")
        payment_issue = status in {"past_due", "unpaid", "incomplete", "incomplete_expired"}
        scheduled_plan = (subscription or {}).get("scheduled_plan")
        scheduled_interval = (subscription or {}).get("scheduled_interval")
        scheduled_effective_at = (subscription or {}).get("change_effective_at")
        cancel_at_period_end = bool((subscription or {}).get("cancel_at_period_end", False))
        legacy_subscription = bool(subscription and not managed_subscription)

        return {
            "plan": plan,
            "interval": interval,
            "interval_label": _interval_label(interval),
            "status": status,
            "current_period_end": current_period_end,
            "next_renewal_at": current_period_end,
            "cancel_at_period_end": cancel_at_period_end,
            "cancel_message": "Aboneliğiniz dönem sonunda sona erecek" if cancel_at_period_end else None,
            "scheduled_change": {
                "plan": scheduled_plan,
                "interval": scheduled_interval,
                "interval_label": _interval_label(scheduled_interval) if scheduled_interval else None,
                "effective_at": scheduled_effective_at,
                "message": "Plan değişikliğiniz bir sonraki dönem başlayacak" if scheduled_plan else None,
            } if scheduled_plan else None,
            "payment_issue": {
                "has_issue": payment_issue,
                "message": "Ödemeniz alınamadı. Hizmetinizin kesintiye uğramaması için ödeme yönteminizi güncelleyin." if payment_issue else None,
                "cta_label": "Ödeme Yöntemini Güncelle" if payment_issue else None,
            },
            "portal_available": portal_available,
            "managed_subscription": managed_subscription,
            "legacy_subscription": legacy_subscription,
            "legacy_notice": (
                "Bu abonelik eski checkout akışından geldiği için bazı self-servis kontroller ilk plan değişikliğinizden sonra aktif olur."
                if legacy_subscription
                else None
            ),
            "can_cancel": managed_subscription and status in {"active", "trialing", "past_due"},
            "can_change_plan": plan in {"starter", "pro", "trial"} or managed_subscription,
            "change_flow": "self_serve" if managed_subscription else "checkout_redirect",
            "provider_customer_id": (customer or {}).get("provider_customer_id"),
            "provider_subscription_id": (subscription or {}).get("provider_subscription_id"),
        }

    async def create_customer_portal_session(
        self,
        tenant_id: str,
        *,
        origin_url: str,
        return_path: Optional[str],
        actor_user_id: str = "",
        actor_email: str = "",
    ) -> dict[str, Any]:
        await self._repair_customer_reference(tenant_id, user_email=actor_email)
        customer = await billing_repo.get_customer(tenant_id)
        customer_id = str((customer or {}).get("provider_customer_id") or "")
        if not _is_real_customer_id(customer_id):
            created_customer = await self._stripe_call(
                stripe.Customer.create,
                email=actor_email or str((customer or {}).get("email") or ""),
                metadata={"tenant_id": tenant_id, "source": "billing_portal_bootstrap"},
            )
            customer_id = created_customer.id
            await billing_repo.upsert_customer(
                tenant_id=tenant_id,
                provider="stripe",
                provider_customer_id=customer_id,
                email=actor_email or str((customer or {}).get("email") or ""),
                mode=_billing_mode(),
            )

        portal_session = await self._stripe_call(
            stripe.billing_portal.Session.create,
            customer=customer_id,
            return_url=f"{self._validate_origin(origin_url)}{self._normalize_path(return_path, '/app/settings/billing')}",
            configuration=await self._ensure_portal_configuration(),
        )
        await append_audit_log(
            scope="billing",
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            actor_email=actor_email,
            action="billing.portal_session_created",
            before=None,
            after={"customer_id": customer_id},
        )
        return {"url": portal_session.url}

    async def cancel_subscription_at_period_end(
        self,
        tenant_id: str,
        *,
        actor_user_id: str = "",
        actor_email: str = "",
    ) -> dict[str, Any]:
        await self._repair_customer_reference(tenant_id, user_email=actor_email)
        subscription = await billing_repo.get_subscription(tenant_id)
        provider_subscription_id = str((subscription or {}).get("provider_subscription_id") or "")
        if not _is_real_subscription_id(provider_subscription_id):
            raise AppError(
                409,
                "subscription_management_unavailable",
                "Bu abonelik için iptal yönetimi henüz self-servis olarak açılamıyor.",
                {"tenant_id": tenant_id},
            )

        if subscription and subscription.get("cancel_at_period_end"):
            return {
                "status": subscription.get("status") or "active",
                "cancel_at_period_end": True,
                "current_period_end": subscription.get("current_period_end"),
                "message": "Aboneliğiniz dönem sonunda sona erecek",
            }

        await self._release_schedule_if_present(str(subscription.get("schedule_id") or "") or None)
        updated = await self._stripe_call(
            stripe.Subscription.modify,
            provider_subscription_id,
            cancel_at_period_end=True,
        )
        synced = await self._sync_subscription_document(
            tenant_id,
            updated.id,
            customer_id=updated.customer if isinstance(updated.customer, str) else getattr(updated.customer, "id", None),
            user_email=actor_email,
        )
        await self._clear_scheduled_change(tenant_id)
        await append_audit_log(
            scope="billing",
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            actor_email=actor_email,
            action="billing.subscription_cancel_scheduled",
            before={"plan": subscription.get("plan") if subscription else None},
            after={"cancel_at_period_end": True, "current_period_end": synced.get("current_period_end")},
        )
        return {
            "status": synced.get("status") or "active",
            "cancel_at_period_end": True,
            "current_period_end": synced.get("current_period_end"),
            "message": "Aboneliğiniz dönem sonunda sona erecek",
        }

    async def change_plan(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        user_id: str,
        user_email: str,
        plan: str,
        interval: str,
        origin_url: str,
        cancel_path: Optional[str],
    ) -> dict[str, Any]:
        if plan == "enterprise":
            raise AppError(422, "enterprise_contact_required", "Enterprise planı için satış ekibiyle görüşmeniz gerekir.", {"plan": plan})

        await self._repair_customer_reference(tenant_id, user_email=user_email)
        current_sub = await billing_repo.get_subscription(tenant_id)
        current_plan = str((current_sub or {}).get("plan") or await feature_service.get_plan(tenant_id) or "trial")
        current_interval = str((current_sub or {}).get("interval") or "monthly")
        provider_subscription_id = str((current_sub or {}).get("provider_subscription_id") or "")

        if current_plan == plan and current_interval == interval and _is_real_subscription_id(provider_subscription_id):
            raise AppError(409, "plan_already_active", "Seçtiğiniz plan zaten aktif.", {"plan": plan, "interval": interval})

        if not _is_real_subscription_id(provider_subscription_id):
            checkout = await self.create_checkout_session(
                tenant_id=tenant_id,
                organization_id=organization_id,
                user_id=user_id,
                user_email=user_email,
                plan=plan,
                interval=interval,
                origin_url=origin_url,
                cancel_path=cancel_path,
                current_plan=current_plan,
            )
            return {
                **checkout,
                "action": "checkout_redirect",
                "message": "Plan değişikliği için Stripe ekranına yönlendiriliyorsunuz.",
            }

        change_mode = _plan_change_mode(current_plan, current_interval, plan, interval)
        if change_mode == "none":
            raise AppError(409, "plan_already_active", "Seçtiğiniz plan zaten aktif.", {"plan": plan, "interval": interval})

        target_price = await self._ensure_recurring_price(plan, interval)
        current_subscription = await self._retrieve_subscription(provider_subscription_id)
        current_item = _subscription_first_item(current_subscription)
        current_quantity = _stripe_value(current_item, "quantity", 1) or 1
        current_price_id = _stripe_value(_stripe_value(current_item, "price"), "id")
        current_item_id = _stripe_value(current_item, "id")
        if not current_item_id or not current_price_id:
            raise AppError(500, "subscription_item_missing", "Stripe abonelik öğesi bulunamadı.", {"subscription_id": provider_subscription_id})
        customer_id = current_subscription.customer if isinstance(current_subscription.customer, str) else getattr(current_subscription.customer, "id", None)

        if change_mode == "upgrade_now":
            await self._release_schedule_if_present(_schedule_id(getattr(current_subscription, "schedule", None)))
            updated = await self._stripe_call(
                stripe.Subscription.modify,
                provider_subscription_id,
                items=[{"id": current_item_id, "price": target_price["provider_price_id"]}],
                proration_behavior="create_prorations",
                cancel_at_period_end=False,
                metadata={"plan": plan, "interval": interval},
            )
            synced = await self._sync_subscription_document(
                tenant_id,
                updated.id,
                customer_id=customer_id,
                plan_hint=plan,
                interval_hint=interval,
                user_email=user_email,
                organization_id=organization_id,
            )
            await self._clear_scheduled_change(tenant_id)
            await append_audit_log(
                scope="billing",
                tenant_id=tenant_id,
                actor_user_id=user_id,
                actor_email=user_email,
                action="billing.plan_changed_now",
                before={"plan": current_plan, "interval": current_interval},
                after={"plan": plan, "interval": interval},
            )
            return {
                "action": "changed_now",
                "message": "Yeni planınız hemen aktif oldu",
                "subscription": synced,
            }

        raw_schedule_id = _schedule_id(getattr(current_subscription, "schedule", None))
        if raw_schedule_id:
            schedule = await self._stripe_call(stripe.SubscriptionSchedule.retrieve, raw_schedule_id)
        else:
            schedule = await self._stripe_call(
                stripe.SubscriptionSchedule.create,
                from_subscription=provider_subscription_id,
            )
        schedule_current_phase = ((schedule.get("phases") or [{}])[0]) if hasattr(schedule, "get") else {}
        current_phase_start = schedule_current_phase.get("start_date") or _stripe_value(current_subscription, "start_date")
        current_phase_end = schedule_current_phase.get("end_date") or _stripe_value(current_subscription, "current_period_end")
        updated_schedule = await self._stripe_call(
            stripe.SubscriptionSchedule.modify,
            schedule.id,
            end_behavior="release",
            phases=[
                {
                    "items": [{"price": current_price_id, "quantity": current_quantity}],
                    "start_date": current_phase_start,
                    "end_date": current_phase_end,
                },
                {
                    "items": [{"price": target_price["provider_price_id"], "quantity": current_quantity}],
                    "metadata": {"plan": plan, "interval": interval},
                },
            ],
            metadata={"plan": plan, "interval": interval},
        )

        db = await get_db()
        effective_at = _iso_from_unix(current_phase_end)
        await db.billing_subscriptions.update_one(
            {"tenant_id": tenant_id},
            {
                "$set": {
                    "scheduled_plan": plan,
                    "scheduled_interval": interval,
                    "change_effective_at": effective_at,
                    "schedule_id": updated_schedule.id,
                    "updated_at": _now(),
                }
            },
        )
        await append_audit_log(
            scope="billing",
            tenant_id=tenant_id,
            actor_user_id=user_id,
            actor_email=user_email,
            action="billing.plan_change_scheduled",
            before={"plan": current_plan, "interval": current_interval},
            after={"plan": plan, "interval": interval, "effective_at": effective_at},
        )
        return {
            "action": "scheduled",
            "message": "Plan değişikliğiniz bir sonraki dönem başlayacak",
            "effective_at": effective_at,
        }

    async def handle_webhook(self, http_request, payload: bytes, signature: Optional[str]) -> dict[str, Any]:
        checkout = self._checkout_client(http_request)
        webhook_response = await checkout.handle_webhook(payload, signature)
        raw_event = None
        try:
            raw_event = json.loads(payload.decode("utf-8"))
        except Exception:
            raw_event = None
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

        event_type = webhook_response.event_type or str((raw_event or {}).get("type") or "")
        event_object = ((raw_event or {}).get("data") or {}).get("object") or {}
        if event_type == "invoice.paid":
            sub_id = str(event_object.get("subscription") or "")
            tenant_id = await self._find_tenant_by_subscription(sub_id) if sub_id else None
            if tenant_id:
                await self.sync_provider_subscription_record(tenant_id, sub_id)
        elif event_type == "customer.subscription.updated":
            sub_id = str(event_object.get("id") or "")
            tenant_id = await self._find_tenant_by_subscription(sub_id) if sub_id else None
            if tenant_id:
                await self.sync_provider_subscription_record(tenant_id, sub_id)
        elif event_type == "customer.subscription.deleted":
            sub_id = str(event_object.get("id") or "")
            tenant_id = await self._find_tenant_by_subscription(sub_id) if sub_id else None
            if tenant_id:
                await billing_repo.update_subscription_status(tenant_id, "canceled", cancel_at_period_end=False)
                await self._clear_scheduled_change(tenant_id)
        elif event_type == "invoice.payment_failed":
            sub_id = str(event_object.get("subscription") or "")
            tenant_id = await self._find_tenant_by_subscription(sub_id) if sub_id else None
            if tenant_id:
                try:
                    await self.sync_provider_subscription_record(tenant_id, sub_id)
                except Exception:
                    logger.warning("payment_failed subscription sync skipped", extra={"tenant_id": tenant_id, "subscription_id": sub_id})
                db = await get_db()
                grace_until = (_now() + timedelta(days=7)).isoformat()
                await db.billing_subscriptions.update_one(
                    {"tenant_id": tenant_id},
                    {"$set": {"status": "past_due", "grace_period_until": grace_until, "updated_at": _now()}},
                )

        return {
            "status": "ok",
            "event_id": webhook_response.event_id,
            "event_type": webhook_response.event_type,
            "session_id": webhook_response.session_id,
        }


stripe_checkout_service = StripeCheckoutService()