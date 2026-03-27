"""Compat shim — moved to app.modules.b2b.routers.partner_v1"""
import importlib as _il
import sys as _sys
_sys.modules[__name__] = _il.import_module("app.modules.b2b.routers.partner_v1")
