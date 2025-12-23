# E2E (Playwright) — Agency Booking Smoke

## Gereksinimler
- Node 18+
- Playwright (repo'da yüklü olmalı)

## Env
Repo root'a `.env.e2e` oluşturun ve `.env.e2e.example`'ı baz alın.

Zorunlu değişkenler:
- E2E_BASE_URL
- AGENCY_EMAIL
- AGENCY_PASSWORD
- TEST_HOTEL_SEARCH_URL
- TEST_CONFIRMED_BOOKING_ID

## Çalıştırma

Sadece bu spec:
```bash
npx playwright test tests/e2e/agency-booking.spec.ts
```

UI ile:

```bash
npx playwright test tests/e2e/agency-booking.spec.ts --ui
```

## Notlar

* TEST_HOTEL_SEARCH_URL ve TEST_CONFIRMED_BOOKING_ID yoksa ilgili testler `skip` olur.
* Clipboard doğrulaması "best-effort" yapılır: bazı headless/secure koşullarda clipboard okunamayabilir.
* Seçiciler tamamen `data-testid` sözleşmesine dayanır.
