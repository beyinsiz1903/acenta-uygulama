"""Compat shim — moved to app.modules.system.routers.health"""
import importlib as _il
import sys as _sys
_sys.modules[__name__] = _il.import_module("app.modules.system.routers.health")
