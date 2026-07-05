# ==============================================================================
# CnSS REST API & Auth Service Dockerfile
# Builds a lightweight, production-ready image for the HTTP gateway, identity
# management, and historical data retrieval service using FastAPI and Uvicorn.
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

# Install production dependencies for the API service.
# The '--no-dev' flag excludes testing and linting tools to keep the image small.
RUN uv sync --extra api --no-dev

# --- Source Code ---
# Copy the core shared modules and the specific API service code.
COPY core/ ./core/
COPY services/api/ ./services/api/

# --- Execution ---
# Expose the HTTP port for internal Docker network routing (handled externally by Nginx).
EXPOSE 8000

# Run the API service using Uvicorn via uv to ensure the virtual environment is activated.
# Note: '--reload' is intentionally omitted for production stability.
CMD ["uv", "run", "uvicorn", "services.api.main:app", "--host", "0.0.0.0", "--port", "8000"]