"""Compat shim — moved to app.modules.pricing.routers.offers_booking"""
import importlib as _il
import sys as _sys
_sys.modules[__name__] = _il.import_module("app.modules.pricing.routers.offers_booking")
