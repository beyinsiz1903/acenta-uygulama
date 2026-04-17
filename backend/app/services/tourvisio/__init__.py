"""TourVisio (San TSG) multi-product integration.

Owner: Inventory Domain.
Auth: per-tenant Login (Agency/User/Password) -> bearer token (cached until
expiresOn, partitioned by tenant credentials). Each Syroce agency stores its
own TourVisio credentials in the encrypted `supplier_credentials` collection
(see `app.domain.suppliers.supplier_credentials_service`). Routers load
credentials based on the calling user's organization.

All responses share an envelope: {header: {requestId, success, messages}, body: ...}
"""
from app.services.tourvisio.client import TourVisioClient
from app.services.tourvisio.errors import TourVisioError

__all__ = ["TourVisioClient", "TourVisioError"]
