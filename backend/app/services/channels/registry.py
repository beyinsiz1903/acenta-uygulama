from __future__ import annotations

from typing import Dict

from app.services.channels.providers.base import BaseChannelProvider
from app.services.channels.providers.exely import ExelyChannelProvider
from app.services.channels.providers.mock_ari import MockAriChannelProvider
from app.services.channels.types import ChannelTestResult


class NotImplementedChannelProvider(BaseChannelProvider):
  """Fallback provider used when a connector.provider has no adapter yet."""

  provider_name = "generic_not_implemented"

  async def test_connection(self, *, connector: Dict[str, any]) -> ChannelTestResult:  # type: ignore[name-defined]
    provider = connector.get("provider") or "unknown"
    return ChannelTestResult(
      ok=False,
      code="NOT_IMPLEMENTED",
      message=f"Provider '{provider}' için adapter henüz uygulanmadı.",
      meta={"provider": provider},
    )

  async def fetch_ari(self, *, connector: Dict[str, any], from_date, to_date):  # type: ignore[name-defined]
    from app.services.channels.types import ChannelAriResult
    provider = connector.get("provider") or "unknown"
    return ChannelAriResult(
      ok=False,
      code="NOT_IMPLEMENTED",
      message=f"Provider '{provider}' için ARI adapter henüz uygulanmadı.",
      meta={"provider": provider},
    )


# Simple in-memory registry.  If we later need per-request state or config, we
# can extend this to a factory.
_PROVIDER_REGISTRY: Dict[str, BaseChannelProvider] = {
  "exely": ExelyChannelProvider(),
  "mock_ari": MockAriChannelProvider(),
}


def get_provider_adapter(provider: str) -> BaseChannelProvider:
  """Resolve provider name to an adapter instance.

  Unknown providers fall back to a NotImplementedChannelProvider, so routers
  can still record runs with a clear NOT_IMPLEMENTED code instead of 500.
  """

  normalized = (provider or "").lower()
  return _PROVIDER_REGISTRY.get(normalized, NotImplementedChannelProvider())
