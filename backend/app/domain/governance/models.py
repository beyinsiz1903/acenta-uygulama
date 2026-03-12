"""Enterprise Governance — Domain Models & Constants.

Covers RBAC roles, permissions, audit schema, compliance, data access policies,
security alerting, and secret management data structures.
"""
from __future__ import annotations

# ============================================================================
# PART 1 — RBAC ROLE HIERARCHY
# ============================================================================

ROLE_HIERARCHY: dict[str, int] = {
    "super_admin": 100,
    "ops_admin": 80,
    "finance_admin": 70,
    "agency_admin": 60,
    "agent": 40,
    "support": 20,
}

ROLE_DESCRIPTIONS: dict[str, str] = {
    "super_admin": "Full platform access. Can manage all tenants, users, roles, secrets, and system config.",
    "ops_admin": "Operations management. Supplier overrides, incident resolution, failover control.",
    "finance_admin": "Financial operations. Payment overrides, refund approvals, settlement management.",
    "agency_admin": "Agency-level admin. Manages agency users, bookings, and agency-level settings.",
    "agent": "Standard booking agent. Create/view bookings, manage customers.",
    "support": "Read-only support access. View bookings and customer data for troubleshooting.",
}

# Parent roles inherit all permissions of child roles
ROLE_INHERITS: dict[str, list[str]] = {
    "super_admin": ["ops_admin", "finance_admin", "agency_admin", "agent", "support"],
    "ops_admin": ["agent", "support"],
    "finance_admin": ["agent", "support"],
    "agency_admin": ["agent", "support"],
    "agent": ["support"],
    "support": [],
}

# ============================================================================
# PART 2 — FINE-GRAINED PERMISSIONS
# ============================================================================

# Resource.action format
GOVERNANCE_PERMISSIONS: dict[str, str] = {
    # Booking
    "booking.view": "View booking details",
    "booking.create": "Create new bookings",
    "booking.update": "Update booking details",
    "booking.cancel": "Cancel bookings",
    "booking.override": "Override booking state (force transitions)",
    "booking.amend": "Amend existing bookings",
    # Supplier
    "supplier.view": "View supplier data",
    "supplier.override": "Override supplier circuit breakers and health",
    "supplier.failover": "Trigger manual supplier failover",
    "supplier.debug": "Access supplier debug/inspection tools",
    # Pricing
    "pricing.view": "View pricing rules",
    "pricing.override": "Override pricing for bookings",
    "pricing.rules.manage": "Create/edit/delete pricing rules",
    # Finance
    "finance.view": "View financial data",
    "finance.payment.create": "Create payments",
    "finance.refund.approve": "Approve refund requests",
    "finance.settlement.manage": "Manage settlements",
    "finance.invoice.generate": "Generate invoices",
    # Incident
    "incident.view": "View incidents",
    "incident.create": "Create incidents",
    "incident.resolve": "Resolve incidents",
    "incident.assign": "Assign incidents to team members",
    # Alert
    "alert.view": "View alerts",
    "alert.acknowledge": "Acknowledge alerts",
    "alert.config": "Configure alert rules and channels",
    # Voucher
    "voucher.view": "View vouchers",
    "voucher.generate": "Generate voucher PDFs",
    "voucher.send": "Send vouchers to customers",
    # User Management
    "user.view": "View user accounts",
    "user.create": "Create user accounts",
    "user.update": "Update user accounts",
    "user.delete": "Delete/deactivate user accounts",
    "user.role.assign": "Assign roles to users",
    # Tenant/Agency
    "tenant.view": "View tenant settings",
    "tenant.settings.update": "Update tenant settings",
    "tenant.features.manage": "Enable/disable tenant features",
    # Governance
    "governance.rbac.manage": "Manage RBAC roles and permissions",
    "governance.audit.view": "View audit logs",
    "governance.secrets.manage": "Manage secrets vault",
    "governance.compliance.view": "View compliance logs",
    "governance.security.alerts": "View and manage security alerts",
    "governance.data_policy.manage": "Manage data access policies",
    # Reports
    "reports.view": "View reports",
    "reports.export": "Export reports",
    # CRM
    "crm.view": "View CRM data",
    "crm.manage": "Full CRM management",
}

# Default role → permission mapping
DEFAULT_ROLE_PERMISSIONS: dict[str, list[str]] = {
    "super_admin": ["*"],  # Wildcard: full access
    "ops_admin": [
        "booking.*", "supplier.*", "incident.*", "alert.*",
        "voucher.*", "user.view", "tenant.view",
        "governance.audit.view", "reports.*", "crm.view",
    ],
    "finance_admin": [
        "booking.view", "booking.cancel",
        "finance.*", "pricing.*",
        "reports.*", "governance.compliance.view",
        "user.view", "tenant.view", "crm.view",
    ],
    "agency_admin": [
        "booking.*", "finance.view", "finance.payment.create",
        "pricing.view", "incident.view", "incident.create",
        "alert.view", "voucher.*",
        "user.view", "user.create", "user.update", "user.role.assign",
        "tenant.view", "tenant.settings.update",
        "reports.*", "crm.*",
    ],
    "agent": [
        "booking.view", "booking.create", "booking.update", "booking.amend",
        "finance.view", "pricing.view",
        "incident.view", "alert.view",
        "voucher.view", "voucher.generate",
        "user.view", "reports.view", "crm.*",
    ],
    "support": [
        "booking.view", "finance.view", "pricing.view",
        "incident.view", "alert.view", "voucher.view",
        "user.view", "reports.view", "crm.view",
    ],
}

# ============================================================================
# PART 3 — AUDIT LOG EVENT TYPES
# ============================================================================

AUDIT_CATEGORIES = [
    "auth", "rbac", "booking", "finance", "supplier",
    "pricing", "incident", "alert", "voucher", "tenant",
    "user", "governance", "secret", "compliance", "data_access",
]

SENSITIVE_ACTIONS = [
    "booking.override", "supplier.override", "pricing.override",
    "finance.refund.approve", "finance.settlement.manage",
    "user.role.assign", "user.delete",
    "governance.rbac.manage", "governance.secrets.manage",
    "tenant.settings.update", "tenant.features.manage",
]

# ============================================================================
# PART 4 — SECRET TYPES
# ============================================================================

SECRET_TYPES = [
    "api_key", "oauth_token", "database_credential",
    "webhook_secret", "encryption_key", "certificate",
]

# ============================================================================
# PART 7 — DATA ACCESS POLICY TYPES
# ============================================================================

POLICY_EFFECT_ALLOW = "allow"
POLICY_EFFECT_DENY = "deny"

DATA_ACCESS_RESOURCES = [
    "bookings", "customers", "payments", "invoices",
    "settlements", "users", "agencies", "suppliers",
    "incidents", "alerts", "audit_logs", "secrets",
]

# ============================================================================
# PART 8 — SECURITY ALERT TYPES
# ============================================================================

SECURITY_ALERT_TYPES = [
    "suspicious_login",
    "privilege_escalation",
    "mass_data_access",
    "cross_tenant_attempt",
    "brute_force_attempt",
    "unauthorized_api_access",
    "secret_access_anomaly",
    "bulk_export_anomaly",
    "role_change_anomaly",
    "inactive_admin_login",
]

SECURITY_SEVERITY = ["critical", "high", "medium", "low", "info"]
