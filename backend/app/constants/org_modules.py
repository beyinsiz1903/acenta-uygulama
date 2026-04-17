from __future__ import annotations

ORG_MODULE_REGISTRY = [
    {
        "group": "OPERASYON",
        "modules": [
            {"key": "orders", "label": "Siparişler", "description": "Sipariş yönetimi ve takibi"},
            {"key": "hotels", "label": "Oteller", "description": "Otel envanter ve oda yönetimi"},
            {"key": "tours", "label": "Turlar", "description": "Tur paketi oluşturma ve yönetimi"},
            {"key": "transfers", "label": "Transferler", "description": "Havalimanı ve şehir içi transfer yönetimi"},
            {"key": "flights", "label": "Uçuşlar", "description": "Uçuş arama ve rezervasyon"},
            {"key": "villas", "label": "Villalar", "description": "Villa envanter, fiyat ve müsaitlik yönetimi"},
            {"key": "activities", "label": "Aktiviteler", "description": "Tur, gezi, deneyim ve aktivite yönetimi"},
            {"key": "guides", "label": "Rehberler", "description": "Rehber atama ve takibi"},
            {"key": "vehicles", "label": "Araçlar", "description": "Araç filosu yönetimi"},
            {"key": "calendar", "label": "Takvim", "description": "Operasyonel takvim görünümü"},
            {"key": "visa", "label": "Vize Takip", "description": "Vize başvuru takip sistemi"},
            {"key": "insurance", "label": "Sigorta", "description": "Seyahat sigortası yönetimi"},
        ],
    },
    {
        "group": "REZERVASYONLAR & FİNANS",
        "modules": [
            {"key": "reservations", "label": "Rezervasyonlar", "description": "Rezervasyon listesi ve yönetimi"},
            {"key": "refunds", "label": "İadeler", "description": "İade talepleri ve takibi"},
            {"key": "exposure", "label": "Açık Bakiye", "description": "Açık bakiye raporları"},
            {"key": "payment_gateways", "label": "Ödeme Altyapıları", "description": "İyzico, PayTR vb. ödeme entegrasyonları"},
            {"key": "settlements", "label": "Mutabakat", "description": "Tedarikçi mutabakat ve hesap kapatma"},
        ],
    },
    {
        "group": "MÜŞTERİ & SATIŞ",
        "modules": [
            {"key": "crm", "label": "CRM / Müşteriler", "description": "Müşteri veritabanı ve ilişki yönetimi"},
            {"key": "agencies", "label": "Acentalar", "description": "Alt acente ve bayi yönetimi"},
            {"key": "partners", "label": "İş Ortakları", "description": "Partner ağı ve iş birliği"},
            {"key": "b2b", "label": "B2B Kanal", "description": "B2B pazar yeri ve acente ağı"},
        ],
    },
    {
        "group": "FİYATLANDIRMA",
        "modules": [
            {"key": "pricing", "label": "Fiyat Yönetimi", "description": "Fiyat kuralları ve dinamik fiyatlama"},
            {"key": "campaigns", "label": "Kampanyalar", "description": "Kampanya ve kupon yönetimi"},
        ],
    },
    {
        "group": "RAPORLAMA",
        "modules": [
            {"key": "analytics", "label": "Gelir Analizi", "description": "Gelir ve performans analitiği"},
            {"key": "reporting", "label": "Raporlama", "description": "Özel rapor oluşturma"},
            {"key": "exports", "label": "Dışa Aktarma", "description": "Veri dışa aktarma (Excel, CSV)"},
        ],
    },
    {
        "group": "AYARLAR & ENTEGRASYON",
        "modules": [
            {"key": "integrations", "label": "Entegrasyonlar", "description": "Tedarikçi ve API entegrasyonları"},
            {"key": "syroce_marketplace", "label": "Syroce Marketplace", "description": "Syroce PMS Marketplace v1 entegrasyonu (otel arama, rezervasyon, mutabakat)"},
            {"key": "email_templates", "label": "E-posta Şablonları", "description": "E-posta şablon yönetimi"},
            {"key": "customer_portal", "label": "Müşteri Portalı", "description": "Müşteri self-servis portalı"},
            {"key": "branding", "label": "Marka Ayarları", "description": "Logo, renk ve white-label ayarları"},
        ],
    },
]

CORE_MODULES = ["dashboard", "users", "settings"]

ALL_MODULE_KEYS = []
for _g in ORG_MODULE_REGISTRY:
    for _m in _g["modules"]:
        ALL_MODULE_KEYS.append(_m["key"])
ALL_MODULE_KEYS = sorted(set(ALL_MODULE_KEYS))
