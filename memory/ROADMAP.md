# ROADMAP — Acenta Master Travel SaaS

## Güncel Durum
- `/api/v1` standardizasyonu tamamlandı
- Web auth/session hardening tamamlandı
- Entitlement Projection Engine V1 tamamlandı ve test edildi
- Usage Metering için PR-UM1 foundation tamamlandı
- Usage Metering için PR-UM2 `reservation.created` instrumentation tamamlandı
- Usage Metering için PR-UM3 tamamlandı:
  - `report.generated`
  - `export.generated`
  - `integration.call` wiring
- Usage Visibility için PR-UM4 tamamlandı:
  - tenant usage read API
  - admin usage trend görünürlüğü
  - dashboard mini kart
  - detay usage sayfası
  - admin usage overview kartı
- Soft Quota Warning için PR-UM5 tamamlandı:
  - warning seviyeleri
  - dashboard + usage page CTA
  - trial recommendation

## P0 — Sıradaki Kritik İş

### Pricing Model
Hedef: hazır usage/veri akışını gelir modeline çevirmek.

Öncelikli teslimler:
- Türkiye pazarı için trial / starter / pro / enterprise sınırları
- rezervasyon hacmine göre en iyi fiyat-kota dengesi
- MRR odaklı plan kurgusu

Teslim beklentisi:
- fiyatlandırma tablosu
- quota → plan eşleşmesi
- satış / demo anlatısı ile hizalı paketleme

### Demo Sales Flow
- Demo tenant / pricing / upgrade akışının satış demosu için cilalanması
- özellikle trial → paid dönüşüm anlatısı

### Sonraki Stratejik İş — Pricing Model
- Trial / Starter / Pro / Enterprise kotalarının gelir optimizasyonu için ayrı çalışma
- PR-UM4 sonrası ele alınacak

## P1 — Sonraki İşler

### Admin “Create Demo Agency” Action
- Demo seed utility artık hazır olduğu için admin panelde tek tıkla tetiklenebilen küçük bir aksiyon PR’ı yapılabilir
- Teknik olmayan ekip üyelerinin demo tenant açmasını hızlandırır

### Migration Dashboard Card
- Admin dashboard içinde `domain_v1_progress` gösteren küçük kart
- Ayrı ve küçük PR olarak ele alınmalı

### Observability Stack
- request / error / job görünürlüğünü artırmak
- üretim öncesi operasyonel güveni yükseltmek

### Admin Endpoint Cleanup
- Defer edilmiş sorunlar:
  - `/api/partner-graph/notifications/summary`
  - `/api/tenant/features`
  - `/api/tenant/quota-status`

## P2 — Daha Sonra

### Mobile PR-5B
- Mobil repo bağlandığında secure session bootstrap
- mevcut durumda bloklu / ertelendi

### Daha İleri Monetizasyon
- hard quota enforcement
- billing alignment
- overage ve self-service plan geçişleri

## Bloklar
- PR-5B için mobil repository erişimi yok

## Son Tamamlanan İş
- **Soft Quota Warning PR-UM5**
  - warning_level + warning_message
  - dashboard + usage page pricing CTA
  - trial recommendation payload + UI
- **Usage Visibility PR-UM4**
  - tenant usage summary endpoint
  - admin usage trend görünürlüğü
  - dashboard mini usage kartı + `/app/usage`
  - admin tenant usage overview
- **Usage Metering PR-UM3**
  - gerçek report/export output instrumentation
  - Google Sheets integration.call metering wiring
  - correlation-id bazlı dedupe doğrulandı
- **Usage Metering PR-UM1 Foundation**
  - usage metric constants
  - usage_daily aggregate repository
  - canonical `track_usage_event(...)`
  - ledger + daily index zemini
- **Entitlement Projection Engine V1**
  - plan katalogu
  - tenant entitlement projection snapshot
  - admin entitlement görünürlüğü
  - public pricing entegrasyonu
