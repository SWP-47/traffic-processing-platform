# Quality Requirements

This document defines the architectural quality requirements for the Traffic Processing Platform and preserves the maintained Assignment 4 quality gates for later work.

*Last updated: June 27, 2026*

---

## QR-001: CnSS health API responsiveness

**ISO/IEC 25010 sub-characteristic:** Time behaviour

**Scenario:** When a monitoring client requests `/api/v1/health` under a normal production-like load, the CnSS shall respond with `200 OK`, valid health metrics, and a `components.cnss` value of `active` within 1 second.

**Why this matters:** Operators and automated monitors rely on fast, reliable health checks to detect service degradation quickly. A slow or inconsistent health endpoint delays incident response and obscures whether the traffic monitoring system is available.

**Linked quality requirement tests:** [QRT-001](quality-requirement-tests.md#qrt-001-cnss-health-api-responsiveness)

---

## QR-002: CnSS access control confidentiality

**ISO/IEC 25010 sub-characteristic:** Confidentiality

**Scenario:** When a user presents a JWT access token for `GET /api/v1/channels` or an authenticated WebSocket connection, the CnSS shall validate the token, enforce channel scope from the token, and return only authorized channel listings or fail with `401 Unauthorized` / `403 Forbidden`.

**Why this matters:** The platform carries channel-specific telemetry and network monitoring data. Unauthorized access would expose sensitive infrastructure details and violate operator trust.

**Linked quality requirement tests:** [QRT-002](quality-requirement-tests.md#qrt-002-jwt-scope-enforcement)

---

## QR-003: Critical module testability and coverage

**ISO/IEC 25010 sub-characteristic:** Testability

**Scenario:** When a developer changes a critical backend module under the standard CI environment, the CnSS codebase shall be covered by automated tests and the backend test suite shall enforce at least 30% line coverage for the critical module surface.

**Why this matters:** Critical backend components such as authentication, telemetry ingestion, and channel state management must be directly verifiable so defects are detected before merge and deployment.

**Linked quality requirement tests:** [QRT-003](quality-requirement-tests.md#qrt-003-critical-module-unit-coverage)

## Architectural Decision Records (ADRs)

Each quality requirement is supported by specific architectural decisions documented in the ADRs below:

### QR-001: CnSS Health API Responsiveness (Time Behaviour)

**Related ADRs:**
- [ADR-001: Hardware-Software Separation](architecture/adr/adr-001-hardware-software-separation.md) — FPGA provides wire-speed packet forwarding, ensuring monitoring doesn't introduce latency
- [ADR-002: Ephemeral Redis Buffering](architecture/adr/adr-002-ephemeral-redis-buffering.md) — Redis in-memory buffering minimizes ingestion latency and maximizes throughput
- [ADR-003: Microservice Decomposition](architecture/adr/adr-003-microservice-decomposition.md) — Independent scaling allows optimization of bottleneck components

### QR-002: Fault Tolerance

**Related ADRs:**
- [ADR-001: Hardware-Software Separation](architecture/adr/adr-001-hardware-software-separation.md) — Complete fault isolation between data plane (FPGA) and control plane (software)
- [ADR-002: Ephemeral Redis Buffering](architecture/adr/adr-002-ephemeral-redis-buffering.md) — Capped buffers prevent OOM crashes; graceful degradation on Redis failure
- [ADR-003: Microservice Decomposition](architecture/adr/adr-003-microservice-decomposition.md) — Fault isolation between microservices; Docker restart policy ensures automatic recovery

### QR-003: Critical Module Testability

**Related ADRs:**
- [ADR-003: Microservice Decomposition](architecture/adr/adr-003-microservice-decomposition.md) — Each microservice tested independently with mocked dependencies; ≥30% coverage enforced per critical module

---

## ADR Index

| ADR ID | Title | Status | Quality Requirements |
|--------|-------|--------|---------------------|
| [ADR-001](architecture/adr/adr-001-hardware-software-separation.md) | Hardware-Software Separation for Zero-Impact Monitoring | Accepted | QR-001, QR-002 |
| [ADR-002](architecture/adr/adr-002-ephemeral-redis-buffering.md) | Ephemeral Redis Buffering for High-Performance Telemetry Ingestion | Accepted | QR-001, QR-002 |
| [ADR-003](architecture/adr/adr-003-microservice-decomposition.md) | Microservice Decomposition of CnSS Backend | Accepted | QR-001, QR-002, QR-003 |
