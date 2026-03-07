# ROADMAP — Acenta Master Travel SaaS

## Güncel Durum
- `/api/v1` standardizasyonu tamamlandı
- Web auth/session hardening tamamlandı
- Entitlement Projection Engine V1 tamamlandı ve test edildi

## P0 — Sıradaki Kritik İş

### Usage Metering
Hedef: entitlement katmanını gerçek kullanım verisiyle birleştirmek.

Öncelikli ölçümler:
- rezervasyon sayısı
- rapor üretimi
- export sayısı
- entegrasyon çağrıları

Teslim beklentisi:
- ortak metric isimleri
- kritik akışlarda instrumentation
- tenant/period bazlı usage summary
- entitlement allowance’ları ile karşılaştırma
- admin görünürlüğü ve sonraki billing aşaması için hazır veri

## P1 — Sonraki İşler

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
- **Entitlement Projection Engine V1**
  - plan katalogu
  - tenant entitlement projection snapshot
  - admin entitlement görünürlüğü
  - public pricing entegrasyonu
