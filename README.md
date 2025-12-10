# ⚠️ OneSelect Backend — Under Active Development

> ⚠️ **Under heavy development — not ready for production / no release yet.**
>
> This repository is currently under active development. Important functionality and tests are still being implemented and validated. There is no stable release yet — do not use this code in production.

| Category | Link |
|----------|--------|
|**Python**|[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)|
|**Documentation**|[![Documentation](https://img.shields.io/badge/docs-mkdocs-blue)](https://johan162.github.io/oneselect/)|
|**API**|[![OpenAPI](https://img.shields.io/badge/OpenAPI-3.1.0-6BA539?logo=openapiinitiative&logoColor=white)](http://localhost:8000/docs)|
|**License**|[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)|
|**Release**|[![GitHub release](https://img.shields.io/github/v/release/johan162/oneselect?include_prereleases)](https://github.com/johan162/oneselect/releases)|
|**Code Quality**|[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black) [![Checked with mypy](https://www.mypy-lang.org/static/mypy_badge.svg)](https://mypy-lang.org/) [![Linting: flake8](https://img.shields.io/badge/linting-flake8-yellowgreen)](https://flake8.pycqa.org/)|
|Repo URL|[![GitHub](https://img.shields.io/badge/GitHub-100000?style=flat-square&logo=github&logoColor=white)](https://github.com/johan162/oneselect)|



## Introduction

Prioritizing a large backlog of tasks or features is a challenge for any team. While humans often struggle to consistently rank a long list of items against complex criteria like "technical complexity" or "business value," we are intuitively good at comparing just two items at a time.

**OneSelect** leverages this intuition. By breaking down complex ranking problems into a series of simple pairwise comparisons ("Is Feature A more valuable than Feature B?"), it builds a robust ranking of all items.

However, comparing every possible pair ($N$ items require $N(N-1)/2$ comparisons) quickly becomes impractical. OneSelect solves this by using a smart, probabilistic approach. Instead of requiring a complete set of comparisons, it uses a Bayesian interpretation of the **Bradley-Terry** (or Thurstone-Mosteller) model to infer the underlying scores of all items from a sparse set of comparisons. This allows for an accurate ranking with significantly less effort—focusing on getting the most important items right, rather than perfect sorting of the entire list.

For a rigorous statistical treatment of the underlying mathematics, see [Efficient Bayesian Inference for Generalized Bradley-Terry Models](https://www.stats.ox.ac.uk/~doucet/caron_doucet_bayesianbradleyterry.pdf) by F. Caron and A. Doucet.

This repository contains the **backend REST API** for the OneSelect system. It is a high-performance, production-ready server built with modern Python technologies:
- **Python 3.13+**
- **FastAPI** for high-performance web API
- **SQLAlchemy** for robust database interactions
- **Pydantic** for data validation

**Note:** This project provides the backend infrastructure and API only. It is designed to power a separate frontend user interface.

## Features

*   **Smart Ranking Algorithm**: Uses Bayesian inference (Bradley-Terry model) to efficiently rank items with minimal comparisons.
*   **Project Workspaces**: Organize comparisons into distinct projects with specific feature sets and criteria.
*   **Multi-User Collaboration**: Share projects with team members and manage access permissions.
*   **Real-time Analytics**: Instant calculation of priority scores, consistency checks, and ranking visualizations.
*   **Full Audit Trail**: Comprehensive history tracking with soft-delete support for data integrity and recovery.
*   **Secure Authentication**: Robust user management with OAuth2 and JWT token-based security.
*   **Production Ready**: Fully containerized with Podman/Docker support, health checks, and database migrations.
*   **Developer Friendly**: Complete OpenAPI specification with interactive Swagger UI and ReDoc documentation.

## Prerequisites

### Option 1: Local Development
- Python 3.13+
- [Poetry](https://python-poetry.org/) for dependency management

### Option 2: Container Deployment
- [Podman](https://podman.io/) or Docker
- podman-compose (or docker-compose)

## Quick Start with Containers (Recommended)

The fastest way to get started is using containers with Podman:

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd oneselect
   ```

2. Create environment configuration:
   ```bash
   cp .env.example .env
   # Edit .env and set your SECRET_KEY and admin credentials
   ```

3. Build and start the container:
   ```bash
   make container-build
   make container-up
   ```

4. The API will be available at `http://localhost:8000`

5. View logs:
   ```bash
   make container-logs
   ```

6. Stop the container:
   ```bash
   make container-down
   ```

### Container Management Commands

```bash
make container-build     # Build the container image
make container-up        # Start services in detached mode
make container-down      # Stop and remove containers
make container-logs      # View and follow logs
make container-restart   # Restart services
make container-shell     # Open shell inside container
make container-clean     # Remove containers and volumes
```

### Alternative: Direct Podman Commands

```bash
# Build image
make podman-build

# Run container
make podman-run

# Stop container
make podman-stop
```

### Container Features

- **Non-root user**: Container runs as user `oneselect` (UID 1000)
- **Persistent data**: Database stored in named volume `oneselect-data`
- **Health checks**: Automatic health monitoring
- **Multi-stage build**: Optimized image size
- **Auto-initialization**: Database and admin user created on first run

## Local Development Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd oneselect
   ```

2. **(Optional)** Configure custom PyPI source:
   ```bash
   # If you use a corporate PyPI mirror/proxy (e.g., Artifactory, Nexus)
   poetry source add --priority=primary <source-name> <source-url>
   
   # Example with Artifactory:
   # poetry source add --priority=primary artifactory https://your-artifactory.com/api/pypi/pypi-virtual/simple
   ```

3. Install dependencies:
   ```bash
   poetry install
   ```

## Configuration

1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and configure:
   - **SECRET_KEY**: Generate with `openssl rand -hex 32`
   - **GOOGLE_CLIENT_ID** and **GOOGLE_CLIENT_SECRET**: Optional, for Google OAuth (see [Authentication Setup](AUTHENTICATION_SETUP.md))
   - **DATABASE_URI**: Default is SQLite, can use PostgreSQL or MySQL

## Database Setup

The project uses SQLite by default for development.

1. Apply database migrations:
   ```bash
   poetry run alembic upgrade head
   ```

2. Create initial data (creates the default superuser):
   ```bash
   poetry run python app/initial_data.py
   ```
   Default credentials:
   - Email: `admin@example.com`
   - Password: `admin`

## Authentication

OneSelect supports two authentication methods:

1. **Username/Password** - Traditional local authentication
2. **Google OAuth** - Sign in with Google (optional)

See [AUTHENTICATION_SETUP.md](AUTHENTICATION_SETUP.md) for quick setup or [docs/authentication.md](docs/authentication.md) for the complete guide.

## Running the Server

Start the development server with hot reload:

```bash
make run
```

or directlys as

```bash
poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`.

## API Documentation

The API provides comprehensive interactive documentation and specifications:

- **Swagger UI**: `http://localhost:8000/docs` - Interactive API explorer with try-it-out functionality
- **ReDoc**: `http://localhost:8000/redoc` - Clean, responsive API documentation
- **OpenAPI Spec**: `http://localhost:8000/v1/openapi.json` - OpenAPI 3.1.0 specification in JSON format

The API includes 49 endpoints across 9 modules:
- **Authentication** (8 endpoints): Login, register, token management, password changes
- **Users** (10 endpoints): User management, profiles, role assignments
- **Projects** (9 endpoints): Project CRUD, sharing, member management
- **Features** (7 endpoints): Feature management for comparisons
- **Comparisons** (13 endpoints): Pairwise comparisons, batch operations, results
- **Statistics** (2 endpoints): Comparison and user statistics
- **Results** (3 endpoints): Aggregated comparison results and rankings
- **Model Configuration** (4 endpoints): AHP model parameters and settings
- **Admin** (8 endpoints): System administration and user management

For complete API documentation, see:
- **[API Reference](docs/api.md)** - Detailed endpoint documentation with examples
- **[API Endpoint List](docs/rest_api_spec_list.md)** - Quick reference summary of all endpoints

## Running Tests

Run the test suite using pytest:

```bash
make test
```

or directly as

```bash
PYTHONPATH=. poetry run pytest
```


## Linting and Formatting

The project uses `black` for formatting, `flake8` for linting, and `mypy` for type checking.

The complete check of all code with respect to these areas are done with the `check` target

```bash
make check
```

or direct with `poetry`

Format code:
```bash
poetry run black .
```

Run linter:
```bash
poetry run flake8 .
```

Run type checker:
```bash
poetry run mypy --explicit-package-bases .
```



## Project Structure

- `app/`: Main application code
  - `api/`: API endpoints and dependencies
  - `core/`: Core configuration and security
  - `crud/`: Database CRUD operations
  - `db/`: Database session and base models
  - `models/`: SQLAlchemy models
  - `schemas/`: Pydantic schemas
- `tests/`: Test suite
- `alembic/`: Database migrations
- `docs/`: Documentation using `mkdocs` documentation system


## Citation

If you use this tool in your research or business process, please cite:

```
@software{oneselect,
  title = {Bradley-Terry model with Bayesian inference for graded decision ranking},
  author = {Johan Persson},
  year = {2025},
  url = {https://github.com/johan162/oneselect}
  version={0.0.1-rc10}
}
```

