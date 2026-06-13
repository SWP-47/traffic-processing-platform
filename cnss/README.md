# Control and Status Server (CnSS)

Backend component responsible for aggregating telemetry data from the Communication Node (CN) and exposing operational status and real-time metrics to the Management User Interface (MUI).

## MVP v0 Scope

This is the minimal technical foundation (MVP v0) for the CnSS component. It currently provides:
- A containerized FastAPI application.
- Distinct build configurations for Local Development (Dev) and Virtual Machine deployment (Prod).
- A single `/health` endpoint to verify service availability and operational status.

*Note: UDP ingestion, WebSocket streaming, and database persistence will be implemented in subsequent iterations (MVP v1).*

---

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/)
- [Docker Compose](https://docs.docker.com/compose/install/)

---

## Local Development (Dev Build)

Use this configuration for active local development. It includes hot-reload capabilities to reflect code changes instantly.

1. Navigate to the `cnss/` directory:
   ```bash
   cd cnss/
   ```
2. (Optional) Create a local `.env` file based on the example:
   ```bash
   cp .env.example .env
   ```
3. Start the development environment:
   ```bash
   docker-compose up --build
   ```
   *The server will be available at `http://localhost:8000`.*

---

## Production Deployment (VM Build)

Use this configuration for deploying the service on a production Virtual Machine. It is optimized for security (non-root user) and performance (multiple Uvicorn workers).

1. Copy the `cnss/` directory to your target VM.
2. Ensure a `.env` file is present with production-appropriate values (do not use default dev tokens).
3. Start the production environment in detached mode:
   ```bash
   docker-compose -f docker-compose.prod.yml up --build -d
   ```
4. Verify the container is running and healthy:
   ```bash
   docker-compose -f docker-compose.prod.yml ps
   ```

---

## Smoke-Check Scenario (MVP v0 Validation)

To validate that the MVP v0 foundation is correctly deployed and operational, perform the following repeatable smoke-check. This applies to both Dev and Prod environments.

### Step 1: Send a Health Check Request
Execute the following `curl` command against the running service:
```bash
curl -v http://localhost:8000/health
```

### Step 2: Verify Expected Results
The request must return an HTTP `200 OK` status and a JSON payload matching the following structure:
```json
{
  "status": "healthy",
  "message": "CnSS server is running",
  "timestamp": "2026-06-13T12:00:00Z"
}
```
*(Note: The `timestamp` will reflect the current UTC time of the server.)*

### Step 3: Verify Logs (Prod Only)
Check the container logs to ensure no startup errors occurred:
```bash
docker-compose -f docker-compose.prod.yml logs cnss
```
*Expected: Logs should show Uvicorn starting successfully on `0.0.0.0:8000` without `ERROR` or `WARNING` levels.*

---

## Related Documentation

- [Root README](../README.md) - Project overview and monorepo setup.
- [API Documentation](../api/README.md) - Detailed endpoint specifications (updated as features are added).
