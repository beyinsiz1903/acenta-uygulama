"""Compat shim — moved to app.modules.identity.routers.agency_profile"""
import importlib as _il, sys as _sys
_sys.modules[__name__] = _il.import_module("app.modules.identity.routers.agency_profile")
