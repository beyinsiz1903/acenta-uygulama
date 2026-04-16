from __future__ import annotations

import base64
import hashlib
import hmac
import logging
from typing import Any, Dict, Optional

import httpx

from app.billing import (
    BillingCustomer,
    BillingProvider,
    BillingSubscription,
    ProviderCapabilities,
)
from app.errors import AppError

logger = logging.getLogger(__name__)

PAYTR_API_URL = "https://www.paytr.com/odeme"


class PayTRBillingProvider(BillingProvider):
    def __init__(
        self,
        merchant_id: str = "",
        merchant_key: str = "",
        merchant_salt: str = "",
        test_mode: bool = True,
    ):
        self._merchant_id = merchant_id
        self._merchant_key = merchant_key
        self._merchant_salt = merchant_salt
        self._test_mode = test_mode

    @property
    def name(self) -> str:
        return "paytr"

    @property
    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(subscriptions=False, webhooks=True, usage_billing=False)

    def _generate_token(self, params: str) -> str:
        hash_str = params + self._merchant_salt
        token_bytes = hmac.new(
            self._merchant_key.encode("utf-8"),
            hash_str.encode("utf-8"),
            hashlib.sha256,
        ).digest()
        return base64.b64encode(token_bytes).decode("utf-8")

    async def create_payment_token(self, order: Dict[str, Any]) -> Dict[str, Any]:
        merchant_id = self._merchant_id
        user_ip = order.get("user_ip", "")
        if not user_ip:
            raise AppError(400, "missing_user_ip", "Ödeme başlatmak için kullanıcı IP adresi gerekli.")

        merchant_oid = order.get("order_id", "")
        email = order.get("email", "")
        payment_amount = int(order.get("amount_cents", 0))
        user_basket = order.get("basket_json", "[]")
        no_installment = order.get("no_installment", 0)
        max_installment = order.get("max_installment", 0)
        currency = order.get("currency", "TL")
        merchant_ok_url = order.get("success_url", "")
        merchant_fail_url = order.get("fail_url", "")
        user_name = order.get("user_name", "")
        user_address = order.get("user_address", "")
        user_phone = order.get("user_phone", "")

        test_mode_val = 1 if self._test_mode else 0
        hash_input = f"{merchant_id}{user_ip}{merchant_oid}{email}{payment_amount}{user_basket}{no_installment}{max_installment}{currency}{test_mode_val}"
        paytr_token = self._generate_token(hash_input)

        payload = {
            "merchant_id": merchant_id,
            "user_ip": user_ip,
            "merchant_oid": merchant_oid,
            "email": email,
            "payment_amount": payment_amount,
            "paytr_token": paytr_token,
            "user_basket": user_basket,
            "debug_on": 1 if self._test_mode else 0,
            "no_installment": no_installment,
            "max_installment": max_installment,
            "user_name": user_name,
            "user_address": user_address,
            "user_phone": user_phone,
            "merchant_ok_url": merchant_ok_url,
            "merchant_fail_url": merchant_fail_url,
            "timeout_limit": 30,
            "currency": currency,
            "test_mode": test_mode_val,
        }

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(f"{PAYTR_API_URL}/api/get-token", data=payload)
            data = resp.json()
            if data.get("status") == "success":
                return {"success": True, "token": data["token"], "iframe_url": f"https://www.paytr.com/odeme/guvenli/{data['token']}"}
            return {"success": False, "error": data.get("reason", "unknown_error")}
        except Exception as e:
            logger.exception("PayTR token creation failed")
            return {"success": False, "error": str(e)}

    def verify_callback(self, post_data: Dict[str, str]) -> bool:
        merchant_oid = post_data.get("merchant_oid", "")
        status = post_data.get("status", "")
        total_amount = post_data.get("total_amount", "")
        callback_hash = post_data.get("hash", "")

        hash_input = f"{merchant_oid}{self._merchant_salt}{status}{total_amount}"
        expected_bytes = hmac.new(
            self._merchant_key.encode("utf-8"),
            hash_input.encode("utf-8"),
            hashlib.sha256,
        ).digest()
        expected = base64.b64encode(expected_bytes).decode("utf-8")
        return hmac.compare_digest(callback_hash, expected)

    async def create_customer(self, email: str, name: str, metadata: Optional[Dict] = None) -> BillingCustomer:
        return BillingCustomer(
            provider_customer_id=f"paytr_{email}",
            email=email,
            name=name,
            metadata=metadata or {},
        )

    async def create_subscription(self, customer_id: str, price_id: str, metadata: Optional[Dict] = None) -> BillingSubscription:
        raise AppError(501, "provider_not_supported", "PayTR tekrarlayan ödeme desteği henüz aktif değil.", {"provider": "paytr"})

    async def update_subscription(self, subscription_id: str, new_price_id: str) -> BillingSubscription:
        raise AppError(501, "provider_not_supported", "PayTR tekrarlayan ödeme desteği henüz aktif değil.", {"provider": "paytr"})

    async def cancel_subscription(self, subscription_id: str, at_period_end: bool = True) -> BillingSubscription:
        raise AppError(501, "provider_not_supported", "PayTR tekrarlayan ödeme desteği henüz aktif değil.", {"provider": "paytr"})

    async def get_subscription(self, subscription_id: str) -> BillingSubscription:
        raise AppError(501, "provider_not_supported", "PayTR tekrarlayan ödeme desteği henüz aktif değil.", {"provider": "paytr"})
