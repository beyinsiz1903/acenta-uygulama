"""AES-256-GCM Credential Encryption Service (Faz 2).

Encrypts and decrypts integrator credentials using AES-256-GCM.
Master key is derived from JWT_SECRET environment variable.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import secrets
from typing import Any

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def _get_master_key() -> bytes:
    """Derive a 256-bit master key from JWT_SECRET."""
    secret = os.environ.get("JWT_SECRET", "")
    return hashlib.sha256(secret.encode()).digest()


def encrypt_credentials(credentials: dict[str, Any]) -> str:
    """Encrypt a credentials dict using AES-256-GCM.

    Returns a base64-encoded string containing: nonce + ciphertext + tag
    """
    key = _get_master_key()
    aesgcm = AESGCM(key)
    nonce = secrets.token_bytes(12)  # 96-bit nonce for GCM
    plaintext = json.dumps(credentials).encode("utf-8")
    ciphertext = aesgcm.encrypt(nonce, plaintext, None)
    # Prepend nonce to ciphertext (nonce is 12 bytes)
    encrypted = nonce + ciphertext
    return base64.b64encode(encrypted).decode("ascii")


def decrypt_credentials(encrypted_str: str) -> dict[str, Any]:
    """Decrypt an AES-256-GCM encrypted credentials string.

    Returns the original credentials dict.
    """
    key = _get_master_key()
    aesgcm = AESGCM(key)
    raw = base64.b64decode(encrypted_str)
    nonce = raw[:12]
    ciphertext = raw[12:]
    plaintext = aesgcm.decrypt(nonce, ciphertext, None)
    return json.loads(plaintext.decode("utf-8"))


def mask_credentials(credentials: dict[str, Any]) -> dict[str, str]:
    """Return masked version of credentials for display."""
    masked = {}
    for k, v in credentials.items():
        sv = str(v)
        if k in ("password", "sifre", "secret", "api_key"):
            masked[k] = sv[:2] + "*" * max(len(sv) - 4, 4) + sv[-2:] if len(sv) > 4 else "****"
        elif k in ("username", "kullanici_adi"):
            masked[k] = sv[:3] + "*" * max(len(sv) - 3, 3)
        else:
            masked[k] = sv
    return masked
