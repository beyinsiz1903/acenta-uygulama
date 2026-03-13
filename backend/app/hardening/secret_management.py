"""PART 6 — Secret Management Migration.

Replace env-based secrets with Vault/AWS Secrets Manager.
Provides migration path, rotation policies, and audit trail.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger("hardening.secret_management")


# Secret inventory — all secrets used by the platform
SECRET_INVENTORY = [
    {
        "name": "JWT_SECRET",
        "env_key": "JWT_SECRET",
        "current_source": "env",
        "target_source": "vault",
        "vault_path": "secret/syroce/auth/jwt_secret",
        "rotation_policy": "90_days",
        "risk_level": "critical",
        "description": "JWT token signing secret",
        "is_configured": bool(os.environ.get("JWT_SECRET")),
    },
    {
        "name": "MONGO_URL",
        "env_key": "MONGO_URL",
        "current_source": "env",
        "target_source": "vault",
        "vault_path": "secret/syroce/database/mongo_url",
        "rotation_policy": "180_days",
        "risk_level": "critical",
        "description": "MongoDB connection string",
        "is_configured": bool(os.environ.get("MONGO_URL")),
    },
    {
        "name": "REDIS_URL",
        "env_key": "REDIS_URL",
        "current_source": "env",
        "target_source": "vault",
        "vault_path": "secret/syroce/cache/redis_url",
        "rotation_policy": "180_days",
        "risk_level": "high",
        "description": "Redis connection string",
        "is_configured": bool(os.environ.get("REDIS_URL")),
    },
    {
        "name": "STRIPE_API_KEY",
        "env_key": "STRIPE_API_KEY",
        "current_source": "env",
        "target_source": "aws_secrets_manager",
        "aws_secret_id": "syroce/payments/stripe_api_key",
        "rotation_policy": "90_days",
        "risk_level": "critical",
        "description": "Stripe payment API key",
        "is_configured": bool(os.environ.get("STRIPE_API_KEY")),
    },
    {
        "name": "PAXIMUM_API_KEY",
        "env_key": "PAXIMUM_API_KEY",
        "current_source": "env",
        "target_source": "vault",
        "vault_path": "secret/syroce/suppliers/paximum_api_key",
        "rotation_policy": "90_days",
        "risk_level": "high",
        "description": "Paximum supplier API key",
        "is_configured": bool(os.environ.get("PAXIMUM_API_KEY")),
    },
    {
        "name": "AMADEUS_API_KEY",
        "env_key": "AMADEUS_API_KEY",
        "current_source": "env",
        "target_source": "vault",
        "vault_path": "secret/syroce/suppliers/amadeus_api_key",
        "rotation_policy": "90_days",
        "risk_level": "high",
        "description": "Amadeus GDS API key",
        "is_configured": bool(os.environ.get("AMADEUS_API_KEY")),
    },
    {
        "name": "AVIATIONSTACK_API_KEY",
        "env_key": "AVIATIONSTACK_API_KEY",
        "current_source": "env",
        "target_source": "vault",
        "vault_path": "secret/syroce/suppliers/aviationstack_api_key",
        "rotation_policy": "90_days",
        "risk_level": "high",
        "description": "AviationStack flight API key",
        "is_configured": bool(os.environ.get("AVIATIONSTACK_API_KEY")),
    },
    {
        "name": "RESEND_API_KEY",
        "env_key": "RESEND_API_KEY",
        "current_source": "env",
        "target_source": "vault",
        "vault_path": "secret/syroce/notifications/resend_api_key",
        "rotation_policy": "180_days",
        "risk_level": "medium",
        "description": "Resend email API key",
        "is_configured": bool(os.environ.get("RESEND_API_KEY")),
    },
    {
        "name": "SLACK_WEBHOOK_URL",
        "env_key": "SLACK_WEBHOOK_URL",
        "current_source": "env",
        "target_source": "vault",
        "vault_path": "secret/syroce/notifications/slack_webhook",
        "rotation_policy": "365_days",
        "risk_level": "low",
        "description": "Slack incoming webhook URL",
        "is_configured": bool(os.environ.get("SLACK_WEBHOOK_URL")),
    },
]


# Migration phases
MIGRATION_PHASES = [
    {
        "phase": 1,
        "name": "Vault/KMS Setup",
        "description": "Deploy HashiCorp Vault or configure AWS Secrets Manager",
        "tasks": [
            "Deploy Vault in HA mode (Raft storage backend)",
            "Configure auth methods (AppRole for services, OIDC for humans)",
            "Create secret engines and mount paths",
            "Set up audit logging backend",
        ],
        "estimated_days": 3,
        "status": "planned",
    },
    {
        "phase": 2,
        "name": "Secret Migration",
        "description": "Migrate secrets from .env to Vault/KMS",
        "tasks": [
            "Write all current secrets to Vault paths",
            "Update application to read from Vault with env fallback",
            "Test secret retrieval latency and caching",
            "Verify all services start correctly with Vault",
        ],
        "estimated_days": 2,
        "status": "planned",
    },
    {
        "phase": 3,
        "name": "Rotation Automation",
        "description": "Enable automatic secret rotation",
        "tasks": [
            "Configure Vault dynamic secrets for MongoDB",
            "Set up automatic JWT secret rotation (with grace period)",
            "Implement Stripe key rotation procedure",
            "Create rotation schedules for all secrets",
        ],
        "estimated_days": 3,
        "status": "planned",
    },
    {
        "phase": 4,
        "name": "Env Cleanup",
        "description": "Remove all secrets from .env files and CI/CD",
        "tasks": [
            "Remove secrets from .env files",
            "Update CI/CD pipelines to use Vault inject",
            "Audit git history for leaked secrets",
            "Enable pre-commit hooks for secret detection",
        ],
        "estimated_days": 1,
        "status": "planned",
    },
]


def get_secret_management_status() -> dict:
    """Get current secret management status."""
    total = len(SECRET_INVENTORY)
    configured = sum(1 for s in SECRET_INVENTORY if s["is_configured"])
    critical = [s for s in SECRET_INVENTORY if s["risk_level"] == "critical"]
    critical_configured = sum(1 for s in critical if s["is_configured"])

    env_based = sum(1 for s in SECRET_INVENTORY if s["current_source"] == "env")
    vault_migrated = sum(1 for s in SECRET_INVENTORY if s["current_source"] == "vault")

    return {
        "inventory": SECRET_INVENTORY,
        "summary": {
            "total_secrets": total,
            "configured": configured,
            "missing": total - configured,
            "critical_total": len(critical),
            "critical_configured": critical_configured,
            "env_based": env_based,
            "vault_migrated": vault_migrated,
            "migration_progress_pct": round((vault_migrated / max(total, 1)) * 100, 1),
        },
        "migration_phases": MIGRATION_PHASES,
        "overall_phase": "phase_0_env_only",
    }
