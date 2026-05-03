"""Stripe checkout — billing overview mixin (T009 / Task #3).

Owns `get_billing_overview`, the read model used by the tenant Settings →
Billing UI. The shape of the returned dict is part of a public API
contract consumed by the frontend, so any change here must also update
the React consumer (`SettingsBilling.jsx`).
"""
from __future__ import annotations

from typing import Any

from app.repositories.billing_repository import billing_repo
from app.services.feature_service import feature_service
from app.services.stripe_checkout_helpers import (
    _format_try_minor,
    _interval_label,
    _is_missing_stripe_resource_error,
    _is_real_customer_id,
    _is_real_subscription_id,
    _should_refresh_subscription_snapshot,
)


class StripeOverviewMixin:
    async def get_billing_overview(self, tenant_id: str, *, user_email: str = "") -> dict[str, Any]:
        await self._repair_customer_reference(tenant_id, user_email=user_email)
        subscription = await billing_repo.get_subscription(tenant_id)
        if (
            subscription
            and _is_real_subscription_id(subscription.get("provider_subscription_id"))
            and _should_refresh_subscription_snapshot(subscription)
        ):
            try:
                subscription = await self._sync_subscription_document(
                    tenant_id,
                    subscription["provider_subscription_id"],
                    user_email=user_email,
                )
            except Exception as exc:
                if _is_missing_stripe_resource_error(exc):
                    subscription = await self._demote_stale_subscription_reference(tenant_id)
                else:
                    raise

        customer = await billing_repo.get_customer(tenant_id)
        plan = str((subscription or {}).get("plan") or await feature_service.get_plan(tenant_id) or "trial")
        interval = str((subscription or {}).get("interval") or "monthly")
        status = str((subscription or {}).get("status") or ("trialing" if plan == "trial" else "active"))
        current_period_end = (subscription or {}).get("current_period_end")
        managed_subscription = _is_real_subscription_id((subscription or {}).get("provider_subscription_id"))
        portal_available = _is_real_customer_id((customer or {}).get("provider_customer_id")) or bool(user_email and plan != "trial")
        payment_issue = status in {"past_due", "unpaid", "incomplete", "incomplete_expired"}
        grace_period_until = (subscription or {}).get("grace_period_until")
        last_payment_failed_at = (subscription or {}).get("last_payment_failed_at")
        last_payment_failed_amount = (subscription or {}).get("last_payment_failed_amount")
        invoice_hosted_url = (subscription or {}).get("invoice_hosted_url")
        invoice_pdf_url = (subscription or {}).get("invoice_pdf_url")
        payment_issue_amount_label = _format_try_minor(last_payment_failed_amount)
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
                "severity": (
                    "critical"
                    if status in {"unpaid", "incomplete_expired"}
                    else "warning"
                    if payment_issue
                    else None
                ),
                "title": "Ödeme yönteminizi güncelleyin" if payment_issue else None,
                "message": (
                    f"Son tahsilat denemesi {payment_issue_amount_label} için başarısız oldu. Hizmetinizin kesintiye uğramaması için ödeme yönteminizi güncelleyin."
                    if payment_issue and payment_issue_amount_label
                    else "Ödemeniz alınamadı. Hizmetinizin kesintiye uğramaması için ödeme yönteminizi güncelleyin."
                    if payment_issue
                    else None
                ),
                "cta_label": "Ödeme Yöntemini Güncelle" if payment_issue else None,
                "grace_period_until": grace_period_until if payment_issue else None,
                "last_failed_at": last_payment_failed_at if payment_issue else None,
                "last_failed_amount": last_payment_failed_amount if payment_issue else None,
                "last_failed_amount_label": payment_issue_amount_label if payment_issue else None,
                "invoice_hosted_url": invoice_hosted_url if payment_issue else None,
                "invoice_pdf_url": invoice_pdf_url if payment_issue else None,
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
