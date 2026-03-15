"""Provider Capability Matrix (MEGA PROMPT #34).

Defines what each accounting provider supports.
Used by the routing layer to validate operations before dispatching.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ProviderCapability:
    """Capability definition for a single provider."""
    code: str
    name: str
    customer_management: bool = False
    invoice_creation: bool = False
    invoice_cancel: bool = False
    status_polling: bool = False
    pdf_download: bool = False
    webhook_support: bool = False
    rate_limit_rpm: int = 0          # requests per minute, 0 = unknown
    is_active: bool = False          # only Luca is active initially
    description: str = ""
    credential_fields: list[dict] | None = None

    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "name": self.name,
            "capabilities": {
                "customer_management": self.customer_management,
                "invoice_creation": self.invoice_creation,
                "invoice_cancel": self.invoice_cancel,
                "status_polling": self.status_polling,
                "pdf_download": self.pdf_download,
                "webhook_support": self.webhook_support,
            },
            "rate_limit_rpm": self.rate_limit_rpm,
            "is_active": self.is_active,
            "description": self.description,
            "credential_fields": self.credential_fields or [],
        }


# ── Provider Definitions ─────────────────────────────────────────────

LUCA = ProviderCapability(
    code="luca",
    name="Luca",
    customer_management=True,
    invoice_creation=True,
    invoice_cancel=True,
    status_polling=True,
    pdf_download=True,
    webhook_support=False,
    rate_limit_rpm=60,
    is_active=True,
    description="Bulut tabanli muhasebe ve finans yonetim sistemi",
    credential_fields=[
        {"key": "username", "label": "Kullanici Adi", "type": "text", "required": True},
        {"key": "password", "label": "Sifre", "type": "password", "required": True},
        {"key": "company_id", "label": "Firma ID", "type": "text", "required": True},
        {"key": "endpoint", "label": "API Endpoint", "type": "text", "required": False,
         "placeholder": "https://api.lfrcloud.com/api/v1"},
    ],
)

LOGO = ProviderCapability(
    code="logo",
    name="Logo",
    customer_management=True,
    invoice_creation=True,
    invoice_cancel=True,
    status_polling=True,
    pdf_download=True,
    webhook_support=True,
    rate_limit_rpm=120,
    is_active=False,
    description="Logo Yazilim — Tiger/Go/J-Platform ERP entegrasyonu",
    credential_fields=[
        {"key": "api_key", "label": "API Anahtari", "type": "password", "required": True},
        {"key": "api_secret", "label": "API Secret", "type": "password", "required": True},
        {"key": "company_code", "label": "Firma Kodu", "type": "text", "required": True},
        {"key": "endpoint", "label": "API Endpoint", "type": "text", "required": False,
         "placeholder": "https://api.logo.com.tr/v1"},
    ],
)

PARASUT = ProviderCapability(
    code="parasut",
    name="Parasut",
    customer_management=True,
    invoice_creation=True,
    invoice_cancel=True,
    status_polling=True,
    pdf_download=True,
    webhook_support=True,
    rate_limit_rpm=100,
    is_active=False,
    description="Parasut — Bulut muhasebe ve e-fatura platformu",
    credential_fields=[
        {"key": "client_id", "label": "Client ID", "type": "text", "required": True},
        {"key": "client_secret", "label": "Client Secret", "type": "password", "required": True},
        {"key": "company_id", "label": "Sirket ID", "type": "text", "required": True},
        {"key": "endpoint", "label": "API Endpoint", "type": "text", "required": False,
         "placeholder": "https://api.parasut.com/v4"},
    ],
)

MIKRO = ProviderCapability(
    code="mikro",
    name="Mikro",
    customer_management=True,
    invoice_creation=True,
    invoice_cancel=False,
    status_polling=True,
    pdf_download=False,
    webhook_support=False,
    rate_limit_rpm=30,
    is_active=False,
    description="Mikro Yazilim — On-premise ERP muhasebe sistemi",
    credential_fields=[
        {"key": "username", "label": "Kullanici Adi", "type": "text", "required": True},
        {"key": "password", "label": "Sifre", "type": "password", "required": True},
        {"key": "database_name", "label": "Veritabani Adi", "type": "text", "required": True},
        {"key": "endpoint", "label": "API Endpoint", "type": "text", "required": True,
         "placeholder": "http://localhost:8080/mikro-api"},
    ],
)


# ── Registry ─────────────────────────────────────────────────────────

CAPABILITY_MATRIX: dict[str, ProviderCapability] = {
    "luca": LUCA,
    "logo": LOGO,
    "parasut": PARASUT,
    "mikro": MIKRO,
}


def get_capability(provider_code: str) -> ProviderCapability | None:
    return CAPABILITY_MATRIX.get(provider_code)


def list_all_providers() -> list[dict]:
    return [cap.to_dict() for cap in CAPABILITY_MATRIX.values()]


def list_active_providers() -> list[dict]:
    return [cap.to_dict() for cap in CAPABILITY_MATRIX.values() if cap.is_active]


def supports_operation(provider_code: str, operation: str) -> bool:
    """Check if a provider supports a given operation."""
    cap = CAPABILITY_MATRIX.get(provider_code)
    if not cap:
        return False
    return getattr(cap, operation, False)
