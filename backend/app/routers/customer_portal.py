"""Compat shim — direct import to avoid circular dependency via app.modules.public.__init__"""
import importlib as _il
import sys as _sys
_mod = _il.import_module("app.modules.operations.routers.customer_portal")
_sys.modules[__name__] = _mod
