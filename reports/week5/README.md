# Assignment 5 Report

## Architecture Description

The Traffic Processing Platform follows a four-component architecture — a transparent inline **traffic-processor** for zero-impact packet counting, a **communication-node** for local data forwarding, a microservice-decomposed **CnSS backend** for telemetry aggregation via REST/WebSocket, and a **MUI frontend** for real-time visualization. This design, shaped by three key Architectural Decision Records (ADR-001 through ADR-003), supports the current product by ensuring wire-speed packet forwarding with no network degradation, high-throughput ephemeral Redis buffering for telemetry ingestion, and independent service scaling and deployment.

## Quality Requirements and Architectural Decisions

Each quality requirement directly drives specific architectural decisions: **QR-001 (Time Behaviour)** is satisfied by ADR-001's FPGA wire-speed forwarding and ADR-002's Redis ephemeral buffering to minimize latency; **QR-002 (Fault Tolerance)** is addressed through ADR-001's hardware-software separation, ADR-002's capped buffers, and ADR-003's microservice isolation to prevent cascading failures. **QR-003 (Testability)** is fulfilled by ADR-003's microservice decomposition, enabling independent unit testing and CI/CD verification of each backend component before deployment.

## Documentation Links

* **Roadmap**: [docs/roadmap.md](../../docs/roadmap.md)
* **Development Process & Git Workflow**: [docs/development-process.md](../../docs/development-process.md)
* **Definition of Done**: [docs/definition-of-done.md](../../docs/definition-of-done.md)
* **Quality Requirements**: [docs/quality-requirements.md](../../docs/process-requirements.md)
* **Hosted Documentation Site**: [https://swp-47.github.io/traffic-processing-platform/](https://swp-47.github.io/traffic-processing-platform/)
* **System Documentation**: [docs/system-documentation.md](../../docs/system-documentation.md)
* **API Documentation**: [api/README.md](../../api/README.md)
* **Architecture Documentation**: [docs/architecture/README.md](../../docs/architecture/README.md)
* **Development Process**: [docs/development-process.md](../../docs/development-process.md)
* **Hosted Documentation Site**: [https://swp-47.github.io/traffic-processing-platform/](https://swp-47.github.io/traffic-processing-platform/)
