"""Stripe checkout — subscription lifecycle mixin (T009 / Task #3).

Owns webhook-driven and self-serve lifecycle transitions:
- `mark_invoice_paid`              — invoice.paid webhook target.
- `mark_payment_failed`            — invoice.payment_failed webhook target.
- `mark_subscription_canceled`     — customer.subscription.deleted target.
- `cancel_subscription_at_period_end` — self-serve cancel.
- `reactivate_subscription`        — self-serve un-cancel.

Each method preserves its original signature, audit log call, and stored
field shape so existing webhook handlers and UI integrations remain
unchanged.
"""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any, Optional

import stripe

from app.db import get_db
from app.errors import AppError
from app.repositories.billing_repository import billing_repo
from app.services.audit_log_service import append_audit_log
from app.services.stripe_checkout_helpers import (
    _coerce_minor_amount,
    _is_missing_stripe_resource_error,
    _is_real_subscription_id,
    _now,
)

logger = logging.getLogger(__name__)


class StripeLifecycleMixin:
    async def mark_invoice_paid(
        self,
        tenant_id: str,
        *,
        subscription_id: str,
        amount_paid: Any = None,
        paid_at: Optional[str] = None,
    ) -> dict[str, Any]:
        synced: dict[str, Any] = {}
        if subscription_id:
            try:
                synced = await self.sync_provider_subscription_record(tenant_id, subscription_id)
            except Exception as exc:
                if not _is_missing_stripe_resource_error(exc):
                    raise
                synced = await self._demote_stale_subscription_reference(tenant_id)
                synced["status"] = "active"

        now = _now()
        paid_at_value = paid_at or now.isoformat()
        amount_minor = _coerce_minor_amount(amount_paid)
        db = await get_db()
        resolved_status = str((synced or {}).get("status") or "active")
        if resolved_status in {"past_due", "unpaid", "incomplete", "incomplete_expired", "canceled"}:
            resolved_status = "active"

        set_fields: dict[str, Any] = {
            "status": resolved_status,
            "updated_at": now,
            "last_invoice_paid_at": paid_at_value,
        }
        if amount_minor is not None:
            set_fields["last_invoice_paid_amount"] = amount_minor

        await db.billing_subscriptions.update_one(
            {"tenant_id": tenant_id},
            {
                "$set": set_fields,
                "$unset": {
                    "grace_period_until": "",
                    "last_payment_failed_at": "",
                    "last_payment_failed_amount": "",
                    "invoice_hosted_url": "",
                    "invoice_pdf_url": "",
                },
            },
        )
        org_id = await self._resolve_org_id_for_tenant(tenant_id)
        if org_id:
            await db.subscriptions.update_one(
                {"org_id": org_id},
                {"$set": {"status": set_fields["status"], "updated_at": now}},
            )

        await append_audit_log(
            scope="billing",
            tenant_id=tenant_id,
            actor_user_id="system",
            actor_email="stripe_webhook",
            action="subscription.invoice_paid",
            before=None,
            after={
                "subscription_id": subscription_id,
                "amount": amount_minor,
                "paid_at": paid_at_value,
            },
        )
        return (await billing_repo.get_subscription(tenant_id)) or synced or {}

    async def mark_payment_failed(
        self,
        tenant_id: str,
        *,
        subscription_id: str,
        amount_due: Any = None,
        invoice_hosted_url: Optional[str] = None,
        invoice_pdf_url: Optional[str] = None,
        failed_at: Optional[str] = None,
    ) -> dict[str, Any]:
        if subscription_id:
            try:
                await self.sync_provider_subscription_record(tenant_id, subscription_id)
            except Exception as exc:
                if not _is_missing_stripe_resource_error(exc):
                    raise

        now = _now()
        failed_at_value = failed_at or now.isoformat()
        grace_until = (now + timedelta(days=7)).isoformat()
        amount_minor = _coerce_minor_amount(amount_due)
        db = await get_db()

        set_fields: dict[str, Any] = {
            "status": "past_due",
            "grace_period_until": grace_until,
            "last_payment_failed_at": failed_at_value,
            "updated_at": now,
        }
        if amount_minor is not None:
            set_fields["last_payment_failed_amount"] = amount_minor
        if invoice_hosted_url:
            set_fields["invoice_hosted_url"] = invoice_hosted_url
        if invoice_pdf_url:
            set_fields["invoice_pdf_url"] = invoice_pdf_url

        unset_fields: dict[str, str] = {}
        if not invoice_hosted_url:
            unset_fields["invoice_hosted_url"] = ""
        if not invoice_pdf_url:
            unset_fields["invoice_pdf_url"] = ""

        update_doc: dict[str, Any] = {"$set": set_fields}
        if unset_fields:
            update_doc["$unset"] = unset_fields

        await db.billing_subscriptions.update_one({"tenant_id": tenant_id}, update_doc)
        org_id = await self._resolve_org_id_for_tenant(tenant_id)
        if org_id:
            await db.subscriptions.update_one(
                {"org_id": org_id},
                {"$set": {"status": "past_due", "updated_at": now}},
            )

        await append_audit_log(
            scope="billing",
            tenant_id=tenant_id,
            actor_user_id="system",
            actor_email="stripe_webhook",
            action="subscription.payment_failed",
            before=None,
            after={
                "status": "past_due",
                "grace_period_until": grace_until,
                "amount": amount_minor,
                "failed_at": failed_at_value,
                "invoice_hosted_url": invoice_hosted_url,
                "invoice_pdf_url": invoice_pdf_url,
            },
        )
        if org_id:
            try:
                from app.services.notification_email_service import enqueue_payment_failed_email

                await enqueue_payment_failed_email(
                    db,
                    organization_id=org_id,
                    tenant_id=tenant_id,
                    subscription_id=subscription_id,
                    amount_due=amount_minor,
                    failed_at=failed_at_value,
                    grace_period_until=grace_until,
                    invoice_hosted_url=invoice_hosted_url,
                    invoice_pdf_url=invoice_pdf_url,
                )
            except Exception:
                logger.warning(
                    "payment failed email enqueue failed tenant=%s subscription=%s",
                    tenant_id,
                    subscription_id,
                    exc_info=True,
                )
        return (await billing_repo.get_subscription(tenant_id)) or {}

    async def mark_subscription_canceled(
        self,
        tenant_id: str,
        *,
        subscription_id: str,
        canceled_at: Optional[str] = None,
    ) -> dict[str, Any]:
        now = _now()
        canceled_at_value = canceled_at or now.isoformat()
        db = await get_db()
        await db.billing_subscriptions.update_one(
            {"tenant_id": tenant_id},
            {
                "$set": {
                    "status": "canceled",
                    "cancel_at_period_end": False,
                    "updated_at": now,
                    "canceled_at": canceled_at_value,
                },
                "$unset": {
                    "grace_period_until": "",
                    "last_payment_failed_at": "",
                    "last_payment_failed_amount": "",
                    "invoice_hosted_url": "",
                    "invoice_pdf_url": "",
                    "scheduled_plan": "",
                    "scheduled_interval": "",
                    "change_effective_at": "",
                    "schedule_id": "",
                },
            },
        )
        org_id = await self._resolve_org_id_for_tenant(tenant_id)
        if org_id:
            await db.subscriptions.update_one(
                {"org_id": org_id},
                {"$set": {"status": "canceled", "updated_at": now}},
            )

        await append_audit_log(
            scope="billing",
            tenant_id=tenant_id,
            actor_user_id="system",
            actor_email="stripe_webhook",
            action="subscription.canceled",
            before=None,
            after={
                "subscription_id": subscription_id,
                "status": "canceled",
                "canceled_at": canceled_at_value,
            },
        )
        return (await billing_repo.get_subscription(tenant_id)) or {}

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
        try:
            updated = await self._stripe_call(
                stripe.Subscription.modify,
                provider_subscription_id,
                cancel_at_period_end=True,
            )
        except Exception as exc:
            if _is_missing_stripe_resource_error(exc):
                await self._demote_stale_subscription_reference(tenant_id)
                raise AppError(
                    409,
                    "subscription_management_unavailable",
                    "Bu abonelik için iptal yönetimi henüz self-servis olarak açılamıyor.",
                    {"tenant_id": tenant_id},
                )
            raise
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

    async def reactivate_subscription(
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
                "Bu abonelik için yeniden başlatma henüz self-servis olarak açılamıyor.",
                {"tenant_id": tenant_id},
            )

        if not subscription or not subscription.get("cancel_at_period_end"):
            return {
                "status": (subscription or {}).get("status") or "active",
                "cancel_at_period_end": False,
                "current_period_end": (subscription or {}).get("current_period_end"),
                "message": "Aboneliğiniz zaten aktif durumda.",
            }

        try:
            updated = await self._stripe_call(
                stripe.Subscription.modify,
                provider_subscription_id,
                cancel_at_period_end=False,
            )
        except Exception as exc:
            if _is_missing_stripe_resource_error(exc):
                await self._demote_stale_subscription_reference(tenant_id)
                raise AppError(
                    409,
                    "subscription_management_unavailable",
                    "Bu abonelik için yeniden başlatma henüz self-servis olarak açılamıyor.",
                    {"tenant_id": tenant_id},
                )
            raise
        synced = await self._sync_subscription_document(
            tenant_id,
            updated.id,
            customer_id=updated.customer if isinstance(updated.customer, str) else getattr(updated.customer, "id", None),
            user_email=actor_email,
        )
        await append_audit_log(
            scope="billing",
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            actor_email=actor_email,
            action="billing.subscription_reactivated",
            before={"cancel_at_period_end": True, "current_period_end": (subscription or {}).get("current_period_end")},
            after={"cancel_at_period_end": False, "current_period_end": synced.get("current_period_end")},
        )
        return {
            "status": synced.get("status") or "active",
            "cancel_at_period_end": False,
            "current_period_end": synced.get("current_period_end"),
            "message": "Aboneliğiniz yeniden aktif hale getirildi",
        }
