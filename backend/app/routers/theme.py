"""Compat shim — moved to app.modules.system.routers.theme"""
import importlib as _il, sys as _sys
_sys.modules[__name__] = _il.import_module("app.modules.system.routers.theme")
