# ──────────────────────────────────────────────────
# Syroce — Unified Quality Gate Commands
# ──────────────────────────────────────────────────
# Usage:
#   make quality          — Run ALL quality gates (lint + test + audit + guard)
#   make lint             — Backend + frontend lint
#   make test-backend     — Backend unit tests with coverage
#   make test-guard       — Architecture guard + scope audit
#   make test-audit       — Dependency/scope audit only
#   make coverage-check   — Check coverage thresholds
#   make docs-generate    — Generate architecture docs (Phase D)
#   make docs-check       — Verify generated docs are fresh (Phase D)
# ──────────────────────────────────────────────────

.PHONY: quality lint lint-backend lint-frontend test-backend test-guard test-audit coverage-check clean

# ── Thresholds ────────────────────────────────────
# Kademeli enforcement: Yeni modüllerde yüksek, legacy'de esnek
COVERAGE_OVERALL_MIN := 20
COVERAGE_CRITICAL_MIN := 50

# ── Composite targets ────────────────────────────
quality: lint test-guard test-audit test-backend coverage-check
	@echo "✅ All quality gates passed."

# ── Lint ──────────────────────────────────────────
lint: lint-backend lint-frontend

lint-backend:
	@echo "🔍 Backend lint (ruff)..."
	cd backend && ruff check app/ --select E,F,W --ignore E501,E402

lint-frontend:
	@echo "🔍 Frontend lint (eslint)..."
	cd frontend && npx eslint src/ --max-warnings 0

# ── Tests ─────────────────────────────────────────
test-backend:
	@echo "🧪 Backend tests with coverage..."
	cd backend && python -m pytest tests/ \
		-x --timeout=60 \
		--reruns=2 --reruns-delay=1 \
		--only-rerun="AutoReconnect" \
		--only-rerun="ConnectionResetError" \
		--only-rerun="ServerSelectionTimeoutError" \
		--cov=app \
		--cov-report=term-missing:skip-covered \
		--cov-report=xml:coverage.xml \
		--cov-report=html:htmlcov \
		-k "not preview and not external and not paximum" \
		--ignore=tests/integration \
		-q

test-guard: test-architecture-guard test-audit
	@echo "✅ All guard tests passed."

test-architecture-guard:
	@echo "🏗️  Architecture guard..."
	cd backend && python -m pytest tests/test_architecture_guard.py -v --timeout=30

test-audit:
	@echo "🔒 Scope/dependency audit..."
	cd backend && python -m pytest tests/test_scope_audit.py -v --timeout=30

# ── Coverage Threshold Check ──────────────────────
coverage-check:
	@echo "📊 Coverage threshold check..."
	cd backend && python scripts/check_coverage_threshold.py

# ── Clean ─────────────────────────────────────────
clean:
	rm -rf backend/htmlcov backend/coverage.xml backend/.coverage
	rm -rf frontend/build
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@echo "Cleaned."

# ── Generated Architecture Docs ───────────────────
docs-generate:
	@echo "Generating architecture docs..."
	cd backend && python scripts/generate_arch_docs.py

docs-check:
	@echo "Checking docs freshness..."
	cd backend && python scripts/generate_arch_docs.py --check
