# ADR-003: Microservice Decomposition of CnSS Backend

## Status

**Accepted** — Implemented in MVP v2 with 4 isolated Docker microservices.

## Context

The Control and Status Server (CnSS) must handle multiple concurrent responsibilities:
- High-frequency UDP telemetry ingestion
- Real-time WebSocket client connections
- Periodic metric aggregation and SQL execution
- REST API for authentication and historical data
- Session management and subscription lifecycle

**Key constraints:**
- Each responsibility has different performance characteristics (CPU, I/O, network)
- Failures in one area must not cascade to others
- System must support horizontal scaling in future versions
- Development teams work on different components concurrently
- CI/CD pipeline must support independent testing and deployment

**Quality Requirements addressed:**
- **QR-003 (Testability)**: Enable independent testing of each component
- **QR-002 (Fault Tolerance)**: Isolate failures to prevent cascading
- **QR-001 (Time Behaviour)**: Allow independent scaling of bottleneck components

## Decision

We decompose CnSS into 4 isolated Docker microservices communicating via Redis and TimescaleDB:

### 1. Ingestion Worker (`cnss-ingestion`)
- **Responsibility**: UDP reception, sequence tracking, Redis buffering, batch flush to TimescaleDB
- **Ports**: 5140/UDP (exposed to host)
- **Dependencies**: Redis, TimescaleDB
- **Failure Impact**: Telemetry ingestion stops; existing buffers persist in Redis

### 2. Reporting Worker (`cnss-reporting`)
- **Responsibility**: 1Hz polling loop, SQL aggregation, Pub/Sub publishing, channel state sync
- **Ports**: None (internal only)
- **Dependencies**: Redis, TimescaleDB
- **Failure Impact**: Real-time updates stop; last known state persists

### 3. WebSocket Service (`cnss-websocket`)
- **Responsibility**: Client connection management, JWT validation, subscription lifecycle, Pub/Sub consumer
- **Ports**: 8001 (internal, proxied by Nginx)
- **Dependencies**: Redis, TimescaleDB
- **Failure Impact**: Active connections dropped; clients reconnect automatically

### 4. REST API & Auth Service (`cnss-api`)
- **Responsibility**: HTTP gateway, authentication, channel discovery, historical data retrieval
- **Ports**: 8000 (internal, proxied by Nginx)
- **Dependencies**: Redis, TimescaleDB
- **Failure Impact**: REST endpoints unavailable; WebSocket continues functioning

### Communication Pattern
- **Redis**: Pub/Sub for real-time updates, shared state for sessions/subscriptions
- **TimescaleDB**: Persistent storage, continuous aggregates for aggregation
- **No Direct Service-to-Service Calls**: All communication mediated by Redis/DB

## Consequences

### Positive
- **Fault Isolation**: Crash in one service doesn't affect others (e.g., WebSocket crash doesn't stop ingestion)
- **Independent Scaling**: Each service can be scaled independently based on load (future improvement)
- **Technology Isolation**: Each service can use different libraries/versions without conflicts
- **Parallel Development**: Teams work on different services without merge conflicts
- **Independent Testing**: Each service tested in isolation with mocked dependencies
- **Clear Boundaries**: Service interfaces defined by Redis key structures and DB schema
- **Docker Restart Policy**: `restart: always` ensures automatic recovery from crashes

### Negative
- **Operational Complexity**: 4 containers to manage, monitor, and debug instead of 1
- **Network Overhead**: Inter-service communication via Redis adds latency (minimal)
- **Distributed Debugging**: Tracing issues across services requires comprehensive logging
- **Redis Dependency**: All services depend on Redis; if Redis fails, entire CnSS degrades
- **Schema Coordination**: Changes to shared data structures (Redis keys, DB schema) require coordinated updates
- **Resource Overhead**: Each container has its own memory/CPU footprint

### Risks
- **Redis as Single Point of Failure**: If Redis crashes, all services lose coordination
- **Distributed Deadlocks**: Unlikely but possible with complex Redis operations
- **Version Incompatibility**: Services may drift in dependency versions over time

## Quality Requirements Traceability

| Quality Requirement | How This Decision Addresses It |
|---------------------|-------------------------------|
| **QR-003 (Testability)** | Each microservice tested independently with mocked Redis/DB. CI pipeline runs separate test suites per service. ≥30% coverage enforced per critical module. |
| **QR-002 (Fault Tolerance)** | Complete fault isolation between services. Docker `restart: always` policy ensures automatic recovery. TTL-based session cleanup prevents orphaned state. |
| **QR-001 (Time Behaviour)** | Independent scaling allows bottleneck components to be optimized separately. Redis Pub/Sub provides low-latency inter-service communication. |

## Alternatives Considered

### Alternative 1: Monolithic Application
- **Pros**: Simpler deployment, easier debugging, no network overhead
- **Cons**: Single point of failure, cannot scale components independently, harder to test in isolation
- **Rejected because**: Cannot meet fault tolerance requirements; one crash brings down entire system

### Alternative 2: Thread-Based Concurrency (Single Process)
- **Pros**: Shared memory, simpler communication, lower resource usage
- **Cons**: GIL limits parallelism in Python, harder to isolate failures, complex thread management
- **Rejected because**: Python GIL prevents true parallelism; fault isolation impossible

### Alternative 3: Kubernetes with Service Mesh
- **Pros**: Advanced orchestration, auto-scaling, service discovery, observability
- **Cons**: Overkill for single-VM deployment, steep learning curve, higher operational cost
- **Rejected because**: Project scope and infrastructure constraints (single VM, course project)

### Alternative 4: Serverless (AWS Lambda / Azure Functions)
- **Pros**: Auto-scaling, pay-per-use, no server management
- **Cons**: Cold start latency, limited execution time, vendor lock-in, complex state management
- **Rejected because**: Real-time WebSocket connections and persistent state don't fit serverless model

## References

- **System Architecture**: [docs/system-documentation.md](../../system-documentation.md) §2.3 Control and Status Server
- **Docker Compose**: [cnss/docker-compose.yml](../../../cnss/docker-compose.yml)
- **Service Dockerfiles**: [cnss/docker/](../../../cnss/docker/)
- **Quality Requirements**: [docs/quality-requirements.md](../../quality-requirements.md)
- **User Stories**: US-014 (Remote MUI Access), US-015 (Real-time Dashboard Updates)
