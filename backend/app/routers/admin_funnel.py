"""Compat shim — moved to app.modules.reporting.routers.admin_funnel"""
import importlib as _il
import sys as _sys
_sys.modules[__name__] = _il.import_module("app.modules.reporting.routers.admin_funnel")
