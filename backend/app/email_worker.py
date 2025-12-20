from __future__ import annotations

import asyncio
import logging

from app.db import get_db
from app.services.email_outbox import dispatch_pending_emails

logger = logging.getLogger("email_worker")


async def email_dispatch_loop() -> None:
  """Background loop to dispatch pending emails periodically."""
  db = await get_db()
  while True:
      try:
          processed = await dispatch_pending_emails(db, limit=10)
          if processed:
              logger.info("Email worker processed %s jobs", processed)
      except Exception as e:  # pragma: no cover
          logger.error("Email worker loop error: %s", e, exc_info=True)

      await asyncio.sleep(5)
