"""Compat shim — moved to app.modules.system.routers.admin_system_integrity"""
import importlib as _il, sys as _sys
_sys.modules[__name__] = _il.import_module("app.modules.system.routers.admin_system_integrity")
