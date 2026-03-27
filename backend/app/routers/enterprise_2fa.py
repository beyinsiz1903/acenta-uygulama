"""Compat shim — moved to app.modules.auth.routers.enterprise_2fa"""
import importlib as _il
import sys as _sys
_sys.modules[__name__] = _il.import_module("app.modules.auth.routers.enterprise_2fa")
