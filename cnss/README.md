# Control and Status Server (CnSS)

The Control and Status Server (CnSS) is the backend core of the traffic processing platform. The architecture is strictly decoupled into isolated, containerized microservices to ensure horizontal scalability, fault isolation, and high-performance telemetry ingestion.

## Architecture Overview

The CnSS consists of four main microservices:

1. **Ingestion Worker**: High-performance UDP telemetry ingestion, sequence tracking, and database buffering.
2. **Reporting Worker**: Periodic metric aggregation, state synchronization, and real-time event publishing.
3. **WebSocket Service**: Persistent client connection management and subscription routing.
4. **REST API & Auth Service**: HTTP gateway, identity management, and historical data retrieval.

## Prerequisites

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) (Fast Python package installer and resolver)
- Docker & Docker Compose

## Getting Started

### 1. Installation

Install all dependencies (including dev extras for linting and testing) using `uv`:

```bash
make install
```

### 2. Environment Setup

Copy the example environment file and adjust the variables if necessary:

```bash
cp .env.example .env
```

### 3. Running Infrastructure

Start the required infrastructure services (TimescaleDB, Redis, pgAdmin) in detached mode using Docker Compose:

```bash
make dev
```

### 4. Database Migrations

Apply the initial database schema, TimescaleDB hypertables, and continuous aggregates:

```bash
make migrate
```

## Development

### Running Microservices Locally

For active development, run microservices directly on your host machine to benefit from hot-reload and IDE debugging:

**Run individual services:**

```bash
make run-api          # REST API (http://localhost:8000)
make run-websocket    # WebSocket service (ws://localhost:8001)
make run-ingestion    # UDP ingestion worker
make run-reporting    # Background aggregator
```

**Run all services at once:**

```bash
make dev-all          # Start all services in background
make logs             # Tail all service logs
make stop-dev         # Stop all services
```

### Running Tests

Execute the test suite (unit, integration, e2e):

```bash
make test
```

### Linting and Formatting

The project uses `black`, `flake8`, `ruff`, and `mypy` for code quality:

```bash
make lint             # Check code quality
make format           # Automatically format code
```

### Makefile Help

View all available commands:

```bash
make help
```

## Production Deployment

For production deployment, all services run in Docker containers:

```bash
make prod
```

This builds and starts the complete stack including:

- All 4 microservices (API, WebSocket, Ingestion, Reporting)
- TimescaleDB (persistent storage)
- Redis (ephemeral buffer and pub/sub)
- Nginx (reverse proxy and TLS termination)

### Interactive script

For deployment, you can use interactive script:

```bash
make deploy
```

### Production cleanup

For cleanup, you can use:

```bash
make clean
```

## Documentation

Detailed architectural decisions, API specifications, WebSocket protocols, and deployment guides can be found in the `docs/` directory.
