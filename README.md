# OneSelect Backend


<div align="center">


[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT) 
[![Documentation](https://img.shields.io/badge/docs-mkdocs-blue)](https://johan162.github.io/oneselect/)
[![OpenAPI](https://img.shields.io/badge/OpenAPI-3.1.0-6BA539?logo=openapiinitiative&logoColor=white)](http://localhost:8000/docs)
[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)


[![GitHub release](https://img.shields.io/github/v/release/johan162/oneselect?include_prereleases)](https://github.com/johan162/oneselect/releases) 
![Coverage](https://img.shields.io/badge/coverage-91%25-darkgreen.svg)

[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black) [![Checked with mypy](https://www.mypy-lang.org/static/mypy_badge.svg)](https://mypy-lang.org/) 
[![Linting: flake8](https://img.shields.io/badge/linting-flake8-yellowgreen)](https://flake8.pycqa.org/) 


 ⚠️ **Under heavy development — not ready for production / no release yet.**


</div>



## Introduction

Prioritizing a large backlog of tasks or features is a challenge for any team. While humans often struggle to consistently rank a long list of items against complex criteria like "technical complexity" or "business value," we are intuitively good at comparing just two items at a time.

**OneSelect** leverages this intuition. By breaking down complex ranking problems into a series of simple pairwise comparisons ("Is Feature A more valuable than Feature B?"), it builds a robust ranking of all items.

However, comparing every possible pair ($N$ items require $N(N-1)/2$ comparisons) quickly becomes impractical. OneSelect solves this by using a smart, probabilistic approach. Instead of requiring a complete set of comparisons, it uses a Bayesian interpretation of the **Bradley-Terry** (or Thurstone-Mosteller) model to infer the underlying scores of all items from a sparse set of comparisons. This allows for an accurate ranking with significantly less effort—focusing on getting the most important items right, rather than perfect sorting of the entire list.

For a rigorous statistical treatment of the underlying mathematics, see [Efficient Bayesian Inference for Generalized Bradley-Terry Models](https://www.stats.ox.ac.uk/~doucet/caron_doucet_bayesianbradleyterry.pdf) by *F. Caron* and *A. Doucet*.


**Note:** This project provides the backend REST API only. It is designed to power a separate frontend user interface. The backend API is designed to minimize roundtrips for typical information needed by a UI. This means that some API calls partly overlaps and does, by choice, not provide a purely orthogonal design in order to make it efficient.

## Documentation

Full documentation is available [OneSelect Documentation](https://johan162.github.io/oneselect/).


## Features

*   **Smart Ranking Algorithm**: Uses Bayesian inference (Bradley-Terry model) to efficiently rank items with minimal comparisons.
*   **Project Workspaces**: Organize comparisons into distinct projects with specific feature sets and criteria.
*   **Multi-User Collaboration**: Share projects with team members and manage access permissions.
*   **Real-time Analytics**: Instant calculation of priority scores, consistency checks, and ranking visualizations.
*   **Full Audit Trail**: Comprehensive history tracking with soft-delete support for data integrity and recovery.
*   **Secure Authentication**: Robust user management with OAuth2 and JWT token-based security.
*   **Production Ready**: Fully containerized with Podman/Docker support, health checks, and database migrations.
*   **Developer Friendly**: Complete OpenAPI specification with interactive Swagger UI and ReDoc documentation.

This repository contains the **backend REST API** for the OneSelect system. It is a high-performance, production-ready server built with modern Python technologies:
- **Python 3.13+**
- **FastAPI** for high-performance web API
- **SQLAlchemy** for robust database interactions
- **Pydantic** for data validation

## 🚀 Quick Start (Recommended)

The quickest way to get the backend API REST set up and running is to use the one-line install script which can be run on your local machine as long as you have `podman` or `Docker` installed.


### Method 1: One-Line Install

```bash
mkdir oneselect-deploy
cd oneselect-deploy
curl -fsSL https://raw.githubusercontent.com/johan162/oneselect/main/deploy/install.sh | bash
```

The above line will download and setup all necessary files and start-up a container with the backend-server. The script will:

1. ✓ Check system requirements (Docker/Podman)
2. ✓ Prompt for configuration (admin credentials, port, etc.)
3. ✓ Generate secure SECRET_KEY automatically
4. ✓ Download docker-compose.prod.yml
5. ✓ Create .env configuration file
6. ✓ Pull and start the container from [ghcr.io](https://ghcr.io/)
7. ✓ Display access information

For an extensive walkthrough in excruciating details about running the container see the [Deployment README File](deploy/README.md).



### Method 2: Download and Run

For more control, download the script first:

```bash
mkdir oneselect-deploy
cd oneselect-deploy
wget https://raw.githubusercontent.com/johan162/oneselect/main/deploy/install.sh
chmod +x install.sh
```

You can now inspect the `install.sh` to better understand what it does under the hood.

Once satisfied run:

```bash
./install.sh
```

### Post-Installation

After installation completes:

1. **Wait 10-15 seconds** for initialization
2. **Access the API**: http://localhost:8000/docs
3. **Login** with your admin credentials
4. **Change password** immediately after first login


### Container Features

- **Non-root user**: Container runs as user `oneselect` (UID 1000)
- **Persistent data**: Database stored in named volume `oneselect-data`
- **Health checks**: Automatic health monitoring
- **Multi-stage build**: Optimized image size
- **Auto-initialization**: Database and admin user created on first run


## Local Development Prerequisites

- Python 3.13+
- [Poetry](https://python-poetry.org/) for dependency management
- [Podman](https://podman.io/) or Docker
- podman-compose (or docker-compose)


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

3. Setup local development environment :
   ```bash
   make dev
   ```

## Configuration

The environment file is read by both Pydentic as well as podman-compose to inject environment variables and is strictly speaking not necessaary form development as there are sane defaults.


1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and configure:
   - **SECRET_KEY**: Generate with `openssl rand -hex 32`
   - **GOOGLE_CLIENT_ID** and **GOOGLE_CLIENT_SECRET**: Optional, for Google OAuth (see [Authentication Setup](AUTHENTICATION_SETUP.md))
   - **DATABASE_URI**: Default is SQLite, can use PostgreSQL or MySQL

## Database Setup

The project uses SQLite by default for development. The previous `make dev` will also set-up a DB. Should you later on want to delete and setup a new DB just delete the old DB and run

```
make init-db
```

and a new freach DB will have been created.

## Authentication

OneSelect supports two authentication methods:

1. **Username/Password** - Traditional local authentication
2. **Google OAuth** - Sign in with Google (optional)

See [AUTHENTICATION_SETUP.md](AUTHENTICATION_SETUP.md) for quick setup or [docs/authentication.md](docs/authentication.md) for the complete guide.

## Running the Server

Once you have a development environment setup you can start the development server with hot reload:

```bash
make run
```

or directly with poetry as

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

Run the test suite and coverage analysis using pytest:

```bash
make test-html
```

or directly as

```bash
PYTHONPATH=. poetry run pytest
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
  version={0.0.1-rc16}
}
```

