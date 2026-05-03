"""Stripe checkout service — composer module (T009 / Task #3).

ADR — Module decomposition:
  This module used to be a single 1539-LOC class. As part of Task #3 it
  was decomposed into eight focused mixin modules, each responsible for
  one cohesive slice of the Stripe integration. The mixins are composed
  here into a single `StripeCheckoutService` class so the public API
  surface (and therefore every external import site) is preserved
  byte-for-byte:

    * `stripe_base_mixin`              — SDK config, helpers, customer/sub
                                         reference repair primitives.
    * `stripe_subscription_sync_mixin` — sync/repair subscription docs.
    * `stripe_lifecycle_mixin`         — invoice paid/failed, cancel,
                                         reactivate, mark canceled.
    * `stripe_session_mixin`           — Checkout Session create/sync,
                                         fulfilment.
    * `stripe_overview_mixin`          — `get_billing_overview` read model.
    * `stripe_portal_mixin`            — Customer portal session bootstrap.
    * `stripe_plan_change_mixin`       — `change_plan` orchestration.
    * `stripe_webhook_mixin`           — Webhook dispatcher.

  The decomposition is purely structural — every method preserves its
  original signature, audit log entries, stored field shapes, and HTTP
  status codes. Existing import sites keep working unchanged:

      from app.services.stripe_checkout_service import (
          stripe_checkout_service,    # singleton
          StripeCheckoutService,      # class
          _iso_from_unix,             # re-exported helper (legacy)
      )

  The pure helpers (date coercion, plan ordering, etc.) live in the
  sibling `stripe_checkout_helpers` module and are re-exported below for
  backwards compatibility with `billing_webhooks` and other legacy call
  sites that historically did
      from app.services.stripe_checkout_service import _iso_from_unix
"""
from __future__ import annotations

import logging
import os  # noqa: F401  (kept for legacy compat: external code may import os via this module)
import json  # noqa: F401  (kept for legacy compat)
import uuid  # noqa: F401  (kept for legacy compat)
from datetime import datetime, timedelta, timezone  # noqa: F401  (re-exported for back-compat)
from typing import Any, Optional  # noqa: F401  (kept for legacy compat)
from urllib.parse import urlparse  # noqa: F401  (kept for legacy compat)

import anyio  # noqa: F401  (kept for legacy compat)
import stripe  # noqa: F401  (kept for legacy compat)
from dotenv import load_dotenv

# Re-export pure helpers — existing import sites (e.g.
# `modules/finance/routers/billing_webhooks.py`) do
#     from app.services.stripe_checkout_service import _iso_from_unix
# and must keep working unchanged.
from app.services.stripe_checkout_helpers import (  # noqa: F401
    PLAN_ORDER,
    REAL_CUSTOMER_PREFIX,
    REAL_PRICE_PREFIX,
    REAL_SUBSCRIPTION_PREFIX,
    _billing_mode,
    _coerce_datetime,
    _coerce_minor_amount,
    _format_try_minor,
    _interval_label,
    _is_missing_stripe_resource_error,
    _is_real_customer_id,
    _is_real_price_id,
    _is_real_subscription_id,
    _iso_from_unix,
    _now,
    _plan_change_mode,
    _schedule_id,
    _should_refresh_subscription_snapshot,
    _stripe_value,
    _subscription_first_item,
)

# Re-export base-module constants for back-compat with any external code
# that historically imported them from this module.
from app.services.stripe_base_mixin import (  # noqa: F401
    PLAN_CHECKOUT_MATRIX,
    PORTAL_CONFIG_MARKER,
    STRIPE_PROXY_BASE,
    StripeBaseMixin,
)
from app.services.stripe_lifecycle_mixin import StripeLifecycleMixin
from app.services.stripe_overview_mixin import StripeOverviewMixin
from app.services.stripe_plan_change_mixin import StripePlanChangeMixin
from app.services.stripe_portal_mixin import StripePortalMixin
from app.services.stripe_session_mixin import StripeSessionMixin
from app.services.stripe_subscription_sync_mixin import StripeSubscriptionSyncMixin
from app.services.stripe_webhook_mixin import StripeWebhookMixin

load_dotenv(override=False)

logger = logging.getLogger(__name__)


class StripeCheckoutService(
    # Order matters: more-specific mixins first so MRO favours their
    # overrides if any are added in the future. Today every method has a
    # single owner, but this ordering keeps the public surface stable
    # against future refactors.
    StripeWebhookMixin,
    StripePlanChangeMixin,
    StripePortalMixin,
    StripeOverviewMixin,
    StripeSessionMixin,
    StripeLifecycleMixin,
    StripeSubscriptionSyncMixin,
    StripeBaseMixin,
):
    """Composed StripeCheckoutService — see module docstring."""


stripe_checkout_service = StripeCheckoutService()
