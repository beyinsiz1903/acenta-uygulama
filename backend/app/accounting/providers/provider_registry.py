"""Provider Registry (MEGA PROMPT #34).

Maps provider codes to their adapter instances.
Single source of truth for provider resolution.
"""
from __future__ import annotations

from app.accounting.providers.base_provider import BaseAccountingProvider
from app.accounting.providers.luca_provider import LucaProvider
from app.accounting.providers.logo_provider import LogoProvider
from app.accounting.providers.parasut_provider import ParasutProvider
from app.accounting.providers.mikro_provider import MikroProvider

_PROVIDER_CLASSES: dict[str, type[BaseAccountingProvider]] = {
    "luca": LucaProvider,
    "logo": LogoProvider,
    "parasut": ParasutProvider,
    "mikro": MikroProvider,
}

_INSTANCES: dict[str, BaseAccountingProvider] = {}


def get_provider(code: str) -> BaseAccountingProvider | None:
    """Get a singleton provider instance by code."""
    if code not in _PROVIDER_CLASSES:
        return None
    if code not in _INSTANCES:
        _INSTANCES[code] = _PROVIDER_CLASSES[code]()
    return _INSTANCES[code]


def list_provider_codes() -> list[str]:
    return list(_PROVIDER_CLASSES.keys())
