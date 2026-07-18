#!/usr/bin/env bash

# ==============================================================================
# CnSS Automated Deployment Script
# This script automates the zero-to-hero deployment of the CnSS backend.
# Target OS: Ubuntu / Debian-based Linux
# ==============================================================================

set -euo pipefail

# --- Color Codes for Output ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# --- Helper Functions ---
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
    exit 1
}

# ==============================================================================
# Step 1: Check System Prerequisites
# ==============================================================================
log_info "Checking system prerequisites..."

# Check Docker
if ! command -v docker &> /dev/null; then
    log_error "Docker is not installed. Please install Docker first (e.g., 'sudo apt install docker.io')."
fi

# Check Docker Compose
if ! docker compose version &> /dev/null; then
    log_error "Docker Compose is not installed or not working. Please install 'docker-compose-plugin'."
fi

# Check Python 3.11+
if ! command -v python3 &> /dev/null; then
    log_error "Python 3 is not installed."
fi
PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
if [[ $(echo "$PYTHON_VERSION < 3.11" | bc) -eq 1 ]]; then
    log_error "Python 3.11 or higher is required. Found version $PYTHON_VERSION."
fi

# Check uv (Fast Python package installer)
if ! command -v uv &> /dev/null; then
    log_warn "uv is not installed. Installing uv via official installer..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    # Add uv to PATH for the current session
    export PATH="$HOME/.cargo/bin:$HOME/.local/bin:$PATH"
    
    if ! command -v uv &> /dev/null; then
        log_error "Failed to install uv. Please install it manually."
    fi
    log_success "uv installed successfully."
else
    log_success "uv is already installed."
fi

# ==============================================================================
# Step 2: Environment Setup
# ==============================================================================
log_info "Setting up environment configuration..."

if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example .env
        log_success "Created .env file from .env.example"
    else
        log_error ".env.example not found. Cannot proceed."
    fi
else
    log_info ".env file already exists. Skipping creation."
fi

# Generate a secure JWT_SECRET_KEY if it's still the default
DEFAULT_JWT="change-this-to-a-secure-random-string-in-production"
if grep -q "^JWT_SECRET_KEY=${DEFAULT_JWT}$" .env; then
    log_info "Generating a secure random JWT_SECRET_KEY..."
    NEW_SECRET=$(openssl rand -hex 32)
    # Use sed to replace the default key (GNU sed syntax for Ubuntu)
    sed -i "s|^JWT_SECRET_KEY=.*|JWT_SECRET_KEY=${NEW_SECRET}|" .env
    log_success "JWT_SECRET_KEY updated securely."
else
    log_info "JWT_SECRET_KEY is already customized. Skipping."
fi

# ==============================================================================
# Step 3: Install Dependencies
# ==============================================================================
log_info "Installing Python dependencies using uv..."
uv sync --all-extras
log_success "Dependencies installed successfully."

# ==============================================================================
# Step 4: Start Infrastructure
# ==============================================================================
log_info "Starting infrastructure services (TimescaleDB, Redis, pgAdmin)..."
make dev
log_success "Infrastructure containers are starting up."

# ==============================================================================
# Step 5: Wait for Database Readiness
# ==============================================================================
log_info "Waiting for TimescaleDB to be ready to accept connections..."
MAX_RETRIES=30
RETRY_COUNT=0
DB_READY=false

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if docker exec cnss-dev-timescaledb pg_isready -U cnss -d cnss &> /dev/null; then
        DB_READY=true
        break
    fi
    RETRY_COUNT=$((RETRY_COUNT + 1))
    sleep 2
done

if [ "$DB_READY" = false ]; then
    log_error "TimescaleDB failed to become ready within the timeout period."
fi
log_success "TimescaleDB is ready."

# ==============================================================================
# Step 6: Run Database Migrations
# ==============================================================================
log_info "Applying database migrations (Alembic)..."
make migrate
log_success "Database migrations applied successfully."

# ==============================================================================
# Step 7: Interactive Data Seeding
# ==============================================================================
log_info "Do you want to seed initial test data (admin/viewer users and channels)? [y/N]"
read -r SEED_CHOICE
if [[ "$SEED_CHOICE" =~ ^[Yy]$ ]]; then
    log_info "Running seed data script..."
    uv run python scripts/seed_data.py
    log_success "Test data seeded successfully."
else
    log_info "Skipping data seeding."
fi

# ==============================================================================
# Step 8: Choose Deployment Mode & Start Services
# ==============================================================================
log_info "Choose deployment mode:"
log_info "  [1] Local Development (microservices run on host via 'make dev-all')"
log_info "  [2] Production (fully containerized via 'make prod')"
read -r -p "Enter your choice [1/2]: " DEPLOY_CHOICE

case $DEPLOY_CHOICE in
    1)
        log_info "Starting microservices in local development mode..."
        make dev-all
        log_success "Local microservices started in the background."
        STOP_CMD="make stop-dev"
        LOGS_CMD="make logs"
        ;;
    2)
        log_info "Building and starting production containers..."
        make prod
        log_success "Production services started successfully."
        STOP_CMD="make down"
        LOGS_CMD="docker compose logs -f"
        ;;
    *)
        log_error "Invalid choice. Please run the script again and choose 1 or 2."
        ;;
esac

# ==============================================================================
# Step 9: Final Health Check & Success Summary
# ==============================================================================
log_info "Performing final health check..."
sleep 3 # Give services a moment to initialize

# We can't easily curl the API without a token, but we can check if the container/process is up.
if [ "$DEPLOY_CHOICE" == "1" ]; then
    if pgrep -f "uvicorn services.api.main" > /dev/null; then
        log_success "API Service is running."
    else
        log_warn "API Service might not have started correctly. Check logs."
    fi
else
    if docker ps --filter "name=cnss-api" --filter "status=running" | grep -q cnss-api; then
        log_success "API Service container is running."
    else
        log_warn "API Service container might not have started correctly. Check logs."
    fi
fi

echo ""
echo "=============================================================================="
echo -e "${GREEN} CnSS Deployment Completed Successfully!${NC}"
echo "=============================================================================="
echo ""
echo " Service Endpoints:"
echo "   - REST API:       http://localhost:8000"
echo "   - WebSocket:      ws://localhost:8001"
echo "   - UDP Ingestion:  0.0.0.0:5140"
echo "   - pgAdmin UI:     http://localhost:5050 (dev mode only)"
echo ""
echo " Default Test Credentials (if seeded):"
echo "   - Admin:  username: admin    | password: admin123"
echo "   - Viewer: username: viewer   | password: viewer123"
echo ""
echo " Useful Commands:"
echo "   - View logs:      $LOGS_CMD"
echo "   - Stop services:  $STOP_CMD"
echo ""
echo "=============================================================================="