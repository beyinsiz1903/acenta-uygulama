"""Compat shim — moved to app.modules.inventory.routers.onboarding.

Kept so legacy absolute imports continue to resolve. Do not add new
code here; edit the canonical module instead. See app/modules/MIGRATION.md.
"""
import importlib as _il
import sys as _sys
_sys.modules[__name__] = _il.import_module("app.modules.inventory.routers.onboarding")
