"""Compat shim — moved to app.modules.public.routers.public_checkout"""
import importlib as _il, sys as _sys
_sys.modules[__name__] = _il.import_module("app.modules.public.routers.public_checkout")
