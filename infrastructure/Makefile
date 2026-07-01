# ==============================================================================
# Infrastructure Layer Makefile
# Manages the Edge Nginx reverse proxy, TLS certificates, and certificate
# distribution for local network clients.
# This layer sits in front of both CnSS (API/WS) and MUI (static) services.
# ==============================================================================

.PHONY: help certs serve-certs up down restart logs status clean-certs test-ssl

# Default target: show help
.DEFAULT_GOAL := help

# ==============================================================================
# Configuration Variables
# ==============================================================================

# Docker Compose file for the infrastructure layer
COMPOSE_FILE := docker-compose.infra.yml

# Directory for TLS certificates (mounted into Nginx container)
CERTS_DIR := ./nginx/certs

# Public certificate filename (distributed to clients)
CERT_PUBLIC := fullchain.pem

# Local certificate copy for system trust store installation
CERT_LOCAL := cnss-local.crt

# Port for the HTTP certificate distribution server
CERTS_PORT := 9000

# ==============================================================================
# Help
# ==============================================================================

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

# ==============================================================================
# TLS Certificate Management
# ==============================================================================

# --- Self-Signed Certificate Generation ---
# Generates a 1-year self-signed certificate with SAN for localhost and 127.0.0.1.
# Modern browsers require SAN (Subject Alternative Name) and ignore CN.
## certs: Generate self-signed TLS certificates for local HTTPS/WSS testing
certs:
	@mkdir -p $(CERTS_DIR)
	@openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
		-keyout $(CERTS_DIR)/privkey.pem \
		-out $(CERTS_DIR)/$(CERT_PUBLIC) \
		-subj "/C=RU/ST=Local/L=Local/O=CnSS/CN=localhost" \
		-addext "subjectAltName=DNS:localhost,DNS:*.local,IP:127.0.0.1"
	@cp $(CERTS_DIR)/$(CERT_PUBLIC) $(CERTS_DIR)/$(CERT_LOCAL)
	@chmod 600 $(CERTS_DIR)/privkey.pem
	@chmod 644 $(CERTS_DIR)/$(CERT_PUBLIC)
	@echo "✓ Certificates generated in $(CERTS_DIR)/"

## serve-certs: Start HTTP server to distribute certificates to local network clients
serve-certs:
	@if [ ! -f "$(CERTS_DIR)/$(CERT_LOCAL)" ]; then \
		echo "✗ Certificate not found. Run 'make certs' first."; \
		exit 1; \
	fi
	@echo "Clients can download the certificate at:"
	@echo "  http://<YOUR-SERVER-IP>:$(CERTS_PORT)/$(CERT_LOCAL)"
	@cd $(CERTS_DIR) && python -m http.server $(CERTS_PORT) --bind 0.0.0.0

## clean-certs: Remove all generated TLS certificates
clean-certs:
	@rm -f $(CERTS_DIR)/privkey.pem $(CERTS_DIR)/$(CERT_PUBLIC) $(CERTS_DIR)/$(CERT_LOCAL)
	@echo "✓ All certificates removed."

## test-ssl: Test SSL connection to Edge Nginx
test-ssl:
	@echo | openssl s_client -connect localhost:443 -servername localhost 2>/dev/null | openssl x509 -noout -dates -subject -issuer

## up: Start Edge Nginx reverse proxy in detached mode
up:
	@echo "🚀 Starting Edge Nginx..."
	@if [ ! -f "$(CERTS_DIR)/$(CERT_PUBLIC)" ]; then \
		echo "⚠ TLS certificate not found. Generating..."; \
		$(MAKE) certs; \
	fi
	docker compose -f $(COMPOSE_FILE) up -d
	@echo "✓ Edge Nginx is running."
	@echo "  - HTTPS: https://localhost"
	@echo "  - API:   https://localhost/api/"
	@echo "  - WS:    wss://localhost/ws/"

## down: Stop and remove Edge Nginx container
down:
	@echo "🛑 Stopping Edge Nginx..."
	docker compose -f $(COMPOSE_FILE) down
	@echo "✓ Edge Nginx stopped."

## restart: Restart Edge Nginx container
restart:
	@echo "🔄 Restarting Edge Nginx..."
	docker compose -f $(COMPOSE_FILE) restart
	@echo "✓ Edge Nginx restarted."

## logs: Follow Edge Nginx logs in real-time
logs:
	docker compose -f $(COMPOSE_FILE) logs -f

## status: Show status of infrastructure containers
status:
	docker compose -f $(COMPOSE_FILE) ps