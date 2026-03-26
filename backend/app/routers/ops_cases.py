"""Compat shim — moved to app.modules.operations.routers.ops_cases"""
import importlib as _il, sys as _sys
_sys.modules[__name__] = _il.import_module("app.modules.operations.routers.ops_cases")
