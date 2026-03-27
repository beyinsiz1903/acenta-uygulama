"""Compat shim — moved to app.modules.public.routers.web_catalog"""
import importlib as _il
import sys as _sys
_sys.modules[__name__] = _il.import_module("app.modules.public.routers.web_catalog")
