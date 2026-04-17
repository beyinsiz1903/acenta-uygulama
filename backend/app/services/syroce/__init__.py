"""Syroce PMS Marketplace integration package.

Two clients:
  - admin: uses platform-wide X-Marketplace-Admin-Token (creating agencies, key rotation).
  - agent: per-organization client using each org's encrypted marketplace API key.
"""
from app.services.syroce.errors import SyroceError  # noqa: F401
