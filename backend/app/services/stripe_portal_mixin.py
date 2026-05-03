"""Stripe checkout — billing portal mixin (T009 / Task #3).

Owns `create_customer_portal_session`. The portal session bootstrap also
handles the case where our cached `provider_customer_id` is stale: it
creates a fresh Stripe Customer and re-tries once. All audit log entries
and stored fields are preserved exactly as in the original service.
"""
from __future__ import annotations

from typing import Any, Optional

import stripe

from app.repositories.billing_repository import billing_repo
from app.services.audit_log_service import append_audit_log
from app.services.stripe_checkout_helpers import (
    _billing_mode,
    _is_missing_stripe_resource_error,
    _is_real_customer_id,
)


class StripePortalMixin:
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

        try:
            portal_session = await self._stripe_call(
                stripe.billing_portal.Session.create,
                customer=customer_id,
                return_url=f"{self._validate_origin(origin_url)}{self._normalize_path(return_path, '/app/settings/billing')}",
                configuration=await self._ensure_portal_configuration(),
            )
        except Exception as exc:
            if not _is_missing_stripe_resource_error(exc):
                raise
            await self._clear_stale_customer_reference(tenant_id)
            created_customer = await self._stripe_call(
                stripe.Customer.create,
                email=actor_email or str((customer or {}).get("email") or ""),
                metadata={"tenant_id": tenant_id, "source": "billing_portal_repair"},
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
