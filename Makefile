.PHONY: install setup clean-venv reinstall run test test-param lint format typecheck migrate init-db check clean docs docs-serve container-build container-up container-down container-logs container-restart container-shell container-clean

# Colors for output
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[1;33m
NC := \033[0m # No Color

# =====================================
# Prerequisites Check
# =====================================
# Add pre-req check that podman is installed
ifeq (, $(shell which podman))
$(error No podman found. Please install podman to build and run containers. "brew install podman" on macOS)
endif

# Check if poetry is installed
ifeq (, $(shell which poetry))
$(error No poetry found. Please install poetry to manage dependencies. "pip install poetry" or "brew install poetry" on macOS)
endif

# =====================================
# Variable configurations
# =====================================

# Directories
SRC_DIR := app
TEST_DIR := tests
DOCS_DIR := docs

# DB - file. NOTE: Also configured in .env.example and podman-compose.yml
DB_FILE := oneselect.db
VERSION := $(shell grep '^version' pyproject.toml | head -1 | cut -d'"' -f2)
PROJECT := oneselect

# Source and Test Files
SRC_FILES := $(shell find $(SRC_DIR) -name '*.py')
TEST_FILES := $(shell find $(TEST_DIR) -name 'test_*.py')
DOC_FILES := $(shell find $(DOCS_DIR) -name '*.md' -o -name '*.yml' -o -name '*.yaml')

# Timestamp files
CONTAINER_STAMP := .container-stamp
DOC_STAMP := .docs-stamp
FORMAT_STAMP := .format-stamp
LINT_STAMP := .lint-stamp
TYPECHECK_STAMP := .typecheck-stamp
INSTALL_STAMP := .install-stamp

# =====================================
# Timestamp dependencies
# =====================================

$(FORMAT_STAMP): $(SRC_FILES) $(TEST_FILES)
	poetry run black $(SRC_DIR) $(TEST_DIR)
	touch $(FORMAT_STAMP)

$(CONTAINER_STAMP): $(SRC_FILES) $(TEST_FILES) $(DOC_STAMP)
	podman-compose build
	podman tag oneselect-backend:latest oneselect-backend:$(VERSION)
	touch $(CONTAINER_STAMP)

$(DOC_STAMP): $(DOC_FILES)
	poetry run mkdocs build
	touch $(DOC_STAMP)

$(LINT_STAMP): $(SRC_FILES) $(TEST_FILES)
	poetry run flake8 $(SRC_DIR) $(TEST_DIR)
	touch $(LINT_STAMP)

$(TYPECHECK_STAMP): $(SRC_FILES) $(TEST_FILES)
	poetry run mypy --explicit-package-bases .
	touch $(TYPECHECK_STAMP)

$(INSTALL_STAMP): pyproject.toml poetry.lock
	poetry install
	touch $(INSTALL_STAMP)

$(DB_FILE): migrate init-db

help: ## Show this help message
	@echo "$(BLUE)OneSelect - Makefile targets$(NC)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN) %-18s$(NC) %s\n", $$1, $$2}'
	@echo ""


install: $(INSTALL_STAMP) ## Install project dependencies and setup virtual environment
	@echo "Project dependencies installed"

clean-venv: ## Remove the virtual environment
	rm -rf .venv
	@echo "Virtual environment removed"

reinstall: clean-venv install ## Reinstall the project from scratch
	@echo "Project reinstalled successfully"

run: | $(DB_FILE) ## Run the development server with auto-reload
	poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

test: ## Run all tests with pytest in parallel
	poetry run pytest -n auto -v -s

test-param: ## Run parameterized integration tests
	poetry run pytest -n 0 tests/test_integration_parametrized.py::TestParameterizedWorkflow -v -s

lint: $(LINT_STAMP) ## Run linting checks with flake8
	@echo "$(GREEN)✓ Lint target runs successfully$(NC)"

format: $(FORMAT_STAMP) ## Format code with black
	@echo "$(GREEN)✓ Format target runs successfully$(NC)"

typecheck: $(TYPECHECK_STAMP) ## Run type checking with mypy
	@echo "$(GREEN)✓ Typecheck target runs successfully$(NC)"

migrate: ## Apply database migrations using Alembic
	poetry run alembic upgrade head

init-db: ## Initialize the database with initial admin user
	poetry run python app/initial_data.py

check: format lint typecheck ## Run all checks: format, lint, and typecheck

clean: ## Clean up build artifacts, virtual environment, and temporary files
	rm -rf .venv
	rm -rf .pytest_cache
	rm -rf .coverage
	rm -rf htmlcov
	rm -rf site
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete

really-clean: clean container-clean ## Perform a thorough cleanup including timestamp files, containers, and database files
	podman-compose down -v
	podman system prune -f
	rm -f $(CONTAINER_STAMP) $(DOC_STAMP) $(FORMAT_STAMP) $(LINT_STAMP) $(TYPECHECK_STAMP)
	rm -rf *.db

docs: $(DOC_STAMP) ## Build the project documentation with MkDocs
	@echo "$(GREEN)✓ Documentation built successfully$(NC)"

docs-serve: ## Serve the project documentation locally with MkDocs
	poetry run mkdocs serve -a localhost:8100

# =====================================
# Container Management with Podman
# =====================================

container-build: $(CONTAINER_STAMP) container-init ## Build the Podman container image for the application and tag it with the current version
	@echo "$(GREEN)✓ Container image built and tagged as oneselect-backend:$(VERSION)$(NC)"

container-init: ## Initialize the container environment, create volumes, and setup the database
	@podman volume create $(PROJECT)_oneselect-data 2>/dev/null || true
	@if ! podman exec oneselect-backend test -f /app/data/oneselect.db 2>/dev/null; then \
		echo "$(YELLOW)Database not found. Initializing...$(NC)"; \
		podman exec oneselect-backend python -m alembic upgrade head; \
		podman exec oneselect-backend python app/initial_data.py; \
		echo "$(GREEN)✓ Database initialized successfully$(NC)"; \
	else \
		echo "$(GREEN)✓ Database already exists, skipping initialization$(NC)"; \
	fi

container-up: $(CONTAINER_STAMP) ## Start the Podman container in detached mode
	podman-compose up -d

container-down: ## Stop and remove the running container
	podman-compose down

container-logs: ## Follow the logs of the running container
	podman-compose logs -f

container-restart: ## Restart the running container
	podman-compose restart

container-shell: ## Open an interactive shell inside the running container
	podman-compose exec oneselect-backend /bin/bash

container-clean: ## Remove all containers, volumes, and prune the Podman system
	podman-compose down -v
	podman system prune -f

container-volume-info: ## Inspect the Podman volume used for persistent data storage
	podman volume ls
	podman volume inspect $(PROJECT)_oneselect-data

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

