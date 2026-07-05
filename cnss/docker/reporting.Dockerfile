# ==============================================================================
# CnSS Reporting Worker Dockerfile
# Builds a lightweight, production-ready image for the background aggregator.
# Handles periodic metric aggregation, state synchronization, and Pub/Sub publishing.
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

# Install production dependencies for the reporting worker.
# The '--no-dev' flag excludes testing and linting tools to keep the image small.
RUN uv sync --extra reporting --no-dev

# --- Source Code ---
# Copy the core shared modules and the specific reporting service code.
COPY core/ ./core/
COPY services/reporting/ ./services/reporting/

# --- Execution ---
# Run the reporting worker using uv to ensure the virtual environment is activated.
# No ports need to be exposed as this is a background worker communicating via Redis/DB.
CMD ["uv", "run", "python", "-m", "services.reporting.main"]