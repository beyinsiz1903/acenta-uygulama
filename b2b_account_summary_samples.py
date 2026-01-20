#!/usr/bin/env python3
"""
B2B Account Summary Endpoint - Sample Response Documentation

Bu dosya, B2B account summary endpoint'inin örnek response'larını içerir.
"""

import json

# Sample Response 1: Ledger-based data (agency1@demo.test)
SAMPLE_LEDGER_BASED_RESPONSE = {
    "total_debit": 0.0,
    "total_credit": 0.0,
    "net": -2300.8,
    "currency": "EUR",
    "recent": [],
    "data_source": "ledger_based",
    "exposure_eur": 2300.8,
    "credit_limit": 10000.0,
    "soft_limit": 9000,
    "payment_terms": "NET14",
    "status": "ok",
    "aging": None
}

# Sample Response 2: Derived from bookings (hypothetical agency without finance data)
SAMPLE_BOOKINGS_DERIVED_RESPONSE = {
    "total_debit": 1250.0,
    "total_credit": 0.0,
    "net": -1250.0,
    "currency": "EUR",
    "recent": [
        {
            "id": "677e1234567890abcdef1234",
            "date": "2026-01-15T10:30:00",
            "type": "booking",
            "description": "BK123ABC",
            "direction": "debit",
            "amount": 750.0,
            "currency": "EUR",
            "ref_id": "677e1234567890abcdef1234"
        },
        {
            "id": "677e1234567890abcdef5678",
            "date": "2026-01-12T14:20:00",
            "type": "booking",
            "description": "BK456DEF",
            "direction": "debit",
            "amount": 500.0,
            "currency": "EUR",
            "ref_id": "677e1234567890abcdef5678"
        }
    ],
    "data_source": "derived_from_bookings",
    "exposure_eur": 0.0,
    "credit_limit": None,
    "soft_limit": None,
    "payment_terms": None,
    "status": "ok",
    "aging": None
}

# Sample Response 3: Near limit scenario
SAMPLE_NEAR_LIMIT_RESPONSE = {
    "total_debit": 0.0,
    "total_credit": 0.0,
    "net": -9200.0,
    "currency": "EUR",
    "recent": [],
    "data_source": "ledger_based",
    "exposure_eur": 9200.0,
    "credit_limit": 10000.0,
    "soft_limit": 9000.0,
    "payment_terms": "NET14",
    "status": "near_limit",
    "aging": None
}

# Sample Response 4: Over limit scenario
SAMPLE_OVER_LIMIT_RESPONSE = {
    "total_debit": 0.0,
    "total_credit": 0.0,
    "net": -10500.0,
    "currency": "EUR",
    "recent": [],
    "data_source": "ledger_based",
    "exposure_eur": 10500.0,
    "credit_limit": 10000.0,
    "soft_limit": 9000.0,
    "payment_terms": "NET14",
    "status": "over_limit",
    "aging": None
}

# Error Response 1: Unauthorized (401)
SAMPLE_UNAUTHORIZED_ERROR = {
    "detail": "Giriş gerekli"
}

# Error Response 2: Invalid Token (401)
SAMPLE_INVALID_TOKEN_ERROR = {
    "detail": "Geçersiz token"
}

# Error Response 3: Forbidden (403) - Non-agency user
SAMPLE_FORBIDDEN_ERROR = {
    "error": {
        "code": "forbidden",
        "message": "Only agency users can view B2B account summary",
        "details": {}
    }
}

def print_all_samples():
    """Print all sample responses in a formatted way"""
    
    print("=" * 80)
    print("B2B ACCOUNT SUMMARY ENDPOINT - SAMPLE RESPONSES")
    print("=" * 80)
    
    samples = [
        ("1. Ledger-based Response (agency1@demo.test)", SAMPLE_LEDGER_BASED_RESPONSE),
        ("2. Bookings-derived Response (hypothetical)", SAMPLE_BOOKINGS_DERIVED_RESPONSE),
        ("3. Near Limit Response", SAMPLE_NEAR_LIMIT_RESPONSE),
        ("4. Over Limit Response", SAMPLE_OVER_LIMIT_RESPONSE),
        ("5. Unauthorized Error (401)", SAMPLE_UNAUTHORIZED_ERROR),
        ("6. Invalid Token Error (401)", SAMPLE_INVALID_TOKEN_ERROR),
        ("7. Forbidden Error (403)", SAMPLE_FORBIDDEN_ERROR),
    ]
    
    for title, response in samples:
        print(f"\n{title}:")
        print("-" * len(title))
        print(json.dumps(response, indent=2, ensure_ascii=False))
    
    print("\n" + "=" * 80)
    print("FIELD EXPLANATIONS")
    print("=" * 80)
    
    explanations = {
        "total_debit": "Toplam borç tutarı (pozitif değer)",
        "total_credit": "Toplam alacak tutarı (pozitif değer)",
        "net": "Net bakiye (credit - debit, negatif = borç)",
        "currency": "Para birimi (EUR, USD, TRY vb.)",
        "recent": "Son hareketler listesi (max 20 item)",
        "data_source": "'ledger_based' veya 'derived_from_bookings'",
        "exposure_eur": "EUR cinsinden risk tutarı (ledger_based için)",
        "credit_limit": "Kredi limiti (null olabilir)",
        "soft_limit": "Yumuşak limit (null olabilir)",
        "payment_terms": "Ödeme koşulları (NET14, NET30 vb.)",
        "status": "'ok', 'near_limit', 'over_limit'",
        "aging": "Yaşlandırma bilgisi (şu anda null)"
    }
    
    for field, explanation in explanations.items():
        print(f"{field:15} : {explanation}")

if __name__ == "__main__":
    print_all_samples()