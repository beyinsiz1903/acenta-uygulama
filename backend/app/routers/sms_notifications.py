"""Compat shim — moved to app.modules.system.routers.sms_notifications"""
import importlib as _il, sys as _sys
_sys.modules[__name__] = _il.import_module("app.modules.system.routers.sms_notifications")
