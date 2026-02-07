# 15 Dakikalık SLA Demo Script (Enterprise Müşteriye)

## 0–2 dk: Security
- RBAC v2 permission örneği göster
- 2FA enable/disable
- IP whitelist toggle

## 2–6 dk: Governance
- Approval inbox (refund approve)
- Audit log export CSV
- Hash chain integrity mention (“her audit kaydı kriptografik zincirle bağlı”)

## 6–10 dk: Ops
- **System Metrics dashboard** (`/app/admin/system-metrics`)
  - 8 metrik kartı: tenant, kullanıcı, fatura, SMS, check-in, latency, hata oranı, disk
- **System Errors** (`/app/admin/system-errors`)
  - Signature aggregation göster
- **Maintenance mode** (`/app/admin/tenant-maintenance`)
  - Demo tenant için aç/kapat

## 10–13 dk: Reliability
- **Backup run** (`/app/admin/system-backups`)
  - Yedek al → listede görünür
- **Restore test** script çıktısını göster (staging)
- **Preflight kontrolü** (`/app/admin/preflight`)
  - GO/NO-GO verdıct göster

## 13–15 dk: Compliance / Domain
- E-Fatura mock send lifecycle
- QR check-in flow
- SMS template send (mock delivered)

## Kapanış Cümlesi

> “Bu platform sadece turizm yazılımı değil; enterprise SaaS standardında işletilebilir bir sistem.”

---

## Demo Hazırlık Checklist

- [ ] Staging ortamında demo tenant oluşturuldu
- [ ] Örnek veriler seed edildi (3-5 fatura, 2-3 bilet, SMS logları)
- [ ] En az 1 başarılı backup mevcut
- [ ] Preflight kontrolü GO veriyor
- [ ] Incident create/resolve test edildi
- [ ] 2FA test hesabı hazır
