"""Compat shim — moved to app.modules.supplier.routers.admin_supplier_health"""
import importlib as _il
import sys as _sys
_sys.modules[__name__] = _il.import_module("app.modules.supplier.routers.admin_supplier_health")
