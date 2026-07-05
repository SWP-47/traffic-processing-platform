# ==============================================================================
# CnSS Ingestion Worker Dockerfile
# Builds a lightweight, production-ready image for the high-performance UDP
# telemetry ingestion, sequence tracking, and database buffering service.
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

# Install production dependencies for the ingestion worker.
# The '--no-dev' flag excludes testing and linting tools to keep the image small.
RUN uv sync --extra ingestion --no-dev

# --- Source Code ---
# Copy the core shared modules and the specific ingestion service code.
COPY core/ ./core/
COPY services/ingestion/ ./services/ingestion/

# --- Execution ---
# Expose the UDP port for receiving TelemetryBatch payloads from Communication Nodes.
EXPOSE 5140/udp

# Run the ingestion worker using uv to ensure the virtual environment is activated.
CMD ["uv", "run", "python", "-m", "services.ingestion.main"]