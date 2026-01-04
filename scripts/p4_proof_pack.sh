#!/usr/bin/env bash
set -euo pipefail

# P4 proof pack script
# Expected env vars:
#   BACKEND_BASE   - base URL of backend without trailing slash (e.g. https://tourism-booking.preview.emergentagent.com)
#   SUPER_ADMIN_TOKEN - JWT for super_admin user (Bearer token)
#   HOTEL_OK_TOKEN    - JWT for hotel user belonging to to_hotel_id
#   HOTEL_WRONG_TOKEN - JWT for hotel user belonging to a different hotel
#
# This script will:
#   1) Seed a match proxy via /api/dev/seed/match-proxy
#   2) POST outcome as HOTEL_OK_TOKEN and expect 200
#   3) Verify drilldown contains the match with non-unknown outcome
#   4) Verify summary invariants for to_hotel_id
#   5) POST outcome as HOTEL_WRONG_TOKEN and expect 403

if [[ -z "${BACKEND_BASE:-}" ]]; then
  echo "BACKEND_BASE is required" >&2
  exit 1
fi

API_BASE="${BACKEND_BASE%/}/api"

if [[ -z "${SUPER_ADMIN_TOKEN:-}" ]]; then
  echo "SUPER_ADMIN_TOKEN is required" >&2
  exit 1
fi
if [[ -z "${HOTEL_OK_TOKEN:-}" ]]; then
  echo "HOTEL_OK_TOKEN is required" >&2
  exit 1
fi
if [[ -z "${HOTEL_WRONG_TOKEN:-}" ]]; then
  echo "HOTEL_WRONG_TOKEN is required" >&2
  exit 1
fi

# 1) Seed match proxy
echo "[P4] Seeding match proxy..." >&2
SEED_RESP=$(curl -fsS -X POST "${API_BASE}/dev/seed/match-proxy" \
  -H "Authorization: Bearer ${SUPER_ADMIN_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{}')

MATCH_ID=$(echo "${SEED_RESP}" | jq -r '.match_id')
TO_HOTEL_ID=$(echo "${SEED_RESP}" | jq -r '.to_hotel_id')
CREATED_AT=$(echo "${SEED_RESP}" | jq -r '.created_at')

if [[ -z "${MATCH_ID}" || "${MATCH_ID}" == "null" ]]; then
  echo "Failed to obtain match_id from seed response" >&2
  echo "Response: ${SEED_RESP}" >&2
  exit 1
fi

if [[ -z "${TO_HOTEL_ID}" || "${TO_HOTEL_ID}" == "null" ]]; then
  echo "Failed to obtain to_hotel_id from seed response" >&2
  echo "Response: ${SEED_RESP}" >&2
  exit 1
fi

if [[ -z "${CREATED_AT}" || "${CREATED_AT}" == "null" ]]; then
  echo "Failed to obtain created_at from seed response" >&2
  echo "Response: ${SEED_RESP}" >&2
  exit 1
fi

CREATED_DATE=${CREATED_AT%%T*}

# Compute from/to window: [created_at - 1 day, created_at + 1 day]
FROM_DATE=$(date -u -d "${CREATED_DATE} -1 day" +%F 2>/dev/null || date -u -jf "%Y-%m-%d" "${CREATED_DATE}" -v-1d +%F)
TO_DATE=$(date -u -d "${CREATED_DATE} +1 day" +%F 2>/dev/null || date -u -jf "%Y-%m-%d" "${CREATED_DATE}" -v+1d +%F)

echo "[P4] Seeded match_id=${MATCH_ID}, to_hotel_id=${TO_HOTEL_ID}, window ${FROM_DATE} -> ${TO_DATE}" >&2

# 2) POST outcome as correct hotel user
echo "[P4] Posting outcome as correct hotel user..." >&2
OUTCOME_RESP=$(curl -fsS -X POST "${API_BASE}/matches/${MATCH_ID}/outcome" \
  -H "Authorization: Bearer ${HOTEL_OK_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"outcome":"arrived","note":"p4-proof"}')

echo "Outcome response: ${OUTCOME_RESP}" >&2

# 3) Drilldown: ensure match appears with non-unknown outcome
echo "[P4] Verifying drilldown entry..." >&2
DRILL_RESP=$(curl -fsS "${API_BASE}/reports/match-risk/drilldown?from=${FROM_DATE}&to=${TO_DATE}&to_hotel_id=${TO_HOTEL_ID}" \
  -H "Authorization: Bearer ${SUPER_ADMIN_TOKEN}")

MATCH_ROW=$(echo "${DRILL_RESP}" | jq -c --arg MID "${MATCH_ID}" '.items[] | select(.match_id == $MID)') || true

if [[ -z "${MATCH_ROW}" ]]; then
  echo "Match ${MATCH_ID} not found in drilldown" >&2
  echo "Drilldown response: ${DRILL_RESP}" >&2
  exit 1
fi

OUTCOME=$(echo "${MATCH_ROW}" | jq -r '.outcome')
if [[ "${OUTCOME}" == "unknown" ]]; then
  echo "Expected non-unknown outcome in drilldown, got unknown" >&2
  echo "Row: ${MATCH_ROW}" >&2
  exit 1
fi

echo "[P4] Drilldown OK for match_id=${MATCH_ID} with outcome=${OUTCOME}" >&2

# 4) Summary invariants for to_hotel_id
echo "[P4] Verifying summary invariants..." >&2
SUMMARY_RESP=$(curl -fsS "${API_BASE}/reports/match-risk?from=${FROM_DATE}&to=${TO_DATE}&group_by=to_hotel" \
  -H "Authorization: Bearer ${SUPER_ADMIN_TOKEN}")

SUMMARY_ROW=$(echo "${SUMMARY_RESP}" | jq -c --arg HID "${TO_HOTEL_ID}" '.items[] | select(.to_hotel_id == $HID)') || true

if [[ -z "${SUMMARY_ROW}" ]]; then
  echo "Summary row for to_hotel_id=${TO_HOTEL_ID} not found" >&2
  echo "Summary response: ${SUMMARY_RESP}" >&2
  exit 1
fi

MATCHES_TOTAL=$(echo "${SUMMARY_ROW}" | jq -r '.matches_total')
OUTCOME_KNOWN=$(echo "${SUMMARY_ROW}" | jq -r '.outcome_known')
OUTCOME_MISSING=$(echo "${SUMMARY_ROW}" | jq -r '.outcome_missing')
NOT_ARRIVED=$(echo "${SUMMARY_ROW}" | jq -r '.not_arrived')
RATE=$(echo "${SUMMARY_ROW}" | jq -r '.not_arrived_rate')

if (( MATCHES_TOTAL <= 0 )); then
  echo "matches_total must be > 0" >&2
  echo "Row: ${SUMMARY_ROW}" >&2
  exit 1
fi

if (( OUTCOME_KNOWN < 0 )) || (( OUTCOME_MISSING < 0 )); then
  echo "outcome_known/outcome_missing must be >= 0" >&2
  echo "Row: ${SUMMARY_ROW}" >&2
  exit 1
fi

if (( MATCHES_TOTAL != OUTCOME_KNOWN + OUTCOME_MISSING )); then
  echo "Invariant failed: matches_total != outcome_known + outcome_missing" >&2
  echo "Row: ${SUMMARY_ROW}" >&2
  exit 1
fi

if (( NOT_ARRIVED < 0 )) || (( NOT_ARRIVED > OUTCOME_KNOWN )); then
  echo "Invariant failed: 0 <= not_arrived <= outcome_known" >&2
  echo "Row: ${SUMMARY_ROW}" >&2
  exit 1
fi

# RATE is float in [0,1]
RATE_OK=$(python - <<EOF
rate = float("${RATE}")
import sys
sys.exit(0 if 0.0 <= rate <= 1.0 else 1)
EOF
) || true

if [[ "${RATE_OK}" != "" ]]; then
  : # python exited 0
else
  echo "Invariant failed: not_arrived_rate must be between 0 and 1" >&2
  echo "Row: ${SUMMARY_ROW}" >&2
  exit 1
fi

echo "[P4] Summary invariants OK for to_hotel_id=${TO_HOTEL_ID}" >&2

# 5) Negative test: wrong hotel user must get 403
set +e
WRONG_RESP_CODE=$(curl -s -o /tmp/p4_wrong_outcome_resp.json -w "%{http_code}" \
  -X POST "${API_BASE}/matches/${MATCH_ID}/outcome" \
  -H "Authorization: Bearer ${HOTEL_WRONG_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"outcome":"arrived","note":"p4-proof-wrong"}')
set -e

if [[ "${WRONG_RESP_CODE}" != "403" ]]; then
  echo "Expected 403 for wrong hotel user, got ${WRONG_RESP_CODE}" >&2
  echo "Response body:" >&2
  cat /tmp/p4_wrong_outcome_resp.json >&2 || true
  exit 1
fi

echo "[P4] Negative test OK: wrong hotel user receives 403" >&2

echo "[P4] All checks passed. P4 proof pack successful." >&2
