# ContractTracker (Python service). Every command lives here. `make help` lists them.
SHELL := /bin/bash
.DEFAULT_GOAL := help
UV ?= uv
STATE := .bearing/state
SKIPPED := $(STATE)/.skipped
# The gates `make check` runs, in order. test-integration needs Postgres, so
# it is a CI job and a manual target, not part of check.
GATES := format-check lint typecheck test vuln web-check eval-extraction eval-qa
POSTGRES_PORT ?= 5432
DATABASE_URL ?= postgresql+asyncpg://postgres:postgres@localhost:$(POSTGRES_PORT)/contract-tracker
# psql takes the plain URL (no SQLAlchemy driver suffix).
PSQL_URL = $(subst +asyncpg,,$(DATABASE_URL))

# $(call skip,gate,tool): the tool is absent. Print it, record it, and let the
# other gates run; `check` fails on any recorded skip. Never a silent pass.
define skip
{ mkdir -p $(STATE); echo "$(1): SKIPPED ($(2) not installed)"; echo "$(1) $(2)" >> $(SKIPPED); exit 0; }
endef
# $(call need_tool,gate,tool): uv, then the project tool inside the venv.
define need_tool
command -v $(UV) >/dev/null || $(call skip,$(1),uv); $(UV) run --quiet $(2) --version >/dev/null 2>&1 || $(call skip,$(1),$(2))
endef

.PHONY: web web-install web-check ui eval-extraction eval-qa eval-live fetch-model embed ask remind mail help setup dev contracts ingest extract check check-file fix test test-integration lint typecheck format format-check migrate migrate-verify migrate-down migrate-new vuln doctor db db-reset clean

help: ## List targets
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-18s %s\n", $$1, $$2}'

setup: ## Install Python 3.12, dependencies (writes uv.lock) and git hooks
	$(UV) python install 3.12
	@if [ -f uv.lock ]; then $(UV) sync --locked --all-groups; else echo "setup: no uv.lock yet, resolving; commit the lockfile it writes"; $(UV) sync --all-groups; fi
	$(UV) run python -m app.retrieval.fetch
	bash .githooks/install.sh
	@echo "setup: the committed .githooks run on commit; .pre-commit-config.yaml is for 'uv run pre-commit run --all-files'"
	@echo "setup done"

dev: ## Run the API locally with reload (reads .env if present)
	@set -a; [ -f .env ] && . ./.env; set +a; $(UV) run uvicorn app.main:create_app --factory --reload --host 0.0.0.0 --port "$${PORT:-8080}"

contracts: ## Write the synthetic contracts, their truth.json files and data/answer_key.json for the 6 golden ones (deterministic)
	$(UV) run python -m evals.contracts.generate data/contracts

ingest: ## Load contract PDFs: make ingest FILES="data/contracts/*.pdf" [TYPE=lease|vendor|service]
	@[ -n "$(FILES)" ] || { echo "usage: make ingest FILES=\"data/contracts/*.pdf\" [TYPE=lease]" >&2; exit 2; }
	DATABASE_URL=$(DATABASE_URL) $(UV) run python -m app.ingestion.cli $(FILES) $(if $(TYPE),--type $(TYPE))

extract: ## Extract the 5 fields (prompt v2): make extract NAMES="lease-01 vendor-02" (no NAMES: every contract)
	DATABASE_URL=$(DATABASE_URL) $(UV) run python -m app.extraction.cli $(NAMES)

format: ## Format
	$(UV) run ruff format .

format-check: ## Fail if any file is unformatted
	@n=$$(git ls-files -co --exclude-standard '*.py' | wc -l | tr -d ' '); \
	[ "$$n" -gt 0 ] || { echo "format-check: 0 python files, nothing checked" >&2; exit 1; }; \
	$(call need_tool,format-check,ruff); \
	$(UV) run ruff format --check . || { echo "format-check: run make fix" >&2; exit 1; }; \
	echo "format-check: $$n files checked"

lint: ## ruff check
	@n=$$(git ls-files -co --exclude-standard '*.py' | wc -l | tr -d ' '); \
	[ "$$n" -gt 0 ] || { echo "lint: 0 python files, nothing checked" >&2; exit 1; }; \
	$(call need_tool,lint,ruff); \
	$(UV) run ruff check . && echo "lint: $$n files checked"

typecheck: ## mypy strict
	@n=$$(git ls-files -co --exclude-standard 'app/*.py' 'evals/*.py' 'tests/*.py' | wc -l | tr -d ' '); \
	[ "$$n" -gt 0 ] || { echo "typecheck: 0 python files, nothing checked" >&2; exit 1; }; \
	$(call need_tool,typecheck,mypy); \
	$(UV) run mypy app evals tests && echo "typecheck: $$n files checked"

ui: ## API on :8080 plus the React page on http://localhost:5173 (reads .env; needs make db and make migrate)
	@set -a; [ -f .env ] && . ./.env; set +a; trap 'kill 0' EXIT; \
	$(UV) run uvicorn app.main:create_app --factory --port 8080 & \
	(cd web && npm run dev); wait

web-install: ## Install the React app's packages exactly as locked (Node 20 or later)
	cd web && npm ci

web: ## The React page alone on :5173; add ?mock=1 to the URL to use sample data without the API
	cd web && npm run dev

web-check: ## Lint, typecheck and unit-test the React app (a gate of make check)
	@command -v npm >/dev/null || $(call skip,web-check,npm); \
	[ -d web/node_modules ] || $(call skip,web-check,web/node_modules: run make web-install); \
	n=$$(git ls-files -co --exclude-standard 'web/src/*.test.ts' 'web/src/*.test.tsx' | wc -l | tr -d ' '); \
	[ "$$n" -gt 0 ] || { echo "web-check: 0 test files, nothing checked" >&2; exit 1; }; \
	cd web && npm run --silent lint && npm run --silent typecheck && npm test --silent 2>&1 | tail -6 && echo "web-check: $$n test files checked"

eval-extraction: ## Extraction eval over the 6 golden contracts, offline from llm_cache (no key, no spend)
	$(UV) run python -m evals.extraction.run

eval-qa: ## Q&A eval over the golden questions, offline from llm_cache (needs the model: make fetch-model)
	$(UV) run python -m evals.qa.run

eval-live: ## Fill llm_cache from OpenRouter for both evals and print spend; the only target that spends
	@set -a; [ -f .env ] && . ./.env; set +a; $(UV) run python -m evals.extraction.run --live; \
	$(UV) run python -m evals.qa.run --live

fetch-model: ## Download the embedding model once into models/ (about 130 MB; later runs are offline)
	$(UV) run python -m app.retrieval.fetch

remind: ## Send due reminders to MailHog: make remind [TODAY=2026-10-31]; PRETEND_TODAY in .env is the default
	@set -a; [ -f .env ] && . ./.env; set +a; $(UV) run python -m app.reminders.cli $(if $(TODAY),--today $(TODAY))

embed: ## Embed every clause that has no vector yet (needs make db, make migrate and make fetch-model)
	@set -a; [ -f .env ] && . ./.env; set +a; $(UV) run python -m app.qa.cli embed

ask: ## Ask a question: make ask Q="Which law governs Supply Agreement 08?"
	@set -a; [ -f .env ] && . ./.env; set +a; $(UV) run python -m app.qa.cli ask "$(Q)"

test: ## Unit tests with coverage (integration tests excluded)
	@n=$$(git ls-files -co --exclude-standard 'tests/test_*.py' 'tests/**/test_*.py' | grep -v '^tests/integration/' | wc -l | tr -d ' '); \
	[ "$$n" -gt 0 ] || { echo "test: 0 test files, nothing checked" >&2; exit 1; }; \
	$(call need_tool,test,pytest); \
	set -o pipefail; $(UV) run pytest -m "not integration" 2>&1 | tail -60 && echo "test: $$n test files checked"

test-integration: ## Repository tests against Postgres (needs make db and make migrate; a CI job, not part of check)
	@n=$$(git ls-files -co --exclude-standard 'tests/integration/test_*.py' | wc -l | tr -d ' '); \
	[ "$$n" -gt 0 ] || { echo "test-integration: 0 test files, nothing checked" >&2; exit 1; }; \
	set -o pipefail; DATABASE_URL=$(DATABASE_URL) $(UV) run pytest -m integration --no-cov tests/integration 2>&1 | tail -60 && echo "test-integration: $$n test files checked"

vuln: ## pip-audit over the locked runtime dependencies
	@command -v $(UV) >/dev/null || $(call skip,vuln,uv); command -v uvx >/dev/null || $(call skip,vuln,uvx); \
	[ -f uv.lock ] || { echo "vuln: no uv.lock; run make setup and commit it" >&2; exit 1; }; \
	n=$$($(UV) export --frozen --no-dev --no-hashes --no-emit-project | grep -c '==' || true); \
	[ "$$n" -gt 0 ] || { echo "vuln: 0 packages, nothing checked" >&2; exit 1; }; \
	uvx pip-audit --strict --no-deps -r <($(UV) export --frozen --no-dev --no-hashes --no-emit-project) && echo "vuln: $$n packages checked"

check: ## The gate: every gate in GATES, then the tally. CI runs exactly this.
	@mkdir -p $(STATE); rm -f $(SKIPPED) $(STATE)/.check-passed
	@for g in $(GATES); do $(MAKE) --no-print-directory $$g || { echo "check: $$g failed" >&2; exit 1; }; done
	@s=$$(cut -d' ' -f1 $(SKIPPED) 2>/dev/null | sort -u | wc -l | tr -d ' '); r=$$(( $(words $(GATES)) - s )); \
	echo "check: $$r gates run, $$s skipped"; \
	if [ "$$s" -eq 0 ]; then touch $(STATE)/.check-passed; echo "check: passed"; \
	elif [ "$${BEARING_ALLOW_SKIP:-0}" = "1" ] && [ -z "$$CI" ]; then sed 's/^/  skipped: /' $(SKIPPED); echo "check: passed with skips (BEARING_ALLOW_SKIP=1 is a local convenience; CI never sets it)"; \
	else sed 's/^/  skipped: /' $(SKIPPED); echo "check: FAILED, $$s gate(s) skipped; run make setup, or BEARING_ALLOW_SKIP=1 make check locally" >&2; exit 1; fi

check-file: ## Lint one edited file, FILE=path (the Bearing edit hook runs this)
	@[ -n "$(FILE)" ] || { echo "check-file: FILE is empty, nothing checked" >&2; exit 1; }; \
	[ -f "$(FILE)" ] || { echo "check-file: $(FILE) does not exist, nothing checked" >&2; exit 1; }; \
	case "$(FILE)" in \
	  *.py) command -v $(UV) >/dev/null || { echo "check-file: uv not installed, $(FILE) not checked"; exit 0; }; $(UV) run ruff check --quiet --force-exclude "$(FILE)" || exit 1;; \
	  *) echo "check-file: no per-file check for $(FILE)"; exit 0;; \
	esac; \
	echo "check-file: 1 file checked"

fix: format ## Apply every automatic fix
	@$(UV) run ruff check --fix . || true

db: ## Start Postgres in Docker (host port POSTGRES_PORT, default 5432)
	POSTGRES_PORT=$(POSTGRES_PORT) docker compose up -d --wait postgres

mail: ## Start MailHog (SMTP on 1025, web UI on http://localhost:8025) for reminder email
	docker compose up -d --wait mailhog

db-reset: ## Drop and recreate the local database (destructive)
	POSTGRES_PORT=$(POSTGRES_PORT) docker compose down -v && POSTGRES_PORT=$(POSTGRES_PORT) docker compose up -d --wait postgres

migrate: ## alembic upgrade head
	DATABASE_URL=$(DATABASE_URL) $(UV) run alembic upgrade head

migrate-down: ## alembic downgrade one
	DATABASE_URL=$(DATABASE_URL) $(UV) run alembic downgrade -1

migrate-verify: ## Every Down runs and restores the schema: up, snapshot, down, up, snapshot, diff (a CI step; needs psql)
	@command -v psql >/dev/null || { echo "migrate-verify: psql not installed (postgresql-client), nothing checked" >&2; exit 1; }; \
	[ -f scripts/schema-snapshot.sql ] || { echo "migrate-verify: no scripts/schema-snapshot.sql, nothing checked" >&2; exit 1; }; \
	n=$$(ls alembic/versions/*.py 2>/dev/null | wc -l | tr -d ' '); \
	[ "$$n" -gt 0 ] || { echo "migrate-verify: 0 migrations in alembic/versions, nothing checked" >&2; exit 1; }; \
	mkdir -p $(STATE); snap() { psql "$(PSQL_URL)" -XAtq -v ON_ERROR_STOP=1 -f scripts/schema-snapshot.sql > "$(STATE)/schema-$$1.txt"; }; \
	$(MAKE) --no-print-directory migrate >/dev/null && snap up || exit 1; \
	o=$$(wc -l < $(STATE)/schema-up.txt | tr -d ' '); [ "$$o" -gt 0 ] || { echo "migrate-verify: the schema snapshot is empty, nothing compared" >&2; exit 1; }; \
	$(MAKE) --no-print-directory migrate-down >/dev/null && $(MAKE) --no-print-directory migrate >/dev/null && snap newest || exit 1; \
	diff -u $(STATE)/schema-up.txt $(STATE)/schema-newest.txt || { echo "migrate-verify: the newest downgrade does not undo exactly what its upgrade did" >&2; exit 1; }; \
	DATABASE_URL=$(DATABASE_URL) $(UV) run alembic downgrade base >/dev/null && $(MAKE) --no-print-directory migrate >/dev/null && snap all || exit 1; \
	diff -u $(STATE)/schema-up.txt $(STATE)/schema-all.txt || { echo "migrate-verify: running every downgrade and every upgrade again changed the schema" >&2; exit 1; }; \
	echo "migrate-verify: $$n migrations, every downgrade ran, $$o schema objects identical after down and up"

migrate-new: ## Start the next hand-written migration: make migrate-new name=add_index (no autogenerate, decision D4)
	@[ -n "$(name)" ] || { echo "usage: make migrate-new name=add_invoices" >&2; exit 2; }
	@id=$$(printf '%04d' $$(( $$(ls alembic/versions/*.py 2>/dev/null | wc -l) + 1 ))); \
	DATABASE_URL=$(DATABASE_URL) $(UV) run alembic revision --rev-id "$$id" -m "$(name)" && \
	echo "migrate-new: alembic/versions/$${id}_$(name).py written; write upgrade and downgrade by hand"

doctor: ## Environment diagnostics
	@echo "uv:        $$(command -v $(UV) >/dev/null && $(UV) --version || echo missing)"
	@echo "python:    $$($(UV) run python --version 2>/dev/null || echo 'missing (run make setup)')"
	@echo "ruff:      $$($(UV) run --quiet ruff --version 2>/dev/null || echo missing)"
	@echo "mypy:      $$($(UV) run --quiet mypy --version 2>/dev/null || echo missing)"
	@echo "alembic:   $$($(UV) run --quiet alembic --version 2>/dev/null || echo missing)"
	@echo "docker:    $$(command -v docker >/dev/null && docker --version || echo missing)"
	@echo "lock:      $$([ -f uv.lock ] && echo present || echo 'MISSING (run make setup and commit uv.lock)')"
	@echo "hooksPath: $$(git config core.hooksPath || echo 'NOT SET (run make setup)')"

clean: ## Remove caches and build output
	rm -rf .venv .ruff_cache .mypy_cache .pytest_cache .coverage htmlcov dist build $(STATE)/.check-passed $(SKIPPED)
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
