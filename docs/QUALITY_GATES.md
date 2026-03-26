# Quality Gates — Syroce CI/CD

## Pipeline Aşamaları

| # | Aşama | Fail Durumu | Blocker? |
|---|-------|-------------|----------|
| 1 | **Lint & Static Analysis** | Ruff E/F/W hatası veya ESLint error | ✅ Evet |
| 2 | **Architecture & Scope Guards** | Cross-domain import, orphan router, duplicate ownership | ✅ Evet |
| 3 | **Security Scan** | Kritik CVE (pip-audit, yarn audit) | ⚠️ Uyarı |
| 4 | **Backend Tests + Coverage** | Test failure veya coverage < threshold | ✅ Evet |
| 5 | **Frontend Build** | React/TS derleme hatası | ✅ Evet |
| 6 | **API Contract Tests** | Exit gate veya contract test failure | ✅ Evet |
| 7 | **Quality Summary** | Özet rapor (PR'da görünür) | — |

## Coverage Threshold'ları

### Kademeli Enforcement Stratejisi

Legacy kod nedeniyle başlangıçta düşük threshold kullanıyoruz:

| Seviye | Threshold | Açıklama |
|--------|-----------|----------|
| **Overall** | ≥ 20% | Tüm `app/` kodu. Aşamalı artırılacak. |
| **Kritik Modüller** | ≥ 30% | `booking`, `auth`, `tenant`, `infrastructure` |
| **Uyarı** | < 50% | CI fail etmez ama uyarı verir |

### Hedef Artırma Takvimi

| Tarih | Overall | Kritik |
|-------|---------|--------|
| Başlangıç | 20% | 30% |
| +1 ay | 30% | 40% |
| +3 ay | 50% | 60% |
| +6 ay | 70% | 80% |

Threshold değerleri: `backend/scripts/check_coverage_threshold.py`

## Architecture Guard

**Test dosyası**: `tests/test_architecture_guard.py`

### Kurallar

1. **Cross-domain import yasağı**: `modules/X/` altındaki dosyalar `modules/Y/`'den import edemez
2. **İstisna**: `__init__.py` dosyaları (router aggregation), `modules/tenant` (security boundary)
3. **Paylaşılan katmanlar**: `app.config`, `app.db`, `app.auth`, `app.services`, `app.infrastructure` serbest

### Fail durumu
- Cross-domain import tespit edildiğinde CI kırmızı olur
- Fix: Service layer veya event-driven iletişim kullanılmalı

## Scope & Dependency Audit

**Test dosyası**: `tests/test_scope_audit.py`

### Denetlenen Kurallar

| # | Kural | Enforcement |
|---|-------|-------------|
| 1 | İmport edilen router dosyaları gerçekten var mı? | ✅ Fail |
| 2 | Hiçbir router birden fazla domain'e ait olmamalı | ✅ Fail |
| 3 | Orphan router (hiçbir modül tarafından import edilmeyen) | ⚠️ Uyarı |
| 4 | Registry'de en fazla 4 legacy import | ✅ Fail |
| 5 | Her modül `__init__.py` docstring'e sahip olmalı | ✅ Fail |
| 6 | Beklenen 16 domain modülü mevcut olmalı | ✅ Fail |
| 7 | Service layer FastAPI import etmemeli | ⚠️ Uyarı |

## Lokal Çalıştırma

```bash
# Tüm kalite kapıları
make quality

# Sadece lint
make lint

# Sadece guard testleri
make test-guard

# Sadece scope audit
make test-audit

# Backend testleri + coverage
make test-backend

# Coverage threshold kontrolü
make coverage-check
```

## Hangi Koşulda Build Fail Olur?

1. **Ruff** herhangi bir E/F/W hatası bulursa
2. **ESLint** herhangi bir error verirse (--max-warnings 0)
3. **Architecture guard** cross-domain import tespit ederse
4. **Scope audit** duplicate ownership veya eksik dosya bulursa
5. **Backend testleri** fail olursa veya coverage threshold'un altında kalırsa
6. **Frontend build** derleme hatası verirse
7. **Contract testleri** fail olursa

## İstisna (Exception) Yönetimi

### Architecture Guard
İstisna eklemek için `test_architecture_guard.py` içindeki `ALLOWED_CROSS_IMPORTS` setine ekle.

### Scope Audit
Bilinen istisna router'lar için `test_scope_audit.py` içindeki `KNOWN_EXCEPTIONS` setine ekle.

### Coverage
Per-file ignore için `pyproject.toml` içindeki `[tool.ruff.lint.per-file-ignores]` bölümünü kullan.
