"""TourVisio (San TSG) multi-product integration.

Owner: Inventory Domain.
Auth: Login (Agency/User/Password) -> bearer token (cached until expiresOn).
All endpoints share an envelope: {header: {requestId, success, messages}, body: ...}

Configured via env vars:
  TOURVISIO_BASE_URL  - e.g. http://service.stage.paximum.com (no trailing slash)
  TOURVISIO_AGENCY    - agency code
  TOURVISIO_USER      - user name
  TOURVISIO_PASSWORD  - user password
"""
from app.services.tourvisio.client import TourVisioClient
from app.services.tourvisio.errors import TourVisioError

__all__ = ["TourVisioClient", "TourVisioError"]
