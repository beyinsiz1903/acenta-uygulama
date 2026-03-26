"""Compat shim — moved to app.modules.supplier.routers.suppliers"""
import importlib as _il, sys as _sys
_sys.modules[__name__] = _il.import_module("app.modules.supplier.routers.suppliers")
