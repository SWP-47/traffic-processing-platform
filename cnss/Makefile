# Makefile for CnSS project management
# Provides aliases for common development and deployment tasks

.PHONY: up down test migrate lint format install

# Install all dependencies including dev extras using uv
install:
	uv sync --all-extras

# Start all services in detached mode using docker-compose
up:
	docker-compose -f docker-compose.dev.yml up -d --build

# Stop all running services
down:
	docker-compose -f docker-compose.dev.yml down

# Run the test suite
test:
	pytest tests/ -v

# Apply database migrations using Alembic
migrate:
	alembic upgrade head

# Run code linters (Ruff, Flake8, and Mypy)
lint:
	ruff check .
	flake8 .
	mypy .

# Automatically format code using Black and Ruff
format:
	black .
	ruff check --fix .