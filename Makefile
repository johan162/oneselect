# Makefile for OneSelect Backend Application
# JP 2024-12-10
# The structure for the Makefile is built on separating timestamp dependencies and command targets
# Each command target may depend on one or more timestamp files that encapsulate the logic for when
# to re-run certain tasks based on file changes.

.PHONY: help install clean-venv reinstall run test test-short test-param lint format typecheck migrate init-db check clean \
really-clean docs docs-serve container-build container-init container-up container-down container-logs container-restart \
container-shell container-clean container-volume-info container-rebuild ensure-poetry ensure-podman ensure-podman-compose

.DEFAULT_GOAL := help

# Make behavior
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
# Tool availability targets
# =====================================

ensure-poetry:
	$(call check_poetry)

ensure-podman:
	$(call check_podman)

ensure-podman-compose:
	$(call check_podman_compose)

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

$(FORMAT_STAMP): ensure-poetry $(SRC_FILES) $(TEST_FILES)
	@echo -e "$(DARKYELLOW)- Running code formatter...$(NC)"
	@poetry run black $(SRC_DIR) $(TEST_DIR)
	@touch $(FORMAT_STAMP)

$(CONTAINER_STAMP): ensure-podman ensure-podman-compose $(SRC_FILES)
	@echo -e "$(DARKYELLOW)- Building container image...$(NC)"
	@podman-compose build
	@podman tag oneselect-backend:latest oneselect-backend:$(VERSION)
	@touch $(CONTAINER_STAMP)

$(DOC_STAMP): ensure-poetry $(DOC_FILES)
	@echo -e "$(DARKYELLOW)- Building documentation...$(NC)"
	@poetry run mkdocs build
	@touch $(DOC_STAMP)

$(LINT_STAMP): ensure-poetry $(SRC_FILES) $(TEST_FILES)
	@echo -e "$(DARKYELLOW)- Running linter...$(NC)"
	@poetry run flake8 $(SRC_DIR) $(TEST_DIR)
	@touch $(LINT_STAMP)

$(TYPECHECK_STAMP): ensure-poetry $(SRC_FILES) $(TEST_FILES)
	@echo -e "$(DARKYELLOW)- Running type checker...$(NC)"
	@poetry run mypy --explicit-package-bases .
	@touch $(TYPECHECK_STAMP)

$(INSTALL_STAMP): ensure-poetry pyproject.toml poetry.lock
	@echo -e "$(DARKYELLOW)- Installing dependencies...$(NC)"
	@poetry config virtualenvs.in-project true  ## make sure venv is created in project dir
	@poetry install
	@touch $(INSTALL_STAMP)

$(BUILD_WHEEL): ensure-poetry $(SRC_FILES) $(TEST_FILES) $(MISC_FILES)
	@echo -e "$(DARKYELLOW)- Building project packages...$(NC)"
	@poetry build

$(LOCK_FILE): ensure-poetry pyproject.toml  ## Ensure poetry.lock is up to date if dependencies change
	@echo -e "$(DARKYELLOW)- Regenerating lock file to ensure consistency...$(NC)"
	@poetry lock
	@touch $(LOCK_FILE)

$(DB_FILE): ## Setup the database if it does not exist
	@if [ ! -f $(DB_FILE) ]; then \
		$(MAKE) migrate; \
		$(MAKE) init-db; \
	fi

# =====================================
# =====================================
# Command Targets
# =====================================
# =====================================

# =====================================
# Help Target
# =====================================
help: ## Show this help message
	@echo -e "$(BLUE)OneSelect - Makefile targets$(NC)"
	@echo -e ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN) %-18s$(NC) %s\n", $$1, $$2}'
	@echo -e ""

# =====================================
# Development Environment Targets
# =====================================
dev-setup: $(INSTALL_STAMP) $(DB_FILE) ## Setup complete development environment
	@echo -e "$(GREEN)✓ Development environment ready!$(NC)"
	@echo -e "$(YELLOW)- TIP! Run 'make run' to start the API-server directly$(NC)"
	@echo -e "$(YELLOW)- TIP! Run 'make container-up' to build and start the container with the API-server$(NC)"

install: $(INSTALL_STAMP) ## Install project dependencies and setup virtual environment
	@echo -e "$(GREEN)✓ Project dependencies installed$(NC)"

reinstall: clean-venv install ## Reinstall the project from scratch
	@echo -e "$(GREEN)✓ Project reinstalled successfully$(NC)"

# =====================================
# Running the Development Server
# =====================================
run: ensure-poetry | $(DB_FILE) ## Run the development server with auto-reload
	@echo -e "$(BLUE)Starting development server on http://$(SERVER_HOST):$(SERVER_PORT)$(NC)"
	@poetry run uvicorn app.main:app --reload --host $(SERVER_HOST) --port $(SERVER_PORT)

# =====================================
# Testing Targets
# =====================================
test: $(INSTALL_STAMP) ## Run all tests with pytest in parallel
	@poetry run pytest -n auto -v -s

test-short: $(INSTALL_STAMP) ## Run all tests with minimal output and no coverage
	@poetry run pytest -n auto -q --no-cov

test-param: $(INSTALL_STAMP) ## Run parameterized integration tests
	@poetry run pytest -n 0 tests/test_integration_parametrized.py::TestParameterizedWorkflow -v -s

# =====================================
# Database Migration Targets
# =====================================
migrate: ensure-poetry ## Apply database migrations using Alembic
	@echo -e "$(DARKYELLOW)- Running database migrations...$(NC)"
	poetry run alembic upgrade head
	@echo -e "$(GREEN)✓ Migrations applied$(NC)"

init-db: ensure-poetry ## Initialize the database with initial admin user
	@echo -e "$(DARKYELLOW)- Initializing database with default data...$(NC)"
	@poetry run python app/initial_data.py > /dev/null 2>&1 || { echo -e "$(RED)⚠️  Warning: Initial data script failed. It may have already been run.$(NC)"; }
	@echo -e "$(BLUE)- Admin user created:$(NC)"
	@sqlite3 oneselect.db "SELECT id, username, email, role, is_active, is_superuser FROM users WHERE username = 'admin'" | while IFS= read -r line; do echo -e "$(BLUE)- $$line$(NC)"; done
	@echo -e "$(GREEN)✓ Database initialized$(NC)"

# =====================================
# Code Quality Targets
# =====================================

lint: $(LINT_STAMP) ## Run linting checks with flake8
	@echo -e "$(GREEN)✓ Lint target runs successfully$(NC)"

format: $(FORMAT_STAMP) ## Format code with black
	@echo -e "$(GREEN)✓ Format target runs successfully$(NC)"

typecheck: $(TYPECHECK_STAMP) ## Run type checking with mypy
	@echo -e "$(GREEN)✓ Typecheck target runs successfully$(NC)"

check: format lint typecheck ## Run all checks: format, lint, and typecheck

# =====================================
# Build Package Targets
# =====================================
build: check docs ${BUILD_WHEEL} ## Build the project packages
	@echo -e "$(GREEN)✓ 📦 Packages built: $(BUILD_WHEEL), $(BUILD_SDIST)$(NC)"


# =====================================
# Cleanup Targets
# =====================================

clean-venv: ## Remove the virtual environment
	@echo -e "$(DARKYELLOW)- Removing virtual environment...$(NC)"
	@rm -rf .venv ${INSTALL_STAMP}
	@echo -e "$(GREEN)✓ Virtual environment removed$(NC)"

clean: ## Clean up build artifacts, caches, and timestamp files
	@echo -e "$(DARKYELLOW)- Cleaning build artifacts and caches...$(NC)"
	@rm -rf .pytest_cache
	@rm -rf .coverage
	@rm -rf htmlcov
	@rm -rf site
	@rm -rf .mypy_cache
	@rm -f $(FORMAT_STAMP) $(LINT_STAMP) $(TYPECHECK_STAMP) $(DOC_STAMP) 
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete
	@echo -e "$(GREEN)✓ Clean completed$(NC)"

maintainer-clean: ## Perform a thorough cleanup including virtual environment, containers and database files
	@echo -e "$(DARKYELLOW)- Performing deep clean...$(NC)"
	@$(MAKE) clean-venv 2>/dev/null || true
	@$(MAKE) clean 2>/dev/null || true
	@$(MAKE) container-clean 2>/dev/null || true
	@rm -rf *.db
	@echo -e "$(GREEN)✓ Deep clean completed$(NC)"

# =====================================
# Documentation Targets
# =====================================

docs: $(DOC_STAMP) ## Build the project documentation with MkDocs
	@echo -e "$(GREEN)✓ Documentation built successfully$(NC)"

docs-serve: ensure-poetry docs ## Serve the project documentation locally with MkDocs
	@echo -e "$(BLUE)Serving documentation on http://localhost:$(DOCS_PORT)$(NC)"
	@poetry run mkdocs serve -a localhost:$(DOCS_PORT)


# =====================================
# Container Management with Podman
# =====================================
container-build: $(CONTAINER_STAMP) ## Build the Podman container image for the application and tag it with the current version
	@echo -e "$(GREEN)✓ Container image built and tagged as oneselect-backend:$(VERSION)$(NC)"

container-up: ensure-podman-compose $(CONTAINER_STAMP) ## Start the Podman container in detached mode
	@echo -e "$(DARKYELLOW)- Starting containers...$(NC)"
	podman-compose up -d
	@echo -e "$(GREEN)✓ Containers started$(NC)"

container-down: ensure-podman-compose | $(CONTAINER_STAMP) ## Stop and remove the running container
	@echo -e "$(DARKYELLOW)- Stopping containers...$(NC)"
	@podman-compose down
	@echo -e "$(GREEN)✓ Containers stopped$(NC)"

container-logs: ensure-podman-compose | $(CONTAINER_STAMP) ## Follow the logs of the running container
	@podman-compose logs -f

container-restart: ensure-podman-compose | $(CONTAINER_STAMP) ## Restart the running container
	@podman-compose restart

container-shell: ensure-podman-compose | $(CONTAINER_STAMP) ## Open an interactive shell inside the running container
	@podman-compose exec oneselect-backend:latest /bin/bash

container-clean: container-clean-container-volumes container-clean-images ## Clean up all containers and images

container-clean-container-volumes: ensure-podman ensure-podman-compose ## Remove all containers, volumes and prune the Podman system
	@echo -e "$(DARKYELLOW)- Cleaning up containers and volumes...$(NC)"
	@podman-compose down -v
	@podman system prune -f
	@echo -e "$(GREEN)✓ Containers and volumes removed$(NC)"

container-clean-images: ensure-podman ## Remove all oneselect container images
	@echo -e "$(DARKYELLOW)- Removing all oneselect images...$(NC)"
	@podman rmi -f $$(podman images --filter "reference=oneselect*" -q) 2>/dev/null || true
	@rm -f $(CONTAINER_STAMP)
	@echo -e "$(GREEN)✓ Images removed$(NC)"

container-volume-info: ensure-podman ## Inspect the Podman volume used for persistent data storage'
	podman volume ls
	podman volume inspect $(PROJECT)_oneselect-data

container-rebuild: ensure-podman ## Rebuild container from scratch
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

