"""Compat shim — moved to app.modules.pricing.routers.admin_pricing_incidents"""
import importlib as _il
import sys as _sys
_sys.modules[__name__] = _il.import_module("app.modules.pricing.routers.admin_pricing_incidents")
