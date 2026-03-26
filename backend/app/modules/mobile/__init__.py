"""Mobile domain — BFF (Backend for Frontend) for mobile clients.

Owner: Mobile Domain
Boundary: Mobile-specific API endpoints, response shaping, and offline sync.
"""
from __future__ import annotations

from app.modules.mobile.router import router

__all__ = ["router"]
