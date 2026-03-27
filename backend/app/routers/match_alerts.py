"""Compat shim — moved to app.modules.booking.routers.match_alerts"""
import importlib as _il
import sys as _sys
_sys.modules[__name__] = _il.import_module("app.modules.booking.routers.match_alerts")
