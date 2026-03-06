from __future__ import annotations

import logging
from pathlib import Path

from dotenv import load_dotenv

logger = logging.getLogger(__name__)


def load_backend_env() -> None:
    load_dotenv(Path(__file__).resolve().parents[2] / ".env")


def ensure_jwt_secret() -> None:
    from app.security.jwt_config import require_jwt_secret

    require_jwt_secret()


def init_observability() -> None:
    from app.middleware.error_tracking_middleware import init_sentry

    init_sentry()


async def ensure_api_runtime_indexes(db) -> None:
    from app.indexes import crm_indexes, finance_indexes, funnel_indexes, inbox_indexes, pricing_indexes, public_indexes, voucher_indexes
    from app.indexes.api_keys_indexes import ensure_api_keys_indexes
    from app.indexes.integration_hub_indexes import ensure_integration_hub_indexes
    from app.indexes.jobs_indexes import ensure_jobs_indexes
    from app.indexes.marketplace_indexes import ensure_marketplace_indexes, ensure_offers_indexes
    from app.indexes.pricing_indexes import ensure_pricing_indexes
    from app.indexes.rate_limit_indexes import ensure_rate_limit_indexes
    from app.indexes.seed_indexes import ensure_seed_indexes
    from app.indexes.storefront_indexes import ensure_storefront_indexes
    from app.indexes.tenant_indexes import ensure_tenant_indexes

    try:
        await finance_indexes.ensure_finance_indexes(db)
        await inbox_indexes.ensure_inbox_indexes(db)
        await pricing_indexes.ensure_pricing_indexes(db)
        await voucher_indexes.ensure_voucher_indexes(db)
        await public_indexes.ensure_public_indexes(db)
        await crm_indexes.ensure_crm_indexes(db)
        await funnel_indexes.ensure_funnel_indexes(db)
        await ensure_jobs_indexes(db)
        await ensure_integration_hub_indexes(db)
        await ensure_api_keys_indexes(db)
        await ensure_rate_limit_indexes(db)
        await ensure_tenant_indexes(db)
        await ensure_storefront_indexes(db)
        await ensure_pricing_indexes(db)
        await ensure_marketplace_indexes(db)
        await ensure_offers_indexes(db)
        await ensure_seed_indexes(db)
    except Exception as exc:
        logger.warning("Index creation failed (non-fatal, may lack permissions): %s", str(exc)[:200])


async def ensure_service_runtime_indexes() -> None:
    try:
        from app.services.agency_contracts_service import ensure_agency_contract_indexes
        from app.services.distributed_lock_service import ensure_lock_indexes
        from app.services.gdpr_service import ensure_gdpr_indexes
        from app.services.inventory_snapshot_service import ensure_inventory_snapshot_indexes
        from app.services.mongo_cache_service import ensure_cache_indexes
        from app.services.refresh_token_service import ensure_refresh_token_indexes
        from app.services.session_service import ensure_session_indexes
        from app.services.token_blacklist import ensure_blacklist_indexes

        await ensure_blacklist_indexes()
        await ensure_refresh_token_indexes()
        await ensure_session_indexes()
        await ensure_gdpr_indexes()
        await ensure_agency_contract_indexes()
        await ensure_cache_indexes()
        await ensure_inventory_snapshot_indexes()
        await ensure_lock_indexes()
    except Exception as exc:
        logger.warning("Service index creation failed (non-fatal): %s", str(exc)[:200])


async def load_sheets_config_from_db(db) -> None:
    try:
        from app.services.sheets_provider import set_db_config

        config_doc = await db.platform_config.find_one({"config_key": "google_service_account"})
        if config_doc and config_doc.get("config_value"):
            set_db_config(config_doc["config_value"])
            logging.getLogger("sheets_provider").info(
                "Loaded Google Service Account from DB: %s",
                config_doc.get("client_email", "?"),
            )
    except Exception as exc:
        logging.getLogger("sheets_provider").warning("Failed to load sheets config from DB: %s", exc)


async def run_worker_boot_tasks() -> None:
    try:
        from app.seed import ensure_seed_data

        await ensure_seed_data()
    except Exception as exc:
        logger.warning("Seed data failed (non-fatal): %s", str(exc)[:200])

    try:
        from app.services.cache_warmup import run_cache_warmup

        warmup_result = await run_cache_warmup()
        logging.getLogger("cache_warmup").info("Warm-up result: %s", warmup_result.get("status", "unknown"))
    except Exception as exc:
        logging.getLogger("cache_warmup").warning("Warm-up failed (non-critical): %s", exc)


def shutdown_runtime_resources() -> None:
    try:
        from app.services.redis_cache import shutdown_pool

        shutdown_pool()
    except Exception:
        pass
