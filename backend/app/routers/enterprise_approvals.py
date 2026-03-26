"""Compat shim — moved to app.modules.enterprise.routers.enterprise_approvals"""
import importlib as _il, sys as _sys
_sys.modules[__name__] = _il.import_module("app.modules.enterprise.routers.enterprise_approvals")
