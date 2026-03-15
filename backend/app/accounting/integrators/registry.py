"""Integrator Registry (Faz 2).

Maps provider names to their integrator adapter classes.
"""
from __future__ import annotations

from typing import Any

from app.accounting.integrators.base_integrator import BaseIntegrator
from app.accounting.integrators.edm_integrator import EDMIntegrator


_REGISTRY: dict[str, type[BaseIntegrator]] = {
    "edm": EDMIntegrator,
}

_INSTANCES: dict[str, BaseIntegrator] = {}


def get_integrator(provider: str) -> BaseIntegrator | None:
    """Get integrator instance by provider name. Singleton per provider."""
    if provider not in _REGISTRY:
        return None
    if provider not in _INSTANCES:
        _INSTANCES[provider] = _REGISTRY[provider]()
    return _INSTANCES[provider]


def list_supported_providers() -> list[dict[str, Any]]:
    """Return list of supported integrator providers."""
    return [
        {
            "code": "edm",
            "name": "EDM (e-Belge Daginim Merkezi)",
            "description": "Turkiye'nin onde gelen e-fatura entegratoru",
            "credential_fields": [
                {"key": "username", "label": "Kullanici Adi", "type": "text", "required": True},
                {"key": "password", "label": "Sifre", "type": "password", "required": True},
                {"key": "company_code", "label": "Firma Kodu", "type": "text", "required": False},
                {"key": "endpoint", "label": "API Endpoint", "type": "text", "required": False,
                 "placeholder": "https://ebelge.edm.com.tr/api"},
            ],
        },
    ]
