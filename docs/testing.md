# Testing and Quality Status

This document serves as the canonical testing status artifact for the Traffic Processing Platform. It details our critical modules, automated test coverage, CI/QA check status, and manual evidence.

## Critical Modules and Coverage

Critical modules are source files, packages, or product areas responsible for core user workflows, persistence, external integration, security, or business rules. Each critical module must maintain at least 30% automated line coverage.

| Critical module | Why critical | Required line coverage | Current line coverage | Evidence |
|---|---|---:|---:|---|
| `cnss/core/` + `cnss/services/` | Core backend: JWT authentication & revocation, Argon2id password validation, WebSocket session lifecycle, UDP telemetry ingestion, sequence tracking, Redis buffering, background flushing, Reporting Worker (1Hz poller, state syncer, ghost cleaner), REST API (auth, channels, health, history). Enforces all QRs. | 30% | ≥ 30% (enforced by `--cov-fail-under=30` gate against `core` and `services` packages) | [Latest CI run → CnSS Check → "Run coverage gate" step](https://github.com/SWP-47/traffic-processing-platform/actions/workflows/ci.yml) |
| `cnss/tests/integration/` | Validates end-to-end API contracts (login, refresh, logout, channels, status, history, host history, health), WebSocket subscription lifecycle, UDP ingestion pipeline, Reporting Worker aggregation, and ghost cleanup against live TimescaleDB and Redis instances. | 30% | ≥ 30% (enforced by `--cov-fail-under=30` gate) | [Latest CI run → CnSS Check → "Run coverage gate" step](https://github.com/SWP-47/traffic-processing-platform/actions/workflows/ci.yml) |
| `mui/src/services/` | Frontend: WebSocket client (`websocket.ts`), REST API client (authentication, channels, health, history), and subscription manager (`subscriptionManager.ts`). Bridges MUI to CnSS. | 30% | N/A — frontend coverage gate not yet configured; type-safety enforced via `tsc --noEmit` | [Latest CI run → MUI Check → "Lint and type check" step](https://github.com/SWP-47/traffic-processing-platform/actions/workflows/ci.yml) |
| `traffic-processor/software-part/` | Core packet extraction logic (`tp_packet_counter.py`) that sniffs network interfaces and produces the per-packet JSON telemetry consumed by the Communication Node. | 30% | N/A — unit tests exist but no coverage gate is configured yet | [Latest CI run → TP Check → "Run unit tests" step](https://github.com/SWP-47/traffic-processing-platform/actions/workflows/ci.yml) |

*If global repository coverage is lower than critical-module coverage, explain why here: N/A — The CnSS backend (the most critical module) is the only component with a hard coverage gate (`--cov-fail-under=30`). Frontend and TP coverage gates are deferred to a future sprint to avoid blocking MVP delivery.*

## Automated Test Status

The CnSS test suite currently collects **253 tests** across three tiers: unit (17 modules), integration (5 modules), and end-to-end (1 stub module).

### Unit Tests (17 modules, `cnss/tests/unit/`)

| Test module | What it tests |
|---|---|
| `test_buffer_manager.py` | Redis capped-list buffering: empty-batch skip, serialization, cap enforcement, OOM protection, error wrapping |
| `test_db.py` | All `core/db.py` query helpers: user fetch, channel upsert, history queries, host data, telemetry aggregation |
| `test_flusher.py` | Background flusher: channel registration, Redis-to-TimescaleDB flush, protocol field extraction, error recovery |
| `test_gc.py` | WebSocket garbage collector: stale-listener cleanup, empty-set pruning, multi-subscription teardown |
| `test_logging.py` | Token masking filter: `?token=` URL redaction, format coercion, logging patch |
| `test_pubsub_consumer.py` | Pub/Sub consumer: pattern subscription, `sub_id` injection, client routing, malformed-JSON handling |
| `test_query_builder.py` | SQL query builder: parameterized tracker, ORDER BY whitelist, LIMIT/OFFSET, WHERE clauses, time window |
| `test_query_hash.py` | SHA-256 subscription deduplication: determinism, `id` exclusion, key-order independence, hex encoding |
| `test_reporting_poller.py` | 1Hz poller: active-hash discovery, listener check, handler dispatch, Pub/Sub publish |
| `test_sequence_tracker.py` | Sequence tracking: initial baseline, sequential, drop calculation, out-of-order ignore, reset detection |
| `test_session.py` | WebSocket session: Redis TTL creation, heartbeat refresh, destruction, expiration |
| `test_state_manager.py` | Redis state manager: HSET activity, dropped-delta HINCRBY, TTL, empty-batch skip |
| `test_subscription.py` | Subscription manager: registry creation, listener sets, unsubscribe, last-listener cleanup |
| `test_telemetry_handler.py` | Telemetry SQL handler: protocol-aware aggregation, multi-protocol rate calculation |
| `test_udp_server.py` | UDP server: transport start/stop, MTU warn-only, JSON/Pydantic validation, pipeline handoff |
| `test_ws_auth.py` | WebSocket auth: viewer/admin success, `4001`/`4002`/`4003` close codes, revoked token rejection |
| `test_ws_server.py` | WebSocket server: subscribe/unsubscribe message dispatch, channel mismatch rejection, heartbeat loop |

### Integration Tests (5 modules, `cnss/tests/integration/`)

| Test module | What it tests |
|---|---|
| `test_api.py` | REST API against live DB/Redis: login (viewer & admin), token refresh, logout, channel scope filtering, channel status access control, channel history pagination, host history, health endpoint (healthy/unhealthy/Redis-down) |
| `test_ingestion_pipeline.py` | Full ingestion pipeline: sequence baseline, sequential no-drops, gap-drops, out-of-order ignore, reset detection, activity tracking, TTL, capped-list enforcement, flusher atomic pop-and-insert, multi-channel independence |
| `test_reporting.py` | Reporting Worker: channel state syncer (active upsert, mass timeout deactivation), ghost cleaner (stale-listener removal), Poller for all 5 subscription targets (`telemetry`, `hosts_table`, `host_details`, `host_top_destinations`, `host_top_ports`), multi-protocol telemetry aggregation |
| `test_ws_subscription.py` | WebSocket subscription engine: session TTL, heartbeat, destruction, registry/listener creation, `id` exclusion from hash, unsubscribe, GC on disconnect, Pub/Sub routing with `sub_id` injection, parallel subscriptions, `sub:active_hashes` lifecycle |
| `test_ghost_cleanup.py`, `test_auth_flow.py` | Stub/empty — reserved for future ghost-cleanup and full auth-flow E2E tests |

### E2E Tests (1 stub, `cnss/tests/e2e/`)

| Test module | What it tests |
|---|---|
| `test_full_pipeline.py` | Stub — reserved for full TP → CN → CnSS → MUI pipeline E2E tests |

| Test type | Scope | Command or CI check | Latest result | Evidence |
|---|---|---|---|---|
| Unit tests | CnSS backend logic (buffer, DB, flusher, GC, logging, pub/sub, query builder, query hash, poller, sequence tracker, session, state manager, subscription, telemetry handler, UDP server, WS auth, WS server) | `uv run pytest tests/unit/ -q` | Passing | [Latest CI run → CnSS Check](https://github.com/SWP-47/traffic-processing-platform/actions/workflows/ci.yml) |
| Unit tests | Traffic Processor packet extraction logic | `pytest tests/ -q` (from `traffic-processor/software-part/`) | Passing | [Latest CI run → TP Check](https://github.com/SWP-47/traffic-processing-platform/actions/workflows/ci.yml) |
| Integration tests | CnSS REST API (auth login/refresh/logout, channels, status, history, health), WebSocket subscription lifecycle, UDP ingestion pipeline, Reporting Worker, ghost cleanup against live TimescaleDB and Redis | `uv run pytest tests/integration/ -q` | Passing | [Latest CI run → CnSS Check](https://github.com/SWP-47/traffic-processing-platform/actions/workflows/ci.yml) |
| Automated QRTs | QR-001 (health API responsiveness), QR-002 (JWT scope enforcement), QR-003 (critical module coverage) | `uv run pytest --cov=core --cov=services --cov-report=term-missing --cov-fail-under=30 tests/ -q` | Passing | [Latest CI run → CnSS Check → "Run coverage gate" step](https://github.com/SWP-47/traffic-processing-platform/actions/workflows/ci.yml) |
| Type checking | MUI frontend type safety (`tsc --noEmit`) and ESLint | `npm run lint && npm run test:ts` | Passing | [Latest CI run → MUI Check → "Lint and type check" step](https://github.com/SWP-47/traffic-processing-platform/actions/workflows/ci.yml) |

## CI and QA Check Status

| Gate or check | Required for Done? | Latest protected-branch status | Evidence |
|---|---|---|---|
| Linting (Python: `black --check`, `flake8`) | Yes | Passing | [Latest CI run → TP/CN/CnSS Check → "Lint code" steps](https://github.com/SWP-47/traffic-processing-platform/actions/workflows/ci.yml) |
| Linting & type checking (CnSS: `ruff`, `flake8`, `mypy`, `black --check`) | Yes | Passing | [Latest CI run → CnSS Check → "Lint code" step](https://github.com/SWP-47/traffic-processing-platform/actions/workflows/ci.yml) |
| Linting (JS/TS: `npm run lint`) | Yes | Passing | [Latest CI run → MUI Check → "Lint and type check" step](https://github.com/SWP-47/traffic-processing-platform/actions/workflows/ci.yml) |
| Type checking (`npm run test:ts` / `tsc --noEmit`) | Yes | Passing | [Latest CI run → MUI Check → "Lint and type check" step](https://github.com/SWP-47/traffic-processing-platform/actions/workflows/ci.yml) |
| Build / Testable snapshot (`npm run build`) | Yes | Passing | [Latest CI run → MUI Check → "Build production bundle" step](https://github.com/SWP-47/traffic-processing-platform/actions/workflows/ci.yml) |
| Database migrations (`alembic upgrade head`) | Yes | Passing | [Latest CI run → CnSS Check → "Run database migrations" step](https://github.com/SWP-47/traffic-processing-platform/actions/workflows/ci.yml) |
| Coverage gate (`--cov=core --cov=services --cov-fail-under=30`) | Yes | Passing | [Latest CI run → CnSS Check → "Run coverage gate" step](https://github.com/SWP-47/traffic-processing-platform/actions/workflows/ci.yml) |
| Dependency audit (`pip-audit`) | Yes | Passing | [Latest CI run → CnSS Check → "Run dependency audit" step](https://github.com/SWP-47/traffic-processing-platform/actions/workflows/ci.yml) |
| Lychee Link Checking | Yes | Passing | [Latest Lychee run](https://github.com/SWP-47/traffic-processing-platform/actions/workflows/lychee.yml) |

**Branch Protection Evidence:**

The `develop` and `general` branches are protected. Merging requires: (1) at least one approving review from a different team member, (2) all required CI status checks passing (including Lychee), and (3) squash/rebase merging is explicitly disabled — only merge commits are permitted to preserve full history.

## Additional QA Check Rationale

Link checking (Lychee) does not satisfy the Assignment 4 additional QA check requirement. The following check was selected to address specific project risks.

| QA objective or risk | Additional QA check | Scope | Latest result | Evidence | Limitations or follow-up |
|---|---|---|---|---|---|
| Dependencies with known vulnerabilities may expose deployments to avoidable security risk, especially since the CnSS is exposed to the network and ingests untrusted UDP payloads. | Automated Python dependency vulnerability scan via `pip-audit` | CnSS `pyproject.toml` (compiled via `uv pip compile --all-extras`, covering all transitive packages) | Passing | [Latest CI run → CnSS Check → "Run dependency audit" step](https://github.com/SWP-47/traffic-processing-platform/actions/workflows/ci.yml) | `pip-audit` only covers Python dependencies. Frontend (`npm audit`) and OS-level vulnerabilities are not yet scanned in CI and should be added in a future sprint. |

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
- [ ] Critical modules must maintain ≥ 30% line coverage (measured against `core` and `services` packages).
- [ ] Linting, formatting, and type-checking gates must pass (Ruff, Flake8, Mypy, Black for CnSS; ESLint + tsc for MUI).
- [ ] Additional QA check (`pip-audit` dependency vulnerability scan) must pass.
- [ ] Lychee link checking must pass.
