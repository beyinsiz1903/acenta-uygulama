# 📊 PILOT HAFTASI CANLI TAKİP REHBERİ

## ⏱ Günlük 5 Dakikalık Ritüel (Her Gün - 09:00)

**Dashboard Aç:** https://admin.syroce.com/app/admin/pilot-dashboard
**Süre:** 5 dakika
**Hedef:** KPI'ları kaydet, red flag'leri yakala

---

## 1️⃣ GOOGLE SHEETS TEMPLATE (Kopyala-Yapıştır)

### Sheet-1: `Daily_Log` (Ana KPI Takibi)

**Google Sheets'te yeni sheet aç → A1'e yapıştır:**

```csv
date,totalRequests,confirmedBookings,cancelledBookings,whatsappClickedCount,whatsappShareRate,hotelPanelActionRate,flowCompletionRate,avgApprovalMinutes,notes
```

**İlk satır (örnek - 2. satıra):**
```csv
2025-12-21,10,6,4,5,=IFERROR(E2/B2,0),=IFERROR((C2+D2)/B2,0),=IFERROR(C2/B2,0),20,İlk test data
```

**Formüller (2. satırdan başla, aşağı kopyala):**
- **F sütunu (whatsappShareRate):** `=IFERROR(E2/B2,0)`
- **G sütunu (hotelPanelActionRate):** `=IFERROR((C2+D2)/B2,0)`
- **H sütunu (flowCompletionRate):** `=IFERROR(C2/B2,0)`

**Manuel Dolduracakların:**
- A: Tarih (YYYY-MM-DD)
- B: totalRequests (dashboard'tan)
- C: confirmedBookings (meta'dan)
- D: cancelledBookings (meta'dan)
- E: whatsappClickedCount (meta'dan)
- I: avgApprovalMinutes (dashboard'tan)
- J: notes (kısa not)

---

### Sheet-2: `Weekly_Summary` (Otomatik Özet)

**A1'e yapıştır:**

```
Haftalık Özet
```

**A3'e başlayarak:**
```csv
Metrik,Değer
Gün Sayısı,=COUNTA(Daily_Log!A2:A)
Toplam Talep,=SUM(Daily_Log!B2:B)
Toplam Onaylı,=SUM(Daily_Log!C2:C)
Toplam İptal,=SUM(Daily_Log!D2:D)
Toplam WhatsApp Click,=SUM(Daily_Log!E2:E)
WhatsApp Share Rate (Weighted),=IFERROR(SUM(Daily_Log!E2:E)/SUM(Daily_Log!B2:B),0)
Hotel Action Rate (Weighted),=IFERROR((SUM(Daily_Log!C2:C)+SUM(Daily_Log!D2:D))/SUM(Daily_Log!B2:B),0)
Flow Completion Rate (Weighted),=IFERROR(SUM(Daily_Log!C2:C)/SUM(Daily_Log!B2:B),0)
Avg Approval Minutes (Ortalama),=IFERROR(AVERAGE(Daily_Log!I2:I),0)
```

**Format:** B sütununda yüzde olanlar (6,7,8) → Format > Number > Percent

---

### Sheet-3: `Hotel_Detail` (Detaylı Otel Takibi)

**Dashboard'dan `breakdown.by_hotel` verilerini manuel kopyala (günlük veya 2 günde bir):**

**A1'e başlıklar:**
```csv
date,hotel_name,total,confirmed,cancelled,action_rate,avg_approval_minutes
```

**Örnek satır (2. satır):**
```csv
2025-12-21,Demo Hotel 1,10,6,4,1.0,20
2025-12-22,Demo Hotel 1,12,7,5,1.0,18
```

**Kullanım:**
- Hangi otel tutarlı yavaş?
- Hangi otel'de approval süresi artıyor?
- Action rate düşen otel var mı?

**Red Flag Formula (Conditional Formatting):**
- **G sütunu (avg_approval_minutes) kırmızı:** `=$G2>180`
- **F sütunu (action_rate) sarı:** `=$F2<0.7`

---

### Sheet-4: `Agency_Detail` (Detaylı Acenta Takibi)

**Dashboard'dan `breakdown.by_agency` verilerini kopyala:**

**A1'e başlıklar:**
```csv
date,agency_name,total,confirmed,whatsapp_clicks,conversion_rate,whatsapp_rate
```

**Örnek satır:**
```csv
2025-12-21,Demo Acente A,10,6,5,0.6,0.5
2025-12-22,Demo Acente A,12,7,6,0.58,0.5
```

**Kullanım:**
- Hangi acenta düşük conversion?
- Hangi acenta WhatsApp kullanmıyor?
- Trend yükseliyor mu düşüyor mu?

**Red Flag Formula:**
- **F sütunu (conversion_rate) kırmızı:** `=AND($C2>=5,$F2<0.3)`
- **G sütunu (whatsapp_rate) turuncu:** `=AND($C2>=5,$G2<0.3)`

---

## B) Conditional Formatting (Red Flag Auto-Highlight)

### Daily_Log sheet'inde:

1. **avgApprovalMinutes > 180** → Kırmızı arka plan
   - Range: `I2:I100`
   - Format rule: Custom formula `=$I2>180`
   - Background: Kırmızı

2. **whatsappShareRate < 0.3 (ve totalRequests >= 5)** → Turuncu
   - Range: `F2:F100`
   - Formula: `=AND($B2>=5,$F2<0.3)`
   - Background: Turuncu

3. **flowCompletionRate < 0.3 (ve totalRequests >= 5)** → Turuncu
   - Range: `H2:H100`
   - Formula: `=AND($B2>=5,$H2<0.3)`
   - Background: Turuncu

---

## C) Hızlı Doldurum Örneği (Pazartesi sabah)

### Dashboard'tan Kopyala:

```bash
# Terminal'de (örnek):
curl -s "https://api.syroce.com/api/admin/pilot/summary?days=7" \
  -H "Authorization: Bearer $(cat token.txt)" \
| jq -r '
  [
    (.range.to[0:10]),
    .kpis.totalRequests,
    .meta.confirmedBookings,
    .meta.cancelledBookings,
    .meta.whatsappClickedCount,
    "",
    "",
    "",
    .kpis.avgApprovalMinutes,
    ""
  ] | @csv'
```

→ Çıktıyı Daily_Log'a yapıştır.

(Manuel de yapabilirsin: Dashboard kartlarından rakamları oku → sheet'e gir)

---

## D) Haftalık Review Formatı (Pazartesi - 20 dk)

### Hazırlık (5 dk önce):

1. Weekly_Summary sheet'ine bak
2. Hotel_Detail + Agency_Detail en son değerlere bak
3. Trend grafiği oluştur (isteğe bağlı - Daily_Log'dan Select All → Insert Chart → Line)

### Meeting içinde:

**Başlık:** *"Pilot 1. Hafta KPI Review"*

**Agenda (toplam 20 dk):**

1. **KPI Özet (3 dk)**

   * *"Toplam X talep, %Y onay, ortalama Z dk approval"*
   * Hedefle karşılaştır
2. **Red Flag Analiz (7 dk)**

   * Hangi gün kırmızı?
   * Hangi otel/acenta?
   * Neden? (notes sütununa bakarak)
3. **Karar (5 dk)**

   * Bildirim sistemi gerekli mi? → **FAZ-3**
   * Yoksa manuel müdahale yeterli mi? → **2. hafta devam**
4. **Aksiyon Planı (5 dk)**

   * Kime ne denilecek (otel/acenta)
   * Gelecek hafta neyi deneyelim

---

# 2️⃣ FAZ-3 Karar Ağacı Kartı (1 Hafta Sonrası)

Aşağıdaki matrisi **1. hafta verileriyle** doldur:

## Profil 1: "Otel Yavaş, Acenta İyi"

**KPI'lar:**

* avgApprovalMinutes > 120 dk
* whatsappShareRate > 0.5
* flowCompletionRate > 0.5

**Teşhis:** Otel alışkanlık/bildirim problemi

**FAZ-3 Tasarımı:**

* ✅ **Otel Reminder Sistemi** (30/60 dk)
* ✅ Email + (opsiyonel) SMS
* ❌ Acenta tarafına müdahale gerekmez

---

## Profil 2: "Acenta Düşük Engagement, Otel İyi"

**KPI'lar:**

* avgApprovalMinutes < 60 dk
* whatsappShareRate < 0.3
* flowCompletionRate < 0.4

**Teşhis:** Acenta ürünü benimsememiş / güvenmiyor

**FAZ-3 Tasarımı:**

* ✅ WhatsApp CTA iyileştirme (buton + mesaj)
* ✅ "Tek tık kopyala" feature
* ✅ Acenta onboarding / training
* ❌ Otel reminder gerekmez

---

## Profil 3: "İkisi de Düşük"

**KPI'lar:**

* avgApprovalMinutes > 180 dk
* whatsappShareRate < 0.3
* flowCompletionRate < 0.3

**Teşhis:** Sistemik / pilot komunikasyon problemi

**FAZ-3 Tasarımı:**

* 🔴 **Önce manuel kontrol** (otel + acenta ile 1-1 görüşme)
* ✅ Temel bildirim sistemi (her iki tarafa)
* ✅ Onboarding gözden geçir
* ⚠️ Ürün/pazara uyum sorgulanmalı (pivot mı?)

---

## Profil 4: "Her Şey İyi" (Senaryo: İdeal)

**KPI'lar:**

* avgApprovalMinutes < 60 dk
* whatsappShareRate > 0.5
* flowCompletionRate > 0.6

**Teşhis:** Pilot başarılı 🎉

**FAZ-3 Tasarımı:**

* ✅ Ölçeklenmeye hazırlık (daha fazla acenta/otel)
* ✅ Gentle optimizations (approval 30 dk'ya düşürmek)
* ✅ Feature roadmap (mutabakat, raporlama, mobile)
* ❌ Kritik müdahale gerekmez

---

# 3️⃣ Pilot 1. Gün Sabah Kontrol Listesi (Yarın)

## 09:00 — İlk Kontrol

1. **Login kontrol:**

   * admin@acenta.test / prod-password
   * Dashboard açılıyor mu?
2. **KPI kartları render:**

   * Tüm kartlar görünüyor mu?
   * Sayılar makul mi? (0 veya önceki test verileri)
3. **Grafikler:**

   * Line chart (günlük trend) crash olmuyor mu?
   * Bar chart (otel) görünüyor mu?
   * Table (acenta) satırlar var mı?

## 10:00 — İlk Booking Testi

1. Agency user login (gerçek pilot acentadan biri)
2. 1 booking oluştur (draft → confirm)
3. Confirmed sayfasında **WhatsApp'a Gönder** tıkla
4. 09:05'te dashboard'u refresh et:
   * `totalRequests +1`
   * `whatsappClickedCount +1`

## Akşam 18:00 — Gün Sonu Log

1. Dashboard'a tekrar bak
2. Daily_Log sheet'e gün sonu değerleri gir
3. Red flag varsa notes'a yaz
4. Yarın sabah aksiyon planı not et

---

# 4️⃣ Haftalık Review Template (Pazartesi)

## Toplantı Formatı (20 dk)

### Slide 1: Haftalık Özet (3 dk)

* **Toplam:** X talep, Y onaylı, Z iptal
* **Ortalama:** Approval W dk, WhatsApp %P
* **Hedef Karşılaştırma:**
  * totalRequests ≥ 20? (✅/❌)
  * flowCompletion ≥ 50%? (✅/❌)
  * avgApproval < 180 dk? (✅/❌)

### Slide 2: Red Flags (7 dk)

* Hangi günler kırmızı?
* Hangi otel en yavaş? (Hotel_Detail'den)
* Hangi acenta en düşük? (Agency_Detail'den)
* Root cause analizi:
  * Bildirim mi eksik?
  * Alışkanlık mı yok?
  * Süreç mi yanlış?

### Slide 3: Karar (5 dk)

* **FAZ-3'e geçiyor muyuz?**
  * Evet → Profil seç (Otel Reminder / Acenta CTA / İkisi)
  * Hayır → 2. hafta devam, manuel müdahale
* **Pilot genişletiliyor mu?**
  * Daha fazla acenta/otel ekleniyor mu?

### Slide 4: Aksiyon Planı (5 dk)

* A1: [Kişi] - [Yapılacak] - [Tarih]
* A2: ...
* A3: ...

---

# 5️⃣ Hotel_Detail Log (Detaylı Otel Takibi)

### Sheet-3: `Hotel_Detail`

**A1'e yapıştır:**
```csv
date,hotel_name,total,confirmed,cancelled,action_rate,avg_approval_minutes,notes
```

**Nasıl doldurulur:**
- Dashboard'dan `breakdown.by_hotel` kopyala
- Günlük değil, **2-3 günde bir** yeter
- Amaç: Otel bazlı trend görmek

**Red Flag Kuralları:**
- **avg_approval_minutes > 180** → Kırmızı
  - Formula: `=$G2>180`
- **action_rate < 0.7** → Sarı
  - Formula: `=$F2<0.7`

**Kullanım:**
- Pazartesi review'da: "Demo Hotel 1 son 3 günde approval 200+ dk"
- Aksiyon: O oteli ara, neden yavaş?

---

# 6️⃣ Agency_Detail Log (Detaylı Acenta Takibi)

### Sheet-4: `Agency_Detail`

**A1'e yapıştır:**
```csv
date,agency_name,total,confirmed,whatsapp_clicks,conversion_rate,whatsapp_rate,notes
```

**Nasıl doldurulur:**
- Dashboard'dan `breakdown.by_agency` kopyala
- 2-3 günde bir
- Amaç: Acenta adoption trend

**Red Flag Kuralları:**
- **conversion_rate < 0.3** → Kırmızı
  - Formula: `=AND($C2>=5,$F2<0.3)`
- **whatsapp_rate < 0.3** → Turuncu
  - Formula: `=AND($C2>=5,$G2<0.3)`

**Kullanım:**
- Pazartesi review'da: "Acente A 10 booking'te 2 WhatsApp click"
- Aksiyon: Acente ile konuş, neden paylaşmıyor?

---

# 7️⃣ Red Flag → Anında Aksiyon Kuralları

## 🚨 Kural 1: avgApprovalMinutes > 180 dk

**Tetikleme:** Daily_Log'da günlük, veya Hotel_Detail'de otel bazlı

**Aksiyon (aynı gün):**
1. O otelin panelini kontrol et (gerçekten pending var mı?)
2. Otele WhatsApp/telefon:
   > "Merhaba, X acenteden rezervasyon talebi 3 saattir bekliyor. Panelden görmediniz mi?"
3. Notes'a yaz: "Otel Y - sebep: panel bakmamış / notification kaçmış"

**Outcome:**
- Manuel reminder'ın etkisi var mı? (bir sonraki gün approval düşer mi?)
- Yoksa bildirim sistemi şart mı? (FAZ-3 go)

---

## 🚨 Kural 2: whatsappShareRate < 0.3 (totalRequests >= 5)

**Tetikleme:** Daily_Log'da weighted rate, veya Agency_Detail'de acenta bazlı

**Aksiyon (2-3 günde bir):**
1. Agency_Detail'den düşük olan acentayı bul
2. Acentaya sor:
   > "WhatsApp paylaşımını kullanıyor musunuz? Mesaj metni size uygun mu?"
3. Notes'a yaz: "Acente X - sebep: alışkın değil / mesaj metni uzun / timing yanlış"

**Outcome:**
- Acenta CTA iyileştirmesi gerekli mi? (buton yeri / mesaj template)
- Onboarding mi eksik?

---

## 🚨 Kural 3: flowCompletionRate < 0.3 (totalRequests >= 10)

**Tetikleme:** Daily_Log weighted veya Weekly_Summary

**Aksiyon (haftalık review'da):**
1. Hotel_Detail + Agency_Detail breakdown'a bak
2. Problem tek aktörde mi yoksa sistemik mi?
   - Tek otelde → O otelle süreç konuş
   - Tüm acentelerde → UX problemi (akış redesign?)
3. Notes'a yaz: "Flow düşük - sebep: draft sonrası otel onaylamıyor / acenta vazgeçiyor"

**Outcome:**
- UX değişikliği mi? (draft sonrası reminder / progress bar)
- Otel eğitimi mi? (panel nasıl kullanılır)

---

# 8️⃣ FAZ-3 Karar Matrisi (1 Hafta Sonrası)

Pazartesi review'da Weekly_Summary'e bak → aşağıdaki tabloya uydur:

| WhatsApp Rate | Approval Time | Flow Completion | → FAZ-3 Tasarımı |
|---------------|---------------|-----------------|------------------|
| **< 0.3** | **> 180 dk** | **< 0.3** | 🔴 **Profil 3:** Manuel kontrol + temel bildirim (ikisi de) |
| **< 0.3** | **< 60 dk** | **< 0.4** | 🟡 **Profil 2:** WhatsApp CTA iyileştirme + acenta training |
| **> 0.5** | **> 180 dk** | **> 0.5** | 🟢 **Profil 1:** Otel reminder sistemi (hedefli) |
| **> 0.5** | **< 60 dk** | **> 0.6** | 🎉 **Profil 4:** Ölçeklendirme + gentle optimizations |

---

## Profil Detayları

### 🟢 Profil 1: Otel Reminder (En Sık Senaryo)

**Semptom:** Acenta kullanıyor, otel yavaş
**FAZ-3 Tasarımı:**
- Backend: Reminder worker (30/60/120 dk)
- Email template: "Acente X'den rezervasyon talebi bekleniyor"
- (Opsiyonel) SMS/WhatsApp
- Admin UI: Reminder history

**Süre:** 1-2 gün implement
**Etki:** avgApproval 120dk → 45dk düşebilir

---

### 🟡 Profil 2: WhatsApp CTA İyileştirme

**Semptom:** Otel iyi, acenta WhatsApp kullanmıyor
**FAZ-3 Tasarımı:**
- Confirmed sayfasında WhatsApp butonu daha görünür
- Mesaj preview (paylaşmadan önce göster)
- "Tek tık kopyala" alternatifi
- Acenta onboarding video/guide

**Süre:** Yarım gün (frontend only)
**Etki:** whatsappShare 0.3 → 0.6 çıkabilir

---

### 🔴 Profil 3: Sistemik Sorun

**Semptom:** Her şey düşük
**FAZ-3 Tasarımı:**
- Manuel kontrol (her otelle 1-1 konuş)
- Temel bildirim (email, her iki tarafa)
- Onboarding review
- Ürün/pazar uyumu sorgulama

**Süre:** 1 hafta (data toplama + karar)
**Etki:** Pivot gerekebilir

---

### 🎉 Profil 4: Pilot Başarılı

**Semptom:** KPI'lar hedefte
**FAZ-3 Tasarımı:**
- Daha fazla acenta/otel ekle (ölçeklendirme)
- Gentle optimizations:
  - Approval 60dk → 30dk hedefi
  - Mutabakat ekranı adoption artırma
- Feature roadmap (mobile, raporlama, AI)

**Süre:** Sürekli
**Etki:** Sürdürülebilir büyüme

---

# 9️⃣ ÖZET - Yarın Sabah Başlamak İçin

## ✅ Hazır Olan:

1. Backend pilot endpoint (GO ✅)
2. Frontend dashboard (GO ✅)
3. WhatsApp tracking (GO ✅)
4. Google Sheets template (yukarıda)
5. Red flag kuralları
6. FAZ-3 karar matrisi

## 📋 Yapılacak (İlk Gün):

1. [ ] Google Sheets aç, template'i yapıştır
2. [ ] Conditional formatting ekle (red flags)
3. [ ] İlk KPI değerlerini gir (baseline)
4. [ ] Pilot kullanıcılara launch announcement
5. [ ] İlk test booking yap (smoke test)

## 📅 Haftalık Ritüel:

- **Her gün 09:00:** Dashboard → Sheets (5 dk)
- **Red flag varsa:** Aynı gün aksiyon
- **Pazartesi 10:00:** Haftalık review (20 dk)
- **FAZ-3 kararı:** 1. hafta sonu

---

## 🚀 İstersen Şimdi:

**A) Pilot launch announcement template** (acenta/otel'e mail)
**B) İlk gün smoke test script** (step-by-step)
**C) FAZ-3 teknik tasarım** (profil 1 veya 2 için)

**Hangisini istersin?** 

(Bence A - launch announcement, çünkü yarın sabah pilot başlayacaksa kullanıcılara bilgi vermek ilk adım olmalı.)
