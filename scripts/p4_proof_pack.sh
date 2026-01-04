#!/usr/bin/env bash
set -euo pipefail

# ---------------------------
# P4 Proof Pack (Token or CI-login mode)
# ---------------------------
# Required:
#   BACKEND_BASE (no /api) e.g. http://localhost:8001 or https://preview.example.com
#
# Token mode (preferred if tokens already available):
#   SUPER_ADMIN_TOKEN
#   HOTEL_OK_TOKEN
#   HOTEL_WRONG_TOKEN
#
# CI-login mode (if tokens are not set):
#   SUPER_ADMIN_EMAIL, SUPER_ADMIN_PASSWORD
#   HOTEL_WRONG_EMAIL, HOTEL_WRONG_PASSWORD
# Optional (stronger proof - real to_hotel user):
#   HOTEL_OK_EMAIL, HOTEL_OK_PASSWORD
# If HOTEL_OK creds are not provided, script falls back to using SUPER_ADMIN_TOKEN as HOTEL_OK_TOKEN.

# ---------------------------
# Helpers
# ---------------------------
die() { echo "[P4][ERR] $*" >&2; exit 1; }
log() { echo "[P4] $*"; }

require_env() {
  local name="$1"
  local val="${!name:-}"
  [[ -n "$val" ]] || die "Missing required env: $name"
}

# Try linux date then macOS date
date_add_days() {
  local iso_date="$1" # YYYY-MM-DD
  local delta="$2"    # integer, may be negative
  if date -d "$iso_date ${delta} day" "+%Y-%m-%d" >/dev/null 2>&1; then
    date -d "$iso_date ${delta} day" "+%Y-%m-%d"
    return 0
  fi
  # macOS: date -j -f "%Y-%m-%d" "$iso_date" -v+1d "+%Y-%m-%d"
  if date -j -f "%Y-%m-%d" "$iso_date" -v"${delta}"d "+%Y-%m-%d" >/dev/null 2>&1; then
    date -j -f "%Y-%m-%d" "$iso_date" -v"${delta}"d "+%Y-%m-%d"
    return 0
  fi
  die "Unable to compute date arithmetic on this system."
}

json_get() {
  local json="$1"
  local jq_expr="$2"
  echo "$json" | jq -r "$jq_expr"
}

login_token() {
  local api_base="$1"  # includes /api
  local email="$2"
  local password="$3"
  local resp
  resp="$(curl -fsS -X POST "${api_base}/auth/login" \
    -H "Content-Type: application/json" \
    -d "{\"email\":\"${email}\",\"password\":\"${password}\"}")" || return 1
  local tok
  tok="$(json_get "$resp" '.access_token')" || return 1
  [[ "$tok" != "null" && -n "$tok" ]] || return 1
  echo "$tok"
}

# ---------------------------
# Main
# ---------------------------
require_env BACKEND_BASE

API_BASE="${BACKEND_BASE%/}/api"

# Determine auth mode
if [[ -n "${SUPER_ADMIN_TOKEN:-}" && -n "${HOTEL_WRONG_TOKEN:-}" ]]; then
  # Token mode
  log "Auth mode: token"
  : "${HOTEL_OK_TOKEN:=${SUPER_ADMIN_TOKEN}}" # allow existing fallback behavior
else
  # CI-login mode
  log "Auth mode: login"
  require_env SUPER_ADMIN_EMAIL
  require_env SUPER_ADMIN_PASSWORD
  require_env HOTEL_WRONG_EMAIL
  require_env HOTEL_WRONG_PASSWORD

  SUPER_ADMIN_TOKEN="$(login_token "$API_BASE" "$SUPER_ADMIN_EMAIL" "$SUPER_ADMIN_PASSWORD")" \
    || die "Super admin login failed"
  HOTEL_WRONG_TOKEN="$(login_token "$API_BASE" "$HOTEL_WRONG_EMAIL" "$HOTEL_WRONG_PASSWORD")" \
    || die "Wrong-hotel user login failed"

  if [[ -n "${HOTEL_OK_EMAIL:-}" && -n "${HOTEL_OK_PASSWORD:-}" ]]; then
    HOTEL_OK_TOKEN="$(login_token "$API_BASE" "$HOTEL_OK_EMAIL" "$HOTEL_OK_PASSWORD")" \
      || die "Hotel OK user login failed"
  else
    # fallback: super_admin can post outcome (allowed) — still passes settlement invariants + 403 negative.
    HOTEL_OK_TOKEN="$SUPER_ADMIN_TOKEN"
    log "HOTEL_OK creds not provided; using SUPER_ADMIN_TOKEN for positive outcome call."
  fi
fi

# Ensure jq exists
command -v jq >/dev/null 2>&1 || die "jq is required"

log "Seeding match proxy..."
SEED_RESP="$(curl -fsS -X POST "${API_BASE}/dev/seed/match-proxy" \
  -H "Authorization: Bearer ${SUPER_ADMIN_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{}')" || die "Seed endpoint failed. Is ENABLE_DEV_ROUTERS=true?"

MATCH_ID="$(json_get "$SEED_RESP" '.match_id')"
TO_HOTEL_ID="$(json_get "$SEED_RESP" '.to_hotel_id')"
CREATED_AT="$(json_get "$SEED_RESP" '.created_at')"

[[ -n "$MATCH_ID" && "$MATCH_ID" != "null" ]] || die "Seed response missing match_id"
[[ -n "$TO_HOTEL_ID" && "$TO_HOTEL_ID" != "null" ]] || die "Seed response missing to_hotel_id"
[[ -n "$CREATED_AT" && "$CREATED_AT" != "null" ]] || die "Seed response missing created_at"

CREATED_DATE="${CREATED_AT%%T*}"
FROM_DATE="$(date_add_days "$CREATED_DATE" -1)"
TO_DATE="$(date_add_days "$CREATED_DATE" 1)"

log "Seeded match_id=$MATCH_ID, to_hotel_id=$TO_HOTEL_ID, window $FROM_DATE -> $TO_DATE"

log "Posting outcome as correct hotel user..."
OUTCOME_RESP="$(curl -fsS -X POST "${API_BASE}/matches/${MATCH_ID}/outcome" \
  -H "Authorization: Bearer ${HOTEL_OK_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"outcome":"arrived","note":"p4-proof"}')" || die "Outcome POST failed (expected 2xx)"

echo "Outcome response: ${OUTCOME_RESP}"

log "Verifying drilldown entry..."
DRILL_RESP="$(curl -fsS "${API_BASE}/reports/match-risk/drilldown?from=${FROM_DATE}&to=${TO_DATE}&to_hotel_id=${TO_HOTEL_ID}")" \
  || die "Drilldown request failed"

MATCH_ROW="$(echo "$DRILL_RESP" | jq -c --arg mid "$MATCH_ID" '.items[] | select(.match_id == $mid)' | head -n 1 || true)"
[[ -n "$MATCH_ROW" ]] || die "Drilldown did not contain match_id=$MATCH_ID"

OUTCOME_VAL="$(echo "$MATCH_ROW" | jq -r '.outcome')"
[[ "$OUTCOME_VAL" != "unknown" ]] || die "Drilldown outcome is still unknown (expected arrived/not_arrived/...)"
log "Drilldown OK for match_id=$MATCH_ID with outcome=$OUTCOME_VAL"

log "Verifying summary invariants..."
SUMMARY_RESP="$(curl -fsS "${API_BASE}/reports/match-risk?from=${FROM_DATE}&to=${TO_DATE}&group_by=to_hotel")" \
  || die "Summary request failed"

SUMMARY_ROW="$(echo "$SUMMARY_RESP" | jq -c --arg hid "$TO_HOTEL_ID" '.items[] | select(.to_hotel_id == $hid)' | head -n 1 || true)"
[[ -n "$SUMMARY_ROW" ]] || die "Summary did not contain to_hotel_id=$TO_HOTEL_ID"

matches_total="$(echo "$SUMMARY_ROW" | jq -r '.matches_total')"
outcome_known="$(echo "$SUMMARY_ROW" | jq -r '.outcome_known')"
outcome_missing="$(echo "$SUMMARY_ROW" | jq -r '.outcome_missing')"
not_arrived="$(echo "$SUMMARY_ROW" | jq -r '.not_arrived')"
not_arrived_rate="$(echo "$SUMMARY_ROW" | jq -r '.not_arrived_rate')"

# Basic numeric checks (integers)
[[ "$matches_total" -gt 0 ]] || die "Invariant failed: matches_total must be > 0"
[[ $((outcome_known + outcome_missing)) -eq "$matches_total" ]] || die "Invariant failed: matches_total != outcome_known + outcome_missing"
[[ "$not_arrived" -ge 0 ]] || die "Invariant failed: not_arrived < 0"
[[ "$not_arrived" -le "$outcome_known" ]] || die "Invariant failed: not_arrived > outcome_known"

# Rate check using python (avoid bash float pitfalls)
python3 - <<PY
r = float("$not_arrived_rate")
if not (0.0 <= r <= 1.0):
    raise SystemExit(1)
PY
log "Summary invariants OK for to_hotel_id=$TO_HOTEL_ID"

log "Negative test: wrong hotel user should get 403..."
TMP_ERR="$(mktemp)"
WRONG_CODE="$(curl -sS -o "$TMP_ERR" -w "%{http_code}" \
  -X POST "${API_BASE}/matches/${MATCH_ID}/outcome" \
  -H "Authorization: Bearer ${HOTEL_WRONG_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"outcome":"arrived","note":"p4-proof-wrong"}' || true)"

if [[ "$WRONG_CODE" != "403" ]]; then
  echo "[P4][ERR] Expected 403, got ${WRONG_CODE}. Response body:" >&2
  cat "$TMP_ERR" >&2
  rm -f "$TMP_ERR"
  exit 1
fi
rm -f "$TMP_ERR"
log "Negative test OK: wrong hotel user receives 403"

log "All checks passed. P4 proof pack successful."
exit 0
