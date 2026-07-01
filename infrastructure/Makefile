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
	@echo "======================================================================"
	@echo " Generating Self-Signed TLS Certificate"
	@echo "======================================================================"
	@mkdir -p $(CERTS_DIR)
	@echo "Generating RSA 2048-bit key and certificate (valid for 365 days)..."
	@openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
		-keyout $(CERTS_DIR)/privkey.pem \
		-out $(CERTS_DIR)/$(CERT_PUBLIC) \
		-subj "/C=RU/ST=Local/L=Local/O=CnSS/CN=localhost" \
		-addext "subjectAltName=DNS:localhost,DNS:*.local,IP:127.0.0.1"
	@cp $(CERTS_DIR)/$(CERT_PUBLIC) $(CERTS_DIR)/$(CERT_LOCAL)
	@chmod 600 $(CERTS_DIR)/privkey.pem
	@chmod 644 $(CERTS_DIR)/$(CERT_PUBLIC)
	@echo ""
	@echo "✓ Certificates generated successfully in $(CERTS_DIR)/"
	@echo "  - privkey.pem      (private key, 600 permissions)"
	@echo "  - $(CERT_PUBLIC)   (certificate for Nginx)"
	@echo "  - $(CERT_LOCAL)    (copy for client distribution)"
	@echo ""
	@echo "----------------------------------------------------------------------"
	@echo " To trust this certificate on Arch Linux (system-wide):"
	@echo "   sudo cp $(CERTS_DIR)/$(CERT_LOCAL) /etc/ca-certificates/trust-source/anchors/cnss-local.crt"
	@echo "   sudo trust extract-compat"
	@echo ""
	@echo " To distribute to LAN clients (Windows/Linux/macOS):"
	@echo "   make serve-certs"
	@echo "----------------------------------------------------------------------"

# --- Certificate Distribution Server ---
# Starts a simple Python HTTP server to serve the public certificate to LAN clients.
# Uses HTTP (not HTTPS) intentionally — clients need the cert before they can trust HTTPS.
## serve-certs: Start HTTP server to distribute certificates to local network clients
serve-certs:
	@if [ ! -f "$(CERTS_DIR)/$(CERT_LOCAL)" ]; then \
		echo "✗ Certificate not found. Run 'make certs' first."; \
		exit 1; \
	fi
	@echo "======================================================================"
	@echo " CnSS Certificate Distribution Server"
	@echo "======================================================================"
	@echo ""
	@echo " Clients can download the certificate at:"
	@echo "   http://<YOUR-SERVER-IP>:$(CERTS_PORT)/$(CERT_LOCAL)"
	@echo ""
	@echo " To find your server IP:"
	@echo "   ip addr show | grep 'inet ' | grep -v 127.0.0.1"
	@echo ""
	@echo " Windows installation:"
	@echo "   1. Download $(CERT_LOCAL) via browser"
	@echo "   2. Double-click the file → Install Certificate"
	@echo "   3. Choose 'Local Machine' → Next"
	@echo "   4. 'Place all certificates in the following store'"
	@echo "   5. Browse → 'Trusted Root Certification Authorities'"
	@echo "   6. Finish → Yes (security warning)"
	@echo ""
	@echo " Press Ctrl+C to stop the server"
	@echo "======================================================================"
	@cd $(CERTS_DIR) && python -m http.server $(CERTS_PORT) --bind 0.0.0.0

# --- Certificate Cleanup ---
# Removes all generated certificates. Use with caution.
## clean-certs: Remove all generated TLS certificates
clean-certs:
	@echo "Removing certificates from $(CERTS_DIR)/..."
	@rm -f $(CERTS_DIR)/privkey.pem
	@rm -f $(CERTS_DIR)/$(CERT_PUBLIC)
	@rm -f $(CERTS_DIR)/$(CERT_LOCAL)
	@echo "✓ All certificates removed."

# --- SSL Connection Test ---
# Verifies that Edge Nginx is serving the certificate correctly on port 443.
## test-ssl: Test SSL connection to Edge Nginx
test-ssl:
	@echo "Testing SSL connection to localhost:443..."
	@echo | openssl s_client -connect localhost:443 -servername localhost 2>/dev/null | openssl x509 -noout -dates -subject -issuer
	@echo ""
	@echo "If you see certificate details above, TLS is working correctly."

# ==============================================================================
# Container Management
# ==============================================================================

# --- Start Infrastructure ---
# Launches Edge Nginx in detached mode. Builds the image if not present.
# Nginx connects to the external 'cnss-network' Docker network to reach CnSS services.
## up: Start Edge Nginx reverse proxy in detached mode
up:
	@echo "🚀 Starting Edge Nginx..."
	@if [ ! -f "$(CERTS_DIR)/$(CERT_PUBLIC)" ]; then \
		echo "⚠ TLS certificate not found. Generating self-signed certificate..."; \
		$(MAKE) certs; \
	fi
	docker compose -f $(COMPOSE_FILE) up -d
	@echo ""
	@echo "✓ Edge Nginx is running."
	@echo "  - HTTPS: https://localhost"
	@echo "  - WSS:   wss://localhost/api/v1/ws/..."
	@echo ""
	@echo "Note: Ensure CnSS services are running ('make prod' in cnss/)"

# --- Stop Infrastructure ---
# Stops and removes the Edge Nginx container and its network.
## down: Stop and remove Edge Nginx container
down:
	@echo "🛑 Stopping Edge Nginx..."
	docker compose -f $(COMPOSE_FILE) down
	@echo "✓ Edge Nginx stopped."

# --- Restart Infrastructure ---
# Restarts Edge Nginx. Useful after nginx.conf changes.
## restart: Restart Edge Nginx container
restart:
	@echo "🔄 Restarting Edge Nginx..."
	docker compose -f $(COMPOSE_FILE) restart
	@echo "✓ Edge Nginx restarted."

# --- Logs ---
# Tails Edge Nginx logs in real-time.
## logs: Follow Edge Nginx logs in real-time
logs:
	docker compose -f $(COMPOSE_FILE) logs -f

# --- Status ---
# Shows the status of infrastructure containers.
## status: Show status of infrastructure containers
status:
	docker compose -f $(COMPOSE_FILE) ps