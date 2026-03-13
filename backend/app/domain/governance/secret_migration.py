"""Secret Management — Migration Path from env-based to Vault/KMS.

Provides:
- Current secret inventory
- Migration readiness check
- Rotation model
- Cutover strategy
"""
from __future__ import annotations

import os
import logging
from typing import Any

logger = logging.getLogger("secrets.migration")

# Current secrets inventory
ENV_SECRETS = {
    "MONGO_URL": {"type": "database_credential", "rotation": "manual", "risk": "high", "vault_path": "secret/data/mongodb"},
    "REDIS_URL": {"type": "connection_string", "rotation": "manual", "risk": "medium", "vault_path": "secret/data/redis"},
    "JWT_SECRET": {"type": "encryption_key", "rotation": "quarterly", "risk": "critical", "vault_path": "secret/data/jwt"},
    "AVIATIONSTACK_API_KEY": {"type": "api_key", "rotation": "annual", "risk": "low", "vault_path": "secret/data/aviationstack"},
    "RESEND_API_KEY": {"type": "api_key", "rotation": "annual", "risk": "medium", "vault_path": "secret/data/resend"},
    "PAXIMUM_API_KEY": {"type": "api_key", "rotation": "annual", "risk": "high", "vault_path": "secret/data/paximum"},
    "AMADEUS_API_KEY": {"type": "api_key", "rotation": "annual", "risk": "high", "vault_path": "secret/data/amadeus"},
    "AMADEUS_API_SECRET": {"type": "api_secret", "rotation": "annual", "risk": "high", "vault_path": "secret/data/amadeus"},
    "SLACK_WEBHOOK_URL": {"type": "webhook_secret", "rotation": "annual", "risk": "low", "vault_path": "secret/data/slack"},
    "STRIPE_SECRET_KEY": {"type": "api_key", "rotation": "annual", "risk": "critical", "vault_path": "secret/data/stripe"},
}


def get_secret_inventory() -> list[dict[str, Any]]:
    """Get inventory of all managed secrets with their status."""
    inventory = []
    for key, meta in ENV_SECRETS.items():
        value = os.environ.get(key)
        inventory.append({
            "key": key,
            "type": meta["type"],
            "rotation_policy": meta["rotation"],
            "risk_level": meta["risk"],
            "vault_path": meta["vault_path"],
            "is_configured": bool(value),
            "is_empty": not bool(value),
            "value_preview": f"{value[:4]}...{value[-4:]}" if value and len(value) > 8 else ("***" if value else "NOT_SET"),
        })
    return inventory


def get_migration_readiness() -> dict[str, Any]:
    """Check migration readiness."""
    inventory = get_secret_inventory()
    configured = sum(1 for s in inventory if s["is_configured"])
    total = len(inventory)
    critical = [s for s in inventory if s["risk_level"] == "critical"]
    critical_configured = sum(1 for s in critical if s["is_configured"])

    return {
        "total_secrets": total,
        "configured": configured,
        "missing": total - configured,
        "critical_secrets": len(critical),
        "critical_configured": critical_configured,
        "readiness_score": round(configured / total * 100, 1) if total > 0 else 0,
        "migration_phase": "env_based",
        "target_phase": "vault_kms",
        "migration_steps": [
            {"step": 1, "action": "Audit current env secrets", "status": "done"},
            {"step": 2, "action": "Deploy Vault/KMS instance", "status": "pending"},
            {"step": 3, "action": "Create vault paths and policies", "status": "pending"},
            {"step": 4, "action": "Migrate secrets to vault", "status": "pending"},
            {"step": 5, "action": "Update app to read from vault", "status": "pending"},
            {"step": 6, "action": "Remove env secrets", "status": "pending"},
            {"step": 7, "action": "Enable rotation policies", "status": "pending"},
        ],
        "rollback_strategy": "Keep env vars as fallback until vault is verified. App reads vault first, falls back to env.",
    }


# Rotation model
ROTATION_MODEL = {
    "critical": {"frequency": "quarterly", "auto_rotate": True, "notification_days_before": 14},
    "high": {"frequency": "semi_annual", "auto_rotate": True, "notification_days_before": 30},
    "medium": {"frequency": "annual", "auto_rotate": False, "notification_days_before": 60},
    "low": {"frequency": "annual", "auto_rotate": False, "notification_days_before": 90},
}
