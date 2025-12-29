from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class ChannelTestResult:
  """Result object for channel provider test_connection.

  This is intentionally lightweight and internal to the backend.  It is not
  exposed as an API schema directly – routers convert it to HTTP responses
  and run documents.
  """

  ok: bool
  code: Optional[str] = None
  message: str = ""
  meta: Dict[str, Any] = field(default_factory=dict)



@dataclass
class ChannelAriResult:
  """Result object for ARI (availability/rates/inventory) reads.

  Similar to ChannelTestResult but carries an opaque data payload that the
  caller can log or inspect. In this phase we do not normalize the schema; we
  just transport provider-specific JSON inside `data`.
  """

  ok: bool
  code: Optional[str] = None
  message: str = ""
  data: Dict[str, Any] = field(default_factory=dict)
  meta: Dict[str, Any] = field(default_factory=dict)
