"""Compat shim — moved to app.modules.reporting.routers.dashboard_enhanced"""
import importlib as _il, sys as _sys
_sys.modules[__name__] = _il.import_module("app.modules.reporting.routers.dashboard_enhanced")
