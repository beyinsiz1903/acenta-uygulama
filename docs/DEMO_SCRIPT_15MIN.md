# 🎬 15 Dakika Enterprise Demo Script

## Hedef Kitle: CTO / COO / IT Director
## Süre: 15 dakika (+ 5 dk Q&A)

---

## 0:00–1:30 | Açılış — "Neyi çözüyoruz?"

**Mesaj:** Turizm operasyonunu ERP + B2B + Finance olarak tek çekirdekte, enterprise yönetişimle sunuyoruz.

**Ekran:** Dashboard (KPI bar + activity + alerts)

**Konuşma:**
> "Turizm sektöründe operasyon genellikle 5-6 farklı araçla yürütülüyor: CRM, muhasebe, kanal yönetimi, faturalama, raporlama. Bu dağınıklık hem maliyet hem veri tutarsızlığı yaratıyor. Biz tüm bu katmanları tek platformda, enterprise standartta sunuyoruz."

---

## 1:30–3:30 | Multi-tenant & Roles (Güven)

**Ekran:** Admin → Tenant Health → RBAC → 2FA

**Göster:**
- Tenant listesi (trial/active/overdue filtreleri)
- RBAC v2 permission yapısı
- 2FA enable/disable akışı
- IP whitelist konfigürasyonu

**Konuşma:**
> "Her müşteri izole bir tenant. Roller ve izinler granüler. 2FA ve IP kısıtlaması kurumsal standart. Audit log'da her işlem kriptografik zincirle bağlı — değiştirilemez."

---

## 3:30–5:30 | CRM (Satış kası)

**Ekran:** CRM Pipeline (DnD) + Deal Drawer

**Göster:**
- Pipeline board'da deal'ı sürükle
- Deal drawer: tasks, notes, activity timeline
- Customer 360 sayfası

**Konuşma:**
> "Satış süreci izlenebilir. Her deal'ın aktivite geçmişi, görevleri ve notları var. Pipeline board drag-drop ile çalışıyor."

---

## 5:30–7:30 | Finance (WebPOS + Ledger)

**Ekran:** WebPOS → payment → ledger

**Göster:**
- WebPOS ödeme kaydı
- Ledger tab (append-only)
- Refund approval flow

**Konuşma:**
> "Ledger append-only — hiçbir kayıt silinemez veya değiştirilemez. İade süreçleri onay mekanizmasından geçer. Finansal denetim için tam iz."

---

## 7:30–9:00 | Reporting (Yönetim)

**Ekran:** Advanced Reports

**Göster:**
- Financial / Product / Partner / Aging raporları
- CSV export
- Scheduled reports ayarı

**Konuşma:**
> "Raporlar zamanlanabilir — her pazartesi CEO'ya mail atılsın. CSV export ile ERP entegrasyonu kolay."

---

## 9:00–10:30 | E-Fatura (Uyum)

**Ekran:** Admin → E-Fatura → create → send

**Göster:**
- Fatura oluştur (satır detay, vergi)
- Gönder (mock provider)
- Durum takibi (taslak → gönderildi → kabul)

**Konuşma:**
> "E-fatura altyapısı provider-agnostic. Şu an mock ile çalışıyor; Paraşüt, Foriba veya tercih ettiğiniz sağlayıcı 1-2 haftada eklenir."

---

## 10:30–11:30 | SMS (Operasyon)

**Ekran:** Admin → SMS → template → send → logs

**Göster:**
- Template seçimi
- Tekli SMS gönder
- Log'da delivered durumu

**Konuşma:**
> "Netgsm, Twilio veya başka sağlayıcı takılabilir. Her SMS audit log'a düşer."

---

## 11:30–12:30 | QR Ticket / Check-in (Saha)

**Ekran:** Tickets → create → check-in

**Göster:**
- Bilet oluştur (QR data)
- Check-in yap
- Guard'lar: already checked-in, canceled, expired

**Konuşma:**
> "Saha ekibi QR kodu tarar, check-in olur. Zaten yapılmışsa hata verir. İptal edilmişse bloklar. Çift kullanım imkansız."

---

## 12:30–14:00 | Ops Excellence (Enterprise farkı)

**Ekran:** Preflight → Runbook → Metrics → Errors → Uptime

**Göster:**
1. **Preflight** — GO/NO-GO banner (yeşil)
2. **Runbook** — P0 incident adımları
3. **Metrics** — 8 metrik kartı
4. **Errors** — Aggregated hatalar
5. **Uptime** — %100 badge
6. **Perf Dashboard** — p50/p95/p99 tablosu

**Konuşma:**
> "Bu platform sadece turizm yazılımı değil. Production go-live checklist'i otomatik, ops runbook'u interaktif, backup/restore test edilmiş, uptime izleniyor. Enterprise SaaS standardında işletilebilir bir sistem."

---

## 14:00–15:00 | Kapanış (Next steps)

**Mesaj:**
> "Önerimiz: 2 haftalık pilot (gerçek veriyle), 1 hafta eğitim, sonra go-live. Checklist hazır, runbook hazır. Başlayalım mı?"

**Göster:** Preflight → GO banner (tekrar)
