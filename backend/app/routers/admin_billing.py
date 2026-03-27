"""Compat shim — moved to app.modules.finance.routers.admin_billing"""
import importlib as _il
import sys as _sys
_sys.modules[__name__] = _il.import_module("app.modules.finance.routers.admin_billing")
