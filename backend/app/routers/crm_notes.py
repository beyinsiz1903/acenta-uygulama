"""Compat shim — moved to app.modules.crm.routers.crm_notes"""
import importlib as _il, sys as _sys
_sys.modules[__name__] = _il.import_module("app.modules.crm.routers.crm_notes")
