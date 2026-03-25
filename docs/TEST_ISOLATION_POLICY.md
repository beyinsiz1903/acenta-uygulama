# Test Suite İzolasyon Kuralları ve Politikası

## Genel Kurallar

### 1. Veritabanı İzolasyonu
- Her test fonksiyonu kendi izole veritabanını alır (`agentis_test_{uuid}`)
- Test sonrası veritabanı otomatik silinir
- `core_db_routing` autouse fixture ile `get_db()` test DB'ye yönlendirilir
- **Kural:** Testler asla global veritabanı durumuna güvenmemeli

### 2. Fixture İzolasyonu
- Tüm ana fixture'lar `function` scope'da çalışır
- `session` scope'lu fixture'lar yalnızca sabit yapılandırma için kullanılır
- Login fixture'ları (`admin_token`, `agency_token`) retry mekanizmasına sahiptir
- **Kural:** Yoğun yük altında geçici hatalar için fixture'lara retry eklenmeli

### 3. Test Sırası Bağımsızlığı  
- Testler herhangi bir sırada çalışabilmeli
- Bir testin başarısı, önceki testin durumuna bağlı olmamalı
- **Kural:** Her test kendi verilerini seed eder, önceki test verilerine güvenmez

### 4. Koleksiyon Temizliği
- `supplier_health` gibi paylaşılan koleksiyonlarda:
  - Birden fazla test aynı `org_id + supplier_code` ile kayıt eklerse
  - `find_one` yanlış kaydı bulabilir
- **Kural:** Test öncesi ilgili koleksiyonları temizle veya benzersiz key'ler kullan

### 5. Audit Log Doğrulama
- Yoğun yük altında audit log yazımı gecikebilir
- **Kural:** Audit log assertion'ları retry loop ile yapılmalı
- DB state kontrolü (primary assertion) + audit log kontrolü (secondary)

## Rerun Politikası

### Otomatik Rerun Edilen Hatalar
Aşağıdaki exception türleri otomatik 2 kez tekrar edilir:
- `AutoReconnect` — MongoDB bağlantı kaybı
- `ConnectionResetError` — TCP bağlantı kopması
- `ServerSelectionTimeoutError` — MongoDB sunucu bulunamadı
- `TimeoutError` — Genel timeout
- `OSError` — İşletim sistemi seviyesi hata

### Flaky Test İşaretleme
- Bilinen flaky testler `@pytest.mark.xfail(reason="...")` ile işaretlenir
- Flaky testler `known_flaky` marker'ı taşır
- Hedef: Sıfır known_flaky test

## Test İstatistikleri (2026-02)

| Metrik | Değer |
|--------|-------|
| Toplam Test | 2476 |
| Geçen (passed) | 680 |
| Atlanan (skipped) | 1787 |
| Beklenen Hata (xfail) | 8 |
| Başarısız (failed) | 0 |
| Hata (error) | 0 |
| Rerun Gerekli | 1 |

## CI Komutları

```bash
# Tam test suite
cd backend && pytest

# Tek dosya
pytest tests/test_booking_*.py

# Belirli marker
pytest -m "exit_sprint1"

# Coverage ile
pytest --cov=app --cov-report=term-missing
```
