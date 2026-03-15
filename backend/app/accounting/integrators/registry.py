"""Integrator Registry (Faz 2 + 3).

Maps provider names to their integrator adapter classes.
Supports both e-document integrators (EDM, Foriba) and accounting integrators (Luca, Logo).
"""
from __future__ import annotations

from typing import Any

from app.accounting.integrators.base_integrator import BaseIntegrator
from app.accounting.integrators.base_accounting_integrator import BaseAccountingIntegrator
from app.accounting.integrators.edm_integrator import EDMIntegrator
from app.accounting.integrators.luca_integrator import LucaIntegrator


# ── E-Document Integrators (EDM, Foriba, etc.) ───────────────────────

_EDOC_REGISTRY: dict[str, type[BaseIntegrator]] = {
    "edm": EDMIntegrator,
}

_EDOC_INSTANCES: dict[str, BaseIntegrator] = {}


def get_integrator(provider: str) -> BaseIntegrator | None:
    """Get e-document integrator instance by provider name. Singleton per provider."""
    if provider not in _EDOC_REGISTRY:
        return None
    if provider not in _EDOC_INSTANCES:
        _EDOC_INSTANCES[provider] = _EDOC_REGISTRY[provider]()
    return _EDOC_INSTANCES[provider]


# ── Accounting Integrators (Luca, Logo, Parasut, Mikro) ──────────────

_ACCT_REGISTRY: dict[str, type[BaseAccountingIntegrator]] = {
    "luca": LucaIntegrator,
}

_ACCT_INSTANCES: dict[str, BaseAccountingIntegrator] = {}


def get_accounting_integrator(provider: str) -> BaseAccountingIntegrator | None:
    """Get accounting integrator instance by provider name. Singleton per provider."""
    if provider not in _ACCT_REGISTRY:
        return None
    if provider not in _ACCT_INSTANCES:
        _ACCT_INSTANCES[provider] = _ACCT_REGISTRY[provider]()
    return _ACCT_INSTANCES[provider]


# ── Provider Listing ──────────────────────────────────────────────────

def list_supported_providers() -> list[dict[str, Any]]:
    """Return list of supported e-document integrator providers."""
    return [
        {
            "code": "edm",
            "name": "EDM (e-Belge Daginim Merkezi)",
            "description": "Turkiye'nin onde gelen e-fatura entegratoru",
            "category": "e_document",
            "credential_fields": [
                {"key": "username", "label": "Kullanici Adi", "type": "text", "required": True},
                {"key": "password", "label": "Sifre", "type": "password", "required": True},
                {"key": "company_code", "label": "Firma Kodu", "type": "text", "required": False},
                {"key": "endpoint", "label": "API Endpoint", "type": "text", "required": False,
                 "placeholder": "https://ebelge.edm.com.tr/api"},
            ],
        },
    ]


def list_accounting_providers() -> list[dict[str, Any]]:
    """Return list of supported accounting integrator providers."""
    return [
        {
            "code": "luca",
            "name": "Luca",
            "description": "Bulut tabanli muhasebe ve finans yonetim sistemi",
            "category": "accounting",
            "credential_fields": [
                {"key": "username", "label": "Kullanici Adi", "type": "text", "required": True},
                {"key": "password", "label": "Sifre", "type": "password", "required": True},
                {"key": "company_id", "label": "Firma ID", "type": "text", "required": True},
                {"key": "endpoint", "label": "API Endpoint", "type": "text", "required": False,
                 "placeholder": "https://api.lfrcloud.com/api/v1"},
            ],
        },
    ]
