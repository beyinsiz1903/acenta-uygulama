"""Paximum (San TSG) hotel marketplace integration.

Owner: Inventory Domain.
Stage base URL: http://api.stage.paximum.com
Auth: Bearer token in Authorization header (configured via PAXIMUM_BEARER_TOKEN).
"""
from app.services.paximum.client import PaximumClient
from app.services.paximum.errors import PaximumError

__all__ = ["PaximumClient", "PaximumError"]
