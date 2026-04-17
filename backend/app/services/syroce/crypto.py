"""Fernet-based encryption for Syroce per-agency API keys."""
from __future__ import annotations

import logging
import os
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _fernet() -> Fernet:
    raw = os.environ.get("SYROCE_KEY_ENCRYPTION_KEY", "").strip()
    if not raw:
        raise RuntimeError(
            "SYROCE_KEY_ENCRYPTION_KEY ortam değişkeni tanımlı değil. "
            "Bir Fernet anahtarı üretin: "
            "python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
        )
    try:
        return Fernet(raw.encode("utf-8"))
    except Exception as e:
        raise RuntimeError(
            "SYROCE_KEY_ENCRYPTION_KEY geçersiz Fernet anahtarı (32 byte url-safe base64 olmalı)."
        ) from e


def encrypt_key(plaintext: str) -> str:
    """Encrypt a raw API key. Returns base64 ciphertext (str)."""
    if not plaintext:
        raise ValueError("encrypt_key: boş anahtar şifrelenemez.")
    return _fernet().encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt_key(ciphertext: str) -> str:
    """Decrypt a stored API key."""
    if not ciphertext:
        raise ValueError("decrypt_key: boş şifreli değer çözülemez.")
    try:
        return _fernet().decrypt(ciphertext.encode("utf-8")).decode("utf-8")
    except InvalidToken as e:
        # Do NOT log the ciphertext — could leak info.
        logger.error("Syroce key decryption failed (InvalidToken).")
        raise RuntimeError(
            "Syroce API key çözülemedi — şifreleme anahtarı değişmiş olabilir."
        ) from e
