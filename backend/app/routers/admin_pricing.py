"""Compat shim — moved to app.modules.pricing.routers.admin_pricing"""
import importlib as _il, sys as _sys
_sys.modules[__name__] = _il.import_module("app.modules.pricing.routers.admin_pricing")
