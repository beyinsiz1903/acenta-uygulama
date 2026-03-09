from __future__ import annotations

from typing import Any, Dict, List

HEADER_ALIASES = {
    "date": ["tarih", "date", "gun", "checkin", "check_in", "check-in", "giris"],
    "room_type": ["oda_tipi", "room_type", "room", "oda", "type", "tip"],
    "price": ["fiyat", "price", "tl", "amount", "ucret", "tutar", "rate"],
    "allotment": ["kontenjan", "allotment", "stok", "qty", "adet", "musaitlik", "availability"],
    "stop_sale": ["stop_sale", "stop", "kapali", "closed", "satis_durdur"],
    "hotel_name": ["otel", "hotel", "otel_adi", "hotel_name", "name", "ad"],
    "city": ["sehir", "city", "il", "bolge", "location"],
    "country": ["ulke", "country"],
    "description": ["aciklama", "description", "desc", "not"],
    "stars": ["yildiz", "stars", "star", "kategori"],
    "phone": ["telefon", "phone", "tel"],
    "email": ["email", "e-posta", "eposta", "mail"],
    "address": ["adres", "address"],
    "image_url": ["resim", "image", "image_url", "foto", "gorsel"],
}

INVENTORY_FIELD_LABELS = {
    "date": "Tarih",
    "room_type": "Oda Tipi",
    "price": "Fiyat",
    "allotment": "Kontenjan",
    "stop_sale": "Stop Sale",
    "hotel_name": "Otel",
    "city": "Şehir",
    "country": "Ülke",
    "description": "Açıklama",
    "stars": "Yıldız",
    "phone": "Telefon",
    "email": "E-posta",
    "address": "Adres",
    "image_url": "Görsel URL",
}

INVENTORY_REQUIRED_FIELDS = ["date", "room_type", "price", "allotment"]
INVENTORY_OPTIONAL_FIELDS = [
    "stop_sale",
    "hotel_name",
    "city",
    "country",
    "description",
    "stars",
    "phone",
    "email",
    "address",
    "image_url",
]

RESERVATION_WRITEBACK_HEADERS = [
    "Kayit Tipi",
    "Kayit ID",
    "Durum",
    "Misafir Ad Soyad",
    "Giris Tarihi",
    "Cikis Tarihi",
    "Kisi Sayisi",
    "Oda Tipi",
    "Tutar",
    "Para Birimi",
    "Kanal",
    "Islem Tarihi",
    "Acenta / Not",
]


def _normalize_header(value: str) -> str:
    return str(value or "").strip().casefold().replace(" ", "")


def _auto_detect_mapping(headers: List[str]) -> Dict[str, str]:
    normalized_headers = [header.lower().strip().replace(" ", "_") for header in headers]
    mapping: Dict[str, str] = {}
    for field, aliases in HEADER_ALIASES.items():
        for index, normalized_header in enumerate(normalized_headers):
            if normalized_header in aliases or any(alias in normalized_header for alias in aliases):
                mapping[headers[index]] = field
                break
    return mapping


def get_reservation_writeback_headers() -> List[str]:
    return list(RESERVATION_WRITEBACK_HEADERS)


def validate_inventory_headers(headers: List[str]) -> Dict[str, Any]:
    detected_mapping = _auto_detect_mapping(headers)
    detected_fields = set(detected_mapping.values())
    missing_required_fields = [
        field for field in INVENTORY_REQUIRED_FIELDS if field not in detected_fields
    ]
    optional_detected_fields = [
        field for field in INVENTORY_OPTIONAL_FIELDS if field in detected_fields
    ]
    recognized_headers = [header for header in headers if header in detected_mapping]
    unrecognized_headers = [header for header in headers if header not in detected_mapping]

    return {
        "valid": len(missing_required_fields) == 0,
        "required_fields": [
            {"field": field, "label": INVENTORY_FIELD_LABELS[field]}
            for field in INVENTORY_REQUIRED_FIELDS
        ],
        "optional_fields": [
            {"field": field, "label": INVENTORY_FIELD_LABELS[field]}
            for field in INVENTORY_OPTIONAL_FIELDS
        ],
        "missing_required_fields": missing_required_fields,
        "missing_required_labels": [
            INVENTORY_FIELD_LABELS[field] for field in missing_required_fields
        ],
        "detected_mapping": detected_mapping,
        "detected_fields": sorted(detected_fields),
        "optional_detected_fields": optional_detected_fields,
        "recognized_headers": recognized_headers,
        "unrecognized_headers": unrecognized_headers,
    }


def headers_match_expected(headers: List[str], expected_headers: List[str]) -> bool:
    normalized_actual = [_normalize_header(header) for header in headers if str(header or "").strip()]
    normalized_expected = [_normalize_header(header) for header in expected_headers]
    return normalized_actual == normalized_expected


def get_sheet_templates_payload() -> Dict[str, Any]:
    return {
        "template_version": "v1",
        "checklist": [
            "Google Service Account JSON tanımlanmalı veya admin panelinden kaydedilmeli.",
            "Ana veri sayfasında en az Tarih, Oda Tipi, Fiyat ve Kontenjan kolonları bulunmalı.",
            "Write-back için ayrı bir Rezervasyonlar sekmesi kullanılmalı.",
            "Sheet, servis hesabı e-posta adresi ile Editor yetkisiyle paylaşılmalı.",
        ],
        "inventory_sync": {
            "tab_name": "Sheet1",
            "required_fields": [
                {"field": field, "label": INVENTORY_FIELD_LABELS[field]}
                for field in INVENTORY_REQUIRED_FIELDS
            ],
            "optional_fields": [
                {"field": field, "label": INVENTORY_FIELD_LABELS[field]}
                for field in INVENTORY_OPTIONAL_FIELDS
            ],
            "sample_headers": [
                "Tarih",
                "Oda Tipi",
                "Fiyat",
                "Kontenjan",
                "Stop Sale",
                "Otel",
                "Şehir",
            ],
        },
        "reservation_writeback": {
            "tab_name": "Rezervasyonlar",
            "headers": get_reservation_writeback_headers(),
            "sample_row": {
                "Kayit Tipi": "reservation_created",
                "Kayit ID": "RSV-2026-001",
                "Durum": "pending",
                "Misafir Ad Soyad": "Ayşe Yılmaz",
                "Giris Tarihi": "2026-04-10",
                "Cikis Tarihi": "2026-04-14",
                "Kisi Sayisi": "2",
                "Oda Tipi": "Deluxe",
                "Tutar": "18500",
                "Para Birimi": "TRY",
                "Kanal": "b2b",
                "Islem Tarihi": "2026-03-09T10:30:00+03:00",
                "Acenta / Not": "Mavi Tur / Erken rezervasyon",
            },
        },
        "required_service_account_fields": [
            "type",
            "project_id",
            "private_key",
            "client_email",
            "token_uri",
        ],
    }