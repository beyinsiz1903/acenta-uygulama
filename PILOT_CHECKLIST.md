# 🚀 PILOT PRODUCTION RELEASE CHECKLIST

## PRE-DEPLOYMENT CHECKLIST

### 1) Environment Variables
- [ ] Backend `.env` tüm production değerlerle güncellendi
  - [ ] `MONGO_URL` (prod database)
  - [ ] `DB_NAME` (production db name)
  - [ ] `JWT_SECRET` (güçlü random değer, min 32 char)
  - [ ] `CORS_ORIGINS` (whitelist: https://admin.syroce.com,https://agency.syroce.com)
  - [ ] `AWS_REGION`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_SES_FROM_EMAIL`
  - [ ] `LOG_LEVEL=INFO` (ERROR değil, metrics için INFO gerekli)

- [ ] Frontend `.env` production backend URL ile güncellendi
  - [ ] `REACT_APP_BACKEND_URL=https://api.syroce.com` (veya domain)
  - [ ] `VITE_BACKEND_URL=https://api.syroce.com` (Vite ise)

### 2) Database Indexes (Critical for Performance)
```bash
# Production MongoDB'de çalıştır
db.bookings.createIndex({organization_id: 1, created_at: 1})
db.bookings.createIndex({organization_id: 1, status: 1, created_at: 1})
db.bookings.createIndex({organization_id: 1, agency_id: 1, status: 1})
db.bookings.createIndex({organization_id: 1, hotel_id: 1, status: 1})

db.booking_events.createIndex({organization_id: 1, event_type: 1, created_at: 1})
db.booking_events.createIndex({organization_id: 1, booking_id: 1, event_type: 1, "payload.actor_email": 1})

db.search_cache.createIndex({expires_at: 1}, {expireAfterSeconds: 0})
db.vouchers.createIndex({expires_at: 1}, {expireAfterSeconds: 0})
```

- [ ] Tüm index'ler oluşturuldu
- [ ] TTL index'ler aktif (`db.search_cache.getIndexes()` ile kontrol)

### 3) Security Hardening

- [ ] CORS origins whitelist (wildcard * kaldırıldı)
- [ ] JWT_SECRET production değeri (min 32 char, random)
- [ ] Rate limiting middleware eklendi (opsiyonel ama önerilir)
  ```python
  from slowapi import Limiter
  limiter = Limiter(key_func=get_remote_address)
  # /api/auth/login için 5 req/min
  ```
- [ ] HTTPS zorunlu (HTTP redirect)
- [ ] Security headers (middleware):
  ```python
  app.add_middleware(
      SecurityHeadersMiddleware,
      headers={
          "X-Frame-Options": "DENY",
          "X-Content-Type-Options": "nosniff",
          "Strict-Transport-Security": "max-age=31536000; includeSubDomains"
      }
  )
  ```

### 4) Monitoring & Alerting

- [ ] Health endpoint `/api/health` monitoring eklendi (uptime check)
- [ ] Critical endpoint monitoring:
  - `/api/admin/pilot/summary`
  - `/api/agency/bookings/confirm`
  - `/api/bookings/{id}/track/whatsapp-click`

- [ ] Log aggregation (ELK / CloudWatch / DataDog)
  - [ ] Backend error logs toplanıyor
  - [ ] Frontend console errors toplanıyor

- [ ] Alerting rules:
  - [ ] Backend health check fail > 2 dakika
  - [ ] Error rate > 5% (5xx responses)
  - [ ] avgApprovalMinutes > 300 dk (pilot KPI alarm)

### 5) Data Migration

- [ ] Staging'den production'a initial data migrate edildi:
  - [ ] organizations
  - [ ] users (admin, demo accounts)
  - [ ] agencies (2-3 pilot acenta)
  - [ ] hotels (3-5 pilot otel)
  - [ ] agency_hotel_links (komisyon tanımları)

- [ ] Migration verification:
  ```bash
  # Prod MongoDB'de kontrol
  db.organizations.countDocuments()  # ≥ 1
  db.users.countDocuments()  # ≥ 3 (admin + pilot users)
  db.agencies.countDocuments()  # ≥ 2
  db.hotels.countDocuments()  # ≥ 3
  db.agency_hotel_links.countDocuments()  # ≥ 3
  ```

### 6) Background Workers

- [ ] Email worker başlıyor mu? (`email_dispatch_loop`)
  - [ ] SES credentials doğru
  - [ ] FROM_EMAIL verified (AWS SES verification)
  
- [ ] Integration sync worker başlıyor mu? (`integration_sync_loop`)

- [ ] Worker logs temiz mi? (error yok)

### 7) Frontend Build

- [ ] Production build oluşturuldu: `yarn build`
- [ ] Build artifacts kontrol:
  - [ ] Bundle size < 2MB (gzip)
  - [ ] No console.log statements (production)
  - [ ] Source maps disabled (veya CDN'den ayrı serve)

- [ ] Deployment:
  - [ ] Static files CDN'de (S3 + CloudFront / Vercel / Netlify)
  - [ ] Cache headers doğru (max-age=31536000 for versioned assets)

### 8) Reverse Proxy / Load Balancer

- [ ] Backend routing:
  ```nginx
  location /api/ {
      proxy_pass http://backend:8001/api/;
      proxy_set_header Host $host;
      proxy_set_header X-Real-IP $remote_addr;
  }
  ```

- [ ] Frontend routing:
  ```nginx
  location / {
      try_files $uri $uri/ /index.html;  # SPA routing
  }
  ```

- [ ] HTTPS sertifikası aktif (Let's Encrypt / AWS ACM)

---

## DEPLOYMENT DAY CHECKLIST

### Pre-Launch (T-2h)

- [ ] Staging'de son smoke test (yukarıdaki 5 adım)
- [ ] Prod database backup alındı
- [ ] Rollback planı hazır (database snapshot + previous build)

### Launch (T-0)

- [ ] Backend deploy (Docker/K8s/systemd)
  ```bash
  # Örnek Docker
  docker-compose up -d backend
  docker logs -f backend  # İlk 2 dk hata yok mu?
  ```

- [ ] Health check geçiyor mu?
  ```bash
  curl https://api.syroce.com/api/health
  ```

- [ ] Frontend deploy (CDN/S3)
  ```bash
  yarn build
  aws s3 sync build/ s3://syroce-frontend --delete
  aws cloudfront create-invalidation --distribution-id XXX --paths "/*"
  ```

- [ ] End-to-end test:
  1. Login (admin@acenta.test)
  2. Pilot dashboard açılıyor mu?
  3. KPI'lar render oluyor mu?
  4. Breakdown grafikleri görünüyor mu?

### Post-Launch (T+1h)

- [ ] Pilot kullanıcılarına mail/WhatsApp gönderildi (launch announcement)
- [ ] İlk 1 saatte 1 test booking oluşturuldu (gerçek kullanıcı veya smoke test)
- [ ] Monitoring dashboard kontrol (error spike yok mu?)

---

## ROLLBACK PLAN

### Tetikleyici koşullar:
- Health check 5 dakika fail
- Error rate > 50% (5xx)
- Kritik feature çalışmıyor (login, booking confirm)

### Rollback adımları:
1. Frontend: Previous S3 deploy'u geri yükle veya CloudFront invalidation revert
2. Backend: Previous Docker image'ı deploy et
   ```bash
   docker-compose down
   docker-compose -f docker-compose.rollback.yml up -d
   ```
3. Database: Snapshot'tan restore (sadece kritik data loss varsa)
4. Verify: Health check + smoke test
5. Notify: Pilot kullanıcılarına bilgi

---

## POST-PILOT KPI REVIEW (Haftalık)

### Her Pazartesi sabah:

1. Admin dashboard → Pilot Dashboard
2. KPI'ları kopyala (yukarıdaki haftalık rapor şablonuna)
3. Breakdown'lara bak:
   - En yavaş otel kimdi? (avg_approval_minutes)
   - En düşük conversion acenta kimdi?
   - Hangi gün peak vardı?

4. Aksiyon belirle:
   - avgApprovalMinutes > 180 → o otelle görüşme (bildirim sistemi?)
   - whatsappShareRate < 30% → acenta onboarding/training mi eksik?
   - flowCompletionRate < 50% → draft sonrası UX problemi

---

## MONITORING DASHBOARD (Önerilir)

### Grafana / DataDog / CloudWatch

**Panel 1: API Health**
- Request count (last 1h, by endpoint)
- Error rate (4xx, 5xx)
- Response time (p50, p95, p99)

**Panel 2: Pilot KPIs (Realtime)**
- totalRequests (last 24h)
- whatsappShareRate (last 24h)
- avgApprovalMinutes (last 24h)

**Panel 3: Worker Health**
- Email outbox pending count
- Email outbox failed count (last 1h)
- Integration sync pending count

**Panel 4: Database**
- Connection pool usage
- Query time (slow queries > 1s)
- Collection size (bookings, booking_events)

---

## ÖZET: FAZ-2.1 PROD-READY STATUS

✅ **Backend:**
- Pilot KPI endpoint çalışıyor
- Breakdown aggregations doğrulandı
- WhatsApp tracking idempotent
- Test data validation passed

✅ **Frontend:**
- Recharts entegre
- Zero-fill helper
- Production-safe error handling
- Theme-friendly design

✅ **Doğrulama:**
- 9/9 matematiksel invariant test passed
- Sample data ile KPI'lar doğru

⏳ **Yapılacak (Ops):**
- Prod env variables set et
- MongoDB indexes oluştur
- CORS whitelist düzenle
- Monitoring setup
- Pilot kullanıcılarına onboarding

**Pilot launch hazır! 🎉**
