"""Compat shim — moved to app.modules.b2b.routers.admin_partners"""
import importlib as _il, sys as _sys
_sys.modules[__name__] = _il.import_module("app.modules.b2b.routers.admin_partners")
