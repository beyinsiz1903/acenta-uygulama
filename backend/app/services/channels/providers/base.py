from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict

from app.services.channels.types import ChannelAriResult, ChannelTestResult


class BaseChannelProvider(ABC):
  """Base interface for channel providers (Exely, Expedia, etc).

  Each provider implementation should encapsulate provider-specific
  authentication, ping / test calls and later ARI / reservation semantics.
  """

  provider_name: str = "base"

  @abstractmethod
  async def test_connection(self, *, connector: Dict[str, Any]) -> ChannelTestResult:
    """Validate connectivity/credentials for this connector.

    Implementations should *not* raise HTTPException.  They should return a
    ChannelTestResult with:
      - ok=True on success (code="OK")
      - ok=False with a stable code (e.g. AUTH_FAILED, NOT_IMPLEMENTED,
        PROVIDER_UNAVAILABLE, UNKNOWN_ERROR)
    """

    raise NotImplementedError

  @abstractmethod
  async def fetch_ari(self, *, connector: Dict[str, Any], from_date, to_date) -> ChannelAriResult:
    """Read ARI (availability/rates/inventory) from the provider.

    For this phase it is a read-only operation; implementations should not
    mutate any database state.  They should return provider-specific JSON in
    `data` and avoid raising HTTPException directly.
    """

    raise NotImplementedError

