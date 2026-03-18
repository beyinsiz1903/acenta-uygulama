"""Tenant isolation errors — hard failures for security boundary violations."""
from __future__ import annotations


class TenantIsolationError(Exception):
    """Base error for tenant isolation violations."""
    pass


class TenantContextMissing(TenantIsolationError):
    """Raised when a tenant-scoped operation is attempted without tenant context."""
    pass


class TenantFilterBypassAttempt(TenantIsolationError):
    """Raised when a query attempts to access data outside its tenant boundary.

    This is a CRITICAL security event and should be logged + alerted.
    """
    pass


class CrossTenantAccessDenied(TenantIsolationError):
    """Raised when an explicit cross-tenant data access is detected and blocked."""
    pass
