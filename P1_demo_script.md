# P1 Demo Script – TRY Flow & Rule-based Pricing

Bu doküman, P1.1 (TRY→EUR standardizasyonu) ve P1.2 (rule-based pricing)
özelliklerini **demo günü** tek koşuda gösterebilmek için hazırlanmış bir
"runbook"tır.

Amaç: 20–30 dakikalık bir oturumda, yatırımcı/iş tarafına şu iki cümleyi
kanıtlı göstermek:

1. "Satış para birimi TRY olsa bile muhasebe defteri tek bir standartta EUR;
   dönüşüm kaynağı booking snapshot ve idempotent."
2. "Aynı ürün ve tarihte, sadece acente değiştirerek fiyat farkı
   oluşturabiliyoruz; bu fark rule-based pricing motorundan geliyor."

---

## 1. Pre-flight Check (2 dk)

### 1.1. Kullanıcılar

Aşağıdaki kullanıcıların çalıştığından emin olun:

- **Admin (Ops):**  `admin@acenta.test / admin123`
- **Agency1 (Demo Acente A):**  `agency1@demo.test / agency123`
  - settings.selling_currency = `"TRY"`
  - P1.2 demo için: %12 markup
- **Agency2 (Demo Acente B):**  (seed ile ikinci acente + kullanıcı varsa)
  - settings.selling_currency yok → default EUR
  - P1.2 demo için: %10 markup

### 1.2. Seed / Konfigürasyon Kontrolü

Bu bölüm, ortamın P1.1 + P1.2 demoları için hazır olup olmadığını hızlıca
kontrol eder.

#### 1.2.1. FX Rate (EUR→TRY) var mı?

```bash
python3 << 'PY'
import os, asyncio, json
from motor.motor_asyncio import AsyncIOMotorClient

mongo_url = os.environ.get("MONGO_URL")
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ.get("DB_NAME", "test_database")]

async def main():
    org = await db.organizations.find_one({})
    org_id = org.get("id") or str(org.get("_id"))
    fx = await db.fx_rates.find_one({
        "organization_id": org_id,
        "base": "EUR",
        "quote": "TRY",
    })
    print(json.dumps(fx or {"error": "NO_EUR_TRY_FX_FOUND"}, default=str, indent=2))

asyncio.run(main())
PY
```

- `error: NO_EUR_TRY_FX_FOUND` görüyorsanız seed henüz çalışmamış olabilir.

#### 1.2.2. Pricing rules (10% + 12%) var mı?

```bash
python3 << 'PY'
import os, asyncio, json
from motor.motor_asyncio import AsyncIOMotorClient

mongo_url = os.environ.get("MONGO_URL")
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ.get("DB_NAME", "test_database")]

async def main():
    org = await db.organizations.find_one({})
    org_id = org.get("id") or str(org.get("_id"))

    cur = db.pricing_rules.find({"organization_id": org_id}, {"_id": 0}).sort("priority", -1)
    rules = await cur.to_list(length=10)
    print(json.dumps(rules, default=str, indent=2))

asyncio.run(main())
PY
```

Beklenen iki demo kuralı:

- `notes = "seed_p12_default_hotel_markup"` → `%10`, `priority=100`, `scope.product_type="hotel"`
- `notes = "seed_p12_agency1_markup"` → `%12`, `priority=200`, `scope.product_type="hotel"`, `scope.agency_id=<Demo Acente A>`

#### 1.2.3. Demo ürünler (otel + rate_plan + inventory) var mı?

Bu P0.1/P0.2 seed’inin doğru çalıştığını hızlıca kontrol etmek için:

```bash
python3 << 'PY'
import os, asyncio, json
from motor.motor_asyncio import AsyncIOMotorClient

mongo_url = os.environ.get("MONGO_URL")
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ.get("DB_NAME", "test_database")]

async def main():
    org = await db.organizations.find_one({})
    org_id = org.get("id") or str(org.get("_id"))

    hotel = await db.hotels.find_one({"organization_id": org_id})
    inv = await db.inventory.find_one({"organization_id": org_id})
    rp = await db.rate_plans.find_one({"organization_id": org_id})

    out = {
        "hotel": {"id": hotel.get("_id"), "name": hotel.get("name")} if hotel else None,
        "inventory": {"product_id": inv.get("product_id"), "date": inv.get("date")} if inv else None,
        "rate_plan": {"id": rp.get("_id"), "currency": rp.get("currency")} if rp else None,
    }
    print(json.dumps(out, default=str, indent=2))

asyncio.run(main())
PY
```

---

## 2. Akış 1 – TRY Selling → EUR Ledger Standardizasyonu (P1.1)

Bu akış P1.1’in hedefini kanıtlar:

> "Agency satış para birimi TRY; fakat defterde her şey EUR ve
>  dönüşüm booking anındaki snapshot ile deterministik."

### 2.1. UI: TRY Booking Oluşturma

1. Tarayıcıda `…/app/login` → `agency1@demo.test / agency123` ile giriş.
2. `/app/agency/hotels` sayfasına gidin.
3. P0.2 akışı ile (Search → Quote → Booking) yeni bir booking oluşturun.
4. Kartta ve özet ekranında fiyatın **TRY** olduğunu gözlemleyin
   (örn. `2200 TRY`).

### 2.2. Booking Dokümanı: TRY + EUR Snapshot

`P0.3_demo_script.md` içindeki **4. TRY Selling → EUR Ledger Standardization
(P1.1 Preview)** bölümündeki adımları kullanın; özetle:

- `BOOKING_ID`’yi UI’dan alın.
- Python snippet ile booking’i gösterin:
  - `currency = "TRY"`
  - `amounts.sell` (TRY)
  - `amounts.sell_eur` (EUR)
  - `fx: {base:"EUR", quote:"TRY", rate, rate_basis:"QUOTE_PER_EUR", snapshot_id}`

Mesaj:

> "Booking TRY satıyor ama amounts.sell_eur alanı sayesinde defter için EUR
>  karşılığı deterministik olarak kilitlenmiş durumda."

### 2.3. Ledger: EUR Posting (Balanced, amount==sell_eur)

Yine `P0.3_demo_script.md` içindeki komutlarla:

- `ledger_postings` üzerinden ilgili booking için:
  - `CURRENCIES == {"EUR"}`
  - `TOTAL_DEBIT ≈ TOTAL_CREDIT ≈ SELL_EUR`

Mesaj:

> "Satış TRY olsa bile ledger_postings tamamen EUR standardında; miktar
>  booking.amounts.sell_eur üzerinden geliyor ve dengeli."

### 2.4. Otomatik Kanıt: Non-EUR Booking FX & Ledger Testi

```bash
cd /app/backend
pytest tests/test_non_eur_booking_fx_and_ledger.py -q
```

- TRY booking varsa: **PASS**
- Hâlâ EUR-only ortamdaysanız (henüz TRY booking yaratılmadıysa):
  - Test `Non-EUR P1.1 flow not yet active...` mesajıyla **SKIP** olur.

Bu test, TRY booking → FX snapshot → booking_financials → EUR ledger-posting
zincirinin tamamını otomatik doğrular.

---

## 3. Akış 2 – Rule-based Pricing (P1.2)

Bu akışın hedefi:

> "Aynı ürün ve tarihte, sadece acente değiştirerek fiyat farkı
>  oluşturabiliyoruz; bu fark rule-based pricing motorundan geliyor."

### 3.1. Kontrat: Seed Kuralları

Seed sonrasında demo org için şu kurallar mevcut olmalı:

1. **Default hotel kuralı**
   - `product_type="hotel"`
   - `priority=100`
   - `action.type="markup_percent"`, `value=10.0`
   - `notes="seed_p12_default_hotel_markup"`

2. **Demo Acente A (agency1) için özel kural**
   - `product_type="hotel"`, `agency_id=<Demo Acente A _id>`
   - `priority=200`
   - `action.type="markup_percent"`, `value=12.0`
   - `notes="seed_p12_agency1_markup"`

Semantik:

- Agency1 → ~%12 markup (priority 200 kuralı kazanır)
- Başka acente → ~%10 markup (default hotel kuralı devreye girer)

### 3.2. UI Üzerinden Fiyat Farkını Gözlemlemek (Opsiyonel)

1. `agency1@demo.test` ile `/app/agency/hotels` ekranında belli bir tarih/otel
   için arama yapın.
2. Seed’de ikinci acente ve kullanıcı varsa, Demo Acente B ile aynı aramayı
   tekrarlayın.
3. Aynı üründe (otel, tarih, occupancy) **Demo Acente A için fiyat biraz daha
   yüksek** olmalı.

UI’de tam oran yerine sadece fiyat farkı gösterildiği için, oranı terminalde
kanıtlayacağız.

### 3.3. API ile sell/net Oranını Kanıtlamak

`P0.3_demo_script.md` içindeki **5. P1.2 Rule-based Pricing – Agency Bazlı
Markup Farkı** bölümündeki komutları kullanabilirsiniz; özetle:

- Admin token al (`ADMIN_TOKEN`).
- Mongo’dan `organization_id`, Demo Acente A/B id’leri, bir `product_id` ve
  `date` çek.
- Ardından backend testini çalıştırın:

```bash
cd /app/backend
pytest tests/test_quote_pricing_uses_rules.py -q
```

Beklenti:

- Demo Acente A (agency1) için ilk offer’da `sell/net ≈ 1.12` (12% markup)
- Demo Acente B için aynı ürün ve tarihte `sell/net ≈ 1.10` (10% markup)

Mesaj:

> "Aynı ürün ve tarihte, yalnızca agency_context değişerek fiyat farkı
>  oluşuyor; bu fark P1.2 pricing_rules motorunun agency + product + date
>  bazlı markup kurallarından geliyor."

---

## 4. Troubleshooting (Kısa Rehber)

### 4.1. TRY Booking Çıkmıyorsa

- `agencies.settings.selling_currency`:
  - Demo Acente A için `"TRY"` olmalı.
- `fx_rates`:
  - `base="EUR"`, `quote="TRY"`, `rate_basis="QUOTE_PER_EUR"` içeren en az bir
    kayıt olmalı.
- Booking hala EUR’da oluşuyorsa:
  - Seed’in çalıştığını ve yeni booking’in gerçekten agency1 ile oluşturulduğunu
    doğrulayın.

### 4.2. Markup Farkı Çıkmıyorsa

- `pricing_rules` koleksiyonunu kontrol edin:
  - Default `%10` ve agency1 `%12` kuralları **status="active"** mi?
  - `validity.from <= check_in < validity.to` aralığı içinde misiniz?
  - `scope.product_type="hotel"` ve agency1 kuralında `scope.agency_id` doğru mu?
- Fiyat oranı hala 1.10 civarında ise:
  - Agency1-specific kuralın priority’sinin (200) gerçekten default kuraldan
    (100) büyük olduğundan emin olun.

---

Bu P1 demo runbook’u, P1.1 ve P1.2’yi birlikte, hem UI hem terminal/pytest
üzerinden tekrar edilebilir biçimde kanıtlamak için hazırdır.
