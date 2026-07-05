.PHONY: help dev prod down logs

help:
	@echo "Available commands:"
	@echo "  make dev    - Launch development environment (Vite) with hot reload."
	@echo "  make prod   - Launch production build (Nginx)."
	@echo "  make down   - Stop and remove all containers."
	@echo "  make logs   - Follow container logs in real-time."

dev:
	@echo "🚀 Launching the development environment..."
	docker compose --profile dev up --build --watch

prod:
	@echo "🏭 Launching the production environment..."
	docker compose --profile prod up -d --build

down:
	@echo "🛑 Stopping all containers..."
	docker compose --profile "*" down

logs:
	docker compose logs -f