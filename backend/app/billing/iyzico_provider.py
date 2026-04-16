from __future__ import annotations

import hashlib
import hmac
import base64
import logging
import json
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

IYZICO_SANDBOX = "https://sandbox-api.iyzipay.com"
IYZICO_PRODUCTION = "https://api.iyzipay.com"


class IyzicoBillingProvider(BillingProvider):
    def __init__(
        self,
        api_key: str = "",
        secret_key: str = "",
        base_url: str = IYZICO_SANDBOX,
    ):
        self._api_key = api_key
        self._secret_key = secret_key
        self._base_url = base_url.rstrip("/")

    @property
    def name(self) -> str:
        return "iyzico"

    @property
    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(subscriptions=True, webhooks=True, usage_billing=False)

    def _generate_auth_header(self, uri: str, body_json: str = "") -> dict:
        random_header_value = hashlib.md5(f"{self._api_key}{__import__('time').time()}".encode()).hexdigest()[:8]
        payload_to_sign = f"{random_header_value}{uri}{body_json}"
        signature = hmac.new(
            self._secret_key.encode("utf-8"),
            payload_to_sign.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        auth_value = base64.b64encode(
            f"apiKey:{self._api_key}&randomHeaderValue:{random_header_value}&signature:{signature}".encode()
        ).decode()
        return {
            "Authorization": f"IYZWSv2 {auth_value}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "x-iyzi-rnd": random_header_value,
        }

    async def _post(self, uri: str, payload: dict) -> dict:
        body_json = json.dumps(payload, ensure_ascii=False)
        headers = self._generate_auth_header(uri, body_json)
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(f"{self._base_url}{uri}", content=body_json, headers=headers)
            data = resp.json()
            if data.get("status") == "success":
                return {"success": True, "data": data}
            return {"success": False, "error": data.get("errorMessage", "unknown"), "error_code": data.get("errorCode")}
        except Exception as e:
            logger.exception("İyzico API error")
            return {"success": False, "error": str(e)}

    async def _get(self, uri: str) -> dict:
        headers = self._generate_auth_header(uri)
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(f"{self._base_url}{uri}", headers=headers)
            data = resp.json()
            if data.get("status") == "success":
                return {"success": True, "data": data}
            return {"success": False, "error": data.get("errorMessage", "unknown")}
        except Exception as e:
            logger.exception("İyzico API error")
            return {"success": False, "error": str(e)}

    async def create_checkout_form(self, order: Dict[str, Any]) -> Dict[str, Any]:
        payload = {
            "locale": "tr",
            "conversationId": order.get("conversation_id", ""),
            "price": str(order.get("price", 0)),
            "paidPrice": str(order.get("paid_price", order.get("price", 0))),
            "currency": order.get("currency", "TRY"),
            "installment": order.get("installment", 1),
            "basketId": order.get("basket_id", ""),
            "paymentChannel": "WEB",
            "paymentGroup": "PRODUCT",
            "callbackUrl": order.get("callback_url", ""),
            "buyer": order.get("buyer", {}),
            "shippingAddress": order.get("shipping_address", {}),
            "billingAddress": order.get("billing_address", {}),
            "basketItems": order.get("basket_items", []),
        }
        result = await self._post("/payment/iyzi-pos/checkoutform/initialize/auth/ecom", payload)
        if result.get("success"):
            return {
                "success": True,
                "checkout_form_content": result["data"].get("checkoutFormContent", ""),
                "token": result["data"].get("token", ""),
                "token_expire_time": result["data"].get("tokenExpireTime", 0),
            }
        return result

    async def retrieve_checkout_result(self, token: str) -> Dict[str, Any]:
        payload = {"locale": "tr", "token": token}
        return await self._post("/payment/iyzi-pos/checkoutform/auth/ecom/detail", payload)

    async def create_payment_3ds(self, order: Dict[str, Any]) -> Dict[str, Any]:
        payload = {
            "locale": "tr",
            "conversationId": order.get("conversation_id", ""),
            "price": str(order.get("price", 0)),
            "paidPrice": str(order.get("paid_price", order.get("price", 0))),
            "currency": order.get("currency", "TRY"),
            "installment": order.get("installment", 1),
            "paymentCard": order.get("payment_card", {}),
            "buyer": order.get("buyer", {}),
            "shippingAddress": order.get("shipping_address", {}),
            "billingAddress": order.get("billing_address", {}),
            "basketItems": order.get("basket_items", []),
            "callbackUrl": order.get("callback_url", ""),
        }
        result = await self._post("/payment/3dsecure/initialize", payload)
        if result.get("success"):
            return {
                "success": True,
                "three_ds_html": result["data"].get("threeDSHtmlContent", ""),
            }
        return result

    async def refund(self, payment_transaction_id: str, amount: float, currency: str = "TRY") -> Dict[str, Any]:
        payload = {
            "locale": "tr",
            "paymentTransactionId": payment_transaction_id,
            "price": str(amount),
            "currency": currency,
        }
        return await self._post("/payment/refund", payload)

    async def cancel(self, payment_id: str, reason: str = "") -> Dict[str, Any]:
        payload = {
            "locale": "tr",
            "paymentId": payment_id,
            "reason": reason or "BUYER_REQUEST",
        }
        return await self._post("/payment/cancel", payload)

    async def create_sub_merchant(self, merchant_data: Dict[str, Any]) -> Dict[str, Any]:
        payload = {
            "locale": "tr",
            "conversationId": merchant_data.get("conversation_id", ""),
            "subMerchantExternalId": merchant_data.get("external_id", ""),
            "subMerchantType": merchant_data.get("type", "PERSONAL_COMPANY"),
            "address": merchant_data.get("address", ""),
            "email": merchant_data.get("email", ""),
            "gsmNumber": merchant_data.get("phone", ""),
            "name": merchant_data.get("name", ""),
            "iban": merchant_data.get("iban", ""),
            "identityNumber": merchant_data.get("identity_number", ""),
            "currency": merchant_data.get("currency", "TRY"),
        }
        return await self._post("/onboarding/submerchant", payload)

    async def create_customer(self, email: str, name: str, metadata: Optional[Dict] = None) -> BillingCustomer:
        return BillingCustomer(
            provider_customer_id=f"iyzico_{email}",
            email=email,
            name=name,
            metadata=metadata or {},
        )

    async def create_subscription(self, customer_id: str, price_id: str, metadata: Optional[Dict] = None) -> BillingSubscription:
        payload = {
            "locale": "tr",
            "customer": customer_id,
            "pricingPlanReferenceCode": price_id,
        }
        result = await self._post("/v2/subscription/initialize", payload)
        if not result.get("success"):
            raise AppError(502, "iyzico_subscription_error", result.get("error", "Abonelik oluşturulamadı."))

        data = result.get("data", {})
        return BillingSubscription(
            provider_subscription_id=data.get("referenceCode", ""),
            provider_customer_id=customer_id,
            plan=price_id,
            status="active",
            metadata=metadata or {},
        )

    async def update_subscription(self, subscription_id: str, new_price_id: str) -> BillingSubscription:
        payload = {
            "locale": "tr",
            "subscriptionReferenceCode": subscription_id,
            "newPricingPlanReferenceCode": new_price_id,
        }
        result = await self._post("/v2/subscription/update", payload)
        if not result.get("success"):
            raise AppError(502, "iyzico_subscription_error", result.get("error", "Abonelik güncellenemedi."))

        return BillingSubscription(
            provider_subscription_id=subscription_id,
            provider_customer_id="",
            plan=new_price_id,
            status="active",
        )

    async def cancel_subscription(self, subscription_id: str, at_period_end: bool = True) -> BillingSubscription:
        payload = {
            "locale": "tr",
            "subscriptionReferenceCode": subscription_id,
        }
        result = await self._post("/v2/subscription/cancel", payload)
        if not result.get("success"):
            raise AppError(502, "iyzico_subscription_error", result.get("error", "Abonelik iptal edilemedi."))

        return BillingSubscription(
            provider_subscription_id=subscription_id,
            provider_customer_id="",
            plan="",
            status="canceled",
        )

    async def get_subscription(self, subscription_id: str) -> BillingSubscription:
        result = await self._get(f"/v2/subscription/{subscription_id}")
        if not result.get("success"):
            raise AppError(502, "iyzico_subscription_error", result.get("error", "Abonelik bulunamadı."))

        data = result.get("data", {})
        return BillingSubscription(
            provider_subscription_id=subscription_id,
            provider_customer_id=data.get("customerReferenceCode", ""),
            plan=data.get("pricingPlanReferenceCode", ""),
            status=data.get("subscriptionStatus", "unknown").lower(),
        )
