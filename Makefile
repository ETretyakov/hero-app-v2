VENV   := .venv
PYTHON := $(VENV)/bin/python
PIP    := $(VENV)/bin/pip
PYTEST := $(VENV)/bin/pytest
ALEMBIC := $(VENV)/bin/alembic

.DEFAULT_GOAL := help

# ── Help ──────────────────────────────────────────────────────────────────────

.PHONY: help
help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ── Environment ───────────────────────────────────────────────────────────────

.PHONY: install
install: ## Create .venv and install all dependencies via pip
	python3 -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install poetry
	$(VENV)/bin/poetry install --no-root

.PHONY: install-deps
install-deps: ## Install/sync dependencies into an existing .venv (no poetry)
	$(PIP) install -r <($(VENV)/bin/poetry export --without-hashes)

# ── Code quality ──────────────────────────────────────────────────────────────

.PHONY: lint
lint: ## Run flake8 linter
	$(VENV)/bin/flake8 app tests

.PHONY: format
format: ## Auto-format code with black and sort imports with isort
	$(VENV)/bin/black app tests
	$(VENV)/bin/isort app tests

.PHONY: format-check
format-check: ## Check formatting without modifying files (CI-friendly)
	$(VENV)/bin/black --check app tests
	$(VENV)/bin/isort --check-only app tests

# ── Tests ─────────────────────────────────────────────────────────────────────

.PHONY: test
test: ## Run the full test suite (requires Docker for testcontainers)
	$(PYTEST) tests/ -v

.PHONY: test-fast
test-fast: ## Run tests, stop on first failure
	$(PYTEST) tests/ -x -v

.PHONY: test-cov
test-cov: ## Run tests with coverage report
	$(PYTEST) tests/ -v --cov=app --cov-report=term-missing

# ── Database ──────────────────────────────────────────────────────────────────

.PHONY: migrate
migrate: ## Apply all pending Alembic migrations
	$(ALEMBIC) upgrade head

.PHONY: migrate-down
migrate-down: ## Roll back the last Alembic migration
	$(ALEMBIC) downgrade -1

.PHONY: migrate-create
migrate-create: ## Generate a new migration; usage: make migrate-create name="add heroes table"
	$(ALEMBIC) revision --autogenerate -m "$(name)"

.PHONY: migrate-history
migrate-history: ## Show migration history
	$(ALEMBIC) history --verbose

# ── Docker ────────────────────────────────────────────────────────────────────

.PHONY: up
up: ## Start all services (db + app) in the background
	docker compose up -d

.PHONY: up-db
up-db: ## Start only the database service
	docker compose up -d db

.PHONY: down
down: ## Stop and remove all containers (keeps volumes)
	docker compose down

.PHONY: down-v
down-v: ## Stop containers and delete volumes (full reset)
	docker compose down -v

.PHONY: logs
logs: ## Tail logs from all running services
	docker compose logs -f

.PHONY: build
build: ## Re-build the app Docker image
	docker compose build

# ── Local dev ─────────────────────────────────────────────────────────────────

.PHONY: run
run: ## Run the app locally (requires a running DB and .env file)
	$(PYTHON) -m app

.PHONY: demo
demo: ## Run full API demo (starts stack, fires curl requests, tears down)
	@bash scripts/demo.sh

.PHONY: clean
clean: ## Remove __pycache__ and .pytest_cache directories
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache .coverage
