"""Compat shim — moved to app.modules.inventory.routers.agency_reservations"""
import importlib as _il, sys as _sys
_sys.modules[__name__] = _il.import_module("app.modules.inventory.routers.agency_reservations")
