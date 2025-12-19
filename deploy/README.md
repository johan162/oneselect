# OneSelect Backend - Production Deployment Guide

<div align="center">

[![OneSelect](https://img.shields.io/badge/OneSelect-Backend-blue)](https://github.com/johan162/oneselect)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker&logoColor=white)](https://www.docker.com/)
[![Podman](https://img.shields.io/badge/Podman-Ready-892CA0?logo=podman&logoColor=white)](https://podman.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Production-ready deployment resources for OneSelect Backend**

[Quick Start](#-quick-start) • [Manual Setup](#-manual-deployment) • [Configuration](#-configuration) • [Troubleshooting](#-troubleshooting)

</div>

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Prerequisites](#-prerequisites)
- [Quick Start (Recommended)](#-quick-start-recommended)
- [Manual Deployment](#-manual-deployment)
- [Configuration](#-configuration)
- [Container Management](#-container-management)
- [Database Options](#-database-options)
- [Security Best Practices](#-security-best-practices)
- [Upgrading](#-upgrading)
- [Backup & Restore](#-backup--restore)
- [Troubleshooting](#-troubleshooting)
- [Production Checklist](#-production-checklist)
- [Advanced Configurations](#-advanced-configurations)

---

## 🎯 Overview

This directory contains production-ready deployment resources for OneSelect Backend:

| File | Purpose |
|------|---------|
| `docker-compose.prod.yml` | Production container orchestration (pulls from ghcr.io) |
| `install.sh` | Automated installation script with interactive setup |
| `.env.production` | Environment configuration template |
| `README.md` | This comprehensive deployment guide |

### Key Features

✅ **Pre-built Images** - No compilation needed, pull from GitHub Container Registry  
✅ **One-Click Install** - Automated setup with interactive prompts  
✅ **Secure Defaults** - Non-root user, health checks, secure permissions  
✅ **Persistent Data** - Database stored in Docker volumes  
✅ **Easy Updates** - Simple version management via image tags  
✅ **Production Ready** - Optimized for stability and security  

---

## 🔧 Prerequisites

### Required Software

Choose **one** of the following container runtimes:

- **Docker** (v20.10+) with Docker Compose
  - Install: https://docs.docker.com/get-docker/
  - Verify: `docker --version && docker-compose --version`

- **Podman** (v3.0+) with podman-compose
  - Install: https://podman.io/getting-started/installation
  - Verify: `podman --version && podman-compose --version`

### System Requirements

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| CPU | 1 core | 2+ cores |
| RAM | 512 MB | 1 GB+ |
| Disk | 500 MB | 2 GB+ |
| OS | Linux, macOS, Windows | Linux (production) |

### Network Requirements

- Port `8000` available (or configure custom port)
- Internet access for pulling container images
- Firewall configured to allow API access

---

## 🚀 Quick Start (Recommended)

### Method 1: One-Line Install

```bash
curl -fsSL https://raw.githubusercontent.com/johan162/oneselect/main/deploy/install.sh | bash
```

The script will:
1. ✓ Check system requirements (Docker/Podman)
2. ✓ Prompt for configuration (admin credentials, port, etc.)
3. ✓ Generate secure SECRET_KEY automatically
4. ✓ Download docker-compose.prod.yml
5. ✓ Create .env configuration file
6. ✓ Pull and start the container
7. ✓ Display access information

### Method 2: Download and Run

For more control, download the script first:

```bash
# Download
wget https://raw.githubusercontent.com/johan162/oneselect/main/deploy/install.sh

# Make executable
chmod +x install.sh

# Run with options
./install.sh
```

### Post-Installation

After installation completes:

1. **Wait 10-15 seconds** for initialization
2. **Access the API**: http://localhost:8000/docs
3. **Login** with your admin credentials
4. **Change password** immediately after first login

---

## 📦 Manual Deployment

For advanced users who prefer manual control:

### Step 1: Create Deployment Directory

```bash
mkdir -p ~/oneselect-deploy
cd ~/oneselect-deploy
```

### Step 2: Download Deployment Files

```bash
# Download docker-compose file
curl -fsSL https://raw.githubusercontent.com/johan162/oneselect/main/deploy/docker-compose.prod.yml \
  -o docker-compose.yml

# Download environment template
curl -fsSL https://raw.githubusercontent.com/johan162/oneselect/main/deploy/.env.production \
  -o .env
```

### Step 3: Configure Environment

Edit `.env` file with your settings:

```bash
# Generate a secure SECRET_KEY
SECRET_KEY=$(openssl rand -hex 32)

# Edit .env
nano .env  # or vim, code, etc.
```

**Required changes:**
- `SECRET_KEY` - Set to generated value
- `FIRST_SUPERUSER` - Your admin email
- `FIRST_SUPERUSER_PASSWORD` - Strong password
- `BACKEND_CORS_ORIGINS` - Your frontend URL

### Step 4: Deploy

```bash
# Pull the image
docker-compose pull

# Start the service
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f
```

### Step 5: Verify Deployment

```bash
# Check health
curl http://localhost:8000/docs

# Should return 200 OK
```

---

## ⚙️ Configuration

### Environment Variables

Comprehensive list of configuration options:

#### Security Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `SECRET_KEY` | *required* | JWT signing key (use `openssl rand -hex 32`) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | JWT token lifetime |

#### Admin User

| Variable | Default | Description |
|----------|---------|-------------|
| `FIRST_SUPERUSER` | `admin@example.com` | Admin email (created on first run) |
| `FIRST_SUPERUSER_PASSWORD` | `admin` | Admin password (CHANGE THIS!) |

#### Database

| Variable | Default | Description |
|----------|---------|-------------|
| `SQLALCHEMY_DATABASE_URI` | `sqlite:////app/data/oneselect.db` | Database connection string |

**Examples:**
```bash
# PostgreSQL
SQLALCHEMY_DATABASE_URI=postgresql://user:pass@postgres:5432/oneselect

# MySQL
SQLALCHEMY_DATABASE_URI=mysql+pymysql://user:pass@mysql:3306/oneselect
```

#### CORS & Application

| Variable | Default | Description |
|----------|---------|-------------|
| `BACKEND_CORS_ORIGINS` | `["http://localhost:3000",...]` | Allowed frontend origins (JSON array) |
| `PROJECT_NAME` | `OneSelect` | Application name |
| `API_V1_STR` | `/v1` | API version prefix |
| `FRONTEND_URL` | `http://localhost:3000` | Frontend URL for OAuth |

#### OAuth (Optional)

| Variable | Default | Description |
|----------|---------|-------------|
| `GOOGLE_CLIENT_ID` | *(empty)* | Google OAuth client ID |
| `GOOGLE_CLIENT_SECRET` | *(empty)* | Google OAuth client secret |
| `GOOGLE_REDIRECT_URI` | `http://localhost:8000/api/v1/auth/google/callback` | OAuth callback URL |

### Port Configuration

Change the exposed port by editing `docker-compose.yml`:

```yaml
ports:
  - "8080:8000"  # Expose on port 8080 instead
```

Or use environment variable:
```bash
PORT=8080 docker-compose up -d
```

### Version Pinning

For production, use specific version tags instead of `latest`:

```yaml
services:
  oneselect-api:
    image: ghcr.io/johan162/oneselect-backend:v0.0.1-rc15  # Pin to specific version
```

---

## 🎮 Container Management

### Basic Commands

#### Docker

```bash
# Start services
docker-compose up -d

# Stop services
docker-compose stop

# Restart services
docker-compose restart

# View logs
docker-compose logs -f

# Check status
docker-compose ps

# Stop and remove (keeps volumes)
docker-compose down

# Stop and remove (INCLUDING volumes - DELETES DATA!)
docker-compose down -v
```

#### Podman

Replace `docker-compose` with `podman-compose`:

```bash
podman-compose up -d
podman-compose logs -f
podman-compose down
```

### Health Checks

Check container health:

```bash
# Docker
docker-compose ps
# Look for "healthy" status

# Check health endpoint directly
curl http://localhost:8000/docs
```

### Viewing Logs

```bash
# Follow all logs
docker-compose logs -f

# Last 100 lines
docker-compose logs --tail=100

# Specific service only
docker-compose logs -f oneselect-api

# Save logs to file
docker-compose logs > oneselect.log
```

### Shell Access

Access container shell for debugging:

```bash
# Docker
docker-compose exec oneselect-api sh

# Or with docker directly
docker exec -it oneselect-backend sh

# Podman
podman exec -it oneselect-backend sh
```

---

## 💾 Database Options

### SQLite (Default)

**Pros:**
- Zero configuration
- Perfect for small deployments
- Stored in Docker volume (persistent)

**Cons:**
- Not ideal for high concurrency
- Limited scalability

**Configuration:**
```bash
SQLALCHEMY_DATABASE_URI=sqlite:////app/data/oneselect.db
```

### PostgreSQL (Recommended for Production)

**Pros:**
- Excellent performance
- Full ACID compliance
- Better concurrent access
- Industry standard

**Setup with Docker Compose:**

Create `docker-compose.override.yml`:

```yaml
version: '3.8'

services:
  oneselect-api:
    depends_on:
      - postgres
    environment:
      - SQLALCHEMY_DATABASE_URI=postgresql://oneselect:secure_password@postgres:5432/oneselect
  
  postgres:
    image: postgres:16-alpine
    container_name: oneselect-postgres
    environment:
      POSTGRES_USER: oneselect
      POSTGRES_PASSWORD: secure_password
      POSTGRES_DB: oneselect
    volumes:
      - postgres-data:/var/lib/postgresql/data
    networks:
      - oneselect-network
    restart: unless-stopped

volumes:
  postgres-data:
```

Then deploy:
```bash
docker-compose -f docker-compose.yml -f docker-compose.override.yml up -d
```

### MySQL/MariaDB

**Configuration:**
```bash
SQLALCHEMY_DATABASE_URI=mysql+pymysql://user:password@mysql:3306/oneselect
```

Similar setup to PostgreSQL, just use `mysql:8` or `mariadb:11` image.

---

## 🔒 Security Best Practices

### 1. Secrets Management

**Never commit secrets to version control:**

```bash
# Add to .gitignore
echo ".env" >> .gitignore
echo "*.env" >> .gitignore
```

**Generate strong secrets:**
```bash
# SECRET_KEY (64 characters)
openssl rand -hex 32

# Passwords (32 characters, alphanumeric + symbols)
openssl rand -base64 32
```

### 2. Change Default Credentials

**Immediately after deployment:**
1. Login with initial admin credentials
2. Navigate to user settings
3. Change password to strong unique password
4. Enable 2FA if available

### 3. HTTPS/TLS

**Never expose API directly to internet without HTTPS!**

Use a reverse proxy (nginx, Traefik, Caddy):

**Example nginx configuration:**

```nginx
server {
    listen 443 ssl http2;
    server_name api.yourdomain.com;
    
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 4. Firewall Configuration

```bash
# Allow only necessary ports
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 443/tcp   # HTTPS
sudo ufw enable

# Block direct access to API port
# Access only through reverse proxy
```

### 5. Regular Updates

```bash
# Pull latest image
docker-compose pull

# Restart with new image
docker-compose up -d

# Clean old images
docker image prune
```

### 6. Container Hardening

The provided container already includes:
- ✅ Non-root user (UID 1000)
- ✅ Minimal Alpine base image
- ✅ No package manager in runtime
- ✅ Read-only filesystem (where possible)
- ✅ Health checks enabled

### 7. Monitoring & Logging

```bash
# Set up log rotation
docker-compose logs --no-log-prefix > /var/log/oneselect.log

# Monitor for suspicious activity
docker-compose logs -f | grep -i "error\|unauthorized\|failed"
```

---

## 🔄 Upgrading

### Standard Upgrade Process

1. **Check current version:**
   ```bash
   docker images | grep oneselect-backend
   ```

2. **Backup database** (see [Backup & Restore](#-backup--restore))

3. **Pull new image:**
   ```bash
   docker-compose pull
   ```

4. **Stop and restart:**
   ```bash
   docker-compose down
   docker-compose up -d
   ```

5. **Verify:**
   ```bash
   docker-compose logs -f
   curl http://localhost:8000/docs
   ```

### Version-Specific Upgrade

Specify exact version in `docker-compose.yml`:

```yaml
services:
  oneselect-api:
    image: ghcr.io/johan162/oneselect-backend:v0.0.1-rc16  # Update version here
```

Then:
```bash
docker-compose pull
docker-compose up -d
```

### Rollback Procedure

If upgrade fails:

```bash
# Stop current container
docker-compose down

# Edit docker-compose.yml and change to previous version
# image: ghcr.io/johan162/oneselect-backend:v0.0.1-rc15

# Start with old version
docker-compose up -d

# Restore backup if needed (see Backup section)
```

---

## 💾 Backup & Restore

### SQLite Backup

#### Manual Backup

```bash
# Find volume location
docker volume inspect oneselect-data

# Copy database file
docker run --rm \
  -v oneselect-data:/data \
  -v $(pwd):/backup \
  alpine sh -c "cp /data/oneselect.db /backup/oneselect-backup-$(date +%Y%m%d-%H%M%S).db"
```

#### Automated Backup Script

Create `backup.sh`:

```bash
#!/bin/bash
BACKUP_DIR="${HOME}/oneselect-backups"
mkdir -p "${BACKUP_DIR}"

docker run --rm \
  -v oneselect-data:/data \
  -v "${BACKUP_DIR}":/backup \
  alpine sh -c "cp /data/oneselect.db /backup/oneselect-$(date +%Y%m%d-%H%M%S).db"

# Keep only last 30 days
find "${BACKUP_DIR}" -name "oneselect-*.db" -mtime +30 -delete

echo "Backup completed: ${BACKUP_DIR}"
```

Schedule with cron:
```bash
# Daily backup at 2 AM
0 2 * * * /path/to/backup.sh
```

#### Restore from Backup

```bash
# Stop container
docker-compose down

# Restore database
docker run --rm \
  -v oneselect-data:/data \
  -v $(pwd):/backup \
  alpine sh -c "cp /backup/oneselect-backup-20251219.db /data/oneselect.db"

# Restart
docker-compose up -d
```

### PostgreSQL Backup

```bash
# Backup
docker-compose exec postgres pg_dump -U oneselect oneselect > backup.sql

# Restore
docker-compose exec -T postgres psql -U oneselect oneselect < backup.sql
```

---

## 🔍 Troubleshooting

### Container Won't Start

**Check logs:**
```bash
docker-compose logs oneselect-api
```

**Common issues:**

1. **Port already in use:**
   ```bash
   # Find what's using port 8000
   lsof -i :8000
   # Kill process or change port in docker-compose.yml
   ```

2. **Permission denied:**
   ```bash
   # Fix volume permissions
   docker-compose down
   docker volume rm oneselect-data
   docker-compose up -d
   ```

3. **Invalid environment variables:**
   ```bash
   # Check .env syntax
   cat .env
   # Look for missing quotes, invalid JSON in BACKEND_CORS_ORIGINS
   ```

### Cannot Access API

1. **Check container is running:**
   ```bash
   docker-compose ps
   # Status should be "Up" and "healthy"
   ```

2. **Test from inside container:**
   ```bash
   docker-compose exec oneselect-api wget -O- http://localhost:8000/docs
   ```

3. **Check firewall:**
   ```bash
   sudo ufw status
   # Allow port if blocked
   sudo ufw allow 8000/tcp
   ```

### Database Connection Errors

**SQLite:**
```bash
# Check volume exists
docker volume ls | grep oneselect-data

# Check permissions
docker-compose exec oneselect-api ls -la /app/data/
```

**PostgreSQL/MySQL:**
```bash
# Test connection from container
docker-compose exec oneselect-api sh -c \
  'python -c "from app.db.session import engine; print(engine.connect())"'
```

### High Memory Usage

```bash
# Check container stats
docker stats oneselect-backend

# Set memory limits in docker-compose.yml:
services:
  oneselect-api:
    deploy:
      resources:
        limits:
          memory: 512M
```

### Slow Performance

1. **Check available resources:**
   ```bash
   docker stats
   ```

2. **Review logs for errors:**
   ```bash
   docker-compose logs --tail=100 | grep ERROR
   ```

3. **Consider using PostgreSQL instead of SQLite**

4. **Enable query logging** (temporarily):
   ```bash
   # Add to .env
   SQLALCHEMY_ECHO=true
   ```

### Image Pull Fails

```bash
# Authenticate with GitHub Container Registry
echo $GITHUB_TOKEN | docker login ghcr.io -u USERNAME --password-stdin

# Or pull public image without auth
docker pull ghcr.io/johan162/oneselect-backend:latest
```

---

## ✅ Production Checklist

Before going to production:

### Security
- [ ] Changed `SECRET_KEY` to randomly generated value
- [ ] Changed default admin password
- [ ] Configured HTTPS/TLS with valid certificate
- [ ] Set up firewall rules
- [ ] Configured CORS with specific frontend URLs (no wildcards)
- [ ] Reviewed and secured all environment variables
- [ ] Disabled debug mode (should be default)
- [ ] Set up secrets management (Vault, AWS Secrets, etc.)

### Database
- [ ] Using PostgreSQL or MySQL (not SQLite for production)
- [ ] Configured database backups
- [ ] Tested backup restoration
- [ ] Set up automated backup schedule
- [ ] Documented database connection strings securely

### Infrastructure
- [ ] Set up reverse proxy (nginx, Traefik, Caddy)
- [ ] Configured health checks
- [ ] Set up monitoring (Prometheus, Grafana, etc.)
- [ ] Configured log aggregation
- [ ] Planned for high availability (if needed)
- [ ] Tested disaster recovery procedures

### Deployment
- [ ] Pinned specific version (not using `latest`)
- [ ] Tested upgrade/downgrade procedures
- [ ] Documented deployment process
- [ ] Set up CI/CD pipeline (if applicable)
- [ ] Configured container resource limits
- [ ] Tested with production-like data volume

### Monitoring
- [ ] Set up uptime monitoring
- [ ] Configured alerting (email, Slack, PagerDuty)
- [ ] Monitoring disk space for volumes
- [ ] Monitoring container health
- [ ] Set up log rotation
- [ ] Configured metrics collection

### Documentation
- [ ] Documented production configuration
- [ ] Created runbook for common issues
- [ ] Documented backup/restore procedures
- [ ] Shared access credentials securely with team
- [ ] Documented upgrade procedures
- [ ] Created incident response plan

---

## 🎛️ Advanced Configurations

### Using External Database

#### Docker Compose Override

Create `docker-compose.override.yml` for local overrides:

```yaml
version: '3.8'

services:
  oneselect-api:
    environment:
      - SQLALCHEMY_DATABASE_URI=postgresql://user:pass@external-db.example.com:5432/oneselect
```

### Multiple Environments

```bash
# Development
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up

# Staging
docker-compose -f docker-compose.yml -f docker-compose.staging.yml up

# Production
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up
```

### Custom Network Configuration

```yaml
networks:
  oneselect-network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.28.0.0/16
```

### Resource Limits

```yaml
services:
  oneselect-api:
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 512M
        reservations:
          cpus: '0.5'
          memory: 256M
```

### Using Docker Secrets

```yaml
services:
  oneselect-api:
    secrets:
      - secret_key
      - db_password

secrets:
  secret_key:
    file: ./secrets/secret_key.txt
  db_password:
    file: ./secrets/db_password.txt
```

### Scaling (with load balancer)

```bash
docker-compose up -d --scale oneselect-api=3
```

Requires external load balancer configuration.

---

## 📚 Additional Resources

### Documentation
- **Main Documentation**: https://johan162.github.io/oneselect/
- **API Reference**: https://johan162.github.io/oneselect/api/
- **Authentication Guide**: https://johan162.github.io/oneselect/authentication/

### Source Code
- **Repository**: https://github.com/johan162/oneselect
- **Issues**: https://github.com/johan162/oneselect/issues
- **Releases**: https://github.com/johan162/oneselect/releases

### Container Images
- **Registry**: https://github.com/johan162/oneselect/pkgs/container/oneselect-backend
- **Pull Command**: `docker pull ghcr.io/johan162/oneselect-backend:latest`

### Community
- **Discussions**: https://github.com/johan162/oneselect/discussions
- **Contributing**: See CONTRIBUTING.md in main repository

---

## 🆘 Getting Help

If you encounter issues:

1. **Check this README** - Most common issues are covered
2. **Review logs** - `docker-compose logs -f`
3. **Search issues** - https://github.com/johan162/oneselect/issues
4. **Open new issue** - Include logs, configuration (redact secrets!), and steps to reproduce

---

## 📄 License

OneSelect Backend is licensed under the [MIT License](https://opensource.org/licenses/MIT).

---

<div align="center">

**Made with ❤️ for better decision making**

[⭐ Star us on GitHub](https://github.com/johan162/oneselect) | [📖 Read the docs](https://johan162.github.io/oneselect/) | [🐛 Report a bug](https://github.com/johan162/oneselect/issues)

</div>
