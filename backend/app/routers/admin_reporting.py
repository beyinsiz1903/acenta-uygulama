"""Compat shim — moved to app.modules.reporting.routers.admin_reporting"""
import importlib as _il, sys as _sys
_sys.modules[__name__] = _il.import_module("app.modules.reporting.routers.admin_reporting")
