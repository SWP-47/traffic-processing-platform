# Quality Requirements

This document defines the architectural quality requirements for the Traffic Processing Platform and preserves the maintained Assignment 4 quality gates for later work.

*Last updated: July 12, 2026*

---

## QR-001: CnSS health API responsiveness

**ISO/IEC 25010 sub-characteristic:** Time behaviour

**Scenario:** When a monitoring client requests `GET /api/v1/health` with a valid Bearer token under a normal production-like load, the CnSS shall respond with `200 OK`, a `status` of `"healthy"`, a `components.cnss` value of `"active"`, and a `timestamp` field within 1 second.

**Why this matters:** Operators and automated monitors rely on fast, reliable health checks to detect service degradation quickly. A slow or inconsistent health endpoint delays incident response and obscures whether the traffic monitoring system is available.

**Linked quality requirement tests:** [QRT-001](quality-requirement-tests.md#qrt-001-cnss-health-api-responsiveness)

---

## QR-002: CnSS access control confidentiality

**ISO/IEC 25010 sub-characteristic:** Confidentiality

**Scenario:** When a user presents a JWT access token for authenticated REST endpoints (`GET /api/v1/channels`, `GET /api/v1/channel/{channel_id}/status`, `GET /api/v1/channel/{channel_id}/history`) or establishes a WebSocket connection, the CnSS shall:
- Validate the JWT signature and expiration (HS256).
- Check the token's `jti` against the `jwt:revoked` Redis set on every request.
- Enforce channel scope from the token's `scope` claim (`viewer` role is restricted to listed channels; `admin` has unrestricted access).
- Return `401 Unauthorized` for invalid, expired, or revoked tokens, or `403 Forbidden` for valid tokens lacking scope.
- Close WebSocket connections with code `4001` (invalid token) or `4003` (channel forbidden) on scope violations.

**Why this matters:** The platform carries channel-specific telemetry and network monitoring data. Unauthorized access would expose sensitive infrastructure details and violate operator trust. Immediate token revocation (via `jwt:revoked` Redis set) is critical for responding to compromised sessions.

**Linked quality requirement tests:** [QRT-002](quality-requirement-tests.md#qrt-002-jwt-scope-enforcement)

---

## QR-003: Critical module testability and coverage

**ISO/IEC 25010 sub-characteristic:** Testability

**Scenario:** When a developer changes a critical backend module under the standard CI environment, the CnSS codebase (`core/` and `services/` packages) shall be covered by automated tests and the backend test suite shall enforce at least 30% line coverage.

**Why this matters:** Critical backend components such as authentication, telemetry ingestion, sequence tracking, WebSocket subscription lifecycle, and Reporting Worker aggregation must be directly verifiable so defects are detected before merge and deployment. The 253-test suite spanning unit and integration tiers provides layered verification of the system.

**Linked quality requirement tests:** [QRT-003](quality-requirement-tests.md#qrt-003-critical-module-unit-coverage)

---

## Architectural Decision Records (ADRs)

Each quality requirement is supported by specific architectural decisions documented in the ADRs below:

### QR-001: CnSS Health API Responsiveness (Time Behaviour)

**Related ADRs:**
- [ADR-001: Hardware-Software Separation](architecture/adr/adr-001-hardware-software-separation.md) — FPGA provides wire-speed packet forwarding, ensuring monitoring doesn't introduce latency
- [ADR-002: Ephemeral Redis Buffering](architecture/adr/adr-002-ephemeral-redis-buffering.md) — Redis in-memory buffering minimizes ingestion latency; health endpoint reads directly from `channels` table (no heavy aggregation queries)
- [ADR-003: Microservice Decomposition](architecture/adr/adr-003-microservice-decomposition.md) — Independent REST API service container allows optimization without affecting other workers

### QR-002: CnSS Access Control Confidentiality

**Related ADRs:**
- [ADR-001: Hardware-Software Separation](architecture/adr/adr-001-hardware-software-separation.md) — Complete fault isolation between data plane (FPGA) and control plane (software); monitoring does not affect core forwarding
- [ADR-002: Ephemeral Redis Buffering](architecture/adr/adr-002-ephemeral-redis-buffering.md) — `jwt:revoked` set stored in Redis enables sub-millisecond token revocation checks on every request
- [ADR-003: Microservice Decomposition](architecture/adr/adr-003-microservice-decomposition.md) — Auth middleware applied consistently across the REST API service; WebSocket service enforces independent JWT validation at connection time

### QR-003: Critical Module Testability

**Related ADRs:**
- [ADR-003: Microservice Decomposition](architecture/adr/adr-003-microservice-decomposition.md) — Each microservice tested independently with mocked or real dependencies; ≥30% coverage enforced against `core` and `services` packages via `--cov-fail-under=30` gate

---

## ADR Index

| ADR ID | Title | Status | Quality Requirements |
|--------|-------|--------|---------------------|
| [ADR-001](architecture/adr/adr-001-hardware-software-separation.md) | Hardware-Software Separation for Zero-Impact Monitoring | Accepted | QR-001, QR-002 |
| [ADR-002](architecture/adr/adr-002-ephemeral-redis-buffering.md) | Ephemeral Redis Buffering for High-Performance Telemetry Ingestion | Accepted | QR-001, QR-002 |
| [ADR-003](architecture/adr/adr-003-microservice-decomposition.md) | Microservice Decomposition of CnSS Backend | Accepted | QR-001, QR-002, QR-003 |
