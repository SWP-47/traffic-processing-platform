# Control and Status Server (CnSS)

Backend component responsible for aggregating telemetry data from the Communication Node (CN) and exposing operational status and real-time metrics to the Management User Interface (MUI).

---

## Prerequisites

- [Docker](https://docs.docker.com/get-started/get-docker/)
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

## Related Documentation

- [Root README](../README.md) - Project overview and monorepo setup.
- [API Documentation](../api/README.md) - Detailed endpoint specifications (updated as features are added).
