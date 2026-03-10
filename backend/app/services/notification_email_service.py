from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterable

from bson import ObjectId

from app.services.email_outbox import enqueue_generic_email
from app.services.quota_warning_service import METRIC_LIMIT_SUBJECTS, METRIC_UNITS, calculate_warning_level

ORG_NOTIFICATION_ROLES = {"super_admin", "admin"}
TENANT_NOTIFICATION_ROLES = {"agency_admin", "hotel_admin"}

LEVEL_SUBJECTS = {
    "warning": "Kota Uyarısı",
    "critical": "Kritik Kota Uyarısı",
    "limit_reached": "Kota Doldu",
}


def _normalize_email_list(values: Iterable[str | None]) -> list[str]:
    emails = sorted({str(value or "").strip().lower() for value in values if value and "@" in str(value)})
    return [email for email in emails if email]


def _id_variants(value: Any) -> list[Any]:
    variants: list[Any] = []
    if value in (None, ""):
        return variants
    variants.append(value)
    text_value = str(value)
    if text_value != value:
        variants.append(text_value)
    try:
        variants.append(ObjectId(text_value))
    except Exception:
        pass
    deduped: list[Any] = []
    for item in variants:
        if item not in deduped:
            deduped.append(item)
    return deduped


def _format_try_minor(value: Any) -> str | None:
    if value in (None, ""):
        return None
    try:
        amount_minor = int(value)
    except Exception:
        try:
            amount_minor = int(float(value))
        except Exception:
            return None
    amount = amount_minor / 100.0
    formatted = f"{amount:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")
    return f"₺{formatted}"


def _format_iso_datetime(value: str | None) -> str | None:
    if not value:
        return None
    try:
        normalized = value.replace("Z", "+00:00")
        dt = datetime.fromisoformat(normalized)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).strftime("%d.%m.%Y %H:%M UTC")
    except Exception:
        return value


async def resolve_notification_recipients(
    db,
    *,
    organization_id: str,
    tenant_id: str,
) -> list[str]:
    membership_rows = await db.memberships.find(
        {"tenant_id": tenant_id, "status": "active"},
        {"_id": 0, "user_id": 1},
    ).to_list(200)

    membership_user_ids: list[Any] = []
    for row in membership_rows:
        membership_user_ids.extend(_id_variants(row.get("user_id")))

    tenant_scope_conditions: list[dict[str, Any]] = [{"tenant_id": tenant_id}]
    if membership_user_ids:
        tenant_scope_conditions.append({"_id": {"$in": membership_user_ids}})

    primary_query: dict[str, Any] = {
        "organization_id": organization_id,
        "is_active": True,
        "$or": [
            {"roles": {"$in": sorted(ORG_NOTIFICATION_ROLES)}},
            {
                "roles": {"$in": sorted(TENANT_NOTIFICATION_ROLES)},
                "$or": tenant_scope_conditions,
            },
        ],
    }
    docs = await db.users.find(primary_query, {"_id": 0, "email": 1}).to_list(100)
    emails = _normalize_email_list(doc.get("email") for doc in docs)
    if emails:
        return emails

    fallback_query = {
        "organization_id": organization_id,
        "is_active": True,
        "$or": tenant_scope_conditions,
    }
    fallback_docs = await db.users.find(fallback_query, {"_id": 0, "email": 1}).to_list(100)
    return _normalize_email_list(doc.get("email") for doc in fallback_docs)


async def enqueue_payment_failed_email(
    db,
    *,
    organization_id: str,
    tenant_id: str,
    subscription_id: str,
    amount_due: Any,
    failed_at: str | None,
    grace_period_until: str | None,
    invoice_hosted_url: str | None = None,
    invoice_pdf_url: str | None = None,
    dedupe_key: str | None = None,
) -> str | None:
    tenant_doc = await db.tenants.find_one({"_id": tenant_id}, {"_id": 0, "name": 1})
    tenant_name = str((tenant_doc or {}).get("name") or "Hesabınız")
    subscription = await db.billing_subscriptions.find_one(
        {"tenant_id": tenant_id},
        {"_id": 0, "plan": 1, "interval": 1},
    )

    recipients = await resolve_notification_recipients(db, organization_id=organization_id, tenant_id=tenant_id)
    if not recipients:
        return None

    failed_label = _format_iso_datetime(failed_at) or "Bilinmiyor"
    grace_label = _format_iso_datetime(grace_period_until) or "Belirtilmedi"
    amount_label = _format_try_minor(amount_due) or "Tutar bilgisi yok"
    plan_label = str((subscription or {}).get("plan") or "plan").title()
    interval_label = "Yıllık" if (subscription or {}).get("interval") == "yearly" else "Aylık"

    links_html = []
    links_text = []
    if invoice_hosted_url:
        links_html.append(f'<li><a href="{invoice_hosted_url}">Faturayı görüntüle</a></li>')
        links_text.append(f"Fatura: {invoice_hosted_url}")
    if invoice_pdf_url:
        links_html.append(f'<li><a href="{invoice_pdf_url}">PDF indir</a></li>')
        links_text.append(f"PDF: {invoice_pdf_url}")
    links_block = f"<ul>{''.join(links_html)}</ul>" if links_html else ""

    subject = f"[Ödeme Başarısız] {tenant_name} için tahsilat alınamadı"
    html_body = (
        f"<h2>Ödeme alınamadı</h2>"
        f"<p><strong>Tenant:</strong> {tenant_name}</p>"
        f"<p><strong>Plan:</strong> {plan_label} · {interval_label}</p>"
        f"<p><strong>Tutar:</strong> {amount_label}</p>"
        f"<p><strong>Son deneme:</strong> {failed_label}</p>"
        f"<p><strong>Grace period sonu:</strong> {grace_label}</p>"
        f"<p>Ödeme yönteminizi güncellemeniz veya faturayı tekrar denemeniz önerilir.</p>"
        f"{links_block}"
    )
    text_body = "\n".join(
        [
            "Ödeme alınamadı",
            f"Tenant: {tenant_name}",
            f"Plan: {plan_label} / {interval_label}",
            f"Tutar: {amount_label}",
            f"Son deneme: {failed_label}",
            f"Grace period sonu: {grace_label}",
            *links_text,
        ]
    )
    computed_dedupe_key = dedupe_key or (
        f"billing.payment_failed:{tenant_id}:{subscription_id}:{failed_at or 'unknown'}:{amount_due or 'na'}"
    )
    return await enqueue_generic_email(
        db,
        organization_id=organization_id,
        tenant_id=tenant_id,
        to_addresses=recipients,
        subject=subject,
        html_body=html_body,
        text_body=text_body,
        event_type="billing.payment_failed",
        metadata={
            "subscription_id": subscription_id,
            "amount_due": amount_due,
            "failed_at": failed_at,
            "grace_period_until": grace_period_until,
            "invoice_hosted_url": invoice_hosted_url,
            "invoice_pdf_url": invoice_pdf_url,
        },
        dedupe_key=computed_dedupe_key,
    )


async def maybe_enqueue_quota_warning_email(
    db,
    *,
    organization_id: str,
    tenant_id: str,
    metric: str,
    used: int,
    limit: int | None,
    previous_used: int,
    billing_period: str,
    plan_label: str,
) -> str | None:
    if limit in (None, 0):
        return None

    current_level = calculate_warning_level(used, limit)
    previous_level = calculate_warning_level(previous_used, limit)
    if current_level not in {"warning", "critical", "limit_reached"}:
        return None
    if current_level == previous_level:
        return None

    recipients = await resolve_notification_recipients(db, organization_id=organization_id, tenant_id=tenant_id)
    if not recipients:
        return None

    tenant_doc = await db.tenants.find_one({"_id": tenant_id}, {"_id": 0, "name": 1})
    tenant_name = str((tenant_doc or {}).get("name") or "Tenant")
    metric_subject = METRIC_LIMIT_SUBJECTS.get(metric, metric)
    metric_unit = METRIC_UNITS.get(metric, "kullanım")
    remaining = max(0, int(limit) - int(used))
    usage_percent = round((used / limit) * 100)

    subject = f"[{LEVEL_SUBJECTS[current_level]}] {tenant_name} · {metric_subject}"
    html_body = (
        f"<h2>{LEVEL_SUBJECTS[current_level]}</h2>"
        f"<p><strong>Tenant:</strong> {tenant_name}</p>"
        f"<p><strong>Plan:</strong> {plan_label}</p>"
        f"<p><strong>Metric:</strong> {metric_subject}</p>"
        f"<p><strong>Kullanım:</strong> {used} / {limit} ({usage_percent}%)</p>"
        f"<p><strong>Kalan:</strong> {remaining} {metric_unit}</p>"
        f"<p>Billing period: {billing_period}</p>"
        f"<p>Plan yükseltme değerlendirmesi için <a href=\"/pricing\">fiyatlandırma</a> ekranını kontrol edin.</p>"
    )
    text_body = "\n".join(
        [
            LEVEL_SUBJECTS[current_level],
            f"Tenant: {tenant_name}",
            f"Plan: {plan_label}",
            f"Metric: {metric_subject}",
            f"Kullanım: {used}/{limit} ({usage_percent}%)",
            f"Kalan: {remaining} {metric_unit}",
            f"Billing period: {billing_period}",
        ]
    )
    return await enqueue_generic_email(
        db,
        organization_id=organization_id,
        tenant_id=tenant_id,
        to_addresses=recipients,
        subject=subject,
        html_body=html_body,
        text_body=text_body,
        event_type=f"usage.quota_{current_level}",
        metadata={
            "metric": metric,
            "used": used,
            "limit": limit,
            "previous_used": previous_used,
            "warning_level": current_level,
            "billing_period": billing_period,
        },
        dedupe_key=f"quota.warning:{tenant_id}:{billing_period}:{metric}:{current_level}",
    )
