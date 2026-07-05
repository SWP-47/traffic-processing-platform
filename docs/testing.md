# Testing and Quality Status

This document serves as the canonical testing status artifact for the Traffic Processing Platform. It details our critical modules, automated test coverage, CI/QA check status, and manual evidence.

## Critical Modules and Coverage

Critical modules are source files, packages, or product areas responsible for core user workflows, persistence, external integration, security, or business rules. Each critical module must maintain at least 30% automated line coverage.

| Critical module | Why critical | Required line coverage | Current line coverage | Evidence |
|---|---|---:|---:|---|
| `cnss/app/` | Core telemetry ingestion (UDP server), JWT authentication, WebSocket state management, TimescaleDB persistence, and Reporting Worker. Enforces all QRs. | 30% | ≥ 30% (enforced by `--cov-fail-under=30` gate) | [Latest CI run → CnSS Check → "Run coverage gate" step](https://github.com/SWP-47/traffic-processing-platform/actions/workflows/ci.yml) |
| `cnss/tests/integration/` | Validates end-to-end API contracts, WebSocket lifecycle, auth middleware, and UDP ingestion against a real TimescaleDB instance. | 30% | ≥ 30% (enforced by `--cov-fail-under=30` gate) | [Latest CI run → CnSS Check → "Run coverage gate" step](https://github.com/SWP-47/traffic-processing-platform/actions/workflows/ci.yml) |
| `mui/src/services/` | Frontend API client, WebSocket telemetry service, and authentication state management. Bridges the MUI to the CnSS. | 30% | N/A — frontend coverage gate not yet configured; type-safety enforced via `tsc --noEmit` | [Latest CI run → MUI Check → "Lint and type check" step](https://github.com/SWP-47/traffic-processing-platform/actions/workflows/ci.yml) |
| `traffic-processor/software-part/` | Core packet extraction logic (`tp_packet_counter.py`) that produces the telemetry consumed by every downstream component. | 30% | N/A — unit tests exist but no coverage gate is configured yet | [Latest CI run → TP Check → "Run unit tests" step](https://github.com/SWP-47/traffic-processing-platform/actions/workflows/ci.yml) |

*If global repository coverage is lower than critical-module coverage, explain why here: N/A — The CnSS backend (the most critical module) is the only component with a hard coverage gate (`--cov-fail-under=30`). Frontend and TP coverage gates are deferred to a future sprint to avoid blocking MVP delivery.*

## Automated Test Status

| Test type | Scope | Command or CI check | Latest result | Evidence |
|---|---|---|---|---|
| Unit tests | Critical backend logic (auth, state store, UDP parsing, recovery) | `pytest cnss/tests/unit/ -q` (executed as part of the containerized integration run) | Passing | [Latest CI run → CnSS Check](https://github.com/SWP-47/traffic-processing-platform/actions/workflows/ci.yml) |
| Unit tests | Traffic Processor packet extraction logic | `pytest traffic-processor/software-part/tests/ -q` | Passing | [Latest CI run → TP Check](https://github.com/SWP-47/traffic-processing-platform/actions/workflows/ci.yml) |
| Integration tests | CnSS REST API endpoints, WebSocket lifecycle, auth middleware, UDP ingestion, and TimescaleDB interaction | `docker compose -f cnss/docker-compose.test.yml up --build --abort-on-container-exit` | Passing | [Latest CI run → CnSS Check → "Run containerized CnSS integration tests" step](https://github.com/SWP-47/traffic-processing-platform/actions/workflows/ci.yml) |
| Automated QRTs | QR-001 (health API responsiveness), QR-002 (JWT scope enforcement), QR-003 (critical module coverage) | `pytest --cov=app --cov-report=term-missing --cov-fail-under=30 tests/ -q` (coverage gate doubles as QRT-003; QRT-001 and QRT-002 are covered by the integration suite) | Passing | [Latest CI run → CnSS Check → "Run coverage gate" step](https://github.com/SWP-47/traffic-processing-platform/actions/workflows/ci.yml) |
| Type checking | MUI frontend type safety (`tsc --noEmit`) and OpenAPI schema validation | `npm run test:ts` | Passing | [Latest CI run → MUI Check → "Lint and type check" step](https://github.com/SWP-47/traffic-processing-platform/actions/workflows/ci.yml) |

## CI and QA Check Status

| Gate or check | Required for Done? | Latest protected-branch status | Evidence |
|---|---|---|---|
| Linting (Python: `black --check`, `flake8`) | Yes | Passing | [Latest CI run → TP/CN/CnSS Check → "Lint code" steps](https://github.com/SWP-47/traffic-processing-platform/actions/workflows/ci.yml) |
| Linting (JS/TS: `npm run lint`) | Yes | Passing | [Latest CI run → MUI Check → "Lint and type check" step](https://github.com/SWP-47/traffic-processing-platform/actions/workflows/ci.yml) |
| Type checking (`tsc --noEmit`) | Yes | Passing | [Latest CI run → MUI Check → "Lint and type check" step](https://github.com/SWP-47/traffic-processing-platform/actions/workflows/ci.yml) |
| Build / Testable snapshot (`npm run build`) | Yes | Passing | [Latest CI run → MUI Check → "Build production bundle" step](https://github.com/SWP-47/traffic-processing-platform/actions/workflows/ci.yml) |
| Coverage gate (`--cov-fail-under=30`) | Yes | Passing | [Latest CI run → CnSS Check → "Run coverage gate" step](https://github.com/SWP-47/traffic-processing-platform/actions/workflows/ci.yml) |
| Dependency audit (`pip-audit`) | Yes | Passing | [Latest CI run → CnSS Check → "Run dependency audit" step](https://github.com/SWP-47/traffic-processing-platform/actions/workflows/ci.yml) |
| Lychee Link Checking | Yes | Passing | [Latest Lychee run](https://github.com/SWP-47/traffic-processing-platform/actions/workflows/lychee.yml) |

**Branch Protection Evidence:**

The `develop` and `general` branches are protected. Merging requires: (1) at least one approving review from a different team member, (2) all required CI status checks passing (including Lychee), and (3) squash/rebase merging is explicitly disabled — only merge commits are permitted to preserve full history.

## Additional QA Check Rationale

Link checking (Lychee) does not satisfy the Assignment 4 additional QA check requirement. The following check was selected to address specific project risks.

| QA objective or risk | Additional QA check | Scope | Latest result | Evidence | Limitations or follow-up |
|---|---|---|---|---|---|
| Dependencies with known vulnerabilities may expose deployments to avoidable security risk, especially since the CnSS is exposed to the network and ingests untrusted UDP payloads. | Automated Python dependency vulnerability scan via `pip-audit` | CnSS `requirements.txt` (and transitively all installed packages) | Passing | [Latest CI run → CnSS Check → "Run dependency audit" step](https://github.com/SWP-47/traffic-processing-platform/actions/workflows/ci.yml) | `pip-audit` only covers Python dependencies. Frontend (`npm audit`) and OS-level (`apt`) vulnerabilities are not yet scanned in CI and should be added in a future sprint. Some transitive vulnerabilities may require manual triage or delayed upstream fixes. |

## Manual Evidence That Does Not Count as QRT

Manual tests, observations, or exploratory checks that do not qualify as automated Quality Requirement Tests (QRTs).

| Evidence | Scope | Result | Follow-up PBI or issue |
|---|---|---|---|
| End-to-end smoke test of the deployment (TP → CN → CnSS → MUI) on the Innopolis University testbed | Full telemetry pipeline | Passed — real-time packet counters and channel activity indicator update correctly | [None] |
| Manual verification of the FPGA bitstream deployment on the ARTIX-7 AX7201 board | TP hardware data plane | Passed — packets forwarded at wire speed with no observable latency | [None] |
| Exploratory UI check of the MUI dashboard on desktop and mobile viewports | MUI Dashboard responsiveness | Passed with minor feedback — customer requested higher contrast on the activity indicator | [#145 — Increase contrast on StatusIndicator component](https://github.com/SWP-47/traffic-processing-platform/issues/145) |

## Active Quality Gates for Future Sprints

The following Assignment 4 quality gates, tests, and CI checks are maintained as active repository requirements for all future project work. Later PBIs must satisfy these gates unless explicitly superseded by a documented equivalent or stronger check.

- [ ] All automated unit and integration tests must pass.
- [ ] Automated Quality Requirement Tests (QRT-001, QRT-002, QRT-003) must pass.
- [ ] Critical modules must maintain ≥ 30% line coverage.
- [ ] Linting, formatting, and type-checking gates must pass.
- [ ] Additional QA check (`pip-audit` dependency vulnerability scan) must pass.
- [ ] Lychee link checking must pass.
