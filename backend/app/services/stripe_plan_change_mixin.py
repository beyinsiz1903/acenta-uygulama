"""Stripe checkout — plan change mixin (T009 / Task #3).

Owns the `change_plan` orchestration: routes the request between three
flows depending on current state (no managed sub → checkout redirect,
upgrade → immediate Stripe modify with prorations, downgrade → schedule
the change for end-of-period via SubscriptionSchedule).
"""
from __future__ import annotations

from typing import Any, Optional

import stripe

from app.db import get_db
from app.errors import AppError
from app.repositories.billing_repository import billing_repo
from app.services.audit_log_service import append_audit_log
from app.services.feature_service import feature_service
from app.services.stripe_checkout_helpers import (
    _is_missing_stripe_resource_error,
    _is_real_subscription_id,
    _iso_from_unix,
    _now,
    _plan_change_mode,
    _schedule_id,
    _stripe_value,
    _subscription_first_item,
)


class StripePlanChangeMixin:
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
        try:
            current_subscription = await self._retrieve_subscription(provider_subscription_id)
        except Exception as exc:
            if _is_missing_stripe_resource_error(exc):
                await self._demote_stale_subscription_reference(tenant_id)
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
            raise
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
