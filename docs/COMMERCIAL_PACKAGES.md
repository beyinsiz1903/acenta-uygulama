# Syroce — Ticari Paketleme Mimarisi

> Bu doküman, platformun ticari paket yapısını, modül-paket eşlemesini ve lisanslama stratejisini tanımlar.

---

## Paket Stratejisi

Syroce, **değer temelli kademeli lisanslama** modeli kullanır:
- Müşteri büyüdükçe daha fazla modül ve kapasite açılır
- Çekirdek iş akışları her pakette mevcuttur
- B2B ve enterprise modüller üst paketlere ayrılmıştır

---

## Paket Tanımları

### 1. Trial (Deneme)
**Hedef:** Ürünü gerçek akışta denemek isteyen acenteler
- Süre: 14 gün
- Fiyat: Ücretsiz
- Tüm modüller açık (düşük limitlerle)
- Kullanıcı: 2 | Aylık Rez: 100

### 2. Starter (Başlangıç)
**Hedef:** Excel kullanan küçük acenteler
- Fiyat: 990 TRY/ay
- Kullanıcı: 3 | Aylık Rez: 100
- **Aktif modüller:** Dashboard, Rezervasyonlar, CRM, Envanter, Raporlar
- **Kapalı modüller:** Muhasebe, WebPOS, İş Ortakları, B2B, Operasyon

### 3. Pro (Profesyonel)
**Hedef:** Büyüyen, operasyonel derinlik isteyen acenteler
- Fiyat: 2.490 TRY/ay
- Kullanıcı: 10 | Aylık Rez: 500
- **Aktif modüller:** Starter + Muhasebe, WebPOS, İş Ortakları, Operasyon
- **Kapalı modüller:** B2B Dağıtım

### 4. Enterprise (Kurumsal)
**Hedef:** Büyük operasyonlar, B2B ağları, white-label ihtiyacı
- Fiyat: 6.990 TRY/ay
- Kullanıcı: Sınırsız | Aylık Rez: Sınırsız
- **Tüm modüller aktif**
- Özel entegrasyon desteği
- White-label seçeneği

---

## Modül-Paket Eşleme Matrisi

| Modül | Feature Flag | Trial | Starter | Pro | Enterprise |
|-------|-------------|-------|---------|-----|------------|
| Dashboard | `dashboard` | + | + | + | + |
| Rezervasyonlar | `reservations` | + | + | + | + |
| CRM | `crm` | + | + | + | + |
| Envanter | `inventory` | + | + | + | + |
| Raporlar | `reports` | + | + | + | + |
| Muhasebe | `accounting` | + | - | + | + |
| WebPOS | `webpos` | + | - | + | + |
| İş Ortakları | `partners` | + | - | + | + |
| Operasyon | `ops` | + | - | + | + |
| B2B Dağıtım | `b2b` | + | - | - | + |

---

## Kota Sistemi

Her paketin kullanım kotaları vardır. Kota aşımında kullanıcıya uyarı gösterilir.

| Kota Metriği | Trial | Starter | Pro | Enterprise |
|-------------|-------|---------|-----|------------|
| `reservation.created` | 100 | 100 | 500 | Sınırsız |
| `report.generated` | 20 | 30 | 250 | Sınırsız |
| `export.generated` | 10 | 20 | 100 | Sınırsız |
| `integration.call` | 250 | 1.000 | 5.000 | Sınırsız |
| `b2b.match_request` | 25 | 25 | 100 | Sınırsız |

---

## Teknik Uygulama

### Feature Flag Kontrol Akışı
```
HTTP İstek → Tenant Middleware → Feature Service → Kota Kontrolü → İş Mantığı
```

### Backend Dosyalar
- **Plan Matrisi:** `app/constants/plan_matrix.py` — Paket tanımları
- **Feature Keys:** `app/constants/features.py` — Feature flag sabitleri
- **Entitlement Service:** `app/services/entitlement_service.py` — Hak kontrolü
- **Quota Enforcement:** `app/services/quota_enforcement_service.py` — Kota zorlama
- **Usage Service:** `app/services/usage_service.py` — Kullanım ölçümü

### Frontend Dosyalar
- **Feature Context:** `src/contexts/FeatureContext.jsx` — Feature flag React context
- **Feature Catalog:** `src/config/featureCatalog.js` — Özellik kataloğu
- **Feature Plans:** `src/config/featurePlans.js` — Plan-özellik eşlemesi
- **Menu Config:** `src/config/menuConfig.js` — Menu item filtreleme

---

## Satış Önerisi: Paket Yükseltme Yolu

```
Trial (14 gün)
    ↓ otomatik
Starter (temel ihtiyaçlar)
    ↓ büyüme sinyali
Pro (operasyonel derinlik)
    ↓ B2B / enterprise ihtiyacı
Enterprise (tam kapasite)
```

### Yükseltme Tetikleyicileri
- **Starter → Pro:** Muhasebe/operasyon ihtiyacı, 3+ kullanıcı
- **Pro → Enterprise:** B2B dağıtım, 10+ kullanıcı, white-label
- **Trial → Starter:** 14 gün dolumu, kullanım alışkanlığı oluşması

---

*Son güncelleme: Şubat 2026*
