from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.bootstrap.runtime_init import ensure_jwt_secret, load_backend_env


def create_app() -> FastAPI:
    load_backend_env()
    ensure_jwt_secret()

    from app.bootstrap.middleware_setup import configure_middlewares
    from app.bootstrap.route_inventory import export_route_inventory_snapshot
    from app.bootstrap.router_registry import register_routers
    from app.bootstrap.runtime_init import (
        ensure_api_runtime_indexes,
        ensure_service_runtime_indexes,
        init_observability,
        load_sheets_config_from_db,
        shutdown_runtime_resources,
    )
    from app.config import API_PREFIX, APP_NAME, APP_VERSION
    from app.db import close_mongo, connect_mongo, get_db

    @asynccontextmanager
    async def api_lifespan(_: FastAPI):
        init_observability()
        await connect_mongo()
        db = await get_db()
        await ensure_api_runtime_indexes(db)
        await ensure_service_runtime_indexes()
        await load_sheets_config_from_db(db)

        # Apply MongoDB schema validation (warn mode in dev, error in prod)
        try:
            from app.indexes.schema_validation import apply_schema_validation
            import os
            strict = os.environ.get("ENV", "dev").lower() in ("production", "prod")
            await apply_schema_validation(db, strict=strict)
        except Exception as exc:
            import logging
            logging.getLogger("startup").warning("Schema validation setup: %s", exc)

        # Apply scalability indexes
        try:
            from app.indexes.scalability_indexes import ensure_scalability_indexes
            await ensure_scalability_indexes(db)
        except Exception as exc:
            import logging
            logging.getLogger("startup").warning("Scalability indexes setup: %s", exc)

        # Initialize observability
        try:
            from app.infrastructure.observability import init_opentelemetry
            init_opentelemetry("syroce-api")
        except Exception as exc:
            import logging
            logging.getLogger("startup").warning("OpenTelemetry init: %s", exc)

        # Initialize supplier ecosystem
        try:
            from app.suppliers.registry import register_default_adapters
            register_default_adapters()
        except Exception as exc:
            import logging
            logging.getLogger("startup").warning("Supplier registry init: %s", exc)

        try:
            from app.suppliers.indexes import ensure_supplier_ecosystem_indexes
            await ensure_supplier_ecosystem_indexes(db)
        except Exception as exc:
            import logging
            logging.getLogger("startup").warning("Supplier ecosystem indexes: %s", exc)

        try:
            from app.suppliers.events import register_supplier_event_handlers
            register_supplier_event_handlers()
        except Exception as exc:
            import logging
            logging.getLogger("startup").warning("Supplier event handlers: %s", exc)

        # Initialize Operations Layer indexes
        try:
            from app.suppliers.operations.indexes import ensure_operations_indexes
            await ensure_operations_indexes(db)
        except Exception as exc:
            import logging
            logging.getLogger("startup").warning("Operations indexes: %s", exc)

        # Initialize Governance Layer indexes
        try:
            from app.domain.governance.indexes import ensure_governance_indexes
            await ensure_governance_indexes(db)
        except Exception as exc:
            import logging
            logging.getLogger("startup").warning("Governance indexes: %s", exc)

        # Initialize Integration Reliability indexes
        try:
            from app.domain.reliability.indexes import ensure_reliability_indexes
            await ensure_reliability_indexes(db)
        except Exception as exc:
            import logging
            logging.getLogger("startup").warning("Reliability indexes: %s", exc)

        # Initialize Inventory Sync indexes
        try:
            from app.services.inventory_sync_service import ensure_inventory_indexes
            await ensure_inventory_indexes()
        except Exception as exc:
            import logging
            logging.getLogger("startup").warning("Inventory indexes setup: %s", exc)

        # Initialize Supplier Config indexes
        try:
            from app.services.supplier_config_service import ensure_supplier_config_indexes
            await ensure_supplier_config_indexes()
        except Exception as exc:
            import logging
            logging.getLogger("startup").warning("Supplier config indexes: %s", exc)

        # Start Job Scheduler
        try:
            from app.services.job_scheduler_service import start_scheduler
            start_scheduler()
        except Exception as exc:
            import logging
            logging.getLogger("startup").warning("Job scheduler start: %s", exc)

        yield
        shutdown_runtime_resources()
        # Shutdown Redis
        try:
            from app.infrastructure.redis_client import shutdown_redis
            await shutdown_redis()
        except Exception:
            pass
        await close_mongo()

    app = FastAPI(
        title=APP_NAME,
        version=APP_VERSION,
        lifespan=api_lifespan,
        openapi_url=f"{API_PREFIX}/openapi.json",
    )

    configure_middlewares(app)
    register_routers(app)

    @app.get("/")
    async def read_root() -> dict[str, str]:
        return {"message": f"{APP_NAME} is running", "version": APP_VERSION}

    @app.get("/health")
    async def health_check() -> dict[str, str]:
        return {"status": "ok"}

    export_route_inventory_snapshot(app)

    return app


app = create_app()
