from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.bootstrap.runtime_init import ensure_jwt_secret, load_backend_env


def create_app() -> FastAPI:
    load_backend_env()
    ensure_jwt_secret()

    from app.bootstrap.middleware_setup import configure_middlewares
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
        yield
        shutdown_runtime_resources()
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

    return app


app = create_app()
