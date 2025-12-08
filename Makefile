.PHONY: help install clean-venv reinstall run test test-short test-param lint format typecheck migrate init-db check clean really-clean docs docs-serve container-build container-init container-up container-down container-logs container-restart container-shell container-clean container-volume-info container-rebuild

.DEFAULT_GOAL := help

# Make behavior
SHELL := /bin/bash
.DELETE_ON_ERROR:
.ONESHELL:

# Colors for output
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[1;33m
NC := \033[0m # No Color

# =====================================
# Prerequisites Check Functions
# =====================================

define check_poetry
	@command -v poetry >/dev/null 2>&1 || { echo "Error: poetry not found. Install with: pip install poetry"; exit 1; }
endef

define check_podman
	@command -v podman >/dev/null 2>&1 || { echo "Error: podman not found. Install with: brew install podman"; exit 1; }
endef

define check_podman_compose
	@command -v podman-compose >/dev/null 2>&1 || { echo "Error: podman-compose not found. Install with: brew install podman-compose"; exit 1; }
endef

# =====================================
# Variable configurations
# =====================================

# Directories
SRC_DIR := app
TEST_DIR := tests
DOCS_DIR := docs

# Server configuration
SERVER_HOST := 0.0.0.0
SERVER_PORT := 8000
DOCS_PORT := 8100

PROJECT := oneselect
APP_NAME := OneSelect
PYPI_NAME := oneselect_backend
VERSION := $(shell grep '^version' pyproject.toml | head -1 | cut -d'"' -f2)
CONTAINER_NAME := $(PROJECT)-backend
DB_FILE := $(PROJECT).db

# Source and Test Files
SRC_FILES := $(shell find $(SRC_DIR) -name '*.py')
TEST_FILES := $(shell find $(TEST_DIR) -name 'test_*.py')
DOC_FILES := $(shell find $(DOCS_DIR) -name '*.md' -o -name '*.yml' -o -name '*.yaml')
MISC_FILES := pyproject.toml poetry.lock README.md mypy.ini .flake8 alembic.ini mkdocs.yml
LOCK_FILE := poetry.lock

# Timestamp files
CONTAINER_STAMP := .container-stamp
DOC_STAMP := .docs-stamp
FORMAT_STAMP := .format-stamp
LINT_STAMP := .lint-stamp
TYPECHECK_STAMP := .typecheck-stamp
INSTALL_STAMP := .install-stamp

# Build files
BUILD_DIR := dist
BUILD_WHEEL := $(BUILD_DIR)/$(PYPI_NAME)-$(VERSION)-py3-none-any.whl
BUILD_SDIST := $(BUILD_DIR)/$(PYPI_NAME)-$(VERSION).tar.gz

# =====================================
# Timestamp dependencies
# =====================================

$(FORMAT_STAMP): $(SRC_FILES) $(TEST_FILES)
	@echo -e "$(YELLOW)Running code formatter...$(NC)"
	$(call check_poetry)
	@poetry run black $(SRC_DIR) $(TEST_DIR)
	@touch $(FORMAT_STAMP)

$(CONTAINER_STAMP): $(SRC_FILES) $(TEST_FILES) $(DOC_STAMP)
	@echo -e "$(YELLOW)Building container image...$(NC)"
	$(call check_podman)
	$(call check_podman_compose)
	@podman-compose build
	@podman tag oneselect-backend:latest oneselect-backend:$(VERSION)
	@touch $(CONTAINER_STAMP)

$(DOC_STAMP): $(DOC_FILES)
	@echo -e "$(YELLOW)Building documentation...$(NC)"
	$(call check_poetry)
	@poetry run mkdocs build
	@touch $(DOC_STAMP)

$(LINT_STAMP): $(SRC_FILES) $(TEST_FILES)
	@echo -e "$(YELLOW)Running linter...$(NC)"
	$(call check_poetry)
	@poetry run flake8 $(SRC_DIR) $(TEST_DIR)
	@touch $(LINT_STAMP)

$(TYPECHECK_STAMP): $(SRC_FILES) $(TEST_FILES)
	@echo -e "$(YELLOW)Running type checker...$(NC)"
	$(call check_poetry)
	@poetry run mypy --explicit-package-bases .
	@touch $(TYPECHECK_STAMP)

$(INSTALL_STAMP): pyproject.toml | poetry.lock
	@echo -e "$(YELLOW)Installing dependencies...$(NC)"
	$(call check_poetry)
	@poetry config virtualenvs.in-project true  ## make sure venv is created in project dir
	@poetry install
	@touch $(INSTALL_STAMP)

$(BUILD_WHEEL): $(SRC_FILES) $(TEST_FILES) $(MISC_FILES)
	@echo -e "$(YELLOW)Building project packages...$(NC)"
	$(call check_poetry)
	@poetry build

$(LOCK_FILE): pyproject.toml  ## Ensure poetry.lock is up to date if dependencies change
	@echo -e "$(YELLOW)Regenerating lock file to ensure consistency...$(NC)"
	$(call check_poetry)
	@poetry lock
	@touch $(LOCK_FILE)

$(DB_FILE): ## Setup the database if it does not exist
	@if [ ! -f $(DB_FILE) ]; then \
		$(MAKE) migrate; \
		$(MAKE) init-db; \
	fi

help: ## Show this help message
	@echo -e "$(BLUE)OneSelect - Makefile targets$(NC)"
	@echo -e ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN) %-18s$(NC) %s\n", $$1, $$2}'
	@echo -e ""

dev: $(INSTALL_STAMP) $(DB_FILE) ## Setup complete development environment
	@echo -e "$(GREEN)✓ Development environment ready!$(NC)"
	@echo -e "$(BLUE)Run 'make run' to start the server$(NC)"

install: $(INSTALL_STAMP) ## Install project dependencies and setup virtual environment
	@echo -e "$(GREEN)✓ Project dependencies installed$(NC)"

clean-venv: ## Remove the virtual environment
	@echo -e "$(YELLOW)Removing virtual environment...$(NC)"
	@rm -rf .venv
	@echo -e "$(GREEN)✓ Virtual environment removed$(NC)"

reinstall: clean-venv install ## Reinstall the project from scratch
	@echo -e "$(GREEN)✓ Project reinstalled successfully$(NC)"

# Note: Uses order-only prerequisite (|) so DB is created if missing but not rebuilt every time
run: | $(DB_FILE) ## Run the development server with auto-reload
	$(call check_poetry)
	@echo -e "$(BLUE)Starting development server on http://$(SERVER_HOST):$(SERVER_PORT)$(NC)"
	@poetry run uvicorn app.main:app --reload --host $(SERVER_HOST) --port $(SERVER_PORT)

test: $(INSTALL_STAMP) ## Run all tests with pytest in parallel
	$(call check_poetry)
	@poetry run pytest -n auto -v -s

test-short: $(INSTALL_STAMP) ## Run all tests with minimal output and no coverage
	$(call check_poetry)
	@poetry run pytest -n auto -q --no-cov

test-param: $(INSTALL_STAMP) ## Run parameterized integration tests
	$(call check_poetry)
	@poetry run pytest -n 0 tests/test_integration_parametrized.py::TestParameterizedWorkflow -v -s

lint: $(LINT_STAMP) ## Run linting checks with flake8
	@echo -e "$(GREEN)✓ Lint target runs successfully$(NC)"

format: $(FORMAT_STAMP) ## Format code with black
	@echo -e "$(GREEN)✓ Format target runs successfully$(NC)"

typecheck: $(TYPECHECK_STAMP) ## Run type checking with mypy
	@echo -e "$(GREEN)✓ Typecheck target runs successfully$(NC)"

migrate: ## Apply database migrations using Alembic
	@echo -e "$(YELLOW)Running database migrations...$(NC)"
	poetry run alembic upgrade head
	@echo -e "$(GREEN)✓ Migrations applied$(NC)"

init-db: ## Initialize the database with initial admin user
	@echo -e "$(YELLOW)Initializing database with default data...$(NC)"
	@poetry run python app/initial_data.py
	@echo -e "$(BLUE)Admin user created:$(NC)"
	@sqlite3 oneselect.db "SELECT id, username, email, role, is_active, is_superuser FROM users WHERE username = 'admin'" | while IFS= read -r line; do echo -e "$(BLUE)$$line$(NC)"; done
	@echo -e "$(GREEN)✓ Database initialized$(NC)"

check: format lint typecheck ## Run all checks: format, lint, and typecheck

build: check docs ${BUILD_WHEEL} ## Build the project packages
	@echo -e "$(GREEN)✓ 📦 Packages built: $(BUILD_WHEEL), $(BUILD_SDIST)$(NC)"

clean: ## Clean up build artifacts, caches, and timestamp files
	@echo -e "$(YELLOW)Cleaning build artifacts and caches...$(NC)"
	rm -rf .venv
	rm -rf .pytest_cache
	rm -rf .coverage
	rm -rf htmlcov
	rm -rf site
	rm -f $(FORMAT_STAMP) $(LINT_STAMP) $(TYPECHECK_STAMP) $(DOC_STAMP) $(INSTALL_STAMP)
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	@echo -e "$(GREEN)✓ Clean completed$(NC)"

really-clean: clean ## Perform a thorough cleanup including containers and database files
	@echo -e "$(YELLOW)Performing deep clean...$(NC)"
	@$(MAKE) container-clean 2>/dev/null || true
	rm -f $(CONTAINER_STAMP)
	rm -rf *.db
	@echo -e "$(GREEN)✓ Deep clean completed$(NC)"

docs: $(DOC_STAMP) ## Build the project documentation with MkDocs
	@echo -e "$(GREEN)✓ Documentation built successfully$(NC)"

docs-serve: docs ## Serve the project documentation locally with MkDocs
	$(call check_poetry)
	@echo -e "$(BLUE)Serving documentation on http://localhost:$(DOCS_PORT)$(NC)"
	@poetry run mkdocs serve -a localhost:$(DOCS_PORT)

# =====================================
# Container Management with Podman
# =====================================

container-build: $(CONTAINER_STAMP) ## Build the Podman container image for the application and tag it with the current version
	@echo -e "$(GREEN)✓ Container image built and tagged as oneselect-backend:$(VERSION)$(NC)"
	@echo -e "$(YELLOW)Tip: Run 'make container-up' to start, then 'make container-init' to initialize database$(NC)"

container-init: | $(CONTAINER_STAMP) ## Initialize the container environment, create volumes, and setup the database
	@if ! podman ps --format "{{.Names}}" | grep -q "oneselect-backend"; then \
		echo -e "$(YELLOW)Error: Container 'oneselect-backend' is not running. Run 'make container-up' first.$(NC)"; \
		exit 1; \
	fi
	@podman volume create $(PROJECT)_oneselect-data 2>/dev/null || true
	@if ! podman exec oneselect-backend test -f /app/data/oneselect.db 2>/dev/null; then \
		echo -e "$(YELLOW)Database not found. Initializing...$(NC)"; \
		podman exec oneselect-backend python -m alembic upgrade head; \
		podman exec oneselect-backend python app/initial_data.py; \
		echo -e "$(GREEN)✓ Database initialized successfully$(NC)"; \
	else \
		echo -e "$(GREEN)✓ Database already exists, skipping initialization$(NC)"; \
	fi

container-up: | $(CONTAINER_STAMP) ## Start the Podman container in detached mode
	@echo -e "$(YELLOW)Starting containers...$(NC)"
	podman-compose up -d
	@echo -e "$(GREEN)✓ Containers started$(NC)"

container-down: | $(CONTAINER_STAMP) ## Stop and remove the running container
	@echo -e "$(YELLOW)Stopping containers...$(NC)"
	podman-compose down
	@echo -e "$(GREEN)✓ Containers stopped$(NC)"

container-logs: | $(CONTAINER_STAMP) ## Follow the logs of the running container
	podman-compose logs -f

container-restart: | $(CONTAINER_STAMP) ## Restart the running container
	podman-compose restart

container-shell: | $(CONTAINER_STAMP) ## Open an interactive shell inside the running container
	podman-compose exec oneselect-backend /bin/bash

container-clean:  ## Remove all containers, images, and prune the Podman system
	podman-compose down -v
	podman system prune -f

container-clean-images: ## Remove all oneselect container images
	$(call check_podman)
	@echo -e "$(YELLOW)Removing all oneselect images...$(NC)"
	@podman rmi -f $$(podman images --filter "reference=oneselect*" -q) 2>/dev/null || true
	@echo -e "$(GREEN)✓ Images removed$(NC)"

container-volume-info: ## Inspect the Podman volume used for persistent data storage
	podman volume ls
	podman volume inspect $(PROJECT)_oneselect-data

container-rebuild: ## Rebuild container from scratch
	$(call check_podman)
	@echo -e "$(YELLOW)Rebuilding container from scratch...$(NC)"
	@$(MAKE) container-down || true
	@rm -f $(CONTAINER_STAMP)
	@$(MAKE) container-build
	@echo -e "$(GREEN)✓ Container rebuilt$(NC)"

# Alternative: using podman directly
# .PHONY: podman-build podman-run podman-stop

# podman-build:
# 	podman build -t oneselect-backend:latest .

# podman-run:
# 	podman run -d \
# 		--name oneselect-backend \
# 		-p 8000:8000 \
# 		-v oneselect-data:/app/data:Z \
# 		-e SECRET_KEY=change-this-secret \
# 		oneselect-backend:latest

# podman-stop:
# 	podman stop oneselect-backend
# 	podman rm oneselect-backend

