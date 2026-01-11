from __future__ import annotations

"""Self-service /my-booking public access helpers (FAZ 3).

Implements the booking_public_tokens model and helper functions for:
- creating access tokens based on PNR + last_name/email
- resolving tokens to booking snapshots with scope checks
- recording guest-initiated cancel/amend requests
"""

from dataclasses import dataclass
from datetime import timedelta
from typing import Any, Iterable, List

from bson import ObjectId

from app.errors import AppError
from app.utils import now_utc


PUBLIC_TOKEN_TTL_MINUTES = 30


@dataclass
class PublicToken:
  
