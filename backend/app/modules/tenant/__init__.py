"""Tenant Isolation Module — enforces strict multi-tenant data boundaries.

This module provides:
- TenantScopedRepository: base class for all tenant-aware data access
- TenantContext: FastAPI dependency for extracting tenant info from request
- TenantGuard: enforcement layer that prevents unfiltered collection access
"""
