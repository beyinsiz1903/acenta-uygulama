"""Compat shim — moved to app.modules.booking.routers.booking_outcomes"""
import importlib as _il, sys as _sys
_sys.modules[__name__] = _il.import_module("app.modules.booking.routers.booking_outcomes")
