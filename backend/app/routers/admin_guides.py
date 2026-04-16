"""Compat shim — moved to app.modules.operations.routers.admin_guides"""
import importlib as _il
import sys as _sys
_sys.modules[__name__] = _il.import_module("app.modules.operations.routers.admin_guides")
