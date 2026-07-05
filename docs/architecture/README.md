# Architecture Documentation

This directory contains the architectural documentation for the Traffic Processing Platform, following a **diagrams-as-code** approach using PlantUML. All diagrams are stored as source files within the repository to ensure they evolve alongside the codebase.

## Table of Contents

1. [Static View](static-view/) — Component structure, interfaces, and data flows
2. [Dynamic View](dynamic-view/) — Runtime behavior and interaction sequences
3. [Deployment View](deployment-view/) — Infrastructure topology and deployment topology

## How to Render Diagrams

All diagrams are stored as `.puml` (PlantUML) source files. You can render them using:

- **VS Code Extension**: [PlantUML](https://marketplace.visualstudio.com/items?itemName=jebbs.plantuml)

Pre-rendered PNG/SVG versions are also provided alongside the source files for convenience.

## Architecture Principles

The platform is built on the following core principles:

1. **Separation of Data Plane and Control Plane**: The Traffic Processor forwards packets at wire speed (data plane) while independently extracting telemetry (control plane). Failure in monitoring must never disrupt traffic flow.
2. **Modular Monorepo**: Four loosely coupled components (`traffic-processor`, `communication-node`, `cnss`, `mui`) communicate via well-defined protocols (UDP, WebSocket, REST).
3. **Ephemeral State, Persistent Storage**: Redis handles high-speed ephemeral buffering and state tracking; TimescaleDB serves as the single source of truth for persistent time-series data.
4. **Horizontal Scalability**: The CnSS is decomposed into four independent microservices that can be scaled independently based on load.
5. **Security by Design**: JWT-based authentication, scope-based authorization, centralized TLS termination, and token masking in logs.

## Architectural Decision Records (ADRs)

The architecture of the Traffic Processing Platform is shaped by a series of explicit architectural decisions, each documented as an **Architectural Decision Record (ADR)**. These ADRs capture the context, rationale, and trade-offs behind key design choices, and explicitly link to the quality requirements they address.

### ADR Index

| ADR ID | Title | Quality Requirements |
|--------|-------|---------------------|
| [ADR-001](adr/adr-001-hardware-software-separation.md) | Hardware-Software Separation for Zero-Impact Monitoring | QR-001, QR-002 |
| [ADR-002](adr/adr-002-ephemeral-redis-buffering.md) | Ephemeral Redis Buffering for High-Performance Telemetry Ingestion | QR-001, QR-002 |
| [ADR-003](adr/adr-003-microservice-decomposition.md) | Microservice Decomposition of CnSS Backend | QR-001, QR-002, QR-003 |

### How Architecture and Decisions Fit Together

The documented architecture and ADRs form a cohesive narrative that explains **why** the system is designed the way it is:

#### 1. Foundation: Zero-Impact Monitoring (ADR-001)

The **Static View** component diagram shows the Traffic Processor split into FPGA (hardware data plane) and Software Telemetry Plane. This separation is not arbitrary — it's a deliberate architectural decision (ADR-001) to ensure that monitoring failures never disrupt user internet connectivity. This directly addresses **QR-002 (Fault Tolerance)** by providing complete fault isolation between the critical data plane and the monitoring control plane.

#### 2. Performance: High-Throughput Ingestion (ADR-002)

The **Dynamic View** sequence diagram illustrates the telemetry pipeline: CN → UDP → Ingestion Worker → Redis Buffer → TimescaleDB. The use of Redis as an ephemeral, capped buffer (ADR-002) is a conscious trade-off that prioritizes performance over durability. By disabling Redis persistence and capping buffer lists at 100,000 items, the system achieves sub-millisecond ingestion latency while preventing OOM crashes during traffic spikes. This addresses **QR-001 (Time Behaviour)** by maximizing throughput and minimizing latency.

#### 3. Maintainability: Microservice Decomposition (ADR-003)

The **Deployment View** shows CnSS decomposed into 4 isolated Docker containers (Ingestion, Reporting, WebSocket, REST API). This microservice architecture (ADR-003) enables independent testing, fault isolation, and future horizontal scaling. Each service communicates exclusively through Redis and TimescaleDB, with no direct service-to-service calls. This addresses **QR-003 (Testability)** by allowing each component to be tested in isolation with mocked dependencies, and **QR-002 (Fault Tolerance)** by containing failures within individual services.

#### 4. Quality Requirements as Design Drivers

Each quality requirement from Assignment 4 directly influenced architectural decisions:

- **QR-001 (Time Behaviour)** → ADR-001 (FPGA wire-speed forwarding) + ADR-002 (Redis ephemeral buffering)
- **QR-002 (Fault Tolerance)** → ADR-001 (hardware-software separation) + ADR-002 (capped buffers) + ADR-003 (microservice isolation)
- **QR-003 (Testability)** → ADR-003 (microservice decomposition with independent testing)

#### 5. Evolution and Future Decisions

As the platform evolves, new architectural decisions will be documented as additional ADRs. For example:
- **ADR-004** (proposed): Horizontal scaling of WebSocket Service via Redis Pub/Sub sharding
- **ADR-005** (proposed): Migration to Kubernetes for multi-node deployment
- **ADR-006** (proposed): Implementation of mTLS for CN → CnSS authentication

Each new ADR will reference existing decisions and quality requirements, maintaining a complete architectural narrative.

### ADR Lifecycle

ADRs follow a simple lifecycle:

1. **Proposed**: Decision is under discussion; not yet implemented
2. **Accepted**: Decision is implemented and validated in production
3. **Deprecated**: Decision is superseded by a newer ADR; legacy approach still supported
4. **Superseded**: Decision is replaced by a newer ADR; legacy approach removed

Current ADRs are all in **Accepted** status, reflecting decisions implemented in MVP v1 and v2.

### Relationship to Other Documentation

- **System Architecture**: [docs/system-documentation.md](../system-documentation.md) — Detailed technical specifications
- **Static View**: [static-view/README.md](static-view/README.md) — Component structure and data flows
- **Dynamic View**: [dynamic-view/README.md](dynamic-view/README.md) — Runtime behavior and sequences
- **Deployment View**: [deployment-view/README.md](deployment-view/README.md) — Infrastructure topology
- **Quality Requirements**: [docs/quality-requirements.md](../quality-requirements.md) — Measurable quality gates