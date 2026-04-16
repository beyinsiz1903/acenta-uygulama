from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from app.auth import require_roles
from app.db import get_db
from app.errors import AppError
from app.security.module_guard import require_org_module

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/admin/payment-gateways",
    tags=["admin-payment-gateways"],
    dependencies=[require_org_module("payment_gateways")],
)

AdminDep = Depends(require_roles(["super_admin", "admin"]))

SUPPORTED_PROVIDERS = ["iyzico", "paytr", "stripe"]


class GatewayConfig(BaseModel):
    provider: str = Field(..., description="iyzico | paytr | stripe")
    label: str = ""
    is_active: bool = False
    is_default: bool = False
    mode: str = "test"
    credentials: Dict[str, str] = {}
    supported_currencies: List[str] = ["TRY"]
    max_installment: int = 12
    commission_rate: float = 0.0


class GatewayUpdate(BaseModel):
    label: Optional[str] = None
    is_active: Optional[bool] = None
    is_default: Optional[bool] = None
    mode: Optional[str] = None
    credentials: Optional[Dict[str, str]] = None
    supported_currencies: Optional[List[str]] = None
    max_installment: Optional[int] = None
    commission_rate: Optional[float] = None


def _encrypt_credentials(creds: Dict[str, str]) -> Dict[str, str]:
    import base64
    return {k: base64.b64encode(v.encode()).decode() for k, v in creds.items()} if creds else {}


def _decrypt_credentials(creds: Dict[str, str]) -> Dict[str, str]:
    import base64
    try:
        return {k: base64.b64decode(v.encode()).decode() for k, v in creds.items()} if creds else {}
    except Exception:
        return creds


def _mask_credentials(creds: Dict[str, str]) -> Dict[str, str]:
    decrypted = _decrypt_credentials(creds)
    return {k: v[:4] + "***" if len(v) > 4 else "***" for k, v in decrypted.items()}


class PaymentInitiate(BaseModel):
    gateway_id: str
    order_id: str
    amount: float
    currency: str = "TRY"
    installment: int = 1
    buyer: Dict[str, Any] = {}
    basket_items: List[Dict[str, Any]] = []
    success_url: str = ""
    fail_url: str = ""


async def _audit(db, org_id: str, user: dict, action: str, target_id: str, meta: dict | None = None):
    try:
        await db.audit_logs.insert_one({
            "id": str(uuid.uuid4()),
            "organization_id": org_id,
            "user_id": user.get("user_id", ""),
            "user_email": user.get("email", ""),
            "action": action,
            "module": "payment_gateways",
            "target_id": target_id,
            "meta": meta or {},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
    except Exception:
        logger.exception("Payment gateway audit log failed")


@router.get("")
async def list_gateways(db=Depends(get_db), user: dict = AdminDep):
    org_id = user["organization_id"]
    items = await db.payment_gateways.find({"organization_id": org_id}, {"_id": 0}).sort("created_at", -1).to_list(50)
    for item in items:
        item["credentials"] = _mask_credentials(item.get("credentials", {}))
    return {"items": items, "supported_providers": SUPPORTED_PROVIDERS}


@router.post("", status_code=201)
async def create_gateway(body: GatewayConfig, db=Depends(get_db), user: dict = AdminDep):
    org_id = user["organization_id"]
    if body.provider not in SUPPORTED_PROVIDERS:
        raise AppError(400, "invalid_provider", f"Desteklenmeyen sağlayıcı. İzin verilenler: {', '.join(SUPPORTED_PROVIDERS)}")

    existing = await db.payment_gateways.find_one({"organization_id": org_id, "provider": body.provider})
    if existing:
        raise AppError(409, "gateway_exists", f"{body.provider} zaten yapılandırılmış.")

    if body.is_default:
        await db.payment_gateways.update_many({"organization_id": org_id}, {"$set": {"is_default": False}})

    now = datetime.now(timezone.utc).isoformat()
    data = body.model_dump()
    data["credentials"] = _encrypt_credentials(data.get("credentials", {}))
    doc = {
        "id": str(uuid.uuid4()),
        "organization_id": org_id,
        **data,
        "created_by": user.get("user_id", ""),
        "created_at": now,
        "updated_at": now,
    }
    await db.payment_gateways.insert_one(doc)
    await _audit(db, org_id, user, "gateway_created", doc["id"], {"provider": body.provider})
    doc.pop("_id", None)
    doc["credentials"] = _mask_credentials(doc.get("credentials", {}))
    return doc


@router.patch("/{gateway_id}")
async def update_gateway(gateway_id: str, body: GatewayUpdate, db=Depends(get_db), user: dict = AdminDep):
    org_id = user["organization_id"]
    updates = {k: v for k, v in body.model_dump(exclude_unset=True).items() if v is not None}
    if "credentials" in updates:
        new_creds = updates["credentials"]
        if not new_creds or all(v == "" for v in new_creds.values()):
            del updates["credentials"]
        else:
            existing = await db.payment_gateways.find_one({"organization_id": org_id, "id": gateway_id}, {"credentials": 1})
            if existing:
                merged = _decrypt_credentials(existing.get("credentials", {}))
                for k, v in new_creds.items():
                    if v:
                        merged[k] = v
                updates["credentials"] = _encrypt_credentials(merged)
            else:
                updates["credentials"] = _encrypt_credentials(new_creds)
    if not updates:
        raise AppError(400, "no_fields", "Güncellenecek alan belirtilmedi.")

    if updates.get("is_default"):
        await db.payment_gateways.update_many({"organization_id": org_id}, {"$set": {"is_default": False}})

    updates["updated_at"] = datetime.now(timezone.utc).isoformat()
    result = await db.payment_gateways.update_one({"organization_id": org_id, "id": gateway_id}, {"$set": updates})
    if result.matched_count == 0:
        raise AppError(404, "gateway_not_found", "Ödeme sağlayıcı bulunamadı.")
    await _audit(db, org_id, user, "gateway_updated", gateway_id, {"fields": list(updates.keys())})
    doc = await db.payment_gateways.find_one({"organization_id": org_id, "id": gateway_id}, {"_id": 0})
    doc["credentials"] = _mask_credentials(doc.get("credentials", {}))
    return doc


@router.delete("/{gateway_id}", status_code=204)
async def delete_gateway(gateway_id: str, db=Depends(get_db), user: dict = AdminDep):
    org_id = user["organization_id"]
    result = await db.payment_gateways.delete_one({"organization_id": org_id, "id": gateway_id})
    if result.deleted_count == 0:
        raise AppError(404, "gateway_not_found", "Ödeme sağlayıcı bulunamadı.")
    await _audit(db, org_id, user, "gateway_deleted", gateway_id)


@router.post("/{gateway_id}/test")
async def test_gateway(gateway_id: str, db=Depends(get_db), user: dict = AdminDep):
    org_id = user["organization_id"]
    gw = await db.payment_gateways.find_one({"organization_id": org_id, "id": gateway_id})
    if not gw:
        raise AppError(404, "gateway_not_found", "Ödeme sağlayıcı bulunamadı.")

    provider = gw["provider"]
    creds = _decrypt_credentials(gw.get("credentials", {}))

    if provider == "iyzico":
        from app.billing.iyzico_provider import IyzicoBillingProvider
        base = "https://sandbox-api.iyzipay.com" if gw.get("mode") == "test" else "https://api.iyzipay.com"
        p = IyzicoBillingProvider(api_key=creds.get("api_key", ""), secret_key=creds.get("secret_key", ""), base_url=base)
        result = await p._get("/payment/bin/check")
        return {"provider": provider, "test_result": "success" if result.get("success") else "failed", "details": result.get("error", "OK")}

    if provider == "paytr":
        return {"provider": provider, "test_result": "configured", "details": "PayTR yapılandırıldı. Test ödemesi ile doğrulayın."}

    return {"provider": provider, "test_result": "skipped", "details": "Test desteklenmiyor."}


@router.post("/initiate-payment")
async def initiate_payment(body: PaymentInitiate, request: Request = None, db=Depends(get_db), user: dict = AdminDep):
    org_id = user["organization_id"]
    gw = await db.payment_gateways.find_one({"organization_id": org_id, "id": body.gateway_id})
    if not gw:
        raise AppError(404, "gateway_not_found", "Ödeme sağlayıcı bulunamadı.")
    if not gw.get("is_active"):
        raise AppError(400, "gateway_inactive", "Ödeme sağlayıcı aktif değil.")

    creds = _decrypt_credentials(gw.get("credentials", {}))
    provider = gw["provider"]

    if provider == "iyzico":
        from app.billing.iyzico_provider import IyzicoBillingProvider
        base = "https://sandbox-api.iyzipay.com" if gw.get("mode") == "test" else "https://api.iyzipay.com"
        p = IyzicoBillingProvider(api_key=creds.get("api_key", ""), secret_key=creds.get("secret_key", ""), base_url=base)
        result = await p.create_checkout_form({
            "conversation_id": body.order_id,
            "price": body.amount,
            "paid_price": body.amount,
            "currency": body.currency,
            "installment": body.installment,
            "basket_id": body.order_id,
            "callback_url": body.success_url,
            "buyer": body.buyer,
            "basket_items": body.basket_items,
        })
        payment_log = {
            "id": str(uuid.uuid4()),
            "organization_id": org_id,
            "gateway_id": body.gateway_id,
            "provider": provider,
            "order_id": body.order_id,
            "amount": body.amount,
            "currency": body.currency,
            "status": "initiated" if result.get("success") else "failed",
            "provider_response": {k: v for k, v in result.items() if k != "checkout_form_content"},
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        await db.payment_transactions.insert_one(payment_log)
        return result

    if provider == "paytr":
        from app.billing.paytr_provider import PayTRBillingProvider
        is_test = gw.get("mode") == "test"
        p = PayTRBillingProvider(
            merchant_id=creds.get("merchant_id", ""),
            merchant_key=creds.get("merchant_key", ""),
            merchant_salt=creds.get("merchant_salt", ""),
            test_mode=is_test,
        )
        buyer = body.buyer
        client_ip = ""
        if request:
            client_ip = request.headers.get("x-forwarded-for", "").split(",")[0].strip() or request.client.host if request.client else ""
        result = await p.create_payment_token({
            "order_id": body.order_id,
            "amount_cents": int(body.amount * 100),
            "email": buyer.get("email", ""),
            "user_name": buyer.get("name", ""),
            "user_address": buyer.get("address", ""),
            "user_phone": buyer.get("phone", ""),
            "success_url": body.success_url,
            "fail_url": body.fail_url,
            "currency": body.currency,
            "user_ip": client_ip,
        })
        payment_log = {
            "id": str(uuid.uuid4()),
            "organization_id": org_id,
            "gateway_id": body.gateway_id,
            "provider": provider,
            "order_id": body.order_id,
            "amount": body.amount,
            "currency": body.currency,
            "status": "initiated" if result.get("success") else "failed",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        await db.payment_transactions.insert_one(payment_log)
        return result

    raise AppError(400, "unsupported_provider", f"Sağlayıcı desteklenmiyor: {provider}")
