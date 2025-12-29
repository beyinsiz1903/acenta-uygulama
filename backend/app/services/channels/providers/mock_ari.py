from __future__ import annotations

from datetime import date
from typing import Any, Dict

from app.services.channels.providers.base import BaseChannelProvider
from app.services.channels.types import ChannelAriResult, ChannelTestResult


class MockAriChannelProvider(BaseChannelProvider):
  """Mock provider that always returns a deterministic ARI payload.

  Amaç: Phase-2.7.1 diff ve apply motorunu gerçekte başarılı bir ARI
  senaryosuyla test edebilmek. Gerçek Exely / Expedia entegrasyonu gelmeden
  önce bu provider üzerinden:

    - fetch_ari -> ok=True + sabit payload
    - normalize_exely_ari -> canonical ARI üretir
    - apply_ari_to_pms -> zengin diff + summary döndürür
  """

  provider_name = "mock_ari"

  async def test_connection(self, *, connector: Dict[str, Any]) -> ChannelTestResult:  # type: ignore[override]
    # Her zaman OK dönüyoruz; amaç bağlantı değil ARI motorunu test etmek.
    return ChannelTestResult(
      ok=True,
      code="OK",
      message="Mock ARI provider bağlantısı her zaman başarılı.",
      meta={"provider": self.provider_name},
    )

  async def fetch_ari(
    self,
    *,
    connector: Dict[str, Any],
    from_date: date,
    to_date: date,
  ) -> ChannelAriResult:  # type: ignore[override]
    """Return a static but realistic ARI payload.

    Normalizer t|fık olduğu key'leri bekliyor; bu yüzden field isimlerini
    normalize_exely_ari'nin taradığı şemaya uygun tutuyoruz:

      - availability: room_type_id / channel_room_type_id, date, available, stop_sell
      - rates: rate_plan_id / channel_rate_plan_id, date, price, currency, min_stay

    Channel mapping UI'de:
      - channel_room_type_id = "ch_rt_1" -> pms_room_type_id
      - channel_rate_plan_id = "ch_rp_1" -> pms_rate_plan_id
    eşleştirmeleri yapıldığında canonical ARI bu PMS id'lerine çözülecek.
    """

    # from/to param'larını debug için meta'da taşıyoruz; payload'ta sabit
    # 2 günlük bir örnek veri dönmek yeterli.
    availability = [
      {
        "room_type_id": "ch_rt_1",
        "date": from_date.isoformat(),
        "available": 2,
        "stop_sell": False,
      },
      {
        "room_type_id": "ch_rt_1",
        "date": to_date.isoformat(),
        "available": 1,
        "stop_sell": False,
      },
    ]

    rates = [
      {
        "rate_plan_id": "ch_rp_1",
        "date": from_date.isoformat(),
        "price": 3500,
        "currency": "TRY",
        "min_stay": 2,
      },
      {
        "rate_plan_id": "ch_rp_1",
        "date": to_date.isoformat(),
        "price": 3700,
        "currency": "TRY",
        "min_stay": 2,
      },
    ]

    data: Dict[str, Any] = {
      "availability": availability,
      "rates": rates,
    }

    return ChannelAriResult(
      ok=True,
      code="OK",
      message="Mock ARI payload üretildi.",
      data=data,
      meta={
        "provider": self.provider_name,
        "from_date": from_date.isoformat(),
        "to_date": to_date.isoformat(),
      },
    )
