# Route Inventory Parity Playbook

## Amaç
- Preview / staging / prod runtime'larının aynı router registry davranışını ürettiğini görünür ve ölçülebilir hale getirmek.
- `/api/v1` rollout'larında sadece "route çalışıyor mu" değil, **kaç route var / kaç tanesi v1 / kaç tanesi legacy** sorularını da standartlaştırmak.

## Üretilen artifact'ler
- `route_inventory.json`
- `route_inventory_summary.json`
- `route_inventory_diff.json`

`route_inventory_summary.json` minimum olarak şu alanları taşır:
- `route_count`
- `v1_count`
- `legacy_count`
- `compat_required_count`
- `inventory_hash`
- `environment`

## Runtime container içinde export
Her ortamda API container içinde aynı komut çalıştırılmalı:

```bash
cd /app/backend
python scripts/export_route_inventory.py \
  --destination /tmp/route_inventory.${APP_ENV_NAME}.json \
  --summary-out /tmp/route_inventory_summary.${APP_ENV_NAME}.json \
  --environment "${APP_ENV_NAME}"
```

Örnek environment etiketleri:
- `preview`
- `staging`
- `prod`

## CI runner içinde diff üretimi
Base snapshot ile current snapshot karşılaştırması:

```bash
cd /app/backend
python scripts/diff_route_inventory.py \
  /tmp/route_inventory.previous.json \
  /tmp/route_inventory.current.json \
  --format json > /tmp/route_inventory_diff.json
```

## Ortamlar arası parity kontrolü
Preview / staging / prod summary artifact'leri toplandıktan sonra:

```bash
cd /app/backend
python scripts/check_route_inventory_parity.py \
  preview=/tmp/route_inventory_summary.preview.json \
  staging=/tmp/route_inventory_summary.staging.json \
  prod=/tmp/route_inventory_summary.prod.json \
  --format text \
  --fail-on-mismatch
```

Başarılı parity için:
- `route_count` aynı olmalı
- `v1_count` aynı olmalı
- `legacy_count` aynı olmalı
- mümkünse `inventory_hash` da aynı olmalı

## Operasyonel checklist
1. API runtime `app.bootstrap.api_app:create_app` ile boot ediyor mu?
2. Boot sonrası `route_inventory.json` ve `route_inventory_summary.json` oluşuyor mu?
3. Container içinde `export_route_inventory.py` elle tekrar çalışıyor mu?
4. CI `diff_route_inventory.py` çıktısını artifact olarak saklıyor mu?
5. Preview / staging / prod summary dosyaları parity check'ten geçiyor mu?

## Not
Bu playbook, route parity'yi deploy sonrası gözle doğrulanabilir hale getirir. Legacy kaldırma kararları, parity uzun süre stabil kaldıktan sonra verilmelidir.