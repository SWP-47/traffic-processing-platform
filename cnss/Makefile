# ==============================================================================
# CnSS Project Makefile
# Provides aliases for common development, testing, and deployment tasks.
# ==============================================================================

.PHONY: help install dev prod down test migrate lint format \
        run-api run-ingestion run-reporting run-websocket dev-all stop-dev \
        deploy clean create-user

# Default target: show help
.DEFAULT_GOAL := help

## help: Show this help message
help:
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@awk '/^## / {sub(/^## /, ""); printf "  \033[36m%-20s\033[0m %s\n", $$1, $$0}' $(MAKEFILE_LIST) \
	| sed 's/^\([a-zA-Z0-9_-]*\):.*$$/\1/'
	@echo ""
	@awk '/^[a-zA-Z0-9_-]+:.*?##/ { \
		helpMessage = match($$0, /## (.*)$$/, m); \
		if (helpMessage) { \
			printf "  \033[36m%-20s\033[0m %s\n", $$1, m[1]; \
		} \
	}' $(MAKEFILE_LIST)

## install: Install all dependencies (including dev extras) using uv
install:
	uv sync --all-extras

## dev: Start infrastructure services (TimescaleDB, Redis, pgAdmin) for local development
dev:
	docker compose -f docker-compose.dev.yml up -d

## prod: Build and start all services (including microservices) for production
prod:
	docker compose -f docker-compose.yml up -d --build

## down: Stop all running services (dev or prod)
down:
	docker compose -f docker-compose.dev.yml down 2>/dev/null || true
	docker compose -f docker-compose.yml down 2>/dev/null || true

## test: Run the test suite
test:
	uv run pytest tests/ -v

## migrate: Apply database migrations using Alembic
migrate:
	uv run alembic upgrade head

## lint: Run code linters (Ruff, Flake8, and Mypy)
lint:
	uv run ruff check .
	uv run flake8 .
	uv run mypy .

## format: Automatically format code using Black and Ruff
format:
	uv run black .
	uv run ruff check --fix .

## create-user: Create a new user. Usage: make create-user USERNAME=name [ROLE=role] [SCOPES="ch1,ch2"]
create-user:
ifndef USERNAME
	@echo "Error: USERNAME is required."
	@echo "Usage: make create-user USERNAME=<username> [ROLE=<admin|viewer>] [SCOPES=<channel1,channel2>]"
	@exit 1
endif
	uv run python scripts/create_user.py $(USERNAME) $(if $(ROLE),--role $(ROLE),) $(if $(SCOPES),--scopes "$(SCOPES)",)

## deploy: Run the automated zero-to-hero deployment script (deploy.sh)
deploy:
	@bash deploy.sh

## clean: Run the production environment cleanup script (clean_prod.sh)
clean:
	@bash clean_prod.sh

# ==============================================================================
# Local Microservices (Run on Host)
# ==============================================================================

## run-api: Run REST API service locally (http://localhost:8000)
run-api:
	uv run uvicorn services.api.main:app --reload --no-access-log --host 0.0.0.0 --port 8000 --log-level info

## run-ingestion: Run Ingestion worker locally (UDP listener)
run-ingestion:
	uv run python -m services.ingestion.main

## run-reporting: Run Reporting worker locally (background aggregator)
run-reporting:
	uv run python -m services.reporting.main

## run-websocket: Run WebSocket service locally (ws://localhost:8001)
run-websocket:
	uv run python -m services.websocket.main

## dev-all: Run ALL microservices locally in background (logs to ./logs/)
dev-all:
	@echo "Starting all microservices in background..."
	@mkdir -p logs
	@echo "Starting API service..."
	@	uv run uvicorn services.api.main:app --reload --no-access-log --host 0.0.0.0 --port 8000 --log-level info > logs/api.log 2>&1 & echo $$! > logs/api.pid
	@echo "Starting Ingestion worker..."
	@uv run python -m services.ingestion.main > logs/ingestion.log 2>&1 & echo $$! > logs/ingestion.pid
	@echo "Starting Reporting worker..."
	@uv run python -m services.reporting.main > logs/reporting.log 2>&1 & echo $$! > logs/reporting.pid
	@echo "Starting WebSocket service..."
	@uv run python -m services.websocket.main > logs/websocket.log 2>&1 & echo $$! > logs/websocket.pid
	@echo ""
	@echo "All services started in background!"
	@echo "  - API:        http://localhost:8000"
	@echo "  - WebSocket:  ws://localhost:8001"
	@echo "  - UDP:        0.0.0.0:5140"
	@echo ""
	@echo "Logs available in ./logs/ directory"
	@echo "Use 'make stop-dev' to stop all services"

## stop-dev: Stop all locally running microservices
stop-dev:
	@echo "Stopping all microservices..."
	@if [ -f logs/api.pid ]; then kill `cat logs/api.pid` 2>/dev/null || true; rm -f logs/api.pid; fi
	@if [ -f logs/ingestion.pid ]; then kill `cat logs/ingestion.pid` 2>/dev/null || true; rm -f logs/ingestion.pid; fi
	@if [ -f logs/reporting.pid ]; then kill `cat logs/reporting.pid` 2>/dev/null || true; rm -f logs/reporting.pid; fi
	@if [ -f logs/websocket.pid ]; then kill `cat logs/websocket.pid` 2>/dev/null || true; rm -f logs/websocket.pid; fi
	@echo "All services stopped"

## logs: Tail all service logs
logs:
	@tail -f logs/*.log