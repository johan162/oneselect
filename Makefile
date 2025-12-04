.PHONY: install setup clean-venv reinstall run test lint format typecheck migrate init-db check clean docs docs-serve
VERSION := $(shell grep '^version' pyproject.toml | head -1 | cut -d'"' -f2)

install:
	poetry install

setup: clean-venv install
	@echo "Virtual environment setup complete"

clean-venv:
	rm -rf .venv
	@echo "Virtual environment removed"

reinstall: clean-venv install
	@echo "Project reinstalled successfully"

run:
	poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

test:
	PYTHONPATH=. poetry run pytest

lint:
	poetry run flake8 app tests

format:
	poetry run black app tests

typecheck:
	poetry run mypy --explicit-package-bases .

migrate:
	poetry run alembic upgrade head

init-db:
	poetry run python app/initial_data.py

check: format lint typecheck test

clean:
	rm -rf .venv
	rm -rf .pytest_cache
	rm -rf .coverage
	rm -rf htmlcov
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete

docs:
	poetry run mkdocs build

docs-serve:
	poetry run mkdocs serve

# Container commands (using Podman)
.PHONY: container-build container-up container-down container-logs container-restart container-shell container-clean

container-build:
	podman-compose build
	podman tag oneselect-backend:latest oneselect-backend:$(VERSION)

container-up:
	podman-compose up -d

container-down:
	podman-compose down

container-logs:
	podman-compose logs -f

container-restart:
	podman-compose restart

container-shell:
	podman-compose exec oneselect-api /bin/bash

container-clean:
	podman-compose down -v
	podman system prune -f

# Alternative: using podman directly
.PHONY: podman-build podman-run podman-stop

podman-build:
	podman build -t oneselect-backend:latest .

podman-run:
	podman run -d \
		--name oneselect-backend \
		-p 8000:8000 \
		-v oneselect-data:/app/data:Z \
		-e SECRET_KEY=change-this-secret \
		oneselect-backend:latest

podman-stop:
	podman stop oneselect-backend
	podman rm oneselect-backend

