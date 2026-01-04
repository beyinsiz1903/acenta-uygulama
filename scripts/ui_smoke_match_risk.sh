#!/usr/bin/env bash
set -euo pipefail

: "${FRONTEND_BASE:?FRONTEND_BASE is required}"
: "${SUPER_ADMIN_EMAIL:?SUPER_ADMIN_EMAIL is required}"
: "${SUPER_ADMIN_PASSWORD:?SUPER_ADMIN_PASSWORD is required}"

echo "[UI-SMOKE] FRONTEND_BASE=$FRONTEND_BASE"

# Prefer Playwright if present
if [ -f "frontend/playwright.config.ts" ] || [ -f "playwright.config.ts" ] || grep -q "\"@playwright/test\"" frontend/package.json 2>/dev/null; then
  echo "[UI-SMOKE] Runner: Playwright"

  pushd frontend >/dev/null
  yarn install --frozen-lockfile
  npx playwright install --with-deps

  if [ -f "tests/admin-match-risk.spec.ts" ]; then
    npx playwright test tests/admin-match-risk.spec.ts
  elif [ -f "tests/admin-match-risk.spec.js" ]; then
    npx playwright test tests/admin-match-risk.spec.js
  else
    echo "[UI-SMOKE] ERROR: Playwright detected but test file not found at frontend/tests/admin-match-risk.spec.(ts|js)" >&2
    exit 2
  fi
  popd >/dev/null
  exit 0
fi

# Cypress if present
if [ -f "frontend/cypress.config.js" ] || [ -f "frontend/cypress.config.ts" ] || grep -q "\"cypress\"" frontend/package.json 2>/dev/null; then
  echo "[UI-SMOKE] Runner: Cypress"

  pushd frontend >/dev/null
  yarn install --frozen-lockfile

  export CYPRESS_FRONTEND_BASE="$FRONTEND_BASE"
  export CYPRESS_SUPER_ADMIN_EMAIL="$SUPER_ADMIN_EMAIL"
  export CYPRESS_SUPER_ADMIN_PASSWORD="$SUPER_ADMIN_PASSWORD"

  if [ -f "cypress/e2e/admin_match_risk.cy.js" ]; then
    npx cypress run --spec cypress/e2e/admin_match_risk.cy.js
  elif [ -f "cypress/e2e/admin_match_risk.cy.ts" ]; then
    npx cypress run --spec cypress/e2e/admin_match_risk.cy.ts
  else
    echo "[UI-SMOKE] ERROR: Cypress detected but spec not found at frontend/cypress/e2e/admin_match_risk.cy.(js|ts)" >&2
    exit 3
  fi
  popd >/dev/null
  exit 0
fi

echo "[UI-SMOKE] ERROR: No supported E2E runner detected (Playwright/Cypress)." >&2
echo "[UI-SMOKE] Hint: add Playwright or Cypress, or wire a Jest+RTL alternative." >&2
exit 4
