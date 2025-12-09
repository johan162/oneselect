# Makefile for OneSelect Backend Application
# The structure for the Makefile is built on separating timestamp dependencies and command targets
# Each command target may depend on one or more timestamp files that encapsulate the logic for when
# to re-run certain tasks based on file changes.

.PHONY: help dev install clean-venv reinstall run test test-short test-param test-html lint format typecheck migrate init-db check \
pre-commit clean maintainer-clean docs docs-serve build container-build container-up container-down container-logs \
container-restart container-shell container-clean container-clean-container-volumes container-clean-images \
container-volume-info container-rebuild ensure-poetry ensure-podman ensure-podman-compose

# Make behavior
.DEFAULT_GOAL := help
SHELL := /usr/bin/env bash
.DELETE_ON_ERROR:
.ONESHELL:

# Colors for output
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[1;33m
DARKYELLOW := \033[0;33m
RED := \033[0;31m
NC := \033[0m # No Color

# =====================================
# Tool availability targets
# =====================================
_ := $(if $(shell command -v poetry),,$(error "⚠️ Error: poetry not found. Install with: pip install poetry"))
_ := $(if $(shell command -v podman),,$(error "⚠️ Error: podman not found. Install with: brew install podman"))
_ := $(if $(shell command -v podman-compose),,$(error "⚠️ Error: podman-compose not found. Install with: brew install podman-compose"))

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

# Project settings
PROJECT := oneselect
APP_NAME := OneSelect
PYPI_NAME := oneselect_backend
VERSION := $(shell grep '^version' pyproject.toml | head -1 | cut -d'"' -f2)
CONTAINER_NAME := $(PROJECT)-backend
SERVICE_NAME := $(PROJECT)-api
DB_FILE := $(PROJECT).db

# Minimum coverage percentage required
COVERAGE := 80

# Source and Test Files
SRC_FILES := $(shell find $(SRC_DIR) -name '*.py')
TEST_FILES := $(shell find $(TEST_DIR) -name 'test_*.py')
DOC_FILES := mkdocs.yml $(shell find $(DOCS_DIR) -name '*.md' -o -name '*.yml' -o -name '*.yaml')
MISC_FILES := pyproject.toml poetry.lock README.md mypy.ini .flake8 alembic.ini 
LOCK_FILE := poetry.lock

# Timestamp files
CONTAINER_STAMP := .container-stamp
DOC_STAMP := .docs-stamp
FORMAT_STAMP := .format-stamp
LINT_STAMP := .lint-stamp
TYPECHECK_STAMP := .typecheck-stamp
INSTALL_STAMP := .install-stamp
TEST_STAMP := .test-stamp

# Build package files
BUILD_DIR := dist
BUILD_WHEEL := $(BUILD_DIR)/$(PYPI_NAME)-$(VERSION)-py3-none-any.whl
BUILD_SDIST := $(BUILD_DIR)/$(PYPI_NAME)-$(VERSION).tar.gz

# ================================================================================================
# Timestamp dependencies
# ================================================================================================
$(TEST_STAMP): $(SRC_FILES) $(TEST_FILES)
	@echo -e "$(DARKYELLOW)- Running tests in parallel with coverage check...$(NC)"
	@poetry run pytest -n auto --cov=app --cov-report= --cov-report=xml --cov-fail-under=${COVERAGE} -s -q
	@touch $(TEST_STAMP)
	@echo -e "$(GREEN)✓ All tests passed with required coverage$(NC)"

$(FORMAT_STAMP): $(SRC_FILES) $(TEST_FILES)
	@echo -e "$(DARKYELLOW)- Running code formatter...$(NC)"
	@poetry run black $(SRC_DIR) $(TEST_DIR) -q
	@touch $(FORMAT_STAMP)
	@echo -e "$(GREEN)✓ Format target runs successfully$(NC)"

$(CONTAINER_STAMP): $(SRC_FILES)
	@echo -e "$(DARKYELLOW)- Building container image...$(NC)"
	@podman-compose build
	@podman tag oneselect-backend:latest oneselect-backend:$(VERSION)
	@touch $(CONTAINER_STAMP)
	@echo -e "$(GREEN)✓ Container image built and tagged as oneselect-backend:$(VERSION)$(NC)"

$(DOC_STAMP): $(DOC_FILES)
	@echo -e "$(DARKYELLOW)- Building documentation...$(NC)"
	@poetry run mkdocs build -q
	@touch $(DOC_STAMP)
	@echo -e "$(GREEN)✓ Documentation built successfully$(NC)"

$(LINT_STAMP): $(SRC_FILES) $(TEST_FILES)
	@echo -e "$(DARKYELLOW)- Running linter...$(NC)"
	@poetry run flake8 $(SRC_DIR) $(TEST_DIR)
	@touch $(LINT_STAMP)
	@echo -e "$(GREEN)✓ Lint run successfully$(NC)"

$(TYPECHECK_STAMP): $(SRC_FILES) $(TEST_FILES)
	@echo -e "$(DARKYELLOW)- Running type checker...$(NC)"
	@poetry run mypy --explicit-package-bases .
	@touch $(TYPECHECK_STAMP)
	@echo -e "$(GREEN)✓ Typecheck target runs successfully$(NC)"

$(INSTALL_STAMP): pyproject.toml $(LOCK_FILE)
	@echo -e "$(DARKYELLOW)- Installing dependencies...$(NC)"
	@poetry config virtualenvs.in-project true  ## make sure venv is created in project dir
	@poetry install
	@cp .env.example .env 2>/dev/null || true  ## copy example env if .env does not exist
	@sleep 1  ## ensure timestamp difference
	@touch $(INSTALL_STAMP)
	@echo -e "$(GREEN)✓ Project dependencies installed$(NC)"

$(BUILD_WHEEL): $(SRC_FILES) $(TEST_FILES) $(MISC_FILES)
	@echo -e "$(DARKYELLOW)- Building project packages...$(NC)"
	@poetry build
	@echo -e "$(GREEN)✓ 📦 Packages built: $(BUILD_WHEEL), $(BUILD_SDIST)$(NC)"

$(LOCK_FILE): pyproject.toml  ## Ensure poetry.lock is up to date if dependencies change
	@echo -e "$(DARKYELLOW)- Regenerating lock file to ensure consistency...$(NC)"
	@poetry lock
	@touch $(LOCK_FILE)

$(DB_FILE): ## Setup the database if it does not exist
	@if [ ! -f $(DB_FILE) ]; then \
		$(MAKE) migrate; \
		$(MAKE) init-db; \
	fi

# ================================================================================================
# Command Targets
# ================================================================================================

# =====================================
# Help Target
# =====================================

# Defines a function to print a section of the help message.
# Arg 1: Section title
# Arg 2: A pipe-separated list of targets for the section
define print_section
	@echo ""
	@echo -e "$(DARKYELLOW)$1:$(NC)"
	@grep -E '^($(2)):.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-22s$(NC) %s\n", $$1, $$2}' | sort
endef

help: ## Show this help message
	@echo -e "$(BLUE)OneSelect - Makefile Targets$(NC)"
	@$(call print_section,Project Setup & Development,dev|install|reinstall|run)
	@$(call print_section,Code Quality,check|lint|format|typecheck|pre-commit)
	@$(call print_section,Testing,test|test-short|test-param|test-html)
	@$(call print_section,Database,migrate|init-db)
	@$(call print_section,Build & Documentation,build|docs|docs-serve)
	@$(call print_section,Container Management,container-build|container-up|container-down|container-logs|container-restart|container-shell|container-rebuild|container-volume-info|container-clean)
	@$(call print_section,Cleanup,clean|clean-venv|maintainer-clean)
	@echo ""

# =====================================
# Development Environment Targets
# =====================================
dev: $(INSTALL_STAMP) $(DB_FILE) ## Setup complete development environment
	@echo -e "$(GREEN)✓ Development environment ready!$(NC)"
	@echo -e "$(YELLOW)- TIP! $(BLUE)Run 'make test' to verify, 'make run' to start the server, or 'make container-up' for containerized deployment$(NC)"

install: $(INSTALL_STAMP) ## Install project dependencies and setup virtual environment
	@:

reinstall: clean-venv clean install ## Reinstall the project from scratch
	@echo -e "$(GREEN)✓ Project reinstalled successfully$(NC)"

# =====================================
# Running the Development Server
# =====================================
run: | $(DB_FILE) ## Run the development server with auto-reload
	@echo -e "$(BLUE)Starting development server on http://$(SERVER_HOST):$(SERVER_PORT)$(NC)"
	@poetry run uvicorn app.main:app --reload --host $(SERVER_HOST) --port $(SERVER_PORT)

# =============================================================================================
# Testing Targets
# The targets: test-short, test-param, and test-html will always be run on invocation.
# Plain test target wilkl ony be run when needed (source- or test-file changes)
# =============================================================================================
test: $(INSTALL_STAMP) $(TEST_STAMP) ## Run tests in parallel, terminal coverage report
	@:

test-short: $(INSTALL_STAMP) ## Run tests in parallel with minimal output, no coverage
	@echo -e "$(DARKYELLOW)- Starting short test without coverage...$(NC)"	
	@poetry run pytest -n auto -q --no-cov

test-param: $(INSTALL_STAMP) ## Run parameterized integration tests, no coverage
	@echo -e "$(DARKYELLOW)- Starting parameterized integration tests...$(NC)"
	@poetry run pytest -n 0 --no-cov tests/test_integration_parametrized.py::TestParameterizedWorkflow -s

test-html: $(INSTALL_STAMP) ## Run tests in parallel, HTML & XML coverage report
	@echo -e "$(DARKYELLOW)- Starting parallel test coverage...$(NC)"
	@poetry run pytest -q -n auto --cov=app --cov-report=xml --cov-report=html --cov-fail-under=${COVERAGE}
	@echo -e "$(GREEN)✓ Test coverage report generated at \"htmlcov/index.html\"$(NC)"

# =====================================
# Database Migration Targets
# =====================================
migrate: ## Apply database migrations using Alembic
	@echo -e "$(DARKYELLOW)- Running database migrations...$(NC)"
	poetry run alembic upgrade head
	@echo -e "$(GREEN)✓ Migrations applied$(NC)"

init-db: $(INSTALL_STAMP) ## Initialize the database with initial admin user
	@echo -e "$(DARKYELLOW)- Initializing database with default data...$(NC)"
	@TMP_LOG=$$(mktemp); \
	if ! poetry run python app/initial_data.py > "$$TMP_LOG" 2>&1; then \
		echo -e "$(RED)⚠️  Warning: Initial data script failed. It may have already been run. See details below:$(NC)"; \
		cat "$$TMP_LOG"; \
	fi; \
	rm -f "$$TMP_LOG"
	@echo -e "$(BLUE)Admin user in database:$(NC)"
	@sqlite3 oneselect.db "SELECT id, username, email, role, is_active, is_superuser FROM users WHERE username = 'admin'" | while IFS= read -r line; do echo -e "$(BLUE)  $$line$(NC)"; done
	@echo -e "$(GREEN)✓ Database initialized$(NC)"

# =====================================
# Code Quality Targets
# =====================================
check: format lint typecheck ## Run all code quality checks
	@:

lint: $(LINT_STAMP) ## Run linting checks with flake8
	@:

format: $(FORMAT_STAMP) ## Format code with black
	@:

typecheck: $(TYPECHECK_STAMP) ## Run type checking with mypy
	@:

pre-commit: $(INSTALL_STAMP) ## Run pre-commit checks (format, lint, typecheck)
	@echo -e "$(DARKYELLOW)Running pre-commit checks...$(NC)"
	@$(MAKE) check
	@$(MAKE) test-short
	@echo -e "$(GREEN)✓ All pre-commit checks passed$(NC)"

# =====================================
# Build Package Targets
# =====================================
build: $(INSTALL_STAMP) check test docs $(BUILD_WHEEL) ## Build the project packages
	@:

# =====================================
# Cleanup Targets
# =====================================
clean-venv: ## Remove the virtual environment
	@echo -e "$(DARKYELLOW)- Removing virtual environment...$(NC)"
	@rm -rf .venv ${INSTALL_STAMP}
	@echo -e "$(GREEN)✓ Virtual environment removed$(NC)"

clean: ## Clean up build artifacts, caches, and timestamp files. Keep the .venv intact.
	@echo -e "$(DARKYELLOW)- Cleaning build artifacts and caches...$(NC)"
	@rm -rf .pytest_cache
	@rm -rf .coverage coverage.xml
	@rm -rf htmlcov
	@rm -rf site dist
	@rm -rf .mypy_cache
	@rm -f $(FORMAT_STAMP) $(LINT_STAMP) $(TYPECHECK_STAMP) $(DOC_STAMP) $(TEST_STAMP)
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete
	@echo -e "$(GREEN)✓ Clean completed$(NC)"

maintainer-clean: ## Perform a thorough cleanup including virtual environment, containers and database files
	@echo -e "$(DARKYELLOW)- Performing deep clean...$(NC)"
	@$(MAKE) clean-venv
	@$(MAKE) clean
	-@$(MAKE) container-clean 2>/dev/null
	@rm -rf *.db .env
	@echo -e "$(GREEN)✓ Deep clean completed$(NC)"

# =====================================
# Documentation Targets
# =====================================
docs: $(DOC_STAMP) ## Build the project documentation with MkDocs
	@:

docs-serve: docs ## Serve the project documentation locally with MkDocs
	@echo -e "$(BLUE)Serving documentation on http://localhost:$(DOCS_PORT)$(NC)"
	@poetry run mkdocs serve -a localhost:$(DOCS_PORT)


# =====================================
# Container Management with Podman
# =====================================
container-build: $(CONTAINER_STAMP) ## Build the Podman container image for the application and tag it with the current version
	@:

container-up: $(CONTAINER_STAMP) ## Start the Podman container in detached mode
	@echo -e "$(DARKYELLOW)- Starting containers...$(NC)"
	podman-compose up -d
	@echo -e "$(GREEN)✓ Containers started$(NC)"

container-down: $(CONTAINER_STAMP) ## Stop and remove the running container
	@echo -e "$(DARKYELLOW)- Stopping containers...$(NC)"
	@podman-compose down
	@echo -e "$(GREEN)✓ Containers stopped$(NC)"

container-logs: $(CONTAINER_STAMP) ## Follow the logs of the running container
	@podman-compose logs -f

container-restart: $(CONTAINER_STAMP) ## Restart the running container
	@echo -e "$(DARKYELLOW)- Restarting containers...$(NC)"
	@podman-compose restart
	@echo -e "$(GREEN)✓ Containers restarted$(NC)"

container-shell: $(CONTAINER_STAMP) ## Open an interactive shell inside the running container
	@podman-compose exec $(SERVICE_NAME) /bin/shz

container-clean: container-clean-container-volumes container-clean-images ## Clean up all containers and images

container-clean-container-volumes: ## Remove all containers, volumes and prune the Podman system
	@echo -e "$(DARKYELLOW)- Cleaning up containers and volumes...$(NC)"
	@podman-compose down -v
	@podman system prune -f
	@echo -e "$(GREEN)✓ Containers and volumes removed$(NC)"

container-clean-images: ## Remove all oneselect container images
	@echo -e "$(DARKYELLOW)- Removing all oneselect images...$(NC)"
	@podman rmi -f $$(podman images --filter "reference=oneselect*" -q) 2>/dev/null || true
	@rm -f $(CONTAINER_STAMP)
	@echo -e "$(GREEN)✓ Images removed$(NC)"

container-volume-info: ## Inspect the Podman volume used for persistent data storage
	@echo -e "$(DARKYELLOW)- Listing Podman volumes...$(NC)"
	podman volume ls
	podman volume inspect $(PROJECT)_oneselect-data

container-rebuild: ## Rebuild container from scratch
	@echo -e "$(DARKYELLOW)- Rebuilding container from scratch...$(NC)"
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

