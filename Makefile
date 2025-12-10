# Makefile for OneSelect Backend Application
# The structure for the Makefile is built on separating timestamp dependencies and command targets
# Each command target may depend on one or more timestamp files that encapsulate the logic for when
# to re-run certain tasks based on file changes.

.PHONY: help dev install clean-venv reinstall run test test-short test-param test-html lint format typecheck migrate init-db check \
pre-commit clean maintainer-clean docs docs-serve build container-build container-up container-down container-logs \
container-restart container-shell container-clean container-clean-container-volumes container-clean-images \
container-volume-info container-rebuild ensure-poetry ensure-podman ensure-podman-compose \
ghcr-login

# Make behavior
.DEFAULT_GOAL := help
SHELL := /usr/bin/env bash
.DELETE_ON_ERROR:
.ONESHELL:

# Colors for output
BLACK := \033[0;30m
RED := \033[0;31m
GREEN := \033[0;32m
YELLOW := \033[1;33m
BLUE := \033[0;34m
MAGENTA := \033[0;35m
CYAN := \033[0;36m
WHITE := \033[1;37m

# Variations
DARKGRAY := \033[1;30m
BRIGHTRED := \033[1;31m
BRIGHTGREEN := \033[1;32m
DARKYELLOW := \033[0;33m
BRIGHTBLUE := \033[1;34m
BRIGHTMAGENTA := \033[1;35m
BRIGHTCYAN := \033[1;36m
LIGHTGRAY := \033[0;37m

# Formatting
BOLD := \033[1m
UNDERLINE := \033[4m

NC := \033[0m # No Color

# ============================================================================================
# Tool availability targets
# ============================================================================================
_ := $(if $(shell command -v poetry),,$(error "⚠️ Error: poetry not found. Install with: pip install poetry"))
_ := $(if $(shell command -v podman),,$(error "⚠️ Error: podman not found. Install with: brew install podman"))
_ := $(if $(shell command -v podman-compose),,$(error "⚠️ Error: podman-compose not found. Install with: brew install podman-compose"))

# ============================================================================================
# Variable configurations
# ============================================================================================

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
GHCR_LOGIN_STAMP := .ghcr-login-stamp

# Build package files
BUILD_DIR := dist
# Remove any hypen in PyPi specifi version number for wheel filename compliance
PYPI_VERSION := $(shell echo $(VERSION) | tr -d '-')
BUILD_WHEEL := $(BUILD_DIR)/$(PYPI_NAME)-$(PYPI_VERSION)-py3-none-any.whl
BUILD_SDIST := $(BUILD_DIR)/$(PYPI_NAME)-$(PYPI_VERSION).tar.gz

# ================================================================================================
# Timestamp dependencies
# ================================================================================================
$(TEST_STAMP): $(SRC_FILES) $(TEST_FILES)
	@echo -e "$(DARKYELLOW)- Running tests in parallel with coverage check...$(NC)"
	@if poetry run pytest -n auto --cov=app --cov-report= --cov-report=xml --cov-fail-under=${COVERAGE} -s -q; then \
		touch $(TEST_STAMP); \
		echo -e "$(GREEN)✓ All tests passed with required coverage$(NC)"; \
	else \
		echo -e "$(RED)✗ Error: Tests failed or coverage below ${COVERAGE}%$(NC)"; \
		exit 1; \
	fi

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
	@if poetry run mkdocs build -q; then \
		touch $(DOC_STAMP); \
		echo -e "$(GREEN)✓ Documentation built successfully$(NC)"; \
	else \
		echo -e "$(RED)✗ Error: Documentation build failed$(NC)"; \
		exit 1; \
	fi

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

$(BUILD_WHEEL) $(BUILD_SDIST): $(SRC_FILES) $(TEST_FILES) $(MISC_FILES)
	@echo -e "$(DARKYELLOW)- Building project packages...$(NC)"
	@if poetry build; then \
		echo -e "$(GREEN)✓ Packages built successfully$(NC)"; \
	else \
		echo -e "$(RED)✗ Error: Package build failed$(NC)"; \
		exit 1; \
	fi
	@echo -e "$(DARKYELLOW)- Verifying packages with twine...$(NC)"
	@if poetry run twine check dist/*; then \
		echo -e "$(GREEN)✓ 📦 Package verification passed$(NC)"; \
	else \
		echo -e "$(RED)✗ Error: Package verification failed$(NC)"; \
		exit 1; \
	fi

$(LOCK_FILE): pyproject.toml  ## Ensure poetry.lock is up to date if dependencies change
	@echo -e "$(DARKYELLOW)- Regenerating lock file to ensure consistency...$(NC)"
	@poetry lock
	@touch $(LOCK_FILE)

$(DB_FILE): ## Setup the database if it does not exist
	@if [ ! -f $(DB_FILE) ]; then \
		$(MAKE) migrate; \
		$(MAKE) init-db; \
	fi

$(GHCR_LOGIN_STAMP): 
	@if [ -z "$(GHCR_TOKEN)" ]; then \
		echo -e "$(RED)✗ Error: GHCR_TOKEN environment variable is not se. Please set GHCR_TOKEN with a valid GitHub Personal Access Token.$(NC)"; \
		exit 1; \
	fi
	@if [ -f $(GHCR_LOGIN_STAMP) ] && [ $$(find $(GHCR_LOGIN_STAMP) -mmin -120) ]; then \
		echo -e "$(GREEN)✓ Already logged in to GHCR recently.$(NC)"; \
		exit 0; \
	else \
		echo -e "$(DARKYELLOW)- Logging in to GitHub Container Registry...$(NC)"; \
		if podman login ghcr.io -u $(GITHUB_USER) -p $(GHCR_TOKEN) >/dev/null 2>&1; then \
			echo -e "$(GREEN)✓ Login to GitHub successful!$(NC)"; \
			touch $(GHCR_LOGIN_STAMP) ; \
		else \
			echo -e "$(RED)✗ Login failed. Please check your GHCR_TOKEN.$(NC)"; \
			rm -f $(GHCR_LOGIN_STAMP); \
			exit 1; \
		fi \
	fi	
	




# ============================================================================================
# Help Target
# ============================================================================================

# Defines a function to print a section of the help message.
# Arg 1: Section title
# Arg 2: A pipe-separated list of targets for the section
define print_section
	@echo ""
	@echo -e "$(BRIGHTCYAN)$1:$(NC)"
	@grep -E '^($(2)):.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(BLUE)%-22s$(NC) %s\n", $$1, $$2}' | sort
endef

help: ## Show this help message
	@echo -e "$(DARKYELLOW)OneSelect - Makefile Targets$(NC)"
	@$(call print_section,Project Setup & Development,dev|install|reinstall|run)
	@$(call print_section,Code Quality,check|lint|format|typecheck|pre-commit)
	@$(call print_section,Testing,test|test-short|test-param|test-html)
	@$(call print_section,Database,migrate|init-db)
	@$(call print_section,Build & Documentation,build|docs|docs-serve|docs-deploy)
	@$(call print_section,Container Management,container-build|container-up|container-down|container-logs|container-restart|container-shell|container-rebuild|container-volume-info|container-clean)
	@$(call print_section,Cleanup,clean|clean-venv|maintainer-clean)
	@$(call print_section,GitHub Container Registry,ghcr-login|ghcr-logout|ghcr-push)
	@echo ""

# ============================================================================================
# Development Environment Targets
# ============================================================================================
dev: $(INSTALL_STAMP) $(DB_FILE) ## Setup complete development environment
	@echo -e "$(GREEN)✓ Development environment ready!$(NC)"
	@echo -e "$(YELLOW)- TIP! $(BLUE)Run 'make test' to verify, 'make run' to start the server, or 'make container-up' for containerized deployment$(NC)"

install: $(INSTALL_STAMP) ## Install project dependencies and setup virtual environment
	@:

reinstall: clean-venv clean install ## Reinstall the project from scratch
	@echo -e "$(GREEN)✓ Project reinstalled successfully$(NC)"

# ============================================================================================
# Run the API Development Server Locally
# ============================================================================================
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

# ============================================================================================
# Database Migration Targets
# ============================================================================================
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

# ============================================================================================
# Code Quality Targets
# ============================================================================================
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

# ============================================================================================
# Build Package Targets
# ============================================================================================
build: $(INSTALL_STAMP) check test docs $(BUILD_WHEEL) $(BUILD_SDIST) ## Build the project packages
	@:

# ============================================================================================
# Cleanup Targets
# ============================================================================================
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

# ============================================================================================
# Documentation Targets
# ============================================================================================
docs: $(DOC_STAMP) ## Build the project documentation with MkDocs
	@:

docs-serve: docs ## Serve the project documentation locally with MkDocs
	@echo -e "$(BLUE)Serving documentation on http://localhost:$(DOCS_PORT)$(NC)"
	@poetry run mkdocs serve -a localhost:$(DOCS_PORT)

docs-deploy: ## Build and deploy documentation to GitHub Pages
	@echo -e "$(DARKYELLOW)- Deploying documentation to GitHub Pages...$(NC)"
	@if poetry run mkdocs gh-deploy --force; then \
		echo -e "$(GREEN)✓ Documentation deployed successfully$(NC)"; \
	else \
		echo -e "$(RED)✗ Error: Documentation deployment failed$(NC)"; \
		exit 1; \
	fi

# ============================================================================================
# Container Management with Podman
# ============================================================================================
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

container-clean-images: container-down ## Remove all oneselect container images
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

# ============================================================================================
# GitHub Container Registry Targets
# ============================================================================================
ghcr-login: $(GHCR_LOGIN_STAMP) ## Login to GitHub Container Registry via Podman

ghcr-push: $(GHCR_LOGIN_STAMP) $(CONTAINER_STAMP)  ## Push container image to GitHub Container Registry
	@if [ -z "$(GITHUB_USER)" ]; then \
        echo -e "$(RED)✗ Error: GITHUB_USER environment variable is not set."; \
        echo -e "  Please set GITHUB_USER as an environment variable or add as argument: make container-push GITHUB_USER=\"XXXXX\"$(NC)"; \
        exit 1; \
	fi
	@echo -e "$(DARKYELLOW)- Checking if image version $(VERSION) already exists on GHCR...$(NC)"
	@if podman manifest inspect ghcr.io/$(GITHUB_USER)/$(CONTAINER_NAME):$(VERSION) >/dev/null 2>&1; then \
        echo -e "$(YELLOW)⚠️  Warning: Image $(CONTAINER_NAME):$(VERSION) already exists in the registry. Skipping push.$(NC)"; \
        exit 1; \
    fi
	@echo -e "$(DARKYELLOW)- Pushing image $(CONTAINER_NAME):$(VERSION) and tagging as latest to GitHub Container Registry...$(NC)"
	@podman tag $(CONTAINER_NAME):$(VERSION) ghcr.io/$(GITHUB_USER)/$(CONTAINER_NAME):$(VERSION)
	@podman tag $(CONTAINER_NAME):$(VERSION) ghcr.io/$(GITHUB_USER)/$(CONTAINER_NAME):latest
	@if podman push ghcr.io/$(GITHUB_USER)/$(CONTAINER_NAME):$(VERSION) && podman push ghcr.io/$(GITHUB_USER)/$(CONTAINER_NAME):latest; then \
        echo -e "$(GREEN)✓ Image pushed successfully.$(NC)"; \
	else \
        echo -e "$(RED)✗ Error: Failed to push image to GHCR.$(NC)"; \
        exit 1; \
    fi

ghcr-logout: ## Logout from GitHub Container Registry
	@if [ ! -f $(GHCR_LOGIN_STAMP) ]; then \
		echo -e "$(YELLOW)⚠️  Warning: Not logged in to GHCR. Skipping logout.$(NC)"; \
		exit 1; \
	fi
	@echo -e "$(DARKYELLOW)- Logging out from GitHub Container Registry...$(NC)"
	@podman logout ghcr.io
	@rm -f $(GHCR_LOGIN_STAMP)
	@echo -e "$(GREEN)✓ Logged out from GHCR$(NC)"

ghcr-clean: ghcr-logout container-clean-images ## Clean up GHCR login and local images
	@:


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

