# ROADMAP — Acenta Master Travel SaaS

## Güncel Durum
- `/api/v1` standardizasyonu tamamlandı
- Web auth/session hardening tamamlandı
- Entitlement Projection Engine V1 tamamlandı ve test edildi
- Usage Metering için PR-UM1 foundation tamamlandı
- Usage Metering için PR-UM2 `reservation.created` instrumentation tamamlandı

## P0 — Sıradaki Kritik İş

### Usage Metering — PR-UM3 / PR-UM4 / PR-UM5
Hedef: foundation + reservation metriğinden sonra kalan monetization akışlarını tamamlamak.

Öncelikli ölçümler:
- rapor üretimi
- export sayısı
- entegrasyon çağrıları

Teslim beklentisi:
- `report.generated`, `export.generated`, `integration.call` instrumentation
- usage görünürlüğü (admin + tenant)
- soft quota enforcement ve upgrade recommendation

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
- quota enforcement
- billing alignment
- overage ve self-service plan geçişleri

## Bloklar
- PR-5B için mobil repository erişimi yok

## Son Tamamlanan İş
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
