# ============================================
# Aqar.ai - Makefile
# ============================================
# Run `make help` to see all available commands
# ============================================

.PHONY: help dev stop build test test-unit test-int test-ml test-coverage \
        lint format migrate seed health logs clean shell-api shell-db

# ── Colors ──
GREEN  := \033[0;32m
YELLOW := \033[0;33m
CYAN   := \033[0;36m
RESET  := \033[0m

# ── Variables ──
DOCKER_COMPOSE := docker compose
PYTHON := python3
PIP := pip3

help: ## Show this help message
	@echo "$(CYAN)═══════════════════════════════════════$(RESET)"
	@echo "$(CYAN)   🏠 Aqar.ai - Developer Commands$(RESET)"
	@echo "$(CYAN)═══════════════════════════════════════$(RESET)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-18s$(RESET) %s\n", $$1, $$2}'

# ═══════════════════════════════════════
# Development
# ═══════════════════════════════════════

dev: ## Start all services (Docker Compose)
	@echo "$(CYAN)🚀 Starting Aqar.ai development stack...$(RESET)"
	$(DOCKER_COMPOSE) up -d
	@echo "$(GREEN)✅ All services started!$(RESET)"
	@echo ""
	@echo "  API:          http://localhost:8000"
	@echo "  API Docs:     http://localhost:8000/docs"
	@echo "  Web:          http://localhost:3000"
	@echo "  Meilisearch:  http://localhost:7700"
	@echo "  Redis:        localhost:6379"
	@echo "  PostgreSQL:   localhost:5432"
	@echo ""

stop: ## Stop all services
	@echo "$(YELLOW)⏹  Stopping services...$(RESET)"
	$(DOCKER_COMPOSE) down

restart: ## Restart all services
	@echo "$(YELLOW)🔄 Restarting services...$(RESET)"
	$(DOCKER_COMPOSE) restart

logs: ## Tail all service logs
	$(DOCKER_COMPOSE) logs -f

logs-api: ## Tail API logs only
	$(DOCKER_COMPOSE) logs -f api

logs-worker: ## Tail pipeline worker logs
	$(DOCKER_COMPOSE) logs -f worker

# ═══════════════════════════════════════
# Building
# ═══════════════════════════════════════

build: ## Build all Docker images
	@echo "$(CYAN)🔨 Building all images...$(RESET)"
	$(DOCKER_COMPOSE) build

build-api: ## Build API image only
	$(DOCKER_COMPOSE) build api

build-worker: ## Build worker image only
	$(DOCKER_COMPOSE) build worker

build-web: ## Build web image only
	$(DOCKER_COMPOSE) build web

# ═══════════════════════════════════════
# Testing
# ═══════════════════════════════════════

test: ## Run all tests (inside Docker)
	@echo "$(CYAN)🧪 Running all tests...$(RESET)"
	$(DOCKER_COMPOSE) exec api python -m pytest apps/api/tests/ -v
	$(DOCKER_COMPOSE) exec worker python -m pytest packages/pipeline/tests/ -v
	@echo "$(GREEN)✅ All tests passed!$(RESET)"

test-unit: ## Run unit tests only (inside Docker)
	@echo "$(CYAN)🧪 Running unit tests...$(RESET)"
	$(DOCKER_COMPOSE) exec api python -m pytest apps/api/tests/unit/ -v
	$(DOCKER_COMPOSE) exec worker python -m pytest packages/pipeline/tests/unit/ -v

test-int: ## Run integration tests (inside Docker, requires services)
	@echo "$(CYAN)🧪 Running integration tests...$(RESET)"
	$(DOCKER_COMPOSE) exec api python -m pytest apps/api/tests/integration/ -v
	$(DOCKER_COMPOSE) exec worker python -m pytest packages/pipeline/tests/integration/ -v

test-ml: ## Run ML quality tests against golden dataset
	@echo "$(CYAN)🧪 Running ML quality benchmarks...$(RESET)"
	$(DOCKER_COMPOSE) exec worker python -m pytest packages/pipeline/tests/golden_data/ -v --tb=long

test-coverage: ## Run tests with coverage report
	@echo "$(CYAN)📊 Running tests with coverage...$(RESET)"
	$(DOCKER_COMPOSE) exec api python -m pytest apps/api/tests/ --cov=app --cov-report=html --cov-report=term
	$(DOCKER_COMPOSE) exec worker python -m pytest packages/pipeline/tests/ --cov=aqar_pipeline --cov-report=html --cov-report=term

test-local: ## Run tests locally (requires local venv with deps)
	@echo "$(CYAN)🧪 Running tests locally...$(RESET)"
	cd apps/api && $(PYTHON) -m pytest tests/ -v
	cd packages/pipeline && $(PYTHON) -m pytest tests/ -v

# ═══════════════════════════════════════
# Code Quality
# ═══════════════════════════════════════

lint: ## Run all linters (inside Docker)
	@echo "$(CYAN)🔍 Running linters...$(RESET)"
	$(DOCKER_COMPOSE) exec api ruff check apps/api/ packages/pipeline/ packages/db/
	@echo "$(GREEN)✅ Lint passed!$(RESET)"

format: ## Auto-format all code (inside Docker)
	@echo "$(CYAN)✨ Formatting code...$(RESET)"
	$(DOCKER_COMPOSE) exec api ruff format apps/api/ packages/pipeline/ packages/db/
	$(DOCKER_COMPOSE) exec api ruff check --fix apps/api/ packages/pipeline/ packages/db/
	@echo "$(GREEN)✅ Formatted!$(RESET)"

typecheck: ## Run type checkers (inside Docker)
	@echo "$(CYAN)🔍 Type checking...$(RESET)"
	$(DOCKER_COMPOSE) exec api mypy apps/api/app/

# ═══════════════════════════════════════
# Database
# ═══════════════════════════════════════

migrate: ## Run database migrations
	@echo "$(CYAN)🗄️  Running migrations...$(RESET)"
	cd apps/api && alembic upgrade head

migrate-create: ## Create a new migration (usage: make migrate-create MSG="add users table")
	cd apps/api && alembic revision --autogenerate -m "$(MSG)"

migrate-rollback: ## Rollback last migration
	cd apps/api && alembic downgrade -1

seed: ## Seed database with sample data
	@echo "$(CYAN)🌱 Seeding database...$(RESET)"
	cd apps/api && $(PYTHON) -m app.core.seed

reset: ## DROP ALL DATA and reset database from scratch
	@bash infra/scripts/reset-db.sh

# ═══════════════════════════════════════
# Utilities
# ═══════════════════════════════════════

health: ## Check health of all services
	@echo "$(CYAN)🏥 Checking service health...$(RESET)"
	@echo -n "  PostgreSQL: " && ($(DOCKER_COMPOSE) exec -T db pg_isready -U aqar > /dev/null 2>&1 && echo "$(GREEN)✅$(RESET)" || echo "$(YELLOW)❌$(RESET)")
	@echo -n "  Redis:      " && ($(DOCKER_COMPOSE) exec -T redis redis-cli ping > /dev/null 2>&1 && echo "$(GREEN)✅$(RESET)" || echo "$(YELLOW)❌$(RESET)")
	@echo -n "  Meilisearch:" && (curl -sf http://localhost:7700/health > /dev/null 2>&1 && echo "$(GREEN)✅$(RESET)" || echo "$(YELLOW)❌$(RESET)")
	@echo -n "  API:        " && (curl -sf http://localhost:8000/health > /dev/null 2>&1 && echo "$(GREEN)✅$(RESET)" || echo "$(YELLOW)❌$(RESET)")

shell-api: ## Open a shell in the API container
	$(DOCKER_COMPOSE) exec api /bin/bash

shell-db: ## Open psql shell
	$(DOCKER_COMPOSE) exec db psql -U aqar -d aqar_db

clean: ## Remove containers, volumes, and caches
	@echo "$(YELLOW)🧹 Cleaning up...$(RESET)"
	$(DOCKER_COMPOSE) down -v --remove-orphans
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name node_modules -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .next -exec rm -rf {} + 2>/dev/null || true
	@echo "$(GREEN)✅ Clean!$(RESET)"

install: ## Install all dependencies
	@echo "$(CYAN)📦 Installing dependencies...$(RESET)"
	$(PIP) install -e "apps/api[dev]"
	$(PIP) install -e "packages/pipeline[dev]"
	$(PIP) install -e "packages/db"
	cd apps/web && npm install
	@echo "$(GREEN)✅ All dependencies installed!$(RESET)"
