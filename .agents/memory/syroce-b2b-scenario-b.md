---
name: Syroce B2B Scenario B integration
description: The locked contract for the agency-side Syroce PMS B2B integration (separate Replit project model).
---

# Syroce B2B — Scenario B (LOCKED contract)

The agency-automation app talks to the authoritative Syroce PMS B2B backend as a
channel-manager-style client. This is the DEFAULT scenario: the agency runs in a
**separate Replit project**, so it cannot reach the PMS Redis.

**Why:** a separate project has no shared Redis/network, so Scenario A's
Redis-Streams ARI consumer is impossible. The PMS is authoritative; on conflict
the PMS wins.

**How to apply (the non-obvious constraints):**
- Security is **X-API-Key only** — no mTLS, no IP allowlist. Do not add them.
- Real-time = **inbound webhook subscription + REST polling** into a local
  last-write-wins table. There are NO Redis Streams anywhere in this path.
- The API key is obtained through an **approval-gated onboarding** flow
  (connect-request → poll until approved → one-time key), NOT from env. An env
  `SYROCE_AGENCY_API_KEY` exists only as a fallback. Credentials live encrypted
  in a single-doc Mongo store, never returned to clients, never logged.
- Polling self-gates: dormant until connected AND polling enabled; it must never
  raise into the event loop (log + back off instead).
- Inbound webhook receiver is mounted PUBLIC (no JWT) — the PMS authenticates by
  HMAC-signing the body with the secret we registered; verify constant-time and
  **fail closed** when no secret is set.
- Old env secrets `SYROCE_AGENCY_API_KEY/AGENCY_ID/REDIS_URL` from the earlier
  Scenario-A attempt are OBSOLETE under Scenario B — leave them blank. The crypto
  store needs `SYROCE_KEY_ENCRYPTION_KEY` (Fernet) for at-rest encryption.
- Do NOT disturb the separate existing marketplace proxy
  (`app/services/syroce/agent.py` + `syroce_marketplace.py`) — different feature.
