from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, Iterable


SENSITIVE_KEYS: Iterable[str] = [
    "email",
    "phone",
    "passport",
    "card",
    "cvv",
    "token",
    "document",
    "identity",
    "iban",
]


def _is_sensitive_key(key: str) -> bool:
    lower = key.lower()
    return any(marker in lower for marker in SENSITIVE_KEYS)


def _redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: _redact("***REDACTED***" if _is_sensitive_key(k) else v) for k, v in value.items()}
    if isinstance(value, list):
        return [_redact(v) for v in value]
    if isinstance(value, tuple):
        return tuple(_redact(v) for v in value)
    return value


def redact_sensitive_fields(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Return a deep redacted copy of payload.

    - Does not mutate the original payload.
    - Recursively traverses dict/list/tuple.
    - Any key containing a sensitive marker (case-insensitive, substring)
      is replaced with "***REDACTED***".
    """

    if payload is None:
        return {}
    copied = deepcopy(payload)
    return _redact(copied)
