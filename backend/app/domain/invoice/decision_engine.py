"""E-Document Decision Engine (Faz 1).

Determines whether an invoice should be:
- e-Fatura (B2B, customer has VKN and is e-fatura registered)
- e-Arsiv (B2C, or customer not e-fatura registered)
- draft_only (no integrator configured)
- accounting_only (no e-document, just accounting sync)

Simple rule-based engine. Will be enhanced in later phases.
"""
from __future__ import annotations

from typing import Any


def decide_document_type(
    customer_type: str,
    tax_id: str = "",
    id_number: str = "",
    agency_policy: str = "auto",
    integrator_available: bool = False,
) -> dict[str, Any]:
    """Determine the e-document type for an invoice.

    Args:
        customer_type: 'b2b' or 'b2c'
        tax_id: VKN (Vergi Kimlik Numarasi) - 10 digits for companies
        id_number: TCKN (TC Kimlik No) - 11 digits for individuals
        agency_policy: 'auto', 'manual', 'e_fatura_only', 'e_arsiv_only', 'draft_only'
        integrator_available: Whether an e-document integrator is configured

    Returns:
        Decision dict with document_type and reasoning
    """
    # Policy overrides
    if agency_policy == "draft_only":
        return {
            "document_type": "draft_only",
            "reason": "agency_policy_draft_only",
            "requires_integrator": False,
        }

    if agency_policy == "e_fatura_only":
        return {
            "document_type": "e_fatura",
            "reason": "agency_policy_e_fatura_only",
            "requires_integrator": True,
        }

    if agency_policy == "e_arsiv_only":
        return {
            "document_type": "e_arsiv",
            "reason": "agency_policy_e_arsiv_only",
            "requires_integrator": True,
        }

    # No integrator → draft_only
    if not integrator_available:
        return {
            "document_type": "draft_only",
            "reason": "no_integrator_configured",
            "requires_integrator": False,
        }

    # B2B with VKN → e-Fatura
    has_vkn = bool(tax_id and len(tax_id.strip()) >= 10)
    has_tckn = bool(id_number and len(id_number.strip()) == 11)

    if customer_type == "b2b" and has_vkn:
        return {
            "document_type": "e_fatura",
            "reason": "b2b_with_vkn",
            "requires_integrator": True,
        }

    # B2C or B2B without VKN → e-Arsiv
    if has_tckn or has_vkn:
        return {
            "document_type": "e_arsiv",
            "reason": "individual_or_unregistered",
            "requires_integrator": True,
        }

    # Fallback: e-Arsiv with TCKN/VKN missing
    return {
        "document_type": "e_arsiv",
        "reason": "default_e_arsiv",
        "requires_integrator": True,
    }
