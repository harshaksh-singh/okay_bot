# ==============================================================================
# Portolan - Autonomous Opportunity Intelligence Platform
# ==============================================================================
# One command: `make run`
#   Preflight (sessions + security) -> Discover (real sources) -> Prepare (14+ apps)
#   -> Dry-run submit -> Phase status. Stops at READY_TO_SUBMIT; human does final click.
#
# Named after medieval portolan nautical charts: navigating complex geography
# via verified landmarks, not guesses.
# ==============================================================================
.PHONY: help setup venv install dev test test-cov lint format worker scheduler \
        frontend backend dry-run discover dashboard db-init db-reset clean \
        acceptance run

PYTHON := python3
VENV := .venv
VENV_BIN := $(VENV)/bin
PIP := $(VENV_BIN)/pip
PY := $(VENV_BIN)/python

help:  ## Show this help
	@echo ""
	@echo "  Portolan - Autonomous Opportunity Intelligence"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-22s\033[0m %s\n", $$1, $$2}'

autonomous-run:  ## Portolan autonomous campaign (usage: make autonomous-run ARGS="--applications 10 --dry-run")
	@cd backend && ../$(PY) -m app --autonomous-run $(ARGS)

run:  ## Portolan unified pipeline: preflight -> discover -> prepare -> dry-run -> status
	@echo ""
	@echo "=========================================================="
	@echo "  Portolan - Opportunity Intelligence Pipeline"
	@echo "=========================================================="
	@echo ""
	@echo "[1/5] Pre-flight: verifying sessions + security..."
	@$(PY) scripts/verify_sessions.py || echo "  (sessions: some platforms need login - run 'make login-<platform>')"
	@echo ""
	@echo "[2/5] OAuth check (Gmail)..."
	@$(PY) scripts/check_oauth_config.py || echo "  (gmail oauth: run 'make connect-gmail' to configure)"
	@echo ""
	@echo "[3/5] Real-source discovery..."
	@cd backend && ../$(PY) -m app --discover 2>&1 | tail -5
	@echo ""
	@echo "[4/5] Preparing applications (dry-run)..."
	@cd backend && ../$(PY) -m app --apply-approved 2>&1 | tail -20
	@echo ""
	@echo "[5/5] Final status:"
	@$(PY) scripts/phase_status.py || true
	@echo ""
	@echo "To go LIVE: set DRY_RUN=false in .env, then re-run \`make run\`"
	@echo "Final submit is manual per project policy (headful Chromium requires your click)."

setup: venv install  ## One-time project setup
	@echo ""
	@echo "✅ Setup complete. Copy .env.example -> .env, then run: make dry-run"

venv:  ## Create Python virtualenv
	@test -d $(VENV) || $(PYTHON) -m venv $(VENV)
	@$(PIP) install --upgrade pip setuptools wheel >/dev/null

install:  ## Install Python dependencies
	@$(PIP) install -r backend/requirements.txt

dev: dry-run  ## Alias for dry-run (first-run experience)

dry-run:  ## Launch interactive CLI in DRY_RUN mode (default)
	@cd backend && ../$(PY) -m app

discover:  ## Run discovery pipeline (mock sources by default)
	@cd backend && ../$(PY) -m app --discover

dashboard:  ## Show dashboard
	@cd backend && ../$(PY) -m app --dashboard

acceptance:  ## Run Phase 1 acceptance tests
	@cd backend && ../$(PY) -m pytest tests/test_acceptance.py -v -m acceptance

test:  ## Run full test suite
	@cd backend && ../$(PY) -m pytest -v

test-cov:  ## Run tests with coverage report
	@cd backend && ../$(PY) -m pytest --cov=app --cov-report=term-missing

lint:  ## Run linter (if ruff installed)
	@cd backend && ../$(PY) -m ruff check app tests 2>/dev/null || echo "ruff not installed - skipping"

format:  ## Format code (if ruff installed)
	@cd backend && ../$(PY) -m ruff format app tests 2>/dev/null || echo "ruff not installed - skipping"

db-init:  ## Initialize database
	@cd backend && ../$(PY) -c "from app.database.engine import init_database; init_database()"
	@echo "✅ Database initialized at data/job_agent.db"

db-reset:  ## WARNING: delete and reinitialize database
	@rm -f data/job_agent.db
	@$(MAKE) db-init

db-migrate:  ## Apply alembic migrations
	@cd backend && ../$(PY) -m alembic upgrade head

db-revision:  ## Autogenerate a new alembic migration (MSG="description")
	@cd backend && ../$(PY) -m alembic revision --autogenerate -m "$(MSG)"

daily-report:  ## Run pipeline + print the daily report
	@cd backend && ../$(PY) -m app --daily-report

weekly-analytics:  ## Print weekly analytics from persisted applications
	@cd backend && ../$(PY) -m app --weekly-analytics

daily-growth:  ## Run pipeline + show CAREER + HARBAN dashboards
	@cd backend && ../$(PY) -m app --daily-growth

apply-approved:  ## Run pipeline + show approved-application outcomes
	@cd backend && ../$(PY) -m app --apply-approved

client-discovery:  ## Run pipeline + show Harban client lead dashboard
	@cd backend && ../$(PY) -m app --client-discovery

client-outreach-dry-run:  ## Run pipeline + print first 5 Harban outreach drafts (never sends)
	@cd backend && ../$(PY) -m app --client-outreach-dry-run

production-daily:  ## Run pipeline + print the Production Daily Report
	@cd backend && ../$(PY) -m app --production-daily

accounts:  ## Show configured accounts (identifiers only — NEVER passwords)
	@cd backend && ../$(PY) -m app --accounts

login-linkedin:  ## Open Playwright persistent profile for LinkedIn (user signs in themselves)
	@cd backend && ../$(PY) -m app.accounts.cli linkedin

login-naukri:  ## Open Playwright persistent profile for Naukri (user signs in themselves)
	@cd backend && ../$(PY) -m app.accounts.cli naukri

login-indeed:  ## Open Playwright persistent profile for Indeed (user signs in themselves)
	@cd backend && ../$(PY) -m app.accounts.cli indeed

login-handshake:  ## Open Playwright persistent profile for Handshake (user signs in themselves)
	@cd backend && ../$(PY) -m app.accounts.cli handshake

login-wellfound:  ## Open Playwright persistent profile for Wellfound (user signs in themselves)
	@cd backend && ../$(PY) -m app.accounts.cli wellfound

login-outlier:  ## Open Playwright persistent profile for Outlier (user signs in themselves)
	@cd backend && ../$(PY) -m app.accounts.cli outlier

login-glassdoor:  ## Open Playwright persistent profile for Glassdoor (user signs in themselves)
	@cd backend && ../$(PY) -m app.accounts.cli glassdoor

login-cutshort:  ## Open Playwright persistent profile for Cutshort (user signs in themselves)
	@cd backend && ../$(PY) -m app.accounts.cli cutshort

login-instahyre:  ## Open Playwright persistent profile for Instahyre (user signs in themselves)
	@cd backend && ../$(PY) -m app.accounts.cli instahyre

login-hirist:  ## Open Playwright persistent profile for Hirist (user signs in themselves)
	@cd backend && ../$(PY) -m app.accounts.cli hirist

login-foundit:  ## Open Playwright persistent profile for Foundit (user signs in themselves)
	@cd backend && ../$(PY) -m app.accounts.cli foundit

login-internshala:  ## Open Playwright persistent profile for Internshala (user signs in themselves)
	@cd backend && ../$(PY) -m app.accounts.cli internshala

login-surge-ai:  ## Open Playwright persistent profile for Surge AI (user signs in themselves)
	@cd backend && ../$(PY) -m app.accounts.cli surge_ai

login-telus-digital-ai:  ## Open Playwright persistent profile for Telus Digital AI (user signs in themselves)
	@cd backend && ../$(PY) -m app.accounts.cli telus_digital_ai

verify-sessions:  ## Verify session status across all configured platforms
	@$(PY) scripts/verify_sessions.py

connect-gmail:  ## Walk through Gmail OAuth setup (never asks for your password)
	@$(PY) scripts/connect_gmail.py

check-oauth-config:  ## Pre-flight: shows exactly where you are in Gmail OAuth setup (never prints secrets)
	@$(PY) scripts/check_oauth_config.py

install-gmail-client:  ## Install Google OAuth client JSON (usage: make install-gmail-client FILE=~/Downloads/client_secret_*.json EMAIL=you@gmail.com)
	@$(PY) scripts/install_gmail_client.py "$(FILE)" $(if $(EMAIL),--email "$(EMAIL)")

authorize-gmail:  ## Run Gmail OAuth authorization flow (opens browser; you sign in; token -> macOS Keychain)
	@$(PY) scripts/connect_gmail.py --authorize

verify-gmail:  ## Verify Gmail OAuth refresh token in macOS Keychain
	@$(PY) scripts/connect_gmail.py --verify

discovery-audit:  ## Audit most recently discovered jobs (scam / duplicate / expired / invalid URL / low match)
	@$(PY) scripts/discovery_audit.py

platform-capabilities:  ## Print honest capability matrix for each platform (REAL vs STUBBED)
	@$(PY) scripts/platform_capabilities.py

phase-status:  ## Full Phase 5 + Phase 6 status report
	@$(PY) scripts/phase_status.py

security-audit:  ## Secret scan + git security + password-column check + no OAuth tokens in DB
	@echo "=== Security audit ==="
	@$(PY) scripts/secret_scan.py || echo "[secret_scan: issues found]"
	@echo ""
	@$(PY) scripts/git_security_check.py || echo "[git_security: issues found]"
	@echo ""
	@test -f data/job_agent.db && $(PY) scripts/db_backup.py check || echo "[db-check: skipped (no db)]"
	@echo ""
	@echo "Browser profiles:"
	@ls -la browser/profiles/ 2>/dev/null | head -10 || echo "  no browser profiles yet"

production-readiness:  ## Run secret scan + git security + db check + resume validation + tests
	@echo "=== Production readiness check ==="
	@$(PY) scripts/secret_scan.py || echo "[secret_scan: issues found]"
	@echo ""
	@$(PY) scripts/git_security_check.py || echo "[git_security: issues found]"
	@echo ""
	@test -f data/job_agent.db && $(PY) scripts/db_backup.py check || echo "[db-check: skipped (no db)]"
	@echo ""
	@$(PY) scripts/resume_validator.py || echo "[resume_validator: issues found]"
	@echo ""
	@cd backend && ../$(PY) -m pytest -q -W ignore::DeprecationWarning 2>&1 | tail -3

secret-scan:  ## Scan the repo for leaked secrets / API keys / tokens
	@$(PY) scripts/secret_scan.py

git-security-check:  ## Verify .gitignore + no tracked secrets
	@$(PY) scripts/git_security_check.py

resume-validate:  ## Validate resume PDFs / generated text resumes against profile facts
	@$(PY) scripts/resume_validator.py

db-backup:  ## Snapshot the SQLite DB with manifest (counts + credential-column check)
	@$(PY) scripts/db_backup.py backup

db-check:  ## PRAGMA integrity_check + credential-column audit on the current DB
	@$(PY) scripts/db_backup.py check

db-restore:  ## Restore a specific backup (usage: make db-restore SOURCE=data/backups/job_agent_backup_YYYYMMDD_HHMMSS.db)
	@$(PY) scripts/db_backup.py restore --source $(SOURCE)

worker:  ## Run background worker (Phase 6)
	@echo "⚠️  Worker: use 'make scheduler' instead; the scheduler runs the pipeline in-process."

scheduler:  ## Start the APScheduler (morning/evening/night IST runs)
	@cd backend && ../$(PY) -m app.scheduler.cli

reset-credentials:  ## Delete persistent browser profile and secret storage
	@rm -rf browser/ 2>/dev/null || true
	@echo "✅ Browser profile cleared. Email OAuth tokens must be removed from macOS Keychain manually."

frontend:  ## Run frontend (Phase 6b - Next.js deferred)
	@echo "⚠️  Next.js frontend not implemented. CLI dashboard: make dashboard. FastAPI backend: make api."

api:  ## Start FastAPI backend on :8000
	@cd backend && ../$(PY) -m uvicorn app.api:app --host 127.0.0.1 --port 8000 --reload

backend: dry-run  ## Alias for dry-run

clean:  ## Remove caches and generated artifacts
	@find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
	@echo "✅ Caches cleaned"
