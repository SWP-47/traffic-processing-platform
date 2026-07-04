# Static View — Component Architecture

## Diagram

The component diagram ([component-diagram.puml](component-diagram.puml)) illustrates the internal structure of the Traffic Processing Platform, showing all major components, their responsibilities, interfaces, protocols, and data flows.

## What the Diagram Shows

### Component Hierarchy

The platform is organized into **four primary subsystems**, each encapsulated in its own package:

1. **Traffic Processor (TP)**: Split into two planes:
   - **FPGA Data Plane**: Handles wire-speed packet forwarding using SystemVerilog on an ARTIX-7 FPGA. This is the critical path — any failure here would disrupt user internet access.
   - **Software Telemetry Plane**: Runs alongside the FPGA, extracting packet metadata (IPs, ports, direction) using Python/Scapy and forwarding it to the Communication Node.

2. **Communication Node (CN)**: Acts as a local batching agent. It receives raw packet metadata from the TP, aggregates it into time-windowed `TelemetryBatch` payloads, and forwards them to the CnSS over UDP.

3. **Control and Status Server (CnSS)**: The backend core, decomposed into **four independent microservices**:
   - **Ingestion Worker**: Receives UDP datagrams, tracks sequences, buffers raw metadata in Redis, and periodically flushes to TimescaleDB.
   - **Reporting Worker**: Runs a 1Hz polling loop, discovers active subscriptions, executes SQL queries, and publishes aggregated results to Redis Pub/Sub.
   - **WebSocket Service**: Manages persistent client connections, handles JWT authentication, subscription lifecycle, and routes Pub/Sub messages to connected clients.
   - **REST API & Auth Service**: Provides HTTP endpoints for login, channel discovery, and historical data retrieval.

4. **Management User Interface (MUI)**: A React/TypeScript single-page application that connects to the CnSS via REST (for discovery and history) and WebSocket (for real-time telemetry).

### Data Stores

- **TimescaleDB** (Persistent): Stores raw `packet_flows`, continuous aggregates (`telemetry_1s`), channel registry, and user/scope data.
- **Redis** (Ephemeral): Provides high-speed buffering (`udp:buffer`), state tracking (`channel:state`), sequence tracking (`channel:seq`), subscription management (`sub:*`), session management (`ws:session`), and token revocation (`jwt:revoked`).

### Infrastructure

- **Edge Nginx**: Serves as the single TLS termination point, routing HTTPS traffic to MUI and CnSS REST API, and WSS traffic to the WebSocket Service.

### Protocols and Data Flows

| Flow | Protocol | Description |
|------|----------|-------------|
| User ↔ TP | Ethernet/IP | Transparent packet forwarding (data plane) |
| TP → CN | Local UDP/IPC | Raw packet metadata transfer |
| CN → CnSS | UDP (port 5140) | `TelemetryBatch` JSON payloads |
| CnSS ↔ Redis | RESP (async) | State, buffering, pub/sub |
| CnSS ↔ TimescaleDB | PostgreSQL (asyncpg) | Batch inserts, time-series queries |
| MUI → CnSS | HTTPS (REST) | Authentication, channel discovery, history |
| MUI ↔ CnSS | WSS (WebSocket) | Real-time telemetry and subscription control |
| Admin → MUI | HTTPS | Browser-based dashboard access |

## Coupling and Cohesion Analysis

### Coupling

The architecture exhibits **low coupling** between major subsystems:

- **TP ↔ CN**: Communicates via a simple local UDP/IPC protocol with a well-defined JSON schema (`PacketMeta`). The TP has no knowledge of the CN's internal batching logic.
- **CN ↔ CnSS**: Communicates via UDP with a single payload type (`TelemetryBatch`). The CN does not need to know about CnSS's database schema, WebSocket protocol, or authentication mechanism.
- **CnSS ↔ MUI**: Communicates via REST (stateless) and WebSocket (stateful but protocol-defined). The MUI has no direct access to TimescaleDB or Redis.
- **CnSS Internal Services**: The four microservices communicate exclusively through Redis (Pub/Sub, shared state) and TimescaleDB. There are no direct service-to-service HTTP calls.

**Inter-service coupling within CnSS** is mediated by Redis and TimescaleDB, which act as shared communication channels. This is a deliberate architectural choice that enables:

- Independent deployment and scaling of each microservice.
- Fault isolation — if the WebSocket Service crashes, the Ingestion Worker continues buffering data.

### Cohesion

Each component demonstrates **high functional cohesion**:

- **Ingestion Worker**: All its responsibilities (UDP reception, sequence tracking, buffering, flushing) are tightly related to the single concern of "receiving and persisting telemetry."
- **Reporting Worker**: All its responsibilities (polling, SQL execution, pub/sub publishing, ghost cleanup) revolve around "aggregating and distributing data to subscribers."
- **WebSocket Service**: Focused entirely on "managing client connections and subscription lifecycle."
- **REST API**: Focused on "authentication and data retrieval over HTTP."

## Impact on Maintainability

### Positive Impacts

1. **Independent Deployment**: Each microservice can be updated, restarted, or scaled without affecting others. For example, adding a new subscription target (e.g., `host_top_ports`) only requires changes to the Reporting Worker's handler registry — no changes to the WebSocket Service or Ingestion Worker.

2. **Technology Isolation**: The FPGA code (SystemVerilog), TP software (Python), CN (Python), CnSS (Python/FastAPI), and MUI (TypeScript/React) are fully isolated. Teams can work on different components without merge conflicts.

3. **Testability**: Each microservice can be tested independently. The Ingestion Worker can be tested with mock UDP packets, the WebSocket Service with mock Redis, and the REST API with `httpx` test clients.

4. **Clear Boundaries**: The use of Redis as a communication bus means that service interfaces are implicitly defined by Redis key structures and Pub/Sub channels, which are documented in `architecture.md`.

### Challenges

1. **Redis as Single Point of Coordination**: All four CnSS microservices depend on Redis. If Redis becomes unavailable, the entire CnSS pipeline stalls (Ingestion can't buffer, Reporting can't poll, WebSocket can't authenticate). This is an accepted trade-off for performance, but it means Redis must be highly available.

2. **Schema Evolution**: Changes to the `TelemetryBatch` schema require coordinated updates across TP, CN, and CnSS Ingestion. The monorepo structure helps here, as all code is in one repository and can be updated atomically.

3. **Distributed Debugging**: When a telemetry update is delayed, the root cause could be in any of the four microservices, Redis, or TimescaleDB. Comprehensive logging and structured tracing are essential.

## Quality Requirements Supported or Constrained

### Supported

| Quality Requirement | How the Architecture Supports It |
|---------------------|----------------------------------|
| **Performance (Time Behaviour)** | The separation of Ingestion (write-heavy) and Reporting (read-heavy) allows independent scaling. Redis buffering decouples UDP ingestion speed from database write speed. Continuous aggregates in TimescaleDB pre-compute metrics, avoiding heavy `GROUP BY` queries at runtime. |
| **Reliability (Fault Tolerance)** | If the WebSocket Service crashes, active sessions expire via Redis TTL (10s), and the Ghost Cleaner removes stale listeners. If the Ingestion Worker crashes, Redis buffers persist until it restarts. If TimescaleDB is temporarily unavailable, the Ingestion Worker continues buffering in Redis (capped at 100k items). |
| **Security (Confidentiality)** | JWT authentication is enforced at the WebSocket and REST layers. Scope-based authorization restricts viewers to specific channels. Token revocation via Redis (`jwt:revoked`) enables immediate session termination. Edge Nginx centralizes TLS termination, ensuring all external traffic is encrypted. |
| **Maintainability (Testability)** | High cohesion and low coupling make each component independently testable. The CI pipeline enforces ≥30% coverage on critical CnSS modules. |
| **Scalability** | The microservice decomposition allows horizontal scaling. For example, if WebSocket connections become the bottleneck, multiple WebSocket Service instances can be deployed behind a load balancer, all sharing the same Redis Pub/Sub channels. |

### Constrained

| Constraint | Explanation |
|------------|-------------|
| **UDP Reliability** | The CN → CnSS communication uses UDP, which is inherently unreliable. Packet loss is accepted for monitoring purposes, but it means the system cannot guarantee 100% telemetry delivery. Sequence tracking and `dropped_batches` metrics mitigate this by making losses visible. |
| **Redis Persistence** | Redis is explicitly configured without persistence (no RDB/AOF) to maximize IOPS. If Redis restarts, unflushed buffers and sequence states are lost. This is an accepted trade-off, but it means the system cannot guarantee zero data loss during Redis failures. |
| **Single TimescaleDB Instance** | The current deployment uses a single TimescaleDB instance. If it becomes unavailable, all persistent data operations fail. Future versions may consider TimescaleDB clustering or read replicas for high availability. |
| **Monorepo Coordination** | While the monorepo simplifies atomic updates, it also means that all components share the same CI/CD pipeline. A breaking change in one component (e.g., `TelemetryBatch` schema) requires coordinated updates across multiple services. |