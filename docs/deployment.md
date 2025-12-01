# Deployment Guide

This guide covers various deployment options for the OneSelect backend.

## Table of Contents

- [Container Deployment (Recommended)](#container-deployment-recommended)
- [Local Development Deployment](#local-development-deployment)
- [Production Deployment](#production-deployment)
- [Environment Configuration](#environment-configuration)
- [Database Options](#database-options)

## Container Deployment (Recommended)

### Prerequisites

- [Podman](https://podman.io/getting-started/installation) or [Docker](https://docs.docker.com/get-docker/)
- podman-compose or docker-compose

### Quick Start

1. **Clone the repository:**
   ```bash
   git clone https://github.com/johan162/oneselect.git
   cd oneselect
   ```

2. **Configure environment:**
   ```bash
   cp .env.example .env
   ```
   
   Edit `.env` and set:
   - `SECRET_KEY`: Generate with `openssl rand -hex 32`
   - `FIRST_SUPERUSER`: Admin email
   - `FIRST_SUPERUSER_PASSWORD`: Admin password

3. **Build and run:**
   ```bash
   make container-build
   make container-up
   ```

4. **Verify deployment:**
   ```bash
   curl http://localhost:8000/docs
   ```

### Container Commands

| Command | Description |
|---------|-------------|
| `make container-build` | Build the container image |
| `make container-up` | Start services (detached mode) |
| `make container-down` | Stop and remove containers |
| `make container-logs` | View application logs |
| `make container-restart` | Restart services |
| `make container-shell` | Access container shell |
| `make container-clean` | Remove everything (including volumes) |

### Development Mode

To enable hot-reload for development, edit `docker-compose.yml` and uncomment:

```yaml
volumes:
  - ./app:/app/app:ro
command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Then restart:
```bash
make container-restart
```

## Local Development Deployment

### Prerequisites

- Python 3.13+
- [Poetry](https://python-poetry.org/)

### Setup

1. **Install dependencies:**
   ```bash
   poetry install
   ```

2. **Setup database:**
   ```bash
   poetry run alembic upgrade head
   poetry run python app/initial_data.py
   ```

3. **Run server:**
   ```bash
   poetry run uvicorn app.main:app --reload
   ```

## Production Deployment

### Cloud Platforms

#### Railway

1. Connect your GitHub repository to Railway
2. Add environment variables in Railway dashboard
3. Railway will auto-detect and deploy

#### Fly.io

```bash
# Install flyctl
curl -L https://fly.io/install.sh | sh

# Launch app
fly launch

# Deploy
fly deploy
```

#### AWS Elastic Beanstalk

```bash
# Initialize EB
eb init -p docker oneselect

# Create environment
eb create oneselect-prod

# Deploy
eb deploy
```

#### Digital Ocean App Platform

1. Connect GitHub repository
2. Configure as Docker container
3. Set environment variables
4. Deploy

### Container Registry

Push to container registry for deployment:

```bash
# Build image
podman build -t oneselect-backend:latest .

# Tag for registry
podman tag oneselect-backend:latest registry.example.com/oneselect-backend:latest

# Push to registry
podman push registry.example.com/oneselect-backend:latest
```

## Environment Configuration

### Required Variables

```bash
# Security
SECRET_KEY=your-secret-key-here
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Admin User
FIRST_SUPERUSER=admin@example.com
FIRST_SUPERUSER_PASSWORD=secure-password

# Database (choose one)
SQLALCHEMY_DATABASE_URI=sqlite:///./oneselect.db
# SQLALCHEMY_DATABASE_URI=postgresql://user:pass@host:5432/oneselect
# SQLALCHEMY_DATABASE_URI=mysql+pymysql://user:pass@host:3306/oneselect

# CORS (adjust for your frontend)
BACKEND_CORS_ORIGINS=["http://localhost:3000"]
```

### Optional Variables

```bash
# Application
PROJECT_NAME=OneSelect
API_V1_STR=/v1

# Logging
LOG_LEVEL=INFO
```

### Generating Secret Key

```bash
# Using OpenSSL
openssl rand -hex 32

# Using Python
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

## Database Options

### SQLite (Default - Development)

Best for development and small deployments:

```bash
SQLALCHEMY_DATABASE_URI=sqlite:///./oneselect.db
```

**Pros:**
- No additional setup required
- File-based, easy to backup
- Perfect for development

**Cons:**
- Not suitable for high-traffic production
- Limited concurrent write operations

### PostgreSQL (Recommended - Production)

Best for production deployments:

```bash
SQLALCHEMY_DATABASE_URI=postgresql://username:password@localhost:5432/oneselect
```

**Setup with Docker/Podman:**

Add to `docker-compose.yml`:

```yaml
services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: oneselect
      POSTGRES_USER: oneselect
      POSTGRES_PASSWORD: secure-password
    volumes:
      - postgres-data:/var/lib/postgresql/data
    networks:
      - oneselect-network

  oneselect-api:
    depends_on:
      - postgres
    environment:
      - SQLALCHEMY_DATABASE_URI=postgresql://oneselect:secure-password@postgres:5432/oneselect

volumes:
  postgres-data:
```

### MySQL/MariaDB

```bash
SQLALCHEMY_DATABASE_URI=mysql+pymysql://username:password@localhost:3306/oneselect
```

## Health Checks

The application includes built-in health checks:

- **Endpoint:** `GET /docs`
- **Container health check:** Runs every 30 seconds
- **Load balancer health check:** Use `/docs` endpoint

## Scaling

### Horizontal Scaling

Run multiple container instances behind a load balancer:

```bash
# Using podman-compose
podman-compose up -d --scale oneselect-api=3
```

### Vertical Scaling

Adjust container resources in `docker-compose.yml`:

```yaml
services:
  oneselect-api:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '1'
          memory: 1G
```

## Monitoring

### Application Logs

```bash
# View logs
make container-logs

# View specific container
podman logs oneselect-backend -f
```

### Health Check

```bash
# Check container health
podman inspect oneselect-backend | grep Health -A 20

# Test endpoint
curl http://localhost:8000/docs
```

## Backup and Restore

### SQLite Backup

```bash
# Backup
podman exec oneselect-backend sqlite3 /app/data/oneselect.db ".backup /app/data/backup.db"
podman cp oneselect-backend:/app/data/backup.db ./backup.db

# Restore
podman cp ./backup.db oneselect-backend:/app/data/oneselect.db
make container-restart
```

### PostgreSQL Backup

```bash
# Backup
podman exec postgres pg_dump -U oneselect oneselect > backup.sql

# Restore
podman exec -i postgres psql -U oneselect oneselect < backup.sql
```

## Troubleshooting

### Container won't start

```bash
# Check logs
make container-logs

# Rebuild image
make container-clean
make container-build
make container-up
```

### Database connection issues

```bash
# Check database is accessible
podman exec oneselect-backend env | grep DATABASE

# Test connection
podman exec oneselect-backend python -c "from app.db.session import engine; print(engine.url)"
```

### Permission issues

If you encounter permission issues with volumes:

```bash
# SELinux systems (Fedora, RHEL, CentOS)
# Already handled with :Z flag in volume mounts

# Or disable SELinux for testing (not recommended for production)
sudo setenforce 0
```

## Security Checklist

- [ ] Change default `SECRET_KEY`
- [ ] Change default admin password
- [ ] Use HTTPS in production (reverse proxy)
- [ ] Configure CORS origins appropriately
- [ ] Use PostgreSQL for production
- [ ] Enable container security scanning
- [ ] Set up regular backups
- [ ] Monitor application logs
- [ ] Keep dependencies updated

## Next Steps

- Configure reverse proxy (Nginx/Traefik) with SSL
- Set up CI/CD pipeline
- Configure monitoring (Prometheus/Grafana)
- Implement log aggregation (ELK/Loki)
- Set up automated backups
