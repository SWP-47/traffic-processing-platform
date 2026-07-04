# ==============================================================================
# CnSS WebSocket Service Dockerfile
# Builds a lightweight, production-ready image for the persistent client
# connection management and subscription routing gateway.
# ==============================================================================

# --- Base Image ---
# Use a slim Python image to minimize the final image footprint and attack surface.
FROM python:3.11-slim

# --- Dependency Management Tool ---
# Install the uv package manager directly from the official Astral image.
# This provides extremely fast dependency resolution and installation.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Set the working directory inside the container
WORKDIR /app

# --- Dependency Installation ---
# Copy only the dependency manifests first to leverage Docker layer caching.
# This prevents re-installing dependencies when only source code changes.
COPY pyproject.toml uv.lock ./

# Install production dependencies for the WebSocket service.
# The '--no-dev' flag excludes testing and linting tools to keep the image small.
RUN uv sync --extra websocket --no-dev

# --- Source Code ---
# Copy the core shared modules and the specific WebSocket service code.
COPY core/ ./core/
COPY services/websocket/ ./services/websocket/

# --- Execution ---
# Expose the HTTP/WS port for client connections (routed externally via Nginx).
EXPOSE 8000

# Run the WebSocket service using uv to ensure the virtual environment is activated.
CMD ["uv", "run", "python", "-m", "services.websocket.main"]