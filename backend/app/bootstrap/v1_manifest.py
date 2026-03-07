from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RouteNamespaceMeta:
    current_namespace: str
    target_namespace: str
    owner: str
    risk_level: str


@dataclass(frozen=True)
class NamespaceRule:
    path_prefixes: tuple[str, ...]
    source_prefixes: tuple[str, ...]
    target_namespace: str
    owner: str
    risk_level: str


V1_NAMESPACE_RULES: tuple[NamespaceRule, ...] = (
    NamespaceRule(("/api/v1/mobile",), ("app.modules.mobile",), "/api/v1/mobile", "mobile", "medium"),
    NamespaceRule(("/api/auth",), ("app.routers.auth", "app.routers.auth_password_reset", "app.routers.enterprise_2fa"), "/api/v1/auth", "auth", "high"),
    NamespaceRule(("/api/admin",), ("app.routers.admin",), "/api/v1/admin", "admin", "medium"),
    NamespaceRule(("/api/agency",), ("app.routers.agency",), "/api/v1/agency", "agency", "medium"),
    NamespaceRule(("/api/b2b",), ("app.routers.b2b",), "/api/v1/b2b", "b2b", "medium"),
    NamespaceRule(("/api/crm",), ("app.routers.crm",), "/api/v1/crm", "crm", "medium"),
    NamespaceRule(("/api/ops", "/api/ops-cases"), ("app.routers.ops",), "/api/v1/ops", "ops", "medium"),
    NamespaceRule(("/api/public",), ("app.routers.public_",), "/api/v1/public", "public", "high"),
    NamespaceRule(("/storefront",), ("app.routers.storefront",), "/api/v1/storefront", "public", "medium"),
    NamespaceRule(("/web",), ("app.routers.web_",), "/api/v1/public", "public", "high"),
    NamespaceRule(("/api/partner",), ("app.routers.partner_",), "/api/v1/partner", "partner", "high"),
    NamespaceRule(("/api/webhook",), ("app.routers.billing_webhooks",), "/api/v1/webhooks", "integrations", "high"),
    NamespaceRule(("/api/settings",), ("app.routers.settings",), "/api/v1/settings", "settings", "medium"),
    NamespaceRule(("/api/health",), ("app.routers.health", "app.routers.enterprise_health"), "/api/v1/health", "system", "low"),
    NamespaceRule(("/api/system",), ("app.routers.health_dashboard", "app.routers.system_product_mode"), "/api/v1/system", "system", "low"),
)


def _starts_with_prefix(path: str, prefix: str) -> bool:
    return path == prefix or path.startswith(f"{prefix}/")


def derive_current_namespace(path: str) -> str:
    known_prefixes = (
        "/api/v1/mobile",
        "/api/admin/system",
        "/api/admin",
        "/api/auth",
        "/api/agency",
        "/api/b2b",
        "/api/crm",
        "/api/ops-cases",
        "/api/ops",
        "/api/public",
        "/api/partner-graph",
        "/api/partner",
        "/api/webhook",
        "/api/settings",
        "/api/health",
        "/api/system",
        "/api/dashboard",
        "/api/reports",
        "/api/tenant",
        "/api/notifications",
        "/api/inventory",
        "/api/products",
        "/api/pricing",
        "/api/payments",
        "/api/reservations",
        "/api/bookings",
        "/api/marketplace",
        "/api/finance",
        "/api/tickets",
        "/api/webpos",
        "/api/onboarding",
        "/api/gdpr",
        "/storefront",
        "/web",
    )
    for prefix in known_prefixes:
        if _starts_with_prefix(path, prefix):
            return prefix

    parts = [segment for segment in path.split("/") if segment]
    if not parts:
        return "/"
    if parts[0] == "api":
        if len(parts) == 1:
            return "/api"
        return f"/api/{parts[1]}"
    if len(parts) == 1:
        return f"/{parts[0]}"
    return f"/{parts[0]}/{parts[1]}"


def _default_target_namespace(current_namespace: str) -> str:
    if current_namespace.startswith("/api/v1/"):
        return current_namespace
    if current_namespace.startswith("/api/"):
        return f"/api/v1{current_namespace.removeprefix('/api')}"
    if current_namespace == "/api":
        return "/api/v1"
    if current_namespace in {"/web", "/storefront"}:
        return "/api/v1/public"
    return "/api/v1"


def classify_route(path: str, source_module: str) -> RouteNamespaceMeta:
    current_namespace = derive_current_namespace(path)

    for rule in V1_NAMESPACE_RULES:
        if any(_starts_with_prefix(path, prefix) for prefix in rule.path_prefixes):
            return RouteNamespaceMeta(
                current_namespace=current_namespace,
                target_namespace=rule.target_namespace,
                owner=rule.owner,
                risk_level=rule.risk_level,
            )
        if any(source_module.startswith(prefix) for prefix in rule.source_prefixes):
            return RouteNamespaceMeta(
                current_namespace=current_namespace,
                target_namespace=rule.target_namespace,
                owner=rule.owner,
                risk_level=rule.risk_level,
            )

    target_namespace = _default_target_namespace(current_namespace)
    risk_level = "medium"
    if current_namespace in {"/api", "/api/health", "/api/system"}:
        risk_level = "low"
    if any(token in path for token in ("/payments", "/billing", "/partner", "/public", "/webhook")):
        risk_level = "high"

    owner = current_namespace.removeprefix("/api/").split("/", 1)[0] or "core"
    if current_namespace.startswith("/api/admin"):
        owner = "admin"
    elif current_namespace in {"/web", "/storefront"}:
        owner = "public"
    elif current_namespace == "/api":
        owner = "system"

    return RouteNamespaceMeta(
        current_namespace=current_namespace,
        target_namespace=target_namespace,
        owner=owner,
        risk_level=risk_level,
    )