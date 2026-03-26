"""Compat shim — moved to app.modules.finance.routers.multicurrency"""
import importlib as _il, sys as _sys
_sys.modules[__name__] = _il.import_module("app.modules.finance.routers.multicurrency")
