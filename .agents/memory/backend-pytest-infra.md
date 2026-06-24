---
name: Backend pytest infra blocker
description: Why pytest is unreliable in this repl and how to verify backend logic instead.
---

# pytest is unreliable here — verify logic with standalone scripts

Running `pytest` against the backend in this environment is flaky:
- The shared Atlas free-tier cluster is at the **500/500 collection cap**, so any
  DB-touching test errors with "already using 500 collections of 500".
- The FastAPI app import + boot is slow (~60-120s), so even DB-free unit tests
  collect slowly and the runner sometimes returns no output / times out.

**Why:** these are environment limits, not test-logic bugs. Fighting the runner
wastes turns.

**How to apply:**
- For DB-free logic, write a small standalone `asyncio` script run with
  `env PYTHONPATH="$PWD" python script.py` from `backend/` — it imports the
  modules directly, monkeypatches `client.httpx.AsyncClient`, and asserts
  behavior fast and reliably. (Set `client._BACKOFF_BASE=0` /
  `_DEFAULT_RETRY_AFTER=0` to make retry tests instant. Do NOT patch global
  `asyncio.sleep` — it breaks anyio's own event loop.)
- Keep the real pytest files committed (they're correct), but verify via the
  script when the runner won't cooperate.
- Background (`&`) processes started from the bash tool do NOT persist past the
  tool call — run verification synchronously.
- DB-free unit tests live under `tests/unit/` with their own `conftest.py` that
  deliberately avoids the parent harness's DB autouse fixtures.
