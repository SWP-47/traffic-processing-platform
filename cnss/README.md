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

Copy the example environment file and adjust the variables if necessary.
*Note: Ensure `DATABASE_URL` and `REDIS_URL` point to `localhost` if you plan to run Python services directly on your host machine, or keep them as `timescaledb`/`redis` if running inside Docker.*

```bash
cp .env.example .env
```

### 3. Running Infrastructure

Start the required infrastructure services (TimescaleDB, Redis, pgAdmin) in detached mode using Docker Compose:

```bash
make up
```

### 4. Database Migrations

Apply the initial database schema, TimescaleDB hypertables, and continuous aggregates:

```bash
make migrate
```

## Development

### Running Tests

Execute the test suite (unit, integration, e2e):

```bash
make test
```

### Linting and Formatting

The project uses `black`, `flake8`, `ruff`, and `mypy` for code quality.
Check code quality:

```bash
make lint
```

Automatically format code:

```bash
make format
```

## Documentation

Detailed architectural decisions, API specifications, WebSocket protocols, and deployment guides can be found in the `docs/` directory.
