from __future__ import annotations

from dataclasses import dataclass, field

from fastapi import APIRouter, FastAPI
from fastapi.routing import APIRoute

from app.bootstrap.v1_manifest import derive_target_path
from app.routers.auth import router as auth_router
from app.routers.health import router as health_router
from app.routers.health_dashboard import router as health_dashboard_router
from app.routers.public_campaigns import router as public_campaigns_router
from app.routers.public_cms_pages import router as public_cms_pages_router
from app.routers.theme import router as theme_router


@dataclass(frozen=True)
class V1AliasRollout:
    name: str
    router: APIRouter
    include_paths: tuple[str, ...] = field(default_factory=tuple)


LOW_RISK_V1_ROLLOUTS: tuple[V1AliasRollout, ...] = (
    V1AliasRollout("health", health_router),
    V1AliasRollout("health_dashboard", health_dashboard_router),
    V1AliasRollout("theme", theme_router),
    V1AliasRollout("public_cms_pages", public_cms_pages_router),
    V1AliasRollout("public_campaigns", public_campaigns_router),
)

AUTH_PR_V1_2A_ROLLOUTS: tuple[V1AliasRollout, ...] = (
    V1AliasRollout(
        "auth_pr_v1_2a",
        auth_router,
        include_paths=(
            "/api/auth/login",
            "/api/auth/me",
            "/api/auth/refresh",
        ),
    ),
)


def _iter_route_methods(route: APIRoute) -> list[str]:
    return sorted(method for method in (route.methods or set()) if method not in {"HEAD", "OPTIONS"})


def _route_is_selected(rollout: V1AliasRollout, route: APIRoute) -> bool:
    if rollout.include_paths and route.path not in rollout.include_paths:
        return False
    return True


def _copy_route(alias_router: APIRouter, route: APIRoute, target_path: str) -> None:
    alias_router.add_api_route(
        target_path,
        route.endpoint,
        response_model=route.response_model,
        status_code=route.status_code,
        tags=route.tags,
        dependencies=route.dependencies,
        summary=route.summary,
        description=route.description,
        response_description=route.response_description,
        responses=route.responses,
        deprecated=route.deprecated,
        methods=_iter_route_methods(route),
        operation_id=None,
        response_model_include=route.response_model_include,
        response_model_exclude=route.response_model_exclude,
        response_model_by_alias=route.response_model_by_alias,
        response_model_exclude_unset=route.response_model_exclude_unset,
        response_model_exclude_defaults=route.response_model_exclude_defaults,
        response_model_exclude_none=route.response_model_exclude_none,
        include_in_schema=route.include_in_schema,
        response_class=route.response_class,
        name=f"{route.name}_v1" if route.name else None,
        callbacks=route.callbacks,
        openapi_extra=route.openapi_extra,
    )


def register_low_risk_v1_aliases(app: FastAPI) -> None:
    existing_routes = {
        (method, route.path)
        for route in app.routes
        if isinstance(route, APIRoute)
        for method in _iter_route_methods(route)
    }

    for rollout in LOW_RISK_V1_ROLLOUTS + AUTH_PR_V1_2A_ROLLOUTS:
        alias_router = APIRouter()

        for route in rollout.router.routes:
            if not isinstance(route, APIRoute):
                continue
            if not _route_is_selected(rollout, route):
                continue

            source_module = getattr(route.endpoint, "__module__", "unknown")
            target_path = derive_target_path(route.path, source_module)
            route_methods = _iter_route_methods(route)

            if target_path == route.path or not target_path.startswith("/api/v1/") or not route_methods:
                continue

            if all((method, target_path) in existing_routes for method in route_methods):
                continue

            _copy_route(alias_router, route, target_path)
            for method in route_methods:
                existing_routes.add((method, target_path))

        if alias_router.routes:
            app.include_router(alias_router)