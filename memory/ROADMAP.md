# ROADMAP — Acenta Master Travel SaaS

## Güncel Durum
- `/api/v1` standardizasyonu tamamlandı
- Web auth/session hardening tamamlandı
- Entitlement Projection Engine V1 tamamlandı ve test edildi
- Usage Metering için PR-UM1 foundation tamamlandı

## P0 — Sıradaki Kritik İş

### Usage Metering — PR-UM2 Reservation Instrumentation
Hedef: foundation hazır olduğu için ilk gerçek gelir metriği olan `reservation.created` akışını instrument etmek.

Öncelikli ölçümler:
- rezervasyon sayısı
- rapor üretimi
- export sayısı
- entegrasyon çağrıları

Teslim beklentisi:
- booking create path’lerinde tekil ve idempotent usage kaydı
- service-level instrumentation
- mevcut business flow’larda regresyonsuz çalışma

## P1 — Sonraki İşler

### Usage Metering — PR-UM3 / PR-UM4 / PR-UM5
- `report.generated`, `export.generated`, `integration.call`
- usage görünürlüğü (admin + tenant)
- soft quota enforcement ve upgrade recommendation

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
