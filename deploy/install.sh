#!/usr/bin/env bash
#
# OneSelect Backend - Production Deployment Installer
# ====================================================
# This script automates the deployment of OneSelect backend server
# using Docker/Podman with pre-built images from GitHub Container Registry.
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/johan162/oneselect/main/deploy/install.sh | bash
#   
# Or download and run locally:
#   wget https://raw.githubusercontent.com/johan162/oneselect/main/deploy/install.sh
#   chmod +x install.sh
#   ./install.sh
#
# Requirements:
#   - Docker or Podman installed
#   - docker-compose or podman-compose installed
#

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
REPO_OWNER="johan162"
REPO_NAME="oneselect"
REPO_URL="https://raw.githubusercontent.com/${REPO_OWNER}/${REPO_NAME}/main/deploy"
INSTALL_DIR="${HOME}/.oneselect"
VERSION="latest"

# Functions
print_header() {
    echo -e "${BLUE}╔══════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║                                                      ║${NC}"
    echo -e "${BLUE}║        OneSelect Backend Deployment Installer        ║${NC}"
    echo -e "${BLUE}║                                                      ║${NC}"
    echo -e "${BLUE}╚══════════════════════════════════════════════════════╝${NC}"
    echo ""
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

check_requirements() {
    print_info "Checking system requirements..."
    
    # Check for Docker or Podman (preferred)
    if command -v podman &> /dev/null; then
        CONTAINER_CMD="podman"
        COMPOSE_CMD="podman-compose"
        print_success "Found Podman"
    elif command -v docker &> /dev/null; then
        CONTAINER_CMD="docker"
        COMPOSE_CMD="docker-compose"
        if ! command -v docker-compose &> /dev/null && docker compose version &> /dev/null; then
            COMPOSE_CMD="docker compose"
        fi
        print_success "Found Docker"
    else
        print_error "Neither Docker nor Podman found. Please install one of them first."
        echo ""
        echo "Install Docker: https://docs.docker.com/get-docker/"
        echo "Install Podman: https://podman.io/getting-started/installation"
        exit 1
    fi
    
    # Check for compose
    if ! command -v ${COMPOSE_CMD%% *} &> /dev/null; then
        print_error "${COMPOSE_CMD} not found. Please install it first."
        exit 1
    fi
    print_success "Found ${COMPOSE_CMD}"
    
    # Check for curl or wget
    if ! command -v curl &> /dev/null && ! command -v wget &> /dev/null; then
        print_error "Neither curl nor wget found. Please install one of them."
        exit 1
    fi
    
    echo ""
}

download_file() {
    local url=$1
    local output=$2
    
    if command -v curl &> /dev/null; then
        curl -fsSL "$url" -o "$output"
    else
        wget -q "$url" -O "$output"
    fi
}

generate_secret_key() {
    if command -v openssl &> /dev/null; then
        openssl rand -hex 32
    else
        # Fallback to urandom
        LC_ALL=C tr -dc 'a-f0-9' < /dev/urandom | head -c 64
    fi
}

prompt_user_input() {
    print_info "Configuration Setup"
    echo ""
    
    # Installation directory
    read -p "Installation directory [${INSTALL_DIR}]: " input_dir
    INSTALL_DIR="${input_dir:-$INSTALL_DIR}"
    
    # Create directory
    mkdir -p "$INSTALL_DIR"
    cd "$INSTALL_DIR"
    
    print_success "Using installation directory: ${INSTALL_DIR}"
    echo ""
    
    # Version selection
    read -p "Select version (e.g., latest, v0.0.1-rc15) [${VERSION}]: " input_version
    VERSION="${input_version:-$VERSION}"
    
    # Secret key
    print_info "Generating secure SECRET_KEY..."
    SECRET_KEY=$(generate_secret_key)
    print_success "SECRET_KEY generated"
    echo ""
    
    # Admin credentials
    print_warning "Admin User Configuration"
    read -p "Admin email [admin@example.com]: " admin_email
    ADMIN_EMAIL="${admin_email:-admin@example.com}"
    
    read -sp "Admin password (will not echo): " admin_password
    echo ""
    if [ -z "$admin_password" ]; then
        admin_password="admin"
        print_warning "Using default password 'admin' - CHANGE THIS IMMEDIATELY!"
    fi
    ADMIN_PASSWORD="$admin_password"
    echo ""
    
    # Port configuration
    read -p "API port [8000]: " api_port
    API_PORT="${api_port:-8000}"
    
    # CORS origins
    read -p "Frontend URL for CORS (leave empty for default) [http://localhost:3000]: " frontend_url
    FRONTEND_URL="${frontend_url:-http://localhost:3000}"
    
    # OAuth (optional)
    echo ""
    print_info "Google OAuth Configuration (optional, press Enter to skip)"
    read -p "Google Client ID: " google_client_id
    read -p "Google Client Secret: " google_client_secret
    
    GOOGLE_CLIENT_ID="${google_client_id:-}"
    GOOGLE_CLIENT_SECRET="${google_client_secret:-}"
    
    echo ""
}

create_env_file() {
    print_info "Creating .env configuration file..."
    
    cat > .env <<EOF
# OneSelect Backend Production Configuration
# Generated on $(date)

# Security - IMPORTANT: Keep this secret!
SECRET_KEY=${SECRET_KEY}
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Admin User Credentials
FIRST_SUPERUSER=${ADMIN_EMAIL}
FIRST_SUPERUSER_PASSWORD=${ADMIN_PASSWORD}

# Database Configuration
# SQLite is used by default and stored in a Docker volume
SQLALCHEMY_DATABASE_URI=sqlite:////app/data/oneselect.db

# CORS Configuration
BACKEND_CORS_ORIGINS=["${FRONTEND_URL}","http://localhost:${API_PORT}"]

# Application Settings
PROJECT_NAME=OneSelect
API_V1_STR=/v1
FRONTEND_URL=${FRONTEND_URL}

# Google OAuth (Optional)
GOOGLE_CLIENT_ID=${GOOGLE_CLIENT_ID}
GOOGLE_CLIENT_SECRET=${GOOGLE_CLIENT_SECRET}
GOOGLE_REDIRECT_URI=http://localhost:${API_PORT}/api/v1/auth/google/callback
EOF

    chmod 600 .env
    print_success "Created .env file with secure permissions"
    echo ""
}

download_compose_file() {
    print_info "Downloading docker-compose.prod.yml..."
    
    if download_file "${REPO_URL}/docker-compose.prod.yml" "docker-compose.yml"; then
        print_success "Downloaded docker-compose.yml"
    else
        print_error "Failed to download docker-compose file"
        exit 1
    fi
    
    # Update version in compose file if not using 'latest'
    if [ "$VERSION" != "latest" ]; then
        if command -v sed &> /dev/null; then
            sed -i.bak "s/:latest/:${VERSION}/" docker-compose.yml
            rm -f docker-compose.yml.bak
            print_success "Updated image version to ${VERSION}"
        fi
    fi
    
    echo ""
}

start_services() {
    print_info "Starting OneSelect backend services..."
    echo ""
    
    # Pull the image
    print_info "Pulling Docker image (this may take a moment)..."
    ${COMPOSE_CMD} pull
    
    # Start services
    print_info "Starting container..."
    ${COMPOSE_CMD} up -d
    
    echo ""
    print_success "Services started successfully!"
    echo ""
}

show_completion_message() {
    echo -e "${GREEN}╔══════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║                                                      ║${NC}"
    echo -e "${GREEN}║           Installation Complete! 🎉                  ║${NC}"
    echo -e "${GREEN}║                                                      ║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${BLUE}Installation Directory:${NC} ${INSTALL_DIR}"
    echo -e "${BLUE}API URL:${NC} http://localhost:${API_PORT}"
    echo -e "${BLUE}API Documentation:${NC} http://localhost:${API_PORT}/docs"
    echo -e "${BLUE}Admin Email:${NC} ${ADMIN_EMAIL}"
    echo ""
    echo -e "${YELLOW}Next Steps:${NC}"
    echo "  1. Wait a few seconds for the container to fully initialize"
    echo "  2. Visit http://localhost:${API_PORT}/docs to access the API"
    echo "  3. Login with your admin credentials"
    echo ""
    echo -e "${BLUE}Useful Commands:${NC}"
    echo "  View logs:       cd ${INSTALL_DIR} && ${COMPOSE_CMD} logs -f"
    echo "  Stop service:    cd ${INSTALL_DIR} && ${COMPOSE_CMD} stop"
    echo "  Start service:   cd ${INSTALL_DIR} && ${COMPOSE_CMD} start"
    echo "  Restart:         cd ${INSTALL_DIR} && ${COMPOSE_CMD} restart"
    echo "  Remove:          cd ${INSTALL_DIR} && ${COMPOSE_CMD} down -v"
    echo ""
    echo -e "${YELLOW}⚠ Security Reminder:${NC}"
    echo "  - Change the admin password after first login"
    echo "  - Keep your .env file secure (${INSTALL_DIR}/.env)"
    echo "  - Consider using HTTPS in production"
    echo ""
    echo -e "${GREEN}Documentation:${NC} https://johan162.github.io/oneselect/"
    echo ""
}

# Main installation flow
main() {
    print_header
    
    check_requirements
    prompt_user_input
    create_env_file
    download_compose_file
    start_services
    show_completion_message
}

# Run main function
main
