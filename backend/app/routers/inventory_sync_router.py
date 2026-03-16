"""DEPRECATED — Replaced by app.routers.inventory package.

This file is kept as a thin redirect for any external references.
All endpoints now live in:
  - inventory/sync_router.py
  - inventory/booking_router.py
  - inventory/diagnostics_router.py
"""
from app.routers.inventory.sync_router import router

__all__ = ["router"]
