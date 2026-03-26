"""Compat shim — moved to app.modules.auth.routers.auth_password_reset"""
import importlib as _il, sys as _sys
_sys.modules[__name__] = _il.import_module("app.modules.auth.routers.auth_password_reset")
