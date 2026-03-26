"""Compat shim — moved to app.modules.finance.routers.ops_finance_documents"""
import importlib as _il, sys as _sys
_sys.modules[__name__] = _il.import_module("app.modules.finance.routers.ops_finance_documents")
