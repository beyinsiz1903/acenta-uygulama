"""Compat shim — moved to app.modules.identity.routers.admin_api_keys"""
import importlib as _il
import sys as _sys
_sys.modules[__name__] = _il.import_module("app.modules.identity.routers.admin_api_keys")
