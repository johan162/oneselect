# OneSelect API

Welcome to the OneSelect API documentation.

## Overview

OneSelect is a pairwise comparison system.

## Getting Started

1. Install dependencies: `poetry install`
2. Run migrations: `poetry run alembic upgrade head`
3. Create initial data: `poetry run python app/initial_data.py`
4. Run server: `poetry run uvicorn app.main:app --reload`

## Documentation Structure

- **[Introduction](introduction.md)** - System overview and getting started
- **[Authentication](authentication.md)** - User authentication with username/password or Google OAuth
- **[Deployment Guide](deployment.md)** - Container and production deployment instructions
- **[API Reference](api.md)** - Detailed endpoint documentation with examples
- **[Database Schema](database_schema.md)** - SQLite schema reference with tables, columns, and relationships
- **[Theory Background](theory_background.md)** - AHP algorithm and mathematical foundations
- **[Appendix: API Endpoint List](rest_api_spec_list.md)** - Quick reference of all endpoints

## API Documentation

The API documentation is available at `/docs` or `/redoc` when the server is running.
